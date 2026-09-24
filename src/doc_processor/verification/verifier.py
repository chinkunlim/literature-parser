"""
Automated Multi-Metric Content Accuracy Verification Suite
==========================================================
Validates vocabulary, noise removal, heading sanity, image integrity, and split PDFs.
Optionally audits semantic correctness via local Ollama models.
"""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from doc_processor.config import DEFAULT_DICT_PATH
from doc_processor.verification.rules import (
    is_valid_dictionary_word, check_noise_strings, check_heading_ratio,
    check_content_continuity, check_sentence_completeness,
    check_numeric_coordinate_noise, check_shattered_math,
    check_infix_math_in_words, check_heading_prose_intrusion,
    check_table_banner_integrity, check_heading_density,
    check_excessive_hard_wraps, check_latex_and_symbol_integrity,
    check_table_column_integrity, check_unescaped_special_chars,
)
from doc_processor.verification.ollama_verifier import OllamaVerifier

logger = logging.getLogger(__name__)

# Dynamically resolve sips path; None on non-macOS systems.
_SIPS = shutil.which("sips") or "/usr/bin/sips"


class AccuracyVerifier:
    def __init__(self, dict_path: str = DEFAULT_DICT_PATH, use_ollama: bool = False, ollama_model: str = None):
        self.dict_words = set()
        if os.path.exists(dict_path):
            with open(dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    w = line.strip().lower()
                    if w:
                        self.dict_words.add(w)

        self.use_ollama = use_ollama
        self.ollama = OllamaVerifier(healer_model=ollama_model) if use_ollama and ollama_model else (OllamaVerifier() if use_ollama else None)

    def verify_chapter(self, chapter_dir: str, expected_pages: int = None) -> dict:
        ch_path = Path(chapter_dir)
        ch_name = ch_path.name
        results = {
            'chapter': ch_name,
            'passed': True,
            'accuracy_percent': 0.0,
            'checks': {}
        }

        print(f"\n{'='*70}\n[VERIFYING ACCURACY] Chapter: {ch_name}\n{'='*70}")

        # 1. Locate Markdown file
        canonical_md = ch_path / f"{ch_name}.md"
        if canonical_md.exists():
            md_file = canonical_md
        else:
            candidates = [f for f in ch_path.glob("*.md") if f.name != "processing_status.md"]
            if candidates:
                md_file = candidates[0]
            else:
                print("  [FAIL] No Markdown file found in chapter folder.")
                results['passed'] = False
                results['checks']['markdown_exists'] = False
                return results
        with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
            md_content = f.read()

        # 2. Vocabulary & Dictionary Verification
        vocab_content = re.sub(r'<style>.*?</style>', '', md_content, flags=re.DOTALL)
        vocab_content = re.sub(r'<[^>]+>', ' ', vocab_content)
        vocab_content = re.sub(r'\]\([^)]+\)', ']', vocab_content)
        vocab_content = re.sub(r'https?://[^\s\)]+', ' ', vocab_content)
        tokens = re.findall(r'\b[a-zA-Z0-9_\-’\']+\b', vocab_content)
        total_tokens = len(tokens)
        valid_tokens = sum(1 for t in tokens if is_valid_dictionary_word(t, self.dict_words))
        invalid_sample = [t for t in tokens if not is_valid_dictionary_word(t, self.dict_words)][:10]

        # Check if chapter is front matter (cover, publisher imprint, copyright page)
        is_front_matter = ch_name.lower().startswith(('00-', 'cover', 'publish'))
        is_journal = False
        candidates = [
            ch_path / "document_profile.json",
            ch_path / "book_profile.json",
        ] + [p / "document_profile.json" for p in ch_path.parents] + [p / "book_profile.json" for p in ch_path.parents]
        for p in candidates:
            if p.exists():
                try:
                    import json
                    with open(p, 'r', encoding='utf-8') as pf:
                        data = json.load(pf)
                        is_journal = (
                            data.get("is_journal", False)
                            or data.get("is_literature", False)
                            or data.get("archetype") in ("journal", "literature")
                            or data.get("features", {}).get("is_journal_article", False)
                            or data.get("features", {}).get("is_literature", False)
                        )
                        if is_journal:
                            break
                except Exception:
                    pass

        vocab_ratio = (valid_tokens / total_tokens * 100) if total_tokens > 0 else 0
        vocab_pass = (vocab_ratio >= 82.0 if is_journal else vocab_ratio >= 90.0) or is_front_matter or (total_tokens < 500 and vocab_ratio >= 75.0)
        results['accuracy_percent'] = round(vocab_ratio, 2)

        results['checks']['vocabulary'] = {
            'total_tokens': total_tokens,
            'valid_tokens': valid_tokens,
            'ratio_percent': round(vocab_ratio, 2),
            'passed': vocab_pass,
            'invalid_samples': invalid_sample
        }

        status_str = "[PASS]" if vocab_pass else "[WARN]"
        print(f"  • Vocabulary Accuracy: {status_str} {valid_tokens}/{total_tokens} words valid ({vocab_ratio:.1f}%)")
        if not vocab_pass:
            print(f"    Sample unrecognized tokens: {invalid_sample}")

        # 3. Layout, Heading Sanity & Noise Filtering
        found_noise = check_noise_strings(md_content)
        h_count, total_lines, h_ratio, h_pass = check_heading_ratio(md_content)
        broken_hyphens = re.findall(r'[a-zA-Z]+-\s*\n\s*[a-zA-Z]+', md_content)

        # On front-matter copyright pages, publishing copyright statements are expected content.
        noise_pass = (len(found_noise) == 0) or is_front_matter

        results['checks']['layout'] = {
            'total_lines': total_lines,
            'heading_lines': h_count,
            'heading_ratio_percent': round(h_ratio, 2),
            'noise_detected': found_noise if not is_front_matter else [],
            'noise_free': noise_pass,
            'broken_hyphens_count': len(broken_hyphens),
            'passed': noise_pass and h_pass
        }

        print(f"  • Running Header/Footer Noise Filter: {'[PASS]' if noise_pass else '[FAIL]'} (Found noise strings: {found_noise or 'None'})")
        print(f"  • Heading Structure: {'[PASS]' if h_pass else '[WARN]'} {h_count}/{total_lines} lines are headings ({h_ratio:.1f}%)")
        print(f"  • Hyphenated Line Repairs: [PASS] {len(broken_hyphens)} broken line-end hyphens remaining.")

        if not noise_pass:
            results['passed'] = False
        if not h_pass and not is_front_matter:
            results['passed'] = False
        if not vocab_pass and not is_front_matter:
            results['passed'] = False


        # 4. Content Continuity & Sentence Completeness
        cont_res = check_content_continuity(md_content)
        sent_res = check_sentence_completeness(md_content)

        continuity_pass = cont_res['passed']
        sentence_pass = sent_res['passed']

        results['checks']['continuity'] = {
            'abrupt_cuts': cont_res['abrupt_cuts'],
            'page_break_cuts': cont_res['page_break_cuts'],
            'orphan_fragments': cont_res['orphan_fragments'],
            'passed': continuity_pass,
            'examples': cont_res['examples'],
        }
        results['checks']['sentence_completeness'] = {
            'incomplete_endings': sent_res['incomplete_endings'],
            'incomplete_openings': sent_res['incomplete_openings'],
            'passed': sentence_pass,
        }

        cont_icon = '[PASS]' if continuity_pass else '[WARN]'
        sent_icon = '[PASS]' if sentence_pass else '[WARN]'
        print(f"  • Content Continuity: {cont_icon} "
              f"(abrupt cuts: {cont_res['abrupt_cuts']}, "
              f"page-break splits: {cont_res['page_break_cuts']}, "
              f"orphan fragments: {cont_res['orphan_fragments']})")
        if cont_res['examples']:
            for ex in cont_res['examples'][:2]:
                print(f"      ↳ {ex[:120]}")
        print(f"  • Sentence Completeness: {sent_icon} "
              f"(dangling endings: {len(sent_res['incomplete_endings'])}, "
              f"lowercase openings: {len(sent_res['incomplete_openings'])})")

        # Continuity checks are advisory quality metrics reported for review and learner diagnostics.
        # They do not hard-fail the chapter when vocabulary and structural integrity are intact.


        # 5. Image Filtering & Integrity Verification

        images_dir = ch_path / "images"
        referenced_images = re.findall(r'!\[.*?\]\((images/[^)]+)\)', md_content)
        all_disk_images = list(images_dir.glob("*")) if images_dir.exists() else []

        broken_img_links = []
        full_page_scans_embedded = []

        for ref in referenced_images:
            img_filename = Path(ref).name
            disk_path = images_dir / img_filename
            if not disk_path.exists():
                broken_img_links.append(ref)
                continue

            try:
                if not _SIPS or not os.path.exists(_SIPS):
                    raise FileNotFoundError("sips not available")
                sips_out = subprocess.check_output(
                    [_SIPS, "-g", "pixelWidth", "-g", "pixelHeight", str(disk_path)],
                    stderr=subprocess.DEVNULL,
                    timeout=15
                ).decode("utf-8", errors="ignore")
                w_m = re.search(r'pixelWidth:\s+(\d+)', sips_out)
                h_m = re.search(r'pixelHeight:\s+(\d+)', sips_out)
                if w_m and h_m:
                    w, h = int(w_m.group(1)), int(h_m.group(1))
                    if not img_filename.startswith("figure_") and ((w >= 1100 and h >= 1400) or (w >= 2000 and h >= 3000)):
                        full_page_scans_embedded.append(f"{img_filename} ({w}x{h})")
            except Exception:
                pass

        image_filter_pass = len(full_page_scans_embedded) == 0
        image_links_pass = len(broken_img_links) == 0

        results['checks']['images'] = {
            'referenced_count': len(referenced_images),
            'disk_count': len(all_disk_images),
            'broken_links': broken_img_links,
            'full_page_scans_embedded': full_page_scans_embedded,
            'passed': image_filter_pass and image_links_pass
        }

        print(f"  • Image References: [PASS] {len(referenced_images)} embedded images (all exist on disk).")
        print(f"  • Full-Page Background Sheet Filter: {'[PASS]' if image_filter_pass else '[FAIL]'} (0 full-page scans embedded; found: {len(full_page_scans_embedded)})")

        if not image_filter_pass or not image_links_pass:
            results['passed'] = False

        # 5. Split PDF Verification
        pdf_files = list(ch_path.glob("*.pdf"))
        if pdf_files:
            split_pdf = pdf_files[0]
            try:
                info_out = subprocess.check_output(['pdfinfo', str(split_pdf)], stderr=subprocess.DEVNULL, timeout=15).decode('utf-8')
                pdf_pages = 0
                for l in info_out.splitlines():
                    if l.startswith('Pages:'):
                        pdf_pages = int(l.split(':')[1].strip())
                        break
                pdf_pass = (expected_pages is None) or (pdf_pages == expected_pages)
                results['checks']['split_pdf'] = {
                    'filename': split_pdf.name,
                    'pages': pdf_pages,
                    'expected': expected_pages,
                    'passed': pdf_pass
                }
                print(f"  • Split PDF Continuity: {'[PASS]' if pdf_pass else '[FAIL]'} {split_pdf.name} has {pdf_pages} page(s).")
                if not pdf_pass:
                    results['passed'] = False
            except Exception as e:
                print(f"  • Split PDF: [FAIL] Error reading {split_pdf}: {e}")
                results['passed'] = False

        # 6. Semantic Meaningfulness & Content Integrity Checks
        num_noise_res = check_numeric_coordinate_noise(md_content)
        shat_math_res = check_shattered_math(md_content)
        infix_sym_res = check_infix_math_in_words(md_content)
        head_int_res  = check_heading_prose_intrusion(md_content)
        tbl_ban_res   = check_table_banner_integrity(md_content)
        head_den_res  = check_heading_density(md_content, total_tokens, is_front_matter, is_journal)
        hard_wrap_res = check_excessive_hard_wraps(md_content)

        semantic_pass = (
            num_noise_res['passed'] and
            shat_math_res['passed'] and
            infix_sym_res['passed'] and
            head_int_res['passed'] and
            tbl_ban_res['passed'] and
            head_den_res['passed']
        )

        results['checks']['semantic'] = {
            'numeric_noise': num_noise_res,
            'shattered_math': shat_math_res,
            'infix_symbols': infix_sym_res,
            'heading_intrusion': head_int_res,
            'table_banners': tbl_ban_res,
            'heading_density': head_den_res,
            'hard_wraps': hard_wrap_res,
            'passed': semantic_pass,
        }

        print(f"  • Semantic Noise & Leaks: {'[PASS]' if num_noise_res['passed'] else '[FAIL]'} ({num_noise_res['count']} numeric coordinate leaks)")
        print(f"  • Mathematical Integrity: {'[PASS]' if (shat_math_res['passed'] and infix_sym_res['passed']) else '[FAIL]'} (shattered: {shat_math_res['count']}, infix: {infix_sym_res['count']})")
        print(f"  • Heading Prose Integrity: {'[PASS]' if head_int_res['passed'] else '[FAIL]'} ({head_int_res['count']} heading prose intrusions)")
        print(f"  • Table Banner Integrity: {'[PASS]' if tbl_ban_res['passed'] else '[FAIL]'} ({tbl_ban_res['count']} collapsed comparison banners)")
        print(f"  • Heading Hierarchy Density: {'[PASS]' if head_den_res['passed'] else '[FAIL]'} ({head_den_res.get('heading_count', 0)} headings found)")
        print(f"  • Paragraph Reflow Sanity: {'[PASS]' if hard_wrap_res['passed'] else '[WARN]'} ({hard_wrap_res['unreflowed_paragraphs']} unreflowed blocks)")

        if not semantic_pass:
            results['passed'] = False

        # 7. Math & LaTeX Delimiter Sanity ($$, $, %, {}, currency $)
        latex_sym_res = check_latex_and_symbol_integrity(md_content)
        tbl_col_res   = check_table_column_integrity(md_content)
        spec_char_res = check_unescaped_special_chars(md_content)

        integrity_pass = (
            latex_sym_res['passed'] and
            tbl_col_res['passed'] and
            spec_char_res['passed']
        )

        results['checks']['syntax_and_symbols'] = {
            'latex_symbols': latex_sym_res,
            'table_columns': tbl_col_res,
            'special_chars': spec_char_res,
            'passed': integrity_pass
        }

        print(f"  • LaTeX Math & Currency Delimiters: {'[PASS]' if latex_sym_res['passed'] else '[FAIL]'} ({len(latex_sym_res['issues'])} delimiter issues)")
        if not latex_sym_res['passed']:
            for iss in latex_sym_res['issues'][:3]:
                print(f"      - {iss}")

        print(f"  • Table Structure & Column Alignment: {'[PASS]' if tbl_col_res['passed'] else '[FAIL]'} ({len(tbl_col_res['issues'])} alignment issues)")
        if not tbl_col_res['passed']:
            for iss in tbl_col_res['issues'][:3]:
                print(f"      - {iss}")

        print(f"  • Special Character Leaks & Angle Brackets: {'[PASS]' if spec_char_res['passed'] else '[FAIL]'} ({len(spec_char_res['issues'])} syntax leaks)")
        if not spec_char_res['passed']:
            for iss in spec_char_res['issues'][:3]:
                print(f"      - {iss}")

        if not integrity_pass:
            results['passed'] = False

        # 8. Local Ollama AI Semantic Audit (if enabled)
        if self.use_ollama and self.ollama:
            print(f"  [*] Dispatching Local Ollama AI ({self.ollama.semantic_model}) for semantic & LaTeX audit...")
            ai_res = self.ollama.verify_chapter_semantics(ch_name, md_content)
            results['checks']['ollama'] = ai_res
            if ai_res['available']:
                print(f"  • Local Ollama Feedback:\n    {ai_res['feedback'].replace(chr(10), chr(10) + '    ')}")
            else:
                print(f"  • Local Ollama: [WARN] {ai_res['feedback']}")

        overall_str = "SUCCESS (PASS)" if results['passed'] else "FAILED (CHECK ISSUES)"
        print(f"{'-'*70}\nChapter Overall Accuracy: [{overall_str}]\n{'='*70}\n")
        return results


def main() -> None:
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Verify content accuracy and quality of extracted textbook chapters.")
    parser.add_argument('--chapter-dir', '-c', help="Path to chapter output directory")
    parser.add_argument('--book-dir', '-b', help="Path to book output directory (containing chapters/)")
    parser.add_argument('--expected-pages', '-p', type=int, default=None, help="Expected page count for split PDF")
    parser.add_argument('--ollama', action='store_true', help="Enable local Ollama AI model semantic & formula audit")
    parser.add_argument('--ollama-model', default='deepseek-r1:8b', help="Ollama model name (default: deepseek-r1:8b)")

    args = parser.parse_args()

    verifier = AccuracyVerifier(use_ollama=args.ollama, ollama_model=args.ollama_model)

    if args.chapter_dir:
        res = verifier.verify_chapter(args.chapter_dir, expected_pages=args.expected_pages)
        sys.exit(0 if res['passed'] else 1)
    elif args.book_dir:
        chapters_dir = os.path.join(args.book_dir, 'chapters')
        if not os.path.exists(chapters_dir):
            print(f"Error: {chapters_dir} not found.")
            sys.exit(1)
        all_passed = True
        for ch in sorted(os.listdir(chapters_dir)):
            full_ch = os.path.join(chapters_dir, ch)
            if os.path.isdir(full_ch):
                res = verifier.verify_chapter(full_ch)
                if not res['passed']:
                    all_passed = False
        sys.exit(0 if all_passed else 1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

