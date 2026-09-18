#!/usr/bin/env python3
"""
Batch re-convert all chapters of Research Methods, Design, and Analysis 13th ed
using the updated book processor (stylesheet refactor, table heading fix, dynamic EOC).
"""
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from book_processor.parsers.digital_pdf import DigitalPDFParser
from book_processor.parsers.layout_detector import set_style, generate_markdown_toc
from book_processor.parsers.scanned_pdf import ScannedPDFParser
from book_processor.core.image_manager import ImageManager
from book_processor.utils.text_utils import stitch_cross_page_continuity
from book_processor.style_loader import load_style

from book_processor.core.invariants import QualityInvariantGuard
from book_processor.profiler.special_block_scanner import SpecialBlockScanner
from book_processor.utils.anki_exporter import AnkiExporter
from book_processor.core.checkpoint import CheckpointManager
from book_processor.verification.visual_auditor import VisualAuditor

import subprocess
import tempfile
import re

DEFAULT_BOOK_OUTPUT = Path("output/Research Methods, Design, and Analysis 13th ed")

def bind_book_context(book_dir: Path):
    global BOOK_OUTPUT, CHAPTERS_DIR, style, checkpoint
    BOOK_OUTPUT = Path(book_dir)
    CHAPTERS_DIR = BOOK_OUTPUT / "chapters"
    style = load_style(str(BOOK_OUTPUT))
    set_style(style)
    DigitalPDFParser.set_style(style)
    import book_processor.parsers.digital_pdf as _dp_mod
    _dp_mod._STYLE = style
    checkpoint = CheckpointManager(str(BOOK_OUTPUT), BOOK_OUTPUT.name)
    return style, checkpoint

style, checkpoint = bind_book_context(DEFAULT_BOOK_OUTPUT)


def get_page_count(pdf_path: str) -> int:
    out = subprocess.check_output(
        ['pdfinfo', pdf_path], stderr=subprocess.DEVNULL
    ).decode('utf-8', errors='ignore')
    for line in out.splitlines():
        if line.startswith('Pages:'):
            return int(line.split(':')[1].strip())
    return 0


def build_css(s: dict) -> str:
    lines = ["<style>", "  /* Textbook typographic styling */"]
    if s.get("css_justify_body", True):
        lines += ["  p {", "    text-align: justify;", "    text-justify: inter-word;", "  }"]
    ha = s.get("css_heading_align", "left")
    lines += [f"  h1, h2, h3, h4, h5, h6 {{ text-align: {ha}; }}"]
    ba = s.get("css_blockquote_align", "left")
    lines += [f"  blockquote {{ text-align: {ba}; }}", "</style>", ""]
    return "\n".join(lines) + "\n"


def is_scanned(pdf_path: str) -> bool:
    try:
        # Check pdftotext first — if it extracts text, it is searchable/born-digital
        res = subprocess.run(
            ['pdftotext', '-f', '1', '-l', '2', pdf_path, '-'],
            capture_output=True, timeout=10
        )
        if len(res.stdout.decode('utf-8', errors='ignore').strip()) > 50:
            return False
        result = subprocess.run(
            ['pdffonts', pdf_path],
            capture_output=True, timeout=10
        )
        out = result.stdout.decode('utf-8', errors='ignore')
        lines = [l for l in out.splitlines() if l.strip() and not l.startswith('name')]
        return len(lines) < 2
    except Exception:
        return False


def convert_chapter(ch_pdf: Path, force: bool = False, book_style: dict = None, book_cp: CheckpointManager = None) -> bool:
    s = book_style if book_style is not None else style
    cp = book_cp if book_cp is not None else checkpoint

    ch_name = ch_pdf.stem
    ch_dir = ch_pdf.parent
    ch_images_dir = ch_dir / "images"
    md_out = ch_dir / f"{ch_name}.md"

    # Checkpoint guard: skip if already converted unless force
    if not force and md_out.exists() and md_out.stat().st_size > 200:
        ch_status = cp.data.get("chapters", {}).get(ch_name, {})
        if ch_status.get("status") == "CONVERTED":
            print(f"  [⏭️ SKIP] Already converted: {ch_name}")
            return True

    print(f"\n  Converting: {ch_name}")
    t0 = time.time()

    try:
        total_pages = get_page_count(str(ch_pdf))
        scanned = is_scanned(str(ch_pdf))

        # Extract images
        raw_images = ImageManager.extract_pdf_images(str(ch_pdf), is_scanned=scanned)
        saved_images = []
        if raw_images:
            os.makedirs(ch_images_dir, exist_ok=True)
            for seq, img in enumerate(raw_images, 1):
                fname = f"{img['page']:03d}_{seq:03d}.{img['ext']}"
                dest = ch_images_dir / fname
                with open(dest, 'wb') as f:
                    f.write(img['data'])
                img['filename'] = fname
                saved_images.append(img)

        # Parse pages
        if not scanned:
            DigitalPDFParser.reset_chapter_state()
        md_parts = []
        with tempfile.TemporaryDirectory() as work_tmp:
            for p in range(1, total_pages + 1):
                p_imgs = [img for img in saved_images if img['page'] == p]
                if scanned:
                    p_md = ScannedPDFParser.parse_page_to_markdown(str(ch_pdf), p, work_tmp)
                else:
                    p_md = DigitalPDFParser.parse_page_to_markdown(str(ch_pdf), p, p_imgs)
                if p_md:
                    md_parts.append(f"<!-- Page {p} -->\n{p_md}")

        full_md = '\n\n'.join(md_parts).strip()

        # Chapter title guard
        if s.get("prepend_chapter_title_if_missing", True):
            if not re.search(r'^\s*#+\s*(?:PART|CHAPTER|\d+|Introduction)', full_md, re.I) \
               and not re.search(r'^\s*<!--.*?-->\s*#+\s*', full_md, re.I):
                full_md = f"# {ch_name}\n\n{full_md}"

        # Insert clickable Table of Contents if configured
        if s.get("generate_toc", True):
            toc_block = generate_markdown_toc(full_md)
            if toc_block and "<summary>📑 <b>Table of Contents</b>" not in full_md:
                m_h1 = re.search(r'^(#[^\n]+\n+)', full_md)
                if m_h1:
                    full_md = full_md[:m_h1.end()] + toc_block + "\n\n" + full_md[m_h1.end():]
                else:
                    full_md = toc_block + "\n\n" + full_md

        # Cross-page stitch
        full_md = stitch_cross_page_continuity(full_md)


        # Append chapter-end flashcards if configured
        if not scanned and s.get("gloss_placement") == "chapter_end":
            ch_gloss = DigitalPDFParser.get_chapter_all_terms()
            if ch_gloss:
                if s.get("gloss_format") == "bullet":
                    fc_lines = [
                        "## 📖 Chapter Key Terms",
                        "",
                    ]
                    for g in ch_gloss:
                        t   = g['term']
                        d   = (g.get('definition') or '').strip()
                        pg  = g.get('page')
                        pg_str = f" *(p. {pg})*" if pg else ""
                        if d:
                            fc_lines.append(f"- **{t}**{pg_str}: {d}")
                        else:
                            fc_lines.append(f"- **{t}**{pg_str}")
                    fc_lines.append("")
                else:
                    fc_lines = [
                        "## 🗂️ Chapter Key Terms & Active Recall",
                        "",
                        "> 💡 **Learning tip:** Try to recall the definition of each term *before* clicking to reveal it.",
                        "> This active retrieval practice strengthens long-term memory far more than re-reading.",
                        "",
                    ]
                    for g in ch_gloss:
                        t   = g['term']
                        d   = (g.get('definition') or '').strip()
                        pg  = g.get('page')
                        pg_str = f" *(p. {pg})*" if pg else ""
                        slug   = re.sub(r'[^a-zA-Z0-9]+', '-', t.lower()).strip('-')
                        fc_lines.append(f"<details id=\"flashcard-{slug}\">")
                        fc_lines.append(f"<summary>📇 **{t}**{pg_str}</summary>")
                        fc_lines.append("")
                        if d:
                            fc_lines.append(f"> **Definition:** {d}")
                            fc_lines.append(">")
                            fc_lines.append("> *Ask yourself: How does this concept relate to others in the chapter?*")
                        else:
                            loc = f"on p. {pg}" if pg else "in the chapter"
                            fc_lines.append(f"> *This term appears in bold {loc}.*")
                            fc_lines.append("> *Write your own definition from context, then re-read that passage to check.*")
                        fc_lines.append("")
                        fc_lines.append("</details>")
                        fc_lines.append("")
                fc_text = '\n'.join(fc_lines)
                m_eoc = re.search(r'(?:<a id="key-terms-and-concepts"></a>|###\s*Key Terms and Concepts)', full_md)
                if m_eoc:
                    pos = m_eoc.start()
                    full_md = full_md[:pos] + fc_text + "\n\n" + full_md[pos:]
                else:
                    full_md = full_md + "\n\n" + fc_text


        # CSS injection
        if '<style>' not in full_md:
            full_md = build_css(s) + full_md

        # Write output
        with open(md_out, 'w', encoding='utf-8') as f:
            f.write(full_md + '\n')

        # Export Anki-compatible flashcard deck if chapter terms were collected
        if not scanned and s.get("gloss_placement") == "chapter_end":
            all_terms = DigitalPDFParser.get_chapter_all_terms()
            if all_terms:
                anki_path = ch_dir / f"{ch_name}_flashcards.tsv"
                AnkiExporter.export_chapter_flashcards_to_tsv(all_terms, anki_path, chapter_name=ch_name)

        elapsed = time.time() - t0
        print(f"    ✓ Done ({total_pages} pages, {len(saved_images)} images, {elapsed:.1f}s)")


        # Update checkpoint
        cp.update_status(
            ch_name,
            status="CONVERTED",
            total_pages=total_pages,
            images_count=len(saved_images),
            markdown_generated=True,
            elapsed_seconds=round(elapsed, 2)
        )
        return True

    except Exception as e:
        print(f"    ✗ FAILED: {e}")
        cp.update_status(ch_name, status="FAILED", error=str(e))
        return False


def process_book_dir(book_dir: Path, args) -> bool:
    b_style, b_cp = bind_book_context(book_dir)
    b_chapters_dir = book_dir / "chapters"
    if not b_chapters_dir.exists():
        print(f"  [!] No chapters directory found in {book_dir}")
        return False

    if args.status:
        dashboard = book_dir / "processing_status.md"
        if dashboard.exists():
            print(dashboard.read_text(encoding='utf-8'))
        else:
            print(f"No checkpoint status file found at {dashboard}")
        return True

    chapters = sorted(b_chapters_dir.glob("*/"))
    chapters = [c for c in chapters if (c / f"{c.name}.pdf").exists()]

    if args.audit:
        print(f"\n[🔍 Visual Quality Audit] Inspecting {len(chapters)} chapters in {book_dir.name}...")
        for ch_dir in chapters:
            ch_pdf = ch_dir / f"{ch_dir.name}.pdf"
            ch_md = ch_dir / f"{ch_dir.name}.md"
            if ch_md.exists():
                res = VisualAuditor.audit_chapter(ch_pdf, ch_md, ch_dir)
                score = res.get("quality_score", 0.0)
                print(f"  • {ch_dir.name:<55} Quality: {score:.1f}/10 ({res.get('status')})")
        return True

    # ── Special Block Scanner ────────────────────────────────────────────────
    if getattr(args, 'scan_only', False) or getattr(args, 'scan', False):
        print(f"\n[🔬 Special Block Scanner] Scanning first 5 chapters for {book_dir.name}...")
        sample_pdfs = [c / f"{c.name}.pdf" for c in sorted(chapters)[:5]]
        scanner = SpecialBlockScanner(book_dir)
        result = scanner.scan_and_update(sample_pdfs, force_rescan=getattr(args, 'scan_only', False))
        print(f"\n  Discovered {len(result.get('discovered_blocks', []))} special blocks:")
        import json
        print(json.dumps(result.get('discovered_blocks', []), indent=2, ensure_ascii=False))
        print(f"\n  Column roles: {result.get('column_roles', {})}")
        print(f"  has_concept_map: {result.get('special_blocks', {}).get('has_concept_map')}")
        print(f"  has_margin_glossary: {result.get('special_blocks', {}).get('has_margin_glossary')}")
        if getattr(args, 'scan_only', False):
            return True
    # ─────────────────────────────────────────────────────────────────────────

    if args.from_ch:
        chapters = [c for c in chapters if c.name >= args.from_ch]
    if args.only_ch:
        chapters = [c for c in chapters if c.name.startswith(args.only_ch)]

    print(f"\n{'='*70}")
    print(f"📖 Processing: {book_dir.name}")
    print(f"Found {len(chapters)} chapters to process (force={args.force}).\n")
    ok = 0
    failed = []
    total_t = time.time()

    for ch_dir in chapters:
        ch_pdf = ch_dir / f"{ch_dir.name}.pdf"
        success = convert_chapter(ch_pdf, force=args.force, book_style=b_style, book_cp=b_cp)
        if success:
            ok += 1
        else:
            failed.append(ch_dir.name)

    elapsed = time.time() - total_t
    print(f"\n{'='*60}")
    print(f"Book conversion complete: {ok}/{len(chapters)} chapters OK  ({elapsed:.1f}s total)")
    if failed:
        print(f"Failed chapters:")
        for f in failed:
            print(f"  - {f}")
    else:
        print("All chapters converted successfully!")
    return len(failed) == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Textbook batch conversion and checkpoint tool")
    parser.add_argument('--book-dir', '-b', default=None,
                        help='Path to specific book directory (default: Research Methods 13th ed)')
    parser.add_argument('--all-books', action='store_true',
                        help='Batch process all books found under output/')
    parser.add_argument('--from', dest='from_ch', default=None,
                        help='Start from this chapter name prefix (e.g. "Ch12")')
    parser.add_argument('--only', dest='only_ch', default=None,
                        help='Convert only this chapter name prefix')
    parser.add_argument('--force', action='store_true',
                        help='Force re-conversion even if chapter was previously marked CONVERTED')
    parser.add_argument('--status', action='store_true',
                        help='Print the current book conversion checkpoint status and exit')
    parser.add_argument('--audit', action='store_true',
                        help='Run visual quality auditor on converted chapters')
    parser.add_argument('--scan', action='store_true',
                        help='Run SpecialBlockScanner before conversion to discover book-specific layout features')
    parser.add_argument('--scan-only', action='store_true',
                        help='Run SpecialBlockScanner only (no conversion) and print discovered blocks')
    args = parser.parse_args()

    if args.all_books:
        output_root = Path("output")
        book_dirs = sorted([d for d in output_root.iterdir() if d.is_dir() and (d / "chapters").exists()])
        print(f"[📚 All Books Mode] Found {len(book_dirs)} books to process.")
        overall_ok = True
        for b_dir in book_dirs:
            ok = process_book_dir(b_dir, args)
            if not ok:
                overall_ok = False
        print(f"\n{'='*70}\n[🎉 ALL BOOKS COMPLETED] Overall status: {'ALL PASSED' if overall_ok else 'SOME FAILED'}\n{'='*70}")
    else:
        target_dir = Path(args.book_dir) if args.book_dir else DEFAULT_BOOK_OUTPUT
        process_book_dir(target_dir, args)


if __name__ == "__main__":
    main()
