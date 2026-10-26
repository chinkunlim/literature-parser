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
from typing import Optional

from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.concurrency import M5WorkerPool
from literature_parser.services.converter import ConversionOptions, MarkdownConversionService
from literature_parser.config.processor_config import (
    CIRCUIT_BREAKER_MAX_FAILURES,
    DEFAULT_INBOX_DIR,
    DEFAULT_OLLAMA_HEALER_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROCESSED_DIR,
)
from literature_parser.services.core.checkpoint import CheckpointManager
from literature_parser.services.core.image_manager import ImageManager
from literature_parser.services.core.invariants import CircuitBreaker, QualityInvariantGuard
from literature_parser.services.core.learner import AdaptiveLearner, GlobalLearner
from literature_parser.services.core.splitter import PDFSplitter
from literature_parser.services.fingerprinting.document_classifier import DocumentClassifier
from literature_parser.services.parsers import digital_pdf as _digital_pdf_mod
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.epub_parser import EPUBProcessor
from literature_parser.services.parsers.layout_detector import generate_markdown_toc
from literature_parser.services.parsers.layout_detector import set_style as _ld_set_style
from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.services.profiler.special_block_scanner import SpecialBlockScanner
from literature_parser.services.style_loader import load_style
from literature_parser.services.utils.anki_exporter import AnkiExporter
from literature_parser.services.utils.text_utils import (
    sanitize_filename,
    stitch_cross_page_continuity,
)
from literature_parser.adapters.parsers.docling_adapter import DoclingBlueprintAdapter
from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier
from literature_parser.adapters.verification.review_manager import ReviewManager
from literature_parser.adapters.verification.verifier import AccuracyVerifier

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

    def archive_source_file(self, source_path: str, doc_type: str = "book"):
        """Moves fully completed and verified document file to appropriate processed directory.

        Books are moved to `input/processed/processed-books/`.
        Literature is moved to `input/processed/processed-literature/`.

        Args:
            source_path: Path to the original document file.
            doc_type: Document archetype ('book' or 'literature').

        Returns:
            None.
        """
        p = Path(source_path)
        from literature_parser.config.settings import load_config as _load_cfg
        app_cfg = _load_cfg()

        p_resolved = p.resolve()
        is_lit = (doc_type in ("literature", "journal"))
        if not is_lit:
            try:
                rel = p_resolved.relative_to(app_cfg.input_dir.resolve())
                if "literature" in [part.lower() for part in rel.parts]:
                    is_lit = True
            except ValueError:
                pass

        dest_dir = app_cfg.processed_literature_dir if is_lit else app_cfg.processed_books_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / p.name
        try:
            shutil.move(str(p), str(dest_file))
            print(f"\n[📦 ARCHIVE] 100% of document verified! Source moved to: {dest_file}\n")
        except Exception as e:
            print(f"  [!] Note: Could not move source to {dest_file}: {e}")

    def discover_books(self, target_file: str = None) -> list:
        """Finds PDF and EPUB files, checking inbox/ first."""
        from literature_parser.config.settings import load_config as _load_cfg
        app_cfg = _load_cfg()
        allowed_roots = [
            os.path.realpath(self.input_dir),
            os.path.realpath(self.inbox_dir),
            os.path.realpath(app_cfg.data_dir),
            os.path.realpath(app_cfg.input_dir),
        ]

        def _safe_path(p: str) -> str | None:
            """Resolve symlinks; return None if target escapes the workspace/data directory."""
            resolved = os.path.realpath(p)
            for root in allowed_roots:
                if resolved.startswith(root):
                    return resolved
            if target_file and os.path.exists(resolved):
                return resolved
            logger.warning(
                "Skipping '%s': symlink resolves outside workspace (%s).", p, resolved
            )
            return None

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
        """Gets page count with pure-Python fallback when pdfinfo is not installed."""
        from literature_parser.adapters.utils.system import get_pdf_page_count as _get_count
        return _get_count(pdf_path)

    @staticmethod
    def is_scanned_pdf(pdf_path: str, sample_count: int = 5) -> bool:
        """Determines if PDF is a scanned book via PyMuPDF or pdfimages fallback."""
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            sample_p = min(sample_count, len(doc))
            scanned_pages = 0
            for idx in range(sample_p):
                page = doc[idx]
                txt = page.get_text().strip()
                imgs = page.get_images()
                # If page has almost no vector text and contains images, likely scanned
                if len(txt) < 50 and len(imgs) >= 1:
                    scanned_pages += 1
            doc.close()
            return scanned_pages >= (sample_p * 0.5)
        except Exception:
            pass

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
        from literature_parser.services.core.analyzer import PDFAnalyzer
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

        # Sanitize section names: remove null bytes and control characters
        for sec in sections:
            sec['name'] = re.sub(r'[\x00-\x1f\x7f]', '', sec.get('name', '')).strip()

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
    def convert_single_chapter(self, chapter_pdf_path: str, book_source_pdf: str = None, retry_count: int = 0, is_scanned: Optional[bool] = None):
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
        # (Strictly skipped for 00-* front matter sections)
        cand_canon = book_dir / "profile.json"
        cand_legacy = book_dir / "book_profile.json"
        if not cand_canon.exists() and not cand_legacy.exists() and not ch_name.startswith("00-"):
            try:
                CoordinateCalibrator.calibrate_and_save_profile(book_dir, ch_pdf)
                if is_journal_doc:
                    target_prof = cand_canon if cand_canon.exists() else cand_legacy
                    try:
                        with open(target_prof, 'r', encoding='utf-8') as f_prof:
                            prof_data = json.load(f_prof)
                        prof_data["is_journal"] = True
                        for p in {cand_canon, cand_legacy}:
                            with open(p, 'w', encoding='utf-8') as f_prof:
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
        elif ch_name.startswith("00-"):
            _style["generate_toc"] = False
            _style["gloss_placement"] = "none"
            _style["prepend_chapter_title_if_missing"] = False
        _ld_set_style(_style)
        _digital_pdf_mod._STYLE = _style


        if is_scanned is None:
            check_path = book_source_pdf or chapter_pdf_path
            p_names = [p.name.lower() for p in Path(check_path).resolve().parents]
            if any(name in ("scanned-pdf", "scanned_pdf", "scanned") for name in p_names):
                is_scanned = True
            elif any(name in ("digital-pdf", "digital_pdf", "digital") for name in p_names):
                is_scanned = False
            else:
                is_scanned = self.is_scanned_pdf(str(ch_pdf))

        print(f"\n{'='*70}\n[STAGE 2: CONVERT CHAPTER] {ch_name} ({total_pages} page(s))\n{'='*70}")
        print(f"  Mode: {'SCANNED BOOK (Neural Layout + LaTeX)' if is_scanned else 'BORN-DIGITAL VECTOR (XML Styles + LaTeX)'}")

        # Delegate Markdown conversion to MarkdownConversionService
        conv_service = MarkdownConversionService()
        prof_obj = None
        target_prof_path = cand_canon if cand_canon.exists() else (cand_legacy if cand_legacy.exists() else None)
        if target_prof_path:
            try:
                with open(target_prof_path, 'r', encoding='utf-8') as f:
                    prof_obj = DocumentProfile.from_dict(json.load(f))
            except Exception:
                pass
        if prof_obj is None:
            prof_obj = DocumentProfile.from_dict(_style)

        prof_obj.meta.mode = "scanned" if is_scanned else "digital"
        prof_obj.meta.doc_type = "literature" if is_journal_doc else "book"

        conv_opts = ConversionOptions(
            extract_images=True,
            crop_figures_and_tables=True,
            uniform_crop_margin_pt=getattr(prof_obj.geometry, "uniform_crop_margin_pt", 16.0),
            generate_toc=_style.get("generate_toc", True),
            toc_mode=_style.get("toc_mode", "open"),
            prepend_title_if_missing=_style.get("prepend_chapter_title_if_missing", True),
            embed_css=True,
            output_standalone_css=True,
            is_front_matter=ch_name.startswith("00-"),
            custom_title=ch_name,
        )

        conv_res = conv_service.convert(
            pdf_path=ch_pdf,
            profile=prof_obj,
            output_dir=ch_dir,
            options=conv_opts,
            context={
                "chapter_name": ch_name,
                "is_journal_doc": is_journal_doc,
                "specialist_enricher": DoclingBlueprintAdapter.enrich_blueprint,
            },
        )
        saved_images = conv_res.images
        full_md = conv_res.markdown
        print(f"  [✓] Genuine figures/photos extracted: {len(saved_images)}")

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

        # 3.1 Persist chapter audit & visual defects into book_profile.json
        try:
            cand_canon = book_dir / "profile.json"
            cand_legacy = book_dir / "book_profile.json"
            prof_file = cand_canon if cand_canon.exists() else cand_legacy
            if prof_file.exists():
                with open(prof_file, "r", encoding="utf-8") as pf:
                    raw_prof = json.load(pf)
                doc_prof = DocumentProfile.from_dict(raw_prof)
                doc_prof.record_chapter_audit(
                    chapter_name=ch_name,
                    audit_data=v_res,
                    visual_data=v_res.get("checks", {}).get("visual_audit"),
                )
                prof_dict = doc_prof.to_dict()
                for target_p in {cand_canon, cand_legacy}:
                    with open(target_p, "w", encoding="utf-8") as pf:
                        json.dump(prof_dict, pf, indent=2, ensure_ascii=False)
                print(f"  [🧠 Profile Sync] Recorded chapter audit and visual fidelity into {prof_file.name}")
        except Exception as prof_err:
            logger.debug("Failed to record chapter audit into profile.json: %s", prof_err)

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
                    print(f"  [💡 AI Review] Saved {len(applied)} proposed correction(s). Run: python3 literature_parser.services.py review -c \"{ch_dir}\"")

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
            split_pdf=True,
            markdown_generated=True,
            images_count=len(saved_images),
            verification_pass=v_res['passed'],
            accuracy_percent=v_res.get('accuracy_percent'),
            status='VERIFIED' if v_res['passed'] else 'FAILED'
        )

        return v_res

    def ensure_book_profile(
        self,
        book_dir: Path,
        sections: list,
        chapters_root: str,
        pdf_path: str,
    ) -> None:
        """Pre-flight profiling: establishes canonical profile.json using pure body sample.

        Strictly excludes all Front Matter sections ('00-*') to ensure geometry, headers,
        and typography are calibrated purely from genuine body chapter content.

        Args:
            book_dir: Output root directory of the book.
            sections: Discovered section definitions.
            chapters_root: Path string to chapters subfolder.
            pdf_path: Full book source PDF filepath.
        """
        cand_canon = book_dir / "profile.json"
        cand_legacy = book_dir / "book_profile.json"
        if cand_canon.exists() or cand_legacy.exists():
            return

        body_sections = [s for s in sections if not s['name'].startswith('00-')]
        if not body_sections:
            return

        sample_sec = body_sections[0]
        s_name = sample_sec['name']
        s_start = sample_sec['start']
        s_end = sample_sec['end']
        s_ch_dir = os.path.join(chapters_root, s_name)
        os.makedirs(s_ch_dir, exist_ok=True)
        s_ch_pdf = os.path.join(s_ch_dir, f"{s_name}.pdf")

        if not os.path.exists(s_ch_pdf) or os.path.getsize(s_ch_pdf) == 0:
            PDFSplitter.split_chapter(pdf_path, s_start, s_end, s_ch_pdf)

        try:
            from literature_parser.adapters.profiler.stage0_profiler import Stage0Profiler
            Stage0Profiler.probe_and_persist_profile(Path(s_ch_pdf), book_dir, use_ollama=self.use_ollama)
            logger.info("Pre-flight calibrated book profile via Stage0Profiler from pure body sample %s", s_name)
        except Exception as e:
            logger.debug("Stage0Profiler pre-flight failed (%s); falling back to legacy.", e)
            try:
                CoordinateCalibrator.calibrate_and_save_profile(book_dir, Path(s_ch_pdf))
                scanner = SpecialBlockScanner(book_dir)
                scanner.scan_and_update([Path(s_ch_pdf)], max_pages_per_chapter=8)
                logger.info("Pre-flight calibrated book profile from pure body sample %s", s_name)
            except Exception as e2:
                logger.debug("Automatic pre-flight book calibration skipped: %s", e2)

    # =========================================================================
    # STAGE 3 & ALL: Full Book / Smart Resume Engine
    # =========================================================================
    def process_pdf_book(
        self,
        pdf_path: str,
        target_chapter: str = None,
        resume: bool = False,
        parallel: bool = False,
        is_scanned: Optional[bool] = None,
        export_epub: bool = False
    ):
        QualityInvariantGuard.check_pdf_pre_split(pdf_path)

        if is_scanned is None:
            p_names = [p.name.lower() for p in Path(pdf_path).resolve().parents]
            if any(name in ("scanned-pdf", "scanned_pdf", "scanned") for name in p_names):
                is_scanned = True
            elif any(name in ("digital-pdf", "digital_pdf", "digital") for name in p_names):
                is_scanned = False

        # Check document archetype: dispatch directly to LiteraturePipeline if academic literature
        from literature_parser.services.config_manager import ConfigManager
        archetype = ConfigManager.detect_archetype(pdf_path)
        if archetype in ("literature", "journal"):
            from literature_parser.adapters.pipelines.literature_pipeline import LiteraturePipeline
            pipeline = LiteraturePipeline(
                output_dir=self.output_dir,
                processed_dir=self.processed_dir,
                use_ollama=self.use_ollama,
                ollama_model=self.ollama_model,
            )
            scanned_flag = self.is_scanned_pdf(pdf_path) if is_scanned is None else is_scanned
            res = pipeline.process(pdf_path, is_scanned=scanned_flag)
            if export_epub:
                from literature_parser.services.exporter.epub_exporter import EpubExporter
                doc_name = sanitize_filename(Path(pdf_path).stem)
                try:
                    EpubExporter.export_literature(Path(self.output_dir) / doc_name)
                except Exception as e:
                    logger.debug("EPUB export error: %s", e)
            return res

        book_name = Path(pdf_path).stem
        book_out = os.path.join(self.output_dir, sanitize_filename(book_name))
        chapters_root = os.path.join(book_out, 'chapters')
        os.makedirs(chapters_root, exist_ok=True)

        sections = self.get_pdf_sections(pdf_path)
        if not sections:
            logger.warning("No sections identified for '%s'", book_name)
            print(f"[!] Unable to identify sections for {book_name}")
            return

        # Sanitize section names: remove null bytes and control characters
        for sec in sections:
            sec['name'] = re.sub(r'[\x00-\x1f\x7f]', '', sec.get('name', '')).strip()

        ckpt = CheckpointManager(book_out, book_name)
        ckpt.init_chapters(sections)

        # Pre-flight: establish pure body profile before launching workers
        self.ensure_book_profile(Path(book_out), sections, chapters_root, pdf_path)

        if target_chapter:
            queries = [q.strip().lower() for q in str(target_chapter).split(",") if q.strip()]
            sections = [s for s in sections if any(q in s['name'].lower() for q in queries)]
            if not sections:
                print(f"[!] Chapter(s) '{target_chapter}' not found.")
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
                if self.interrupted:
                    return None
                i_idx, s_sec = item
                s_name = s_sec['name']
                s_start = s_sec['start']
                s_end = s_sec['end']
                s_ch_dir = os.path.join(chapters_root, s_name)
                os.makedirs(s_ch_dir, exist_ok=True)
                s_ch_pdf = os.path.join(s_ch_dir, f"{s_name}.pdf")
                try:
                    if not os.path.exists(s_ch_pdf) or os.path.getsize(s_ch_pdf) == 0:
                        PDFSplitter.split_chapter(pdf_path, s_start, s_end, s_ch_pdf)
                    ckpt.update_status(s_name, split_pdf=True, status='SPLIT')
                    return self.convert_single_chapter(s_ch_pdf, book_source_pdf=pdf_path, is_scanned=is_scanned)
                except Exception as ch_err:
                    logger.error("Chapter '%s' raised exception during parallel run: %s", s_name, ch_err)
                    ckpt.update_status(s_name, verification_pass=False, status='FAILED', error=str(ch_err))
                    return {"chapter": s_name, "passed": False, "error": str(ch_err)}

            pool.execute_parallel(pending_sections, _process_task, desc="M5 Parallel Chapters")
        else:
            for idx, sec in pending_sections:
                if self.interrupted:
                    print(f"[!] Process paused at section {sec['name']}. Resume later with: book_processor resume")
                    break

                if self.circuit_breaker.is_tripped():
                    logger.warning(
                        "[Circuit Breaker Advisory] Multiple chapters had verification warnings, but continuing unattended batch."
                    )

                name = sec['name']
                start = sec['start']
                end = sec['end']

                print(f"\n  [{idx:02d}/{len(sections):02d}] Processing Chapter: {name} (pp. {start}-{end})...")
                ch_dir = os.path.join(chapters_root, name)
                os.makedirs(ch_dir, exist_ok=True)
                ch_pdf = os.path.join(ch_dir, f"{name}.pdf")

                try:
                    # 1. Split PDF (skip if already exists)
                    if not os.path.exists(ch_pdf) or os.path.getsize(ch_pdf) == 0:
                        PDFSplitter.split_chapter(pdf_path, start, end, ch_pdf)
                    ckpt.update_status(name, split_pdf=True, status='SPLIT')

                    # 2. Convert & Auto-Verify (with auto-retry feedback loop)
                    self.convert_single_chapter(ch_pdf, book_source_pdf=pdf_path, is_scanned=is_scanned)
                except Exception as ch_err:
                    logger.error("Chapter '%s' raised exception during serial run: %s", name, ch_err)
                    ckpt.update_status(name, verification_pass=False, status='FAILED', error=str(ch_err))

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

            from literature_parser.services.utils.obsidian_linker import (
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

        if export_epub:
            from literature_parser.services.exporter.epub_exporter import EpubExporter
            from literature_parser.adapters.verification.epub_visual_auditor import EpubVisualAuditor
            try:
                EpubExporter.export_book(Path(book_out))
                print(f"  [📸 EPUB AUDITOR] 啟動全書 EPUB 逐頁截圖與閉環自動修復...")
                aud_res = EpubVisualAuditor.closed_loop_heal_book_epub(Path(book_out))
                print(f"  [✓] EPUB 逐頁截圖完成: 共渲染 {aud_res.get('total_pages_rendered', 0)} 頁，剩餘排版缺陷: {aud_res.get('remaining_defects', 0)}")
            except Exception as e:
                logger.debug("EPUB export / visual audit error: %s", e)

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
