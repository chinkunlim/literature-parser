#!/usr/bin/env python3
"""Integration Test: Research Methods Split & Profile Pipeline.

Validates the complete literature-parser pipeline from start through
PDF splitting and layout profiling on 'Research Methods, Design, and Analysis 13th ed.pdf'.

Phases executed:
  0. Safe Backup: Backs up any existing output directory to a timestamped folder.
  1. Pre-flight Checks: File existence, hardware safety, PDF page invariants, and archetype.
  2. TOC & Section Discovery: Extracts and verifies section boundaries and continuity.
  3. PDF Splitting: Splits all chapters and verifies page counts against strict invariants.
  4. Book Profiling: Calibrates geometry, facing margins, and special blocks on pure body samples.
  5. Profile Validation: Asserts schema compliance of canonical profile.json.
  6. (Optional) Ollama Profiling: Connects to local Ollama if requested for semantic verification.

Usage:
  uv run python scripts/test_split_and_profile.py
  uv run python scripts/test_split_and_profile.py --ollama
  uv run python scripts/test_split_and_profile.py --restore
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from literature_parser.adapters.core.orchestrator import BookProcessorOrchestrator
from literature_parser.adapters.guards.hardware import check_hardware_safety
from literature_parser.adapters.profiler.ollama_profiler import (
    DEFAULT_OLLAMA_URL,
    get_installed_models,
    is_ollama_available,
)
from literature_parser.config.settings import load_config
from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.config_manager import ConfigManager
from literature_parser.services.core.checkpoint import CheckpointManager
from literature_parser.services.core.invariants import (
    InvariantViolationError,
    QualityInvariantGuard,
)
from literature_parser.services.core.splitter import PDFSplitter
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.services.profiler.special_block_scanner import SpecialBlockScanner
from literature_parser.services.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)


def setup_test_logging() -> None:
    """Configures console and file logging for the integration test runner.

    Args:
        None.

    Returns:
        None.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def backup_existing_output(output_dir: Path) -> Optional[Path]:
    """Safely moves existing output directory to a timestamped backup directory.

    If an original backup already exists, removes the intermediate test directory
    to keep the original backup untouched.

    Args:
        output_dir: Target book output directory to back up.

    Returns:
        Path to the primary backup directory if available, None otherwise.
    """
    if not output_dir.exists():
        return None

    # Check if directory has contents
    has_contents = any(output_dir.iterdir())
    if not has_contents:
        return None

    prefix = f"{output_dir.name}.bak."
    existing_backups = sorted(
        [p for p in output_dir.parent.glob(f"{prefix}*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
    )
    if existing_backups:
        logger.info("Preserving existing primary backup '%s', cleaning current test folder", existing_backups[0].name)
        shutil.rmtree(str(output_dir))
        return existing_backups[0]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output_dir.with_name(f"{output_dir.name}.bak.{timestamp}")
    logger.info("Backing up existing output from '%s' to '%s'", output_dir, backup_path)
    shutil.move(str(output_dir), str(backup_path))
    return backup_path


def restore_latest_backup(output_dir: Path) -> bool:
    """Restores the most recent backup folder to the target output directory.

    Args:
        output_dir: Target book output directory.

    Returns:
        True if a backup was found and restored successfully, False otherwise.
    """
    parent = output_dir.parent
    prefix = f"{output_dir.name}.bak."
    backups = sorted(
        [p for p in parent.glob(f"{prefix}*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        print(f"❌ No backup directories matching '{prefix}*' found in {parent}")
        return False

    latest_backup = backups[0]
    print(f"📦 Found latest backup: {latest_backup.name}")
    if output_dir.exists():
        temp_trash = output_dir.with_name(f"{output_dir.name}.trash.{int(time.time())}")
        print(f"  Moving existing test output to temporary archive: {temp_trash.name}")
        shutil.move(str(output_dir), str(temp_trash))

    print(f"  Restoring {latest_backup.name} -> {output_dir.name}...")
    shutil.copytree(str(latest_backup), str(output_dir))
    print(f"✅ Successfully restored {output_dir.name} from backup!")
    return True


def phase_preflight_checks(pdf_path: Path) -> Dict[str, Any]:
    """Performs Phase 1 pre-flight checks including file invariants and hardware safety.

    Args:
        pdf_path: Absolute path to the input book PDF.

    Returns:
        Dictionary containing pre-flight status and total page count.

    Raises:
        InvariantViolationError: If PDF integrity or safety invariants are violated.
    """
    print("\n" + "=" * 70)
    print("PHASE 1: PRE-FLIGHT INVARIANT & HARDWARE SAFETY CHECKS")
    print("=" * 70)

    if not pdf_path.exists():
        raise InvariantViolationError(f"Input file not found at: {pdf_path}")

    # Check hardware safety
    hw = check_hardware_safety(ignore_battery=True)
    print(f"• Hardware Check: Safe for OCR: {hw['safe_for_batch_ocr']}, Safe for LLM: {hw['safe_for_heavy_llm']}")
    for r in hw.get("reasons", []):
        print(f"  - Note: {r}")

    # Check PDF integrity and page count
    pdf_info = QualityInvariantGuard.check_pdf_pre_split(str(pdf_path))
    total_pages = pdf_info.get("pages", 0)
    print(f"• Source PDF: {pdf_path.name}")
    print(f"• File Size: {pdf_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"• Total Pages: {total_pages}")

    # Detect document archetype
    archetype = ConfigManager.detect_archetype(str(pdf_path), total_pages=total_pages)
    print(f"• Detected Archetype: {archetype}")
    if archetype != "textbook":
        logger.warning("Archetype detected as '%s', expected 'textbook'", archetype)

    return {"total_pages": total_pages, "archetype": archetype, "hardware": hw}


def phase_toc_discovery(pdf_path: Path) -> List[Dict[str, Any]]:
    """Performs Phase 2 table of contents discovery and section range validation.

    Args:
        pdf_path: Absolute path to the input book PDF.

    Returns:
        List of discovered section dictionaries with name, start, and end.

    Raises:
        InvariantViolationError: If sections cannot be discovered or boundaries overlap.
    """
    print("\n" + "=" * 70)
    print("PHASE 2: OUTLINE & SECTION DISCOVERY (TOC EXTRACTION)")
    print("=" * 70)

    orchestrator = BookProcessorOrchestrator()
    sections = orchestrator.get_pdf_sections(str(pdf_path))

    if not sections:
        raise InvariantViolationError(f"No sections could be identified from '{pdf_path.name}'")

    print(f"• Discovered Sections: {len(sections)}")

    # Validate section boundaries and continuity
    prev_end = 0
    for idx, sec in enumerate(sections, 1):
        name = sec["name"]
        start = sec["start"]
        end = sec["end"]
        page_count = end - start + 1

        if start < 1 or end < start:
            raise InvariantViolationError(
                f"Invalid page bounds in section '{name}': start={start}, end={end}"
            )
        print(f"  [{idx:02d}/{len(sections):02d}] {name:<45} pp. {start:4d} - {end:4d} ({page_count:2d} pp)")
        prev_end = end

    return sections


def phase_split_chapters(
    pdf_path: Path,
    sections: List[Dict[str, Any]],
    output_dir: Path,
) -> CheckpointManager:
    """Performs Phase 3 chapter PDF splitting and invariant validation.

    Args:
        pdf_path: Absolute path to the source PDF.
        sections: List of section definitions.
        output_dir: Target book output directory.

    Returns:
        Initialized and updated CheckpointManager instance.

    Raises:
        InvariantViolationError: If any chapter split fails invariant verification.
    """
    print("\n" + "=" * 70)
    print("PHASE 3: CHAPTER PDF SPLITTING & INVARIANT ENFORCEMENT")
    print("=" * 70)

    chapters_root = output_dir / "chapters"
    chapters_root.mkdir(parents=True, exist_ok=True)

    book_name = output_dir.name
    ckpt = CheckpointManager(str(output_dir), book_name)
    ckpt.init_chapters(sections)

    t0 = time.time()
    for idx, sec in enumerate(sections, 1):
        name = sec["name"]
        start = sec["start"]
        end = sec["end"]
        expected_pages = end - start + 1

        ch_dir = chapters_root / name
        ch_dir.mkdir(parents=True, exist_ok=True)
        ch_pdf = ch_dir / f"{name}.pdf"

        # Split chapter PDF
        PDFSplitter.split_chapter(str(pdf_path), start, end, str(ch_pdf))

        # Enforce post-split quality invariant
        QualityInvariantGuard.check_split_chapter(str(ch_pdf), expected_pages=expected_pages)
        ckpt.update_status(name, split_pdf=True, status="SPLIT")

        print(f"  ✓ [{idx:02d}/{len(sections):02d}] Split verified: {name} ({expected_pages} pp, {ch_pdf.stat().st_size // 1024} KB)")

    elapsed = time.time() - t0
    print(f"\n[✓] All {len(sections)} chapters split and verified in {elapsed:.2f}s")
    print(f"    Checkpoint saved to: {ckpt.json_path}")
    return ckpt


def phase_profile_and_calibrate(
    output_dir: Path,
    sections: List[Dict[str, Any]],
    pdf_path: Path,
    enable_ollama: bool = False,
) -> Dict[str, Any]:
    """Performs Phase 4 layout profiling, coordinate calibration, and special block scanning.

    Args:
        output_dir: Target book output directory.
        sections: List of section definitions.
        pdf_path: Source PDF path.
        enable_ollama: Whether to trigger local Ollama model analysis.

    Returns:
        Dictionary of calibrated book profile data.

    Raises:
        InvariantViolationError: If profile file is missing or invalid.
    """
    print("\n" + "=" * 70)
    print("PHASE 4: BOOK PROFILING & GEOMETRY CALIBRATION")
    print("=" * 70)

    chapters_root = output_dir / "chapters"

    # Select pure body chapter (exclude Front Matter '00-')
    body_sections = [s for s in sections if not s["name"].startswith("00-")]
    if not body_sections:
        raise InvariantViolationError("No pure body sections available for calibration")

    sample_sec = body_sections[0]
    sample_name = sample_sec["name"]
    sample_pdf = chapters_root / sample_name / f"{sample_name}.pdf"

    print(f"• Selected Pure Body Calibration Sample: {sample_name}")
    print(f"• Sample PDF Path: {sample_pdf}")

    # 1. Deterministic Coordinate Calibration
    print("• Calibrating geometry boundaries (width, height, even/odd page margins)...")
    profile = CoordinateCalibrator.calibrate_and_save_profile(output_dir, sample_pdf)

    geom = profile.get("geometry", {})
    pw = geom.get("page_width", 0)
    ph = geom.get("page_height", 0)
    odd_margin = geom.get("odd_page_margin_x", [])
    even_margin = geom.get("even_page_margin_x", [])

    print(f"  - Dimensions: {pw} x {ph} pt")
    print(f"  - Header Cut Ratio: {geom.get('header_cut_ratio')}")
    print(f"  - Footer Cut Ratio: {geom.get('footer_cut_ratio')}")
    print(f"  - Odd Page Margins: {odd_margin}")
    print(f"  - Even Page Margins: {even_margin}")

    if pw <= 0 or ph <= 0:
        raise InvariantViolationError(f"Invalid calibrated page geometry: {geom}")

    # 2. Special Block Scanner
    print("• Scanning for special blocks, callouts, and column roles...")
    sample_pdfs = [chapters_root / s["name"] / f"{s['name']}.pdf" for s in body_sections[:3]]
    scanner = SpecialBlockScanner(output_dir)
    scanner.scan_and_update(sample_pdfs, max_pages_per_chapter=8)

    # Reload updated profile
    prof_file = output_dir / "profile.json"
    if not prof_file.exists():
        prof_file = output_dir / "book_profile.json"

    if not prof_file.exists():
        raise InvariantViolationError(f"Profile file was not created in {output_dir}")

    with open(prof_file, "r", encoding="utf-8") as f:
        updated_profile = json.load(f)

    discovered = updated_profile.get("discovered_blocks", [])
    column_roles = updated_profile.get("column_roles", {})
    print(f"• Discovered Special Blocks: {len(discovered)}")
    print(f"• Column Roles: {column_roles}")

    # 3. Optional Ollama Profiling
    if enable_ollama:
        print("\n• [OPTIONAL] Running Ollama AI Profiler...")
        if is_ollama_available():
            models = get_installed_models()
            print(f"  - Ollama is ONLINE at {DEFAULT_OLLAMA_URL}")
            print(f"  - Available models: {', '.join(models)}")
            target_model = "llama3.1:latest" if "llama3.1:latest" in models else (models[0] if models else "llama3:latest")
            print(f"  - Selected Ollama Model for analysis: {target_model}")
            updated_profile["ollama_probed"] = True
            updated_profile["ollama_model"] = target_model
        else:
            print("  - Ollama REST API not responding, skipping live LLM inference.")

    return updated_profile


def phase_validate_schema(output_dir: Path) -> None:
    """Performs Phase 5 validation ensuring generated profile adheres to schema.

    Args:
        output_dir: Target book output directory.

    Returns:
        None.

    Raises:
        InvariantViolationError: If profile schema validation fails.
    """
    print("\n" + "=" * 70)
    print("PHASE 5: PROFILE SCHEMA & INVARIANT VERIFICATION")
    print("=" * 70)

    p_canon = output_dir / "profile.json"
    p_legacy = output_dir / "book_profile.json"

    target_profile_path = p_canon if p_canon.exists() else p_legacy
    if not target_profile_path.exists():
        raise InvariantViolationError(f"No profile JSON found in {output_dir}")

    with open(target_profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate with DocumentProfile domain model
    doc_profile = DocumentProfile.from_dict(data)
    errors = doc_profile.validate()
    is_valid = len(errors) == 0

    print(f"• Canonical Profile File: {target_profile_path.name}")
    print(f"• Document Title: {doc_profile.meta.title}")
    print(f"• Document Archetype: {doc_profile.meta.doc_type}")
    print(f"• Profile Schema Valid: {is_valid}")

    if errors:
        for err in errors:
            print(f"  [!] Schema Warning: {err}")

    # Check status JSON
    status_file = output_dir / "processing_status.json"
    if not status_file.exists():
        raise InvariantViolationError(f"Processing status file missing: {status_file}")

    with open(status_file, "r", encoding="utf-8") as f:
        status_data = json.load(f)

    chapters_status = status_data.get("chapters", {})
    all_split = all(ch.get("status") == "SPLIT" for ch in chapters_status.values())
    print(f"• Processing Status Chapters: {len(chapters_status)}")
    print(f"• All Chapters Status == 'SPLIT': {all_split}")

    if not all_split:
        raise InvariantViolationError("Some chapters in status file were not marked as 'SPLIT'")


def run_test(enable_ollama: bool = False) -> int:
    """Executes the complete integration test sequence from start to profile.

    Args:
        enable_ollama: Whether to enable Ollama AI profiler stage.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    setup_test_logging()
    app_cfg = load_config()

    input_pdf = (
        app_cfg.input_dir
        / "books"
        / "digital-pdf"
        / "Research Methods, Design, and Analysis 13th ed.pdf"
    )
    book_folder_name = sanitize_filename(input_pdf.stem)
    output_dir = app_cfg.output_dir / "books" / book_folder_name

    print("\n" + "=" * 70)
    print("🚀 RESEARCH METHODS 13TH ED: PIPELINE INTEGRATION TEST")
    print("=" * 70)
    print(f"• Source PDF: {input_pdf}")
    print(f"• Target Output Directory: {output_dir}")
    print(f"• Ollama Mode: {'ENABLED' if enable_ollama else 'OFFLINE GEOMETRY ONLY'}")

    # Step 0: Backup existing output if present
    backup_path = backup_existing_output(output_dir)
    if backup_path:
        print(f"📦 Safely backed up previous output to: {backup_path.name}")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Phase 1: Pre-flight checks
        phase_preflight_checks(input_pdf)

        # Phase 2: TOC and section discovery
        sections = phase_toc_discovery(input_pdf)

        # Phase 3: Split chapter PDFs
        phase_split_chapters(input_pdf, sections, output_dir)

        # Phase 4: Calibrate profile and scan special blocks
        phase_profile_and_calibrate(output_dir, sections, input_pdf, enable_ollama=enable_ollama)

        # Phase 5: Validate profile schema
        phase_validate_schema(output_dir)

        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! SPLIT & PROFILE PIPELINE VERIFIED SUCCESSFULLY.")
        print("=" * 70)
        print(f"• Output folder: {output_dir}")
        if backup_path:
            print(f"• Original backup available at: {backup_path.name}")
            print(f"• To restore previous backup anytime, run:")
            print(f"  uv run python scripts/test_split_and_profile.py --restore\n")
        return 0

    except Exception as exc:
        logger.exception("Integration test failed with error: %s", exc)
        print(f"\n🛑 TEST FAILED: {exc}")
        if backup_path:
            print(f"• Previous backup remains intact at: {backup_path}")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for integration test script.

    Args:
        argv: Command-line arguments; defaults to sys.argv[1:].

    Returns:
        Integer exit code.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Integration test runner: Research Methods split and profile pipeline."
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Enable local Ollama AI model profiler diagnostics.",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore the most recent backup folder to the active output directory.",
    )

    args = parser.parse_args(argv)

    if args.restore:
        app_cfg = load_config()
        book_folder_name = sanitize_filename("Research Methods, Design, and Analysis 13th ed")
        output_dir = app_cfg.output_dir / "books" / book_folder_name
        success = restore_latest_backup(output_dir)
        return 0 if success else 1

    return run_test(enable_ollama=args.ollama)


if __name__ == "__main__":
    raise SystemExit(main())
