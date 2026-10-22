"""Non-interventional batch runner for all input books in DATA_DIR.

Executes sequential processing of all input books without modifying any application code.
Enforces the strict requirement: if any chapter fails verification or raises an unhandled
error, immediately halt the current book, log its defect profile, and proceed to the next book.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature_parser.adapters.core.orchestrator import BookProcessorOrchestrator
from literature_parser.config.settings import load_config
from literature_parser.services.core.checkpoint import CheckpointManager
from literature_parser.services.core.invariants import QualityInvariantGuard
from literature_parser.services.core.splitter import PDFSplitter
from literature_parser.services.utils.text_utils import sanitize_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("batch_audit_runner")


def discover_input_books(input_books_dir: Path) -> List[Path]:
    """Finds all target book PDF files in the input directory.

    Args:
        input_books_dir: Directory containing input books (digital and scanned).

    Returns:
        List of absolute paths to discovered book PDF files.
    """
    found: List[Path] = []
    if not input_books_dir.exists():
        logger.warning("Input directory does not exist: %s", input_books_dir)
        return found

    for root, _, files in os.walk(input_books_dir):
        if "samples" in root:
            continue
        for file in sorted(files):
            if file.lower().endswith(".pdf") and not file.startswith("."):
                found.append(Path(root) / file)
    return found


def run_book_until_first_failure(
    orch: BookProcessorOrchestrator,
    pdf_path: Path,
    output_books_dir: Path,
) -> Dict[str, Any]:
    """Processes a single book chapter by chapter, stopping immediately at first failure.

    Args:
        orch: Initialized BookProcessorOrchestrator instance.
        pdf_path: Path to the target book PDF.
        output_books_dir: Root output directory for books.

    Returns:
        Dictionary summarizing processing results, completed chapters, and any failure encountered.
    """
    book_name = pdf_path.stem
    book_out = output_books_dir / sanitize_filename(book_name)
    chapters_root = book_out / "chapters"
    chapters_root.mkdir(parents=True, exist_ok=True)

    result: Dict[str, Any] = {
        "book_name": book_name,
        "pdf_path": str(pdf_path),
        "status": "NOT_STARTED",
        "total_sections": 0,
        "completed_chapters": [],
        "failed_chapter": None,
        "failure_reason": None,
        "error_type": None,
        "traceback": None,
        "start_time": time.time(),
        "elapsed_seconds": 0.0,
    }

    print(f"\n{'='*80}")
    print(f"[📚 BATCH AUDIT] Starting Book: {book_name}")
    print(f"  Path: {pdf_path}")
    print(f"{'='*80}\n")

    try:
        QualityInvariantGuard.check_pdf_pre_split(str(pdf_path))
    except Exception as exc:
        result["status"] = "PRE_SPLIT_FAILED"
        result["failure_reason"] = f"Invariant check failed: {exc}"
        result["error_type"] = exc.__class__.__name__
        result["traceback"] = traceback.format_exc()
        result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
        print(f"  [🛑 STOP & SWITCH] Book '{book_name}' failed invariant pre-split check: {exc}")
        return result

    # Determine scanned vs digital
    parent_names = [p.name.lower() for p in pdf_path.resolve().parents]
    if any(name in ("scanned-pdf", "scanned_pdf", "scanned") for name in parent_names):
        is_scanned = True
    elif any(name in ("digital-pdf", "digital_pdf", "digital") for name in parent_names):
        is_scanned = False
    else:
        is_scanned = orch.is_scanned_pdf(str(pdf_path))

    sections = orch.get_pdf_sections(str(pdf_path))
    if not sections:
        result["status"] = "NO_SECTIONS_FOUND"
        result["failure_reason"] = "No sections could be identified from TOC or layout scan."
        result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
        print(f"  [🛑 STOP & SWITCH] Book '{book_name}' has no identifiable sections.")
        return result

    result["total_sections"] = len(sections)
    print(f"  [ℹ] Discovered {len(sections)} sections. Mode: {'SCANNED' if is_scanned else 'DIGITAL'}")

    ckpt = CheckpointManager(str(book_out), book_name)
    ckpt.init_chapters(sections)

    # Pre-flight profile setup
    try:
        orch.ensure_book_profile(book_out, sections, str(chapters_root), str(pdf_path))
    except Exception as exc:
        logger.warning("ensure_book_profile raised non-fatal warning: %s", exc)

    # Process sequentially; STOP AT FIRST FAILURE
    for idx, sec in enumerate(sections, 1):
        ch_name = sec["name"]
        start_p = sec["start"]
        end_p = sec["end"]

        print(f"\n--- [{idx:02d}/{len(sections):02d}] Auditing Chapter: {ch_name} (pp. {start_p}-{end_p}) ---")
        ch_dir = chapters_root / ch_name
        ch_dir.mkdir(parents=True, exist_ok=True)
        ch_pdf = ch_dir / f"{ch_name}.pdf"

        # If already verified in checkpoint and markdown exists, fast-forward
        ch_md = ch_dir / f"{ch_name}.md"
        if ckpt.is_chapter_verified(ch_name) and ch_md.exists():
            print(f"  [⏩ RESUME] Chapter '{ch_name}' is already verified. Fast-forwarding...")
            result["completed_chapters"].append({
                "name": ch_name,
                "accuracy_percent": ckpt.data["chapters"].get(ch_name, {}).get("accuracy_percent", 100.0),
                "visual_audit": "PREVIOUSLY_PASSED",
            })
            continue

        # Split if needed
        try:
            if not ch_pdf.exists() or ch_pdf.stat().st_size == 0:
                PDFSplitter.split_chapter(str(pdf_path), start_p, end_p, str(ch_pdf))
            ckpt.update_status(ch_name, split_pdf=True, status="SPLIT")
        except Exception as exc:
            result["status"] = "SPLIT_FAILED"
            result["failed_chapter"] = ch_name
            result["failure_reason"] = f"Failed to split chapter: {exc}"
            result["error_type"] = exc.__class__.__name__
            result["traceback"] = traceback.format_exc()
            result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
            print(f"\n[🛑 STOP & SWITCH] Book '{book_name}' failed at Chapter '{ch_name}' during split: {exc}")
            print(">>> Switching immediately to next book as instructed! <<<\n")
            return result

        # Convert and verify
        try:
            v_res = orch.convert_single_chapter(
                str(ch_pdf),
                book_source_pdf=str(pdf_path),
                is_scanned=is_scanned,
            )
        except Exception as exc:
            result["status"] = "EXCEPTION"
            result["failed_chapter"] = ch_name
            result["failure_reason"] = f"Unhandled exception in chapter conversion: {exc}"
            result["error_type"] = exc.__class__.__name__
            result["traceback"] = traceback.format_exc()
            result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
            print(f"\n[🛑 STOP & SWITCH] Book '{book_name}' CRASHED at Chapter '{ch_name}': {exc}")
            print(">>> Switching immediately to next book as instructed! <<<\n")
            return result

        if not v_res or not v_res.get("passed", False):
            result["status"] = "VERIFICATION_FAILED"
            result["failed_chapter"] = ch_name
            result["failure_reason"] = v_res or "Empty verification result"
            result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
            print(f"\n[🛑 STOP & SWITCH] Book '{book_name}' FAILED accuracy verification at Chapter '{ch_name}'!")
            print(f"    Passed: {v_res.get('passed') if v_res else False}")
            print(f"    Accuracy: {v_res.get('accuracy_percent', 0)}%")
            print(">>> Halting this book and switching to the next book as instructed! <<<\n")
            return result

        # Chapter passed!
        print(f"  [✓] Chapter '{ch_name}' PASSED verification! (Accuracy: {v_res.get('accuracy_percent')}%)")
        result["completed_chapters"].append({
            "name": ch_name,
            "accuracy_percent": v_res.get("accuracy_percent"),
            "visual_audit": v_res.get("checks", {}).get("visual_audit"),
        })

    # If all sections passed
    result["status"] = "ALL_PASSED"
    result["elapsed_seconds"] = round(time.time() - result["start_time"], 2)
    print(f"\n[🎉 SUCCESS] Book '{book_name}' completed all {len(sections)} sections successfully!")
    return result


def main() -> int:
    """Entry point for the non-interventional batch runner.

    Returns:
        Exit code (0 for success, non-zero for fatal script errors).
    """
    app_cfg = load_config()
    input_books_dir = app_cfg.input_dir / "books"
    output_books_dir = app_cfg.output_dir / "books"
    output_books_dir.mkdir(parents=True, exist_ok=True)

    summary_file = output_books_dir.parent / "batch_audit_summary.json"

    print("=" * 80)
    print("NON-INTERVENTIONAL BATCH AUDIT RUNNER")
    print(f"Input Directory:  {input_books_dir}")
    print(f"Output Directory: {output_books_dir}")
    print(f"Ollama URL:       {app_cfg.ollama_base_url}")
    print("=" * 80)

    books = discover_input_books(input_books_dir)
    if len(sys.argv) > 1:
        filters = [arg.lower() for arg in sys.argv[1:] if not arg.startswith("-")]
        if filters:
            books = [b for b in books if any(f in b.name.lower() for f in filters)]
    print(f"Discovered {len(books)} book(s) for batch processing:")
    for i, b in enumerate(books, 1):
        print(f"  {i}. {b.name}")
    print()

    orch = BookProcessorOrchestrator(
        input_dir=str(input_books_dir),
        output_dir=str(output_books_dir),
        use_ollama=True,
        ollama_model="qwen2.5:latest",
    )

    batch_results: List[Dict[str, Any]] = []

    for idx, book_path in enumerate(books, 1):
        print(f"\n{'#'*80}")
        print(f"PROCESSING BOOK [{idx}/{len(books)}]: {book_path.name}")
        print(f"{'#'*80}")

        book_res = run_book_until_first_failure(orch, book_path, output_books_dir)
        batch_results.append(book_res)

        # Write intermediate summary
        with open(summary_file, "w", encoding="utf-8") as f_out:
            json.dump(batch_results, f_out, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("BATCH AUDIT COMPLETE - FINAL SUMMARY")
    print("=" * 80)
    for res in batch_results:
        print(f"- Book: {res['book_name']}")
        print(f"  Status:             {res['status']}")
        print(f"  Completed Chapters: {len(res['completed_chapters'])} / {res['total_sections']}")
        if res["failed_chapter"]:
            print(f"  Halted At Chapter:  {res['failed_chapter']}")
            print(f"  Failure Reason:     {res['failure_reason']}")
        print(f"  Elapsed Time:       {res['elapsed_seconds']}s")
        print()

    print(f"Detailed JSON report saved to: {summary_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
