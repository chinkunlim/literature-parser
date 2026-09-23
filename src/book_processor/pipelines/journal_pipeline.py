"""
Academic Journal Article Pipeline (JournalPipeline)
===================================================
Dedicated, modular processing pipeline for single-article academic journal PDFs.
Completely separated from textbook logic:
  - No Chapter Splitting (treats paper as a single atomic document)
  - No Table of Contents (TOC) injection
  - No Learning Objectives (🎯) or Concept Maps
  - No Margin Glossaries or Anki flashcards
  - Universal Two-Column Band Flow Engine
  - Universal Hanging-Indent Reference List Parser
  - IMRAD Headings & Emergent Sections Resolver
  - Academic Typographic CSS Injection
  - Closed-Loop Multi-Metric Verification + Ollama Auto-Healing
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from book_processor.pipelines.base_pipeline import BasePipeline
from book_processor.config_manager import ConfigManager
from book_processor.core.invariants import QualityInvariantGuard
from book_processor.core.image_manager import ImageManager
from book_processor.core.analyzer import PDFAnalyzer
from book_processor.core.learner import GlobalLearner
from book_processor.parsers.digital_pdf import DigitalPDFParser
import book_processor.parsers.digital_pdf as _digital_pdf_mod
from book_processor.parsers.scanned_pdf import ScannedPDFParser
from book_processor.parsers.layout_detector import set_style as _ld_set_style, load_style
from book_processor.parsers.journal.imrad_resolver import IMRADResolver
from book_processor.parsers.journal.reference_parser import ReferenceParser
from book_processor.verification.verifier import AccuracyVerifier
from book_processor.verification.ollama_healer import OllamaHealer
from book_processor.utils.text_utils import sanitize_filename, stitch_cross_page_continuity

logger = logging.getLogger(__name__)

# Standard academic styling injected into journal Markdown
ACADEMIC_JOURNAL_CSS = """<style>
/* Academic Journal Layout Stylesheet */
body {
  font-family: 'Times New Roman', Times, serif;
  line-height: 1.5;
  text-align: justify;
}
h1 {
  text-align: center;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
table {
  width: 100%;
  max-width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
  display: table !important;
}
table th, table td {
  padding: 6px 10px;
}
</style>
"""


class JournalPipeline(BasePipeline):
    """Processes academic journal articles into high-fidelity Markdown."""

    def process(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """Runs the end-to-end journal pipeline."""
        p_path = Path(pdf_path)
        if not p_path.exists():
            raise FileNotFoundError(f"Journal PDF not found: {pdf_path}")

        # Invariant check
        QualityInvariantGuard.check_pdf_pre_split(str(p_path))

        doc_name = p_path.stem
        clean_name = sanitize_filename(doc_name)
        doc_out = self.output_dir / clean_name
        doc_images_dir = doc_out / "images"
        doc_out.mkdir(parents=True, exist_ok=True)

        total_pages = PDFAnalyzer.get_page_count(str(p_path))

        # ---------------------------------------------------------------------
        # Stage 1: Load Hierarchical Configuration (L1 -> L2 -> L3 -> L4)
        # ---------------------------------------------------------------------
        config = self.load_pipeline_config(str(p_path), archetype="journal")
        ConfigManager.save_instance_profile(doc_out, config)

        # Configure DigitalPDFParser specifically for journal articles
        style = dict(config.get("features", {}))
        style["is_journal_article"] = True
        style["generate_toc"] = False
        style["gloss_placement"] = "none"
        style["prepend_chapter_title_if_missing"] = False
        style["has_learning_objectives"] = False
        style["has_concept_map"] = False
        style["images_dir"] = str(doc_images_dir)
        _ld_set_style(style)
        _digital_pdf_mod._STYLE = style

        is_scanned = kwargs.get("is_scanned", False)

        print(f"\n{'='*70}\n[JOURNAL PIPELINE] {doc_name} ({total_pages} page(s))\n{'='*70}")
        print(f"  Publisher: {config.get('publisher', 'Generic').upper()}")
        print(f"  Mode: {'SCANNED (OCR Layout)' if is_scanned else 'BORN-DIGITAL VECTOR (Two-Column Flow)'}")

        # ---------------------------------------------------------------------
        # Stage 2: Extract Genuine Figures/Photos
        # ---------------------------------------------------------------------
        raw_images = ImageManager.extract_pdf_images(str(p_path), is_scanned=is_scanned)
        saved_images = []
        if raw_images:
            doc_images_dir.mkdir(parents=True, exist_ok=True)
            for seq, img in enumerate(raw_images, 1):
                p = img['page']
                ext = img['ext']
                fname = f"{p:03d}_{seq:03d}.{ext}"
                dest = doc_images_dir / fname
                with open(dest, 'wb') as f_out:
                    f_out.write(img['data'])
                img['filename'] = fname
                saved_images.append(img)
        print(f"  [✓] Genuine figures/charts extracted: {len(saved_images)}")

        # ---------------------------------------------------------------------
        # Stage 3: Page Extraction & Two-Column Reading Flow
        # ---------------------------------------------------------------------
        md_parts = []
        if not is_scanned:
            DigitalPDFParser.reset_chapter_state()

        with tempfile.TemporaryDirectory() as work_tmp:
            for p in range(1, total_pages + 1):
                p_imgs = [img for img in saved_images if img['page'] == p]
                if is_scanned:
                    p_md = ScannedPDFParser.process_scanned_page(str(p_path), p, work_tmp)
                else:
                    p_md = DigitalPDFParser.parse_page_to_markdown(str(p_path), p, p_imgs)
                if p_md:
                    md_parts.append(f"<!-- Page {p} -->\n{p_md}")

        full_md = '\n\n'.join(md_parts).strip()

        # ---------------------------------------------------------------------
        # Stage 4: Structure Resolution & Typography
        # ---------------------------------------------------------------------
        # Ensure top-level title is promoted to # (H1)
        if not re.search(r'^\s*#\s+[^\n]+', full_md):
            m_first_h = re.search(r'###\s+([^\n]+)(?:\n+###\s+([^\n]+))?', full_md)
            if m_first_h:
                t1 = m_first_h.group(1).strip()
                t2 = m_first_h.group(2).strip() if m_first_h.group(2) else ""
                combined_title = f"{t1} {t2}".strip()
                full_md = full_md[:m_first_h.start()] + f"# {combined_title}" + full_md[m_first_h.end():]

        # Resolve IMRAD structure & emergent sections
        full_md = IMRADResolver.resolve_structure(full_md, config=config)

        # Standardize hanging-indent references
        full_md = ReferenceParser.clean_document_references(full_md)

        # Apply symbol normalizations from shared knowledge
        shared_symbols = config.get("shared_symbols", {})
        for sym, rep in shared_symbols.items():
            if sym in full_md:
                full_md = full_md.replace(sym, rep)

        # Stitch cross-page continuity
        full_md = stitch_cross_page_continuity(full_md)

        # Prepend Academic CSS
        if ACADEMIC_JOURNAL_CSS.strip() not in full_md:
            full_md = f"{ACADEMIC_JOURNAL_CSS}\n{full_md}"

        # Save primary document Markdown
        md_file = doc_out / f"{clean_name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(full_md + '\n')
        print(f"  [✓] Markdown generated: {md_file.name}")

        # ---------------------------------------------------------------------
        # Stage 5: Dual Verification
        # ---------------------------------------------------------------------
        # ── Global Learning Pre-Application ──────────────────────────────────
        # Apply all globally-learned journal fix rules before Ollama verification,
        # so recurring issues from previous papers never waste Ollama compute.
        try:
            full_md, _pre_fixes = GlobalLearner.apply_known_fixes(full_md, archetype="journal")
            if _pre_fixes:
                print(f"  [🧠 Global Learn] Pre-applied {len(_pre_fixes)} known fix rule(s).")
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(full_md + '\n')
        except Exception as _gl_err:
            logger.debug("GlobalLearner pre-application skipped: %s", _gl_err)

        print(f"  [*] Running automatic accuracy verification...")
        verifier = AccuracyVerifier(use_ollama=self.use_ollama, ollama_model=self.ollama_model)
        v_res = verifier.verify_chapter(str(doc_out), expected_pages=total_pages)

        # ---------------------------------------------------------------------
        # Stage 6: Closed-Loop Ollama Auto-Healing
        # ---------------------------------------------------------------------
        if not v_res.get('passed', True) and self.use_ollama:
            healer = OllamaHealer(model_name=self.ollama_model)
            if healer.is_available:
                healed_md, modified, fixes = healer.heal_markdown(
                    full_md, v_res, doc_name=clean_name, archetype="journal"
                )
                if modified:
                    full_md = healed_md
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(full_md + '\n')
                    print(f"  [*] Re-running verification following Ollama healing...")
                    v_res = verifier.verify_chapter(str(doc_out), expected_pages=total_pages)


        # ---------------------------------------------------------------------
        # Stage 7: Status Manifest & Archival
        # ---------------------------------------------------------------------
        status_file = doc_out / "processing_status.json"
        status_payload = {
            "archetype": "journal",
            "doc_name": doc_name,
            "total_pages": total_pages,
            "passed": v_res.get("passed", False),
            "accuracy_percent": v_res.get("accuracy_percent", 0),
            "images_extracted": len(saved_images),
            "publisher": config.get("publisher"),
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, indent=2)

        if v_res.get("passed", False):
            print(f"\n[✓ JOURNAL COMPLETE] 100% verified! Output saved in: {doc_out}\n")
            # If input file was in inbox, archive it
            if "inbox" in str(p_path):
                self.archive_source(str(p_path))

        return {
            "passed": v_res.get("passed", False),
            "output_dir": str(doc_out),
            "markdown_file": str(md_file),
            "verification": v_res,
        }
