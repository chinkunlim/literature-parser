"""Tri-Vision EPUB vs PDF Visual Cross-Audit Runner.
==================================================
Runs high-fidelity page-by-page visual cross-auditing across all 5 textbooks in the library.
Compares rendered EPUB pages against source PDF pages using:
1. Apple Vision Native OCR (Swift VNRecognizeTextRequest)
2. MiniCPM-V 2.6 (Local Ollama vision model)
3. Llama 3.2 Vision 11B (Local Ollama multimodal vision model)

Outputs structured visual audit reports to:
$DATA_DIR/evals/visual_audit/<book>/cross_audit_summary.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from literature_parser.config.logging_setup import setup_logging
from literature_parser.config.settings import load_config
from literature_parser.services.verification.visual_cross_audit_orchestrator import (
    VisualCrossAuditOrchestrator,
)

logger = logging.getLogger(__name__)


def run_cross_audit_for_books(
    sample_stride: int = 1,
    book_filter: str | None = None,
    max_chapters: int | None = None,
) -> int:
    """Runs Tri-Vision dual-render cross audit across library books.

    Args:
        sample_stride: Stride for sampling pages (1 = every page).
        book_filter: Substring to filter specific book directory names.
        max_chapters: Optional limit on number of chapters to audit per book.

    Returns:
        Exit code (0 for success, 1 if any book fails).
    """
    cfg = load_config()
    books_dir = cfg.output_dir / "books"
    if not books_dir.exists():
        print(f"❌ Books directory not found: {books_dir}")
        return 1

    book_dirs = sorted([d for d in books_dir.iterdir() if d.is_dir()])
    if book_filter:
        book_dirs = [d for d in book_dirs if book_filter.lower() in d.name.lower()]

    if not book_dirs:
        print(f"⚠️ No books matched filter: {book_filter}")
        return 1

    orchestrator = VisualCrossAuditOrchestrator()
    print("=" * 80)
    print("🔍 [TRI-VISION CROSS-AUDIT] Starting Dual-Render EPUB vs PDF Inspection")
    print(f"📚 Found {len(book_dirs)} books to verify")
    print(f"📐 Sample Stride: {sample_stride} (1 = 100% dense all-page audit)")
    print("=" * 80)

    total_books_passed = 0
    all_book_summaries: List[Dict[str, Any]] = []

    start_total_time = time.time()

    for idx, b_dir in enumerate(book_dirs, start=1):
        print(f"\n📖 [{idx}/{len(book_dirs)}] Processing Book: {b_dir.name}")
        b_start = time.time()
        summary = orchestrator.audit_book(
            book_dir=b_dir,
            sample_stride=sample_stride,
            max_chapters=max_chapters,
        )
        elapsed = time.time() - b_start
        all_book_summaries.append(summary)

        status_str = "✅ PASSED" if summary.get("passed", False) else "⚠️ DEFECTS DETECTED"
        if summary.get("passed", False):
            total_books_passed += 1

        print(
            f"   Result: {status_str} | Chapters: {summary.get('total_chapters_audited', 0)} | "
            f"Pages: {summary.get('total_pages_audited', 0)} | "
            f"Avg Recall: {summary.get('average_content_coverage', 0.0)}% | "
            f"Defects: {summary.get('total_defects', 0)} | "
            f"Time: {elapsed:.1f}s"
        )

        # Print details of any detected defects
        for ch in summary.get("chapters", []):
            if ch.get("defect_count", 0) > 0:
                print(f"     ⚠️ [{ch.get('chapter_name')}]: {ch.get('defect_count')} defect(s)")
                for d in ch.get("defects", [])[:5]:
                    print(f"        - Page {d.get('pdf_page_index', '?')}: {d.get('defects')}")

    total_time = time.time() - start_total_time

    print("\n" + "=" * 80)
    print("📊 [TRI-VISION AUDIT SUMMARY REPORT]")
    print(f"• Total Books Audited: {len(book_dirs)}")
    print(f"• Total Books Passed: {total_books_passed}/{len(book_dirs)}")
    print(f"• Total Time Elapsed: {total_time:.1f}s")
    print("=" * 80)

    return 0 if total_books_passed == len(book_dirs) else 1


def main() -> None:
    """CLI entrypoint for running visual cross-auditing."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Tri-Vision EPUB vs PDF Cross-Audit Runner")
    parser.add_argument("--stride", type=int, default=1, help="Page sampling stride (default: 1)")
    parser.add_argument("--book", type=str, default=None, help="Book name filter")
    parser.add_argument("--max-chapters", type=int, default=None, help="Max chapters per book")

    args = parser.parse_args()
    exit_code = run_cross_audit_for_books(
        sample_stride=args.stride,
        book_filter=args.book,
        max_chapters=args.max_chapters,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
