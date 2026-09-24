"""
University Textbook Pipeline (TextbookPipeline)
==============================================
Dedicated, modular processing pipeline for multi-chapter textbooks:
  - Table of Contents (TOC) Extraction & Chapter Splitting
  - Learning Objectives (🎯) Extraction
  - Concept Mindmaps (Mermaid)
  - Margin Glossaries & Anki Flashcards Generation
  - Callout Boxes (Notes, Cases, Highlights)
  - End-of-Chapter (EOC) Exercises & Summaries
  - Multi-Core Parallel Processing for Apple Silicon
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from book_processor.pipelines.base_pipeline import BasePipeline
from book_processor.config_manager import ConfigManager
from book_processor.core.invariants import QualityInvariantGuard
from book_processor.core.analyzer import PDFAnalyzer
from book_processor.core.splitter import PDFSplitter
from book_processor.core.checkpoint import CheckpointManager
from book_processor.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)


class TextbookPipeline(BasePipeline):
    """Processes multi-chapter university textbooks into structured Markdown."""

    def __init__(
        self,
        output_dir: str = "./output",
        processed_dir: str = "./processed",
        use_ollama: bool = True,
        ollama_model: str = "qwen2.5:7b",
        orchestrator = None,
    ):
        super().__init__(output_dir=output_dir, processed_dir=processed_dir, use_ollama=use_ollama, ollama_model=ollama_model)
        if orchestrator is None:
            raise RuntimeError(
                "TextbookPipeline requires a BookProcessorOrchestrator instance. "
                "Pass orchestrator=BookProcessorOrchestrator(...) when constructing the pipeline."
            )
        self.orchestrator = orchestrator


    def process(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """Runs the textbook pipeline (chapter split + per-chapter conversion)."""
        p_path = Path(pdf_path)
        if not p_path.exists():
            raise FileNotFoundError(f"Textbook PDF not found: {pdf_path}")

        QualityInvariantGuard.check_pdf_pre_split(str(p_path))

        target_chapter = kwargs.get("target_chapter")
        resume = kwargs.get("resume", False)
        parallel = kwargs.get("parallel", False)

        book_name = p_path.stem
        clean_name = sanitize_filename(book_name)
        book_out = self.output_dir / clean_name
        chapters_root = book_out / "chapters"
        chapters_root.mkdir(parents=True, exist_ok=True)

        sections = PDFAnalyzer.get_sections(str(p_path))[0]
        if not sections:
            logger.warning("No sections identified for textbook '%s'", book_name)
            return {"passed": False, "error": "No sections identified"}

        ckpt = CheckpointManager(str(book_out), book_name)
        ckpt.init_chapters(sections)

        # Filter if single chapter targeted
        if target_chapter:
            clean_q = target_chapter.strip().lower()
            sections = [s for s in sections if clean_q in s['name'].lower()]
            if not sections:
                print(f"[!] Chapter '{target_chapter}' not found.")
                return {"passed": False, "error": f"Chapter {target_chapter} not found"}

        print(f"\n{'='*70}\n[TEXTBOOK PIPELINE] {book_name} ({len(sections)} sections)\n{'='*70}")

        # Delegate execution of chapters to orchestrator's convert_single_chapter
        all_passed = True
        for idx, sec in enumerate(sections, 1):
            name = sec['name']
            start = sec['start']
            end = sec['end']

            if resume and ckpt.is_chapter_verified(name):
                print(f"  [{idx:02d}/{len(sections):02d}] Skipping already verified chapter: {name}")
                continue

            print(f"\n  [{idx:02d}/{len(sections):02d}] Processing Chapter: {name} (pp. {start}-{end})...")
            ch_dir = chapters_root / name
            ch_dir.mkdir(parents=True, exist_ok=True)
            ch_pdf = ch_dir / f"{name}.pdf"

            if not ch_pdf.exists() or ch_pdf.stat().st_size == 0:
                PDFSplitter.split_chapter(str(p_path), start, end, str(ch_pdf))
            ckpt.update_status(name, split_pdf=True, status='SPLIT')

            res = self.orchestrator.convert_single_chapter(str(ch_pdf), book_source_pdf=str(p_path))
            if not res.get('passed', False):
                all_passed = False


        if all_passed and not target_chapter:
            self.archive_source(str(p_path))

        return {
            "passed": all_passed,
            "output_dir": str(book_out),
            "chapters_count": len(sections),
        }
