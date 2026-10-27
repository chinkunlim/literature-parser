"""
Visual Cross-Audit Orchestrator
===============================
Coordinates full-scale, ultra-dense page-by-page visual cross-auditing across
textbooks in the library. Renders EPUB and PDF pages to high-resolution PNGs,
evaluating them with Apple Vision OCR, MiniCPM-V, and Llama 3.2 Vision.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature_parser.config.settings import load_config
from literature_parser.services.verification.dual_render_comparator import DualRenderComparator

logger = logging.getLogger(__name__)


class VisualCrossAuditOrchestrator:
    """Orchestrator executing full-scale Tri-Vision cross-auditing on textbooks."""

    def __init__(self, comparator: Optional[DualRenderComparator] = None) -> None:
        """Initializes the visual cross-audit orchestrator.

        Args:
            comparator: Configured DualRenderComparator instance.
        """
        self.comparator = comparator or DualRenderComparator()
        self.cfg = load_config()

    def audit_book(
        self,
        book_dir: Path | str,
        sample_stride: int = 1,
        max_chapters: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs full dual-render visual cross-audit for a book.

        Args:
            book_dir: Directory of the book (containing `chapters/` and EPUB).
            sample_stride: Page sampling stride (1 = every page).
            max_chapters: Optional limit on number of chapters to audit.

        Returns:
            Dictionary containing audit summary, chapter reports, and defect count.
        """
        b_dir = Path(book_dir)
        ch_dir = b_dir / "chapters"
        eval_base = self.cfg.data_dir / "evals" / "visual_audit" / b_dir.name
        eval_base.mkdir(parents=True, exist_ok=True)

        epubs_dir = self.cfg.data_dir / "output" / "epubs"
        target_epub = epubs_dir / f"{b_dir.name}.epub"
        if not target_epub.exists():
            target_epub = b_dir / f"{b_dir.name}.epub"

        chapter_dirs = sorted([d for d in ch_dir.iterdir() if d.is_dir()])
        if max_chapters is not None:
            chapter_dirs = chapter_dirs[:max_chapters]

        chapter_reports: List[Dict[str, Any]] = []
        total_defects = 0
        total_pages_audited = 0
        total_coverage_accum = 0.0

        for ch_d in chapter_dirs:
            pdf_path = ch_d / f"{ch_d.name}.pdf"
            if not pdf_path.exists():
                logger.warning("Chapter PDF missing for %s: %s", ch_d.name, pdf_path)
                continue

            report = self.comparator.cross_audit_chapter(
                chapter_name=ch_d.name,
                pdf_path=pdf_path,
                epub_path=target_epub,
                eval_dir=eval_base,
                sample_stride=sample_stride,
            )
            chapter_reports.append(report)
            print(
                f"   [Ch {len(chapter_reports)}/{len(chapter_dirs)}] {ch_d.name}: "
                f"{report.get('inspected_pages', 0)} pages, "
                f"recall={report.get('average_content_coverage', 0.0)}%, "
                f"defects={report.get('defect_count', 0)}"
            )
            total_defects += report.get("defect_count", 0)
            pages_cnt = report.get("inspected_pages", 0)
            total_pages_audited += pages_cnt
            total_coverage_accum += report.get("average_content_coverage", 0.0) * pages_cnt

        avg_overall_coverage = (
            round(total_coverage_accum / max(1, total_pages_audited), 2)
            if total_pages_audited > 0
            else 0.0
        )

        audit_summary = {
            "book_name": b_dir.name,
            "passed": total_defects == 0,
            "total_chapters_audited": len(chapter_reports),
            "total_pages_audited": total_pages_audited,
            "total_defects": total_defects,
            "average_content_coverage": avg_overall_coverage,
            "chapters": chapter_reports,
        }

        # Persist summary report
        report_file = eval_base / "cross_audit_summary.json"
        try:
            report_file.write_text(json.dumps(audit_summary, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as save_err:
            logger.warning("Failed saving cross audit report for %s: %s", b_dir.name, save_err)

        return audit_summary
