"""
Master Workflow Orchestrator
============================
Coordinates PDF splitting, image extraction, layout analysis, LaTeX conversion,
automated accuracy verification, and checkpoint manifest updates.
"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

from doc_processor.book_style import build_textbook_css
from doc_processor.concurrency import M5WorkerPool
from doc_processor.config import (
    CIRCUIT_BREAKER_MAX_FAILURES,
    DEFAULT_INBOX_DIR,
    DEFAULT_OLLAMA_HEALER_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROCESSED_DIR,
)
from doc_processor.core.checkpoint import CheckpointManager
from doc_processor.core.image_manager import ImageManager
from doc_processor.core.invariants import CircuitBreaker, QualityInvariantGuard
from doc_processor.core.learner import AdaptiveLearner, GlobalLearner
from doc_processor.core.splitter import PDFSplitter
from doc_processor.fingerprinting.document_classifier import DocumentClassifier
from doc_processor.parsers import digital_pdf as _digital_pdf_mod
from doc_processor.parsers.digital_pdf import DigitalPDFParser
from doc_processor.parsers.epub_parser import EPUBProcessor
from doc_processor.parsers.layout_detector import generate_markdown_toc
from doc_processor.parsers.layout_detector import set_style as _ld_set_style
from doc_processor.parsers.scanned_pdf import ScannedPDFParser
from doc_processor.profiler.coordinate_calibrator import CoordinateCalibrator
from doc_processor.profiler.special_block_scanner import SpecialBlockScanner
from doc_processor.style_loader import load_style
from doc_processor.utils.anki_exporter import AnkiExporter
from doc_processor.utils.text_utils import (
    sanitize_filename,
    stitch_cross_page_continuity,
)
from doc_processor.verification.layout_healer import LayoutAutoHealer
from doc_processor.verification.ollama_verifier import OllamaVerifier
from doc_processor.verification.review_manager import ReviewManager
from doc_processor.verification.verifier import AccuracyVerifier

logger = logging.getLogger(__name__)



class BookProcessorOrchestrator:
    """Master workflow orchestrator for multi-stage processing and resume capability."""

    def __init__(
        self,
        input_dir: str = ".",
        output_dir: str = DEFAULT_OUTPUT_DIR,
        inbox_dir: str = DEFAULT_INBOX_DIR,
        processed_dir: str = DEFAULT_PROCESSED_DIR,
        use_ollama: bool = False,
        ollama_model: str = DEFAULT_OLLAMA_HEALER_MODEL
    ):
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.inbox_dir = os.path.abspath(inbox_dir)
        self.processed_dir = os.path.abspath(processed_dir)
        self.use_ollama = use_ollama
        self.ollama_model = ollama_model
        self.interrupted = False
        self.circuit_breaker = CircuitBreaker(max_consecutive_failures=CIRCUIT_BREAKER_MAX_FAILURES)
        self._setup_signals()

    def _setup_signals(self):
        """Sets up graceful interrupt handler for overheating / emergency stop."""
        def handle_sigint(sig, frame):
            print("\n\n[!] Interrupt signal received (Ctrl+C). Saving current checkpoint and stopping safely...")
            self.interrupted = True

        signal.signal(signal.SIGINT, handle_sigint)

    def archive_source_file(self, source_path: str):
        """Moves fully completed and verified book file to processed/ directory."""
        p = Path(source_path)
        dest_dir = Path(self.processed_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / p.name
        try:
            shutil.move(str(p), str(dest_file))
            print(f"\n[📦 ARCHIVE] 100% of chapters verified! Source book moved to: {dest_file}\n")
        except Exception as e:
            print(f"  [!] Note: Could not move source book to {dest_file}: {e}")

    def discover_books(self, target_file: str = None) -> list:
        """Finds PDF and EPUB files, checking inbox/ first."""
        workspace_root = os.path.abspath(self.input_dir)

        def _safe_path(p: str) -> str | None:
            """Resolve symlinks; return None if target escapes the workspace."""
            resolved = os.path.realpath(p)
            if not resolved.startswith(workspace_root):
                logger.warning(
                    "Skipping '%s': symlink resolves outside workspace (%s).", p, resolved
                )
                return None
            return resolved

        if target_file:
            path = os.path.abspath(target_file)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Target file not found: {path}")
            safe = _safe_path(path)
            if safe is None:
                raise PermissionError(f"Target file resolves outside workspace: {path}")
            return [(path, Path(path).suffix.lower())]

        # 1. Check inbox directory first
        items = []
        if os.path.exists(self.inbox_dir):
            for f in sorted(os.listdir(self.inbox_dir)):
                ext = Path(f).suffix.lower()
                full = os.path.join(self.inbox_dir, f)
                if ext in ('.pdf', '.epub') and not f.startswith('.'):
                    if _safe_path(full) is not None:
                        items.append((full, ext))
        if items:
            return items

        # 2. Fallback to scanning input_dir
        for root, dirs, files in os.walk(self.input_dir):
            rel = os.path.relpath(root, self.input_dir)
            parts = rel.split(os.sep)
            if any(p in ('sample', 'output', 'processed', '.git', '.gemini', 'tmp_test') for p in parts):
                continue
            for f in sorted(files):
                ext = Path(f).suffix.lower()
                full = os.path.join(root, f)
                if ext in ('.pdf', '.epub') and not f.startswith('.'):
                    if _safe_path(full) is not None:
                        items.append((full, ext))
        return items

    @staticmethod
    def get_pdf_page_count(pdf_path: str) -> int:
        try:
            out = subprocess.check_output(
                ['pdfinfo', pdf_path],
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode('utf-8', errors='ignore')
            for line in out.splitlines():
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except subprocess.TimeoutExpired:
            logger.warning("pdfinfo timed out (15s) for '%s'", pdf_path)
        except subprocess.CalledProcessError as e:
            logger.warning("pdfinfo returned error %d for '%s'", e.returncode, pdf_path)
        except Exception as e:
            logger.debug("Failed to get PDF page count for '%s': %s", pdf_path, e)
        return 0

    @staticmethod
    def is_scanned_pdf(pdf_path: str, sample_count: int = 5) -> bool:
        try:
            total_p = BookProcessorOrchestrator.get_pdf_page_count(pdf_path)
            sample_pages = min(sample_count, total_p)
            out = subprocess.check_output(
                ['pdfimages', '-list', '-f', '1', '-l', str(sample_pages), pdf_path],
                stderr=subprocess.DEVNULL,
                timeout=30
            ).decode('utf-8')
            lines = out.splitlines()[2:]
            full_page_images = 0
            for l in lines:
                parts = l.split()
                if len(parts) >= 12:
                    enc = parts[8]
                    w = int(parts[3])
                    h = int(parts[4])
                    if enc != 'jbig2' and (w >= 1000 and h >= 1000):
                        full_page_images += 1
            return full_page_images >= (sample_pages * 0.5)
        except subprocess.TimeoutExpired:
            logger.warning("pdfimages -list timed out (30s) for '%s'", pdf_path)
        except subprocess.CalledProcessError as e:
            logger.warning("pdfimages -list returned error %d for '%s'", e.returncode, pdf_path)
        except Exception as e:
            logger.debug("Failed to check if scanned PDF for '%s': %s", pdf_path, e)
        return False

    @staticmethod
    def get_pdf_sections(pdf_path: str) -> list:
        from doc_processor.core.analyzer import PDFAnalyzer
        secs, _ = PDFAnalyzer.get_sections(pdf_path)
        return secs or []

    # =========================================================================
    # STAGE 1: Fast Split-Only Mode
    # =========================================================================
    def split_book_only(self, pdf_path: str):
        """Splits an entire book into chapter PDFs in seconds without OCR."""
        # Enforce pre-split invariant
        QualityInvariantGuard.check_pdf_pre_split(pdf_path)

        book_name = Path(pdf_path).stem
        book_out = os.path.join(self.output_dir, sanitize_filename(book_name))
        chapters_root = os.path.join(book_out, 'chapters')
        os.makedirs(chapters_root, exist_ok=True)

        sections = self.get_pdf_sections(pdf_path)
        if not sections:
            logger.warning("No sections identified for '%s'", book_name)
            print(f"[!] Unable to identify sections for {book_name}")
            return

        ckpt = CheckpointManager(book_out, book_name)
        ckpt.init_chapters(sections)

        print(f"\n{'='*70}\n[STAGE 1: SPLIT ONLY] Book: {book_name} ({len(sections)} sections)\n{'='*70}")
        for idx, sec in enumerate(sections, 1):
            if self.interrupted:
                break
            name = sec['name']
            start = sec['start']
            end = sec['end']
            ch_dir = os.path.join(chapters_root, name)
            os.makedirs(ch_dir, exist_ok=True)
            ch_pdf = os.path.join(ch_dir, f"{name}.pdf")

            print(f"  [{idx:02d}/{len(sections):02d}] Splitting: {name} (pp. {start}-{end})...")
            PDFSplitter.split_chapter(pdf_path, start, end, ch_pdf)
            QualityInvariantGuard.check_split_chapter(ch_pdf, expected_pages=(end - start + 1))
            ckpt.update_status(name, split_pdf=True, status='SPLIT')

        print(f"\n[✓] Split complete! Chapter PDFs saved in: {chapters_root}")
        print(f"    Check progress dashboard at: {ckpt.md_path}\n")

    # =========================================================================
    # STAGE 2: Convert Single Chapter (with Automatic Verification)
    # =========================================================================
    def convert_single_chapter(self, chapter_pdf_path: str, book_source_pdf: str = None, retry_count: int = 0):
        """
        Converts a single chapter PDF into Markdown, extracts images, enforces quality invariants,
        runs automatic verification, generates AI review diffs, and auto-retries on failure.
        """
        ch_pdf = Path(chapter_pdf_path)
        if not ch_pdf.exists():
            raise FileNotFoundError(f"Chapter PDF not found: {ch_pdf}")

        ch_dir = ch_pdf.parent
        ch_name = ch_pdf.stem
        ch_images_dir = ch_dir / "images"

        total_pages = self.get_pdf_page_count(str(ch_pdf))
        # Post-split invariant check
        QualityInvariantGuard.check_split_chapter(str(ch_pdf), expected_pages=total_pages)

        book_dir = ch_dir.parent.parent
        learner = AdaptiveLearner(str(book_dir))

        # Check document classification (journal vs textbook)
        is_journal_doc = DocumentClassifier.is_journal_article(str(ch_pdf)) or (book_source_pdf and DocumentClassifier.is_journal_article(str(book_source_pdf)))

        # Auto-calibrate geometry and scan special blocks on first chapter run if profile missing
        book_profile_path = book_dir / "book_profile.json"
        if not book_profile_path.exists():
            try:
                CoordinateCalibrator.calibrate_and_save_profile(book_dir, ch_pdf)
                if is_journal_doc:
                    try:
                        with open(book_profile_path, 'r', encoding='utf-8') as f_prof:
                            prof_data = json.load(f_prof)
                        prof_data["is_journal"] = True
                        with open(book_profile_path, 'w', encoding='utf-8') as f_prof:
                            json.dump(prof_data, f_prof, indent=2)
                    except Exception as e:
                        logger.debug("Failed updating is_journal in profile: %s", e)

                scanner = SpecialBlockScanner(book_dir)
                scanner.scan_and_update([ch_pdf], max_pages_per_chapter=10)
            except Exception as e:
                logger.debug("Automatic book calibration skipped: %s", e)

        # Load per-book style (merges global defaults with book-level override if present)
        _style = load_style(str(book_dir))
        if is_journal_doc:
            _style["is_journal_article"] = True
            _style["generate_toc"] = False
            _style["gloss_placement"] = "none"
            _style["prepend_chapter_title_if_missing"] = False
        _ld_set_style(_style)
        _digital_pdf_mod._STYLE = _style


        is_scanned = self.is_scanned_pdf(str(ch_pdf))


        print(f"\n{'='*70}\n[STAGE 2: CONVERT CHAPTER] {ch_name} ({total_pages} page(s))\n{'='*70}")
        print(f"  Mode: {'SCANNED BOOK (Neural Layout + LaTeX)' if is_scanned else 'BORN-DIGITAL VECTOR (XML Styles + LaTeX)'}")

        # 1. Extract Images (discards background sheets)
        raw_images = ImageManager.extract_pdf_images(str(ch_pdf), is_scanned=is_scanned)
        saved_images = []
        if raw_images:
            os.makedirs(ch_images_dir, exist_ok=True)
            for seq, img in enumerate(raw_images, 1):
                p = img['page']
                ext = img['ext']
                fname = f"{p:03d}_{seq:03d}.{ext}"
                dest = ch_images_dir / fname
                with open(dest, 'wb') as f_out:
                    f_out.write(img['data'])
                img['filename'] = fname
                saved_images.append(img)
        print(f"  [✓] Genuine figures/photos extracted: {len(saved_images)}")

        md_parts = []
        if not is_scanned:
            DigitalPDFParser.reset_chapter_state()
        with tempfile.TemporaryDirectory() as work_tmp:
            for p in range(1, total_pages + 1):
                p_imgs = [img for img in saved_images if img['page'] == p]
                if is_scanned:
                    p_md = ScannedPDFParser.parse_page_to_markdown(str(ch_pdf), p, work_tmp)
                else:

                    p_md = DigitalPDFParser.parse_page_to_markdown(str(ch_pdf), p, p_imgs)
                if p_md:
                    md_parts.append(f"<!-- Page {p} -->\n{p_md}")

        full_md = '\n\n'.join(md_parts).strip()
        if is_journal_doc:
            # Promote the main article title to # (H1) if only ### was assigned
            if not re.search(r'^\s*#\s+[^\n]+', full_md):
                m_first_h = re.search(r'###\s+([^\n]+)(?:\n+###\s+([^\n]+))?', full_md)
                if m_first_h:
                    t1 = m_first_h.group(1).strip()
                    t2 = m_first_h.group(2).strip() if m_first_h.group(2) else ""
                    combined_title = f"{t1} {t2}".strip()
                    full_md = full_md[:m_first_h.start()] + f"# {combined_title}" + full_md[m_first_h.end():]
        elif _style.get("prepend_chapter_title_if_missing", True):
            if not re.search(r'^\s*#+\s*(?:PART|CHAPTER|\d+|Introduction)', full_md, re.IGNORECASE) and not re.search(r'^\s*<!--.*?-->\s*#+\s*', full_md, re.IGNORECASE):
                full_md = f"# {ch_name}\n\n{full_md}"

        # Insert clickable Table of Contents if configured
        toc_mode = _style.get("toc_mode", "open")
        if not is_journal_doc and _style.get("generate_toc", True) and toc_mode != "none":
            toc_block = generate_markdown_toc(full_md, toc_mode=toc_mode)
            if toc_block and "<summary>📑 <b>Table of Contents</b>" not in full_md:
                # Place TOC after the first top-level # heading
                m_h1 = re.search(r'^(#[^\n]+\n+)', full_md)
                if m_h1:
                    full_md = full_md[:m_h1.end()] + toc_block + "\n\n" + full_md[m_h1.end():]
                else:
                    full_md = toc_block + "\n\n" + full_md

        full_md = stitch_cross_page_continuity(full_md)


        # Append chapter-end flashcards if configured
        if not is_scanned and _style.get("gloss_placement") == "chapter_end":
            ch_gloss = DigitalPDFParser.get_chapter_all_terms()
            if ch_gloss:
                if _style.get("gloss_format") == "bullet":
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
                        src = g.get('source')
                        pg_str = f" *(p. {pg})*" if pg else ""
                        slug   = re.sub(r'[^a-zA-Z0-9]+', '-', t.lower()).strip('-')

                        # All cards use <b>{t}</b> inside summary so bolding works in standard HTML
                        fc_lines.append(f"<details id=\"flashcard-{slug}\">")
                        fc_lines.append(f"<summary>📇 <b>{t}</b>{pg_str}</summary>")
                        fc_lines.append("")

                        if d:
                            # Margin-defined term: clean definition without unwanted notes
                            fc_lines.append(f"> **Definition:** {d}")
                        else:
                            # Inline bold term: guide to self-generate
                            loc = f"on p. {pg}" if pg else "in the chapter"
                            fc_lines.append(f"> *This term appears in bold {loc}.*")
                            fc_lines.append("> *Write your own definition from context, then re-read that passage to check.*")

                        fc_lines.append("")
                        fc_lines.append("</details>")
                        fc_lines.append("")

                fc_text = '\n'.join(fc_lines)
                m_eoc = re.search(
                    r'(?:<a id="key-terms-and-concepts"></a>|###\s*Key Terms and Concepts)',
                    full_md
                )
                if m_eoc:
                    pos = m_eoc.start()
                    full_md = full_md[:pos] + fc_text + "\n\n" + full_md[pos:]
                else:
                    full_md = full_md + "\n\n" + fc_text


        # Build CSS block from STYLE (only inject once — guard against retry duplication)
        if '<style>' not in full_md:
            full_md = build_textbook_css(_style) + full_md

        # ──────────────────────────────────────────────────────────────────────
        # Global Learning Pre-Application:
        # Before running any Ollama calls, pre-emptively apply all fix rules that
        # were learned from previous documents of the same archetype.  This prevents
        # known issues (e.g. publisher OCR typos, recurring LaTeX patterns) from
        # ever reaching the verification / Ollama stage on subsequent documents.
        # ──────────────────────────────────────────────────────────────────────
        _doc_archetype = "journal" if is_journal_doc else "textbook"
        try:
            full_md, _pre_fixes = GlobalLearner.apply_known_fixes(full_md, archetype=_doc_archetype)
            if _pre_fixes:
                print(f"  [🧠 Global Learn] Pre-applied {len(_pre_fixes)} known fix rule(s) from global memory.")
                for _pf in _pre_fixes[:3]:
                    print(f"     • [{_pf.get('category', 'global')}] '{_pf.get('original', '')[:50]}…'")
        except Exception as _gl_err:
            logger.debug("GlobalLearner pre-application skipped: %s", _gl_err)

        # Closed-loop layout auto-healing before syntax invariant checks
        full_md, fixes = LayoutAutoHealer.audit_and_heal_chapter(
            full_md,
            str(ch_pdf),
            str(ch_dir),
            images_dir=ch_images_dir,
            use_ollama_vision=self.use_ollama
        )
        if fixes:
            print(f"  [⚡ Auto-Healer] Applied {len(fixes)} layout correction(s):")
            for fix in fixes[:3]:
                print(f"     • {fix}")


        # Syntax & delimiter invariant check
        QualityInvariantGuard.check_markdown_syntax(full_md, str(ch_dir))

        md_file = ch_dir / f"{ch_name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(full_md + '\n')
        print(f"  [✓] Markdown generated: {md_file.name}")

        # Export Anki-compatible flashcard deck if chapter terms were collected
        if not is_scanned and _style.get("gloss_placement") == "chapter_end":
            all_terms = DigitalPDFParser.get_chapter_all_terms()
            if all_terms:
                anki_path = ch_dir / f"{ch_name}_flashcards.tsv"
                count = AnkiExporter.export_chapter_flashcards_to_tsv(all_terms, anki_path, chapter_name=ch_name)
                if count > 0:
                    print(f"  [🗂️ Anki] Exported {count} flashcard(s) to: {anki_path.name}")


        # 3. Automatic Verification
        print("  [*] Running automatic accuracy verification...")
        verifier = AccuracyVerifier(use_ollama=self.use_ollama, ollama_model=self.ollama_model)
        v_res = verifier.verify_chapter(str(ch_dir), expected_pages=total_pages)

        # 4. Local AI Review & Diff Generation
        if self.use_ollama:
            ollama = OllamaVerifier(healer_model=self.ollama_model) if self.ollama_model else OllamaVerifier()
            if ollama.is_available:
                print(f"  [AI Review] Requesting local AI audit & diff suggestions from {self.ollama_model}...")
                proposals = ollama.audit_and_propose_fixes(full_md)
                if proposals:
                    annotated_md, applied = OllamaVerifier.apply_review_annotations(full_md, proposals)
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(annotated_md + '\n')
                    ReviewManager.save_review_manifest(str(ch_dir), applied)
                    print(f"  [💡 AI Review] Saved {len(applied)} proposed correction(s). Run: python3 doc_processor.py review -c \"{ch_dir}\"")

        # 5. Self-Healing Adaptive Auto-Retry Loop
        if not v_res['passed'] and retry_count < 2:
            diag = learner.diagnose_and_learn(v_res, str(ch_dir))
            if diag['should_retry']:
                print(f"\n  [🔄 AUTO-RETRY] Verification failed on {ch_name}. Adapting: {', '.join(diag['actions'])}")
                print(f"  [🔄 AUTO-RETRY] Automatically re-running chapter (Attempt {retry_count + 1}/2)...")
                return self.convert_single_chapter(chapter_pdf_path, book_source_pdf=book_source_pdf, retry_count=retry_count + 1)

        # Record circuit breaker status
        if v_res['passed']:
            self.circuit_breaker.record_success(ch_name)
        else:
            self.circuit_breaker.record_failure(ch_name, reason="Verification checks failed.")

        # 6. Update Checkpoint Manifest if book_dir exists
        ckpt = CheckpointManager(str(book_dir), book_dir.name)
        ckpt.update_status(
            ch_name,
            markdown_generated=True,
            images_count=len(saved_images),
            verification_pass=v_res['passed'],
            accuracy_percent=v_res.get('accuracy_percent'),
            status='VERIFIED' if v_res['passed'] else 'FAILED'
        )

        return v_res

    # =========================================================================
    # STAGE 3 & ALL: Full Book / Smart Resume Engine
    # =========================================================================
    def process_pdf_book(self, pdf_path: str, target_chapter: str = None, resume: bool = False, parallel: bool = False):
        QualityInvariantGuard.check_pdf_pre_split(pdf_path)

        # Check document archetype: dispatch directly to LiteraturePipeline if academic literature
        from doc_processor.config_manager import ConfigManager
        archetype = ConfigManager.detect_archetype(pdf_path)
        if archetype in ("literature", "journal"):
            from doc_processor.pipelines.literature_pipeline import LiteraturePipeline
            pipeline = LiteraturePipeline(
                output_dir=self.output_dir,
                processed_dir=self.processed_dir,
                use_ollama=self.use_ollama,
                ollama_model=self.ollama_model,
            )
            return pipeline.process(pdf_path, is_scanned=self.is_scanned_pdf(pdf_path))

        book_name = Path(pdf_path).stem
        book_out = os.path.join(self.output_dir, sanitize_filename(book_name))
        chapters_root = os.path.join(book_out, 'chapters')
        os.makedirs(chapters_root, exist_ok=True)

        sections = self.get_pdf_sections(pdf_path)
        if not sections:
            logger.warning("No sections identified for '%s'", book_name)
            print(f"[!] Unable to identify sections for {book_name}")
            return

        ckpt = CheckpointManager(book_out, book_name)
        ckpt.init_chapters(sections)

        if target_chapter:
            clean_q = target_chapter.strip().lower()
            sections = [s for s in sections if clean_q in s['name'].lower()]
            if not sections:
                print(f"[!] Chapter '{target_chapter}' not found.")
                return

        print(f"\n{'='*70}\n[PROCESSING BOOK] {book_name} ({len(sections)} sections)\n{'='*70}")

        pending_sections = []
        for idx, sec in enumerate(sections, 1):
            name = sec['name']
            if resume and ckpt.is_chapter_verified(name):
                print(f"  [{idx:02d}/{len(sections):02d}] Skipping already verified chapter: {name}")
                continue
            pending_sections.append((idx, sec))

        if parallel and len(pending_sections) > 1 and not target_chapter:
            print(f"  [⚡ Apple M5 Engine] Launching parallel processing for {len(pending_sections)} chapter(s)...")
            pool = M5WorkerPool()

            def _process_task(item):
                if self.interrupted or self.circuit_breaker.is_tripped():
                    return None
                i_idx, s_sec = item
                s_name = s_sec['name']
                s_start = s_sec['start']
                s_end = s_sec['end']
                s_ch_dir = os.path.join(chapters_root, s_name)
                os.makedirs(s_ch_dir, exist_ok=True)
                s_ch_pdf = os.path.join(s_ch_dir, f"{s_name}.pdf")
                if not os.path.exists(s_ch_pdf) or os.path.getsize(s_ch_pdf) == 0:
                    PDFSplitter.split_chapter(pdf_path, s_start, s_end, s_ch_pdf)
                ckpt.update_status(s_name, split_pdf=True, status='SPLIT')
                return self.convert_single_chapter(s_ch_pdf, book_source_pdf=pdf_path)

            pool.execute_parallel(pending_sections, _process_task, desc="M5 Parallel Chapters")
        else:
            for idx, sec in pending_sections:
                if self.interrupted:
                    print(f"[!] Process paused at section {sec['name']}. Resume later with: book_processor resume")
                    break

                # Circuit breaker guard
                if self.circuit_breaker.is_tripped():
                    print("\n[🚨 CIRCUIT BREAKER TRIPPED] Multiple consecutive chapters failed verification!")
                    print("  Pipeline automatically paused to protect downstream output. Inspect errors before resuming.\n")
                    break

                name = sec['name']
                start = sec['start']
                end = sec['end']

                print(f"\n  [{idx:02d}/{len(sections):02d}] Processing Chapter: {name} (pp. {start}-{end})...")
                ch_dir = os.path.join(chapters_root, name)
                os.makedirs(ch_dir, exist_ok=True)
                ch_pdf = os.path.join(ch_dir, f"{name}.pdf")

                # 1. Split PDF (skip if already exists)
                if not os.path.exists(ch_pdf) or os.path.getsize(ch_pdf) == 0:
                    PDFSplitter.split_chapter(pdf_path, start, end, ch_pdf)
                ckpt.update_status(name, split_pdf=True, status='SPLIT')

                # 2. Convert & Auto-Verify (with auto-retry feedback loop)
                self.convert_single_chapter(ch_pdf, book_source_pdf=pdf_path)

        # Mirror chapter markdown to root directory if single section or journal article
        if len(sections) == 1:
            sec_name = sections[0]['name']
            src_md = os.path.join(chapters_root, sec_name, f"{sec_name}.md")
            dst_md = os.path.join(book_out, f"{sanitize_filename(book_name)}.md")
            if os.path.exists(src_md):
                try:
                    shutil.copy2(src_md, dst_md)
                except Exception as e:
                    logger.debug("Failed copying root markdown: %s", e)

        # Generate Obsidian index.md and inter-chapter navigation footers
        try:

            from doc_processor.utils.obsidian_linker import (
                generate_book_index,
                inject_chapter_navigation,
            )
            ch_list = [
                {
                    "name": s["name"],
                    "md_path": os.path.join(chapters_root, s["name"], f"{s['name']}.md")
                }
                for s in sections
            ]
            idx_file = generate_book_index(book_out, ch_list)
            nav_count = inject_chapter_navigation(ch_list)
            if nav_count > 0:
                print(f"  [🔗 Obsidian] 已生成 {idx_file.name}，並為 {nav_count} 個章節加入導航雙鏈。")
        except Exception as _obs_err:
            logger.debug("Obsidian linker skipped: %s", _obs_err)

        print(f"\n{'='*70}\nBOOK RUN COMPLETE! Progress saved in: {ckpt.md_path}\n{'='*70}\n")


        # Archive completed book if all chapters are verified
        all_verified = all(ckpt.is_chapter_verified(s['name']) for s in sections)
        if all_verified and not target_chapter:
            self.archive_source_file(pdf_path)

    def process_epub_book(self, epub_path: str):
        print(f"\n{'='*70}\n[PROCESSING EPUB] {Path(epub_path).name}\n{'='*70}")
        EPUBProcessor.process(epub_path, self.output_dir)
        # Archive completed EPUB
        self.archive_source_file(epub_path)
