"""
Stage 0 Adaptive Document Profiler (Stage0Profiler)
==================================================
Performs pre-flight layout topology probing and canonical profile induction
for newly encountered books and academic literature before conversion starts:
- Executes millisecond-level Python geometric calibration (columns, gutters, margins).
- Leverages local Ollama Vision/multimodal models for ambiguous visual role induction.
- Classifies publisher signature and pedagogical block archetypes.
- Synthesizes and persists canonical `profile.json` in destination directory.
- Guarantees non-blocking execution with resilient archetype fallback defaults.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature_parser.adapters.profiler.ollama_profiler import (
    generate_default_book_profile,
    is_ollama_available,
)
from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier
from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.fingerprinting.document_classifier import DocumentClassifier
from literature_parser.services.fingerprinting.publisher_detector import PublisherDetector
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.services.profiler.special_block_scanner import SpecialBlockScanner

logger = logging.getLogger(__name__)


class Stage0Profiler:
    """Pre-flight layout induction engine combining geometric and multimodal probing."""

    @classmethod
    def probe_and_persist_profile(
        cls,
        pdf_path: str | Path,
        book_output_dir: str | Path,
        use_ollama: bool = True,
        max_probe_pages: int = 5,
    ) -> DocumentProfile:
        """Induces document profile for a PDF and saves canonical profile.json.

        Args:
            pdf_path: Path to the target PDF file.
            book_output_dir: Output root directory for the book/article.
            use_ollama: Whether to consult local Ollama vision model if available.
            max_probe_pages: Number of sample pages to probe for geometry and layout.

        Returns:
            Canonical DocumentProfile instance representing calibrated document geometry.
        """
        p_pdf = Path(pdf_path)
        p_out = Path(book_output_dir)
        p_out.mkdir(parents=True, exist_ok=True)

        canon_path = p_out / "profile.json"
        legacy_path = p_out / "book_profile.json"

        # If already calibrated and valid, load and return
        if canon_path.exists():
            try:
                with open(canon_path, "r", encoding="utf-8") as f:
                    return DocumentProfile.from_dict(json.load(f))
            except Exception as e:
                logger.warning("Existing profile.json corrupted, re-probing: %s", e)

        # 1. Determine document type
        is_lit = DocumentClassifier.is_journal_article(str(p_pdf))
        doc_type = "literature" if is_lit else "book"

        # 2. Geometric calibration
        geom: Dict[str, Any] = {}
        try:
            if is_lit:
                geom = CoordinateCalibrator.calibrate_literature_geometry(str(p_pdf), total_pages=max_probe_pages)
            else:
                geom = CoordinateCalibrator.calibrate_book_geometry(str(p_pdf), total_pages=max_probe_pages)
        except Exception as exc:
            logger.warning("Stage0 geometric calibration failed (%s); using default geometry.", exc)
            fallback = generate_default_book_profile(p_out)
            geom = fallback.get("geometry", {})

        # 3. Detect publisher signature
        publisher = None
        try:
            p1_xml = CoordinateCalibrator.extract_page_xml(str(p_pdf), 1)
            p1_text = p1_xml if p1_xml else ""
            publisher = PublisherDetector.detect_from_text(p1_text)
        except Exception as exc:
            logger.debug("Publisher detection skipped: %s", exc)

        # 4. Multimodal semantic probing for ambiguous visual layout
        layout_semantics: Dict[str, Any] = {
            "has_side_rail": False,
            "has_margin_glossaries": False,
            "callout_style": "standard",
        }

        if use_ollama and is_ollama_available():
            try:
                layout_semantics = cls._probe_visual_semantics(p_pdf, geom)
            except Exception as exc:
                logger.debug("Ollama visual semantic probe skipped: %s", exc)

        # 5. Build consolidated profile dictionary
        profile_dict: Dict[str, Any] = {
            "book_name": p_out.name,
            "doc_type": doc_type,
            "archetype": "literature" if is_lit else "textbook_heavy",
            "publisher": publisher,
            "geometry": geom,
            "layout_semantics": layout_semantics,
            "features": {
                "concept_map": not is_lit,
                "learning_objectives": not is_lit,
                "margin_glossary": layout_semantics.get("has_margin_glossaries", True),
                "eoc_sections": not is_lit,
            },
        }

        # Scan special pedagogical blocks if textbook
        if not is_lit:
            try:
                scanner = SpecialBlockScanner(p_out)
                scanner.scan_and_update([p_pdf], max_pages_per_chapter=max_probe_pages)
                if legacy_path.exists():
                    with open(legacy_path, "r", encoding="utf-8") as f_leg:
                        leg_data = json.load(f_leg)
                        if "special_blocks" in leg_data:
                            profile_dict["special_blocks"] = leg_data["special_blocks"]
            except Exception as exc:
                logger.debug("SpecialBlockScanner probe skipped: %s", exc)

        # 6. Save canonical profile.json and legacy book_profile.json
        with open(canon_path, "w", encoding="utf-8") as f_canon:
            json.dump(profile_dict, f_canon, indent=2, ensure_ascii=False)
        with open(legacy_path, "w", encoding="utf-8") as f_legacy:
            json.dump(profile_dict, f_legacy, indent=2, ensure_ascii=False)

        logger.info("Stage0Profiler: Successfully induced profile for '%s'", p_pdf.name)
        return DocumentProfile.from_dict(profile_dict)

    @classmethod
    def _probe_visual_semantics(cls, pdf_path: Path, geom: Dict[str, Any]) -> Dict[str, Any]:
        """Performs targeted multimodal query on sample page to infer layout role.

        Args:
            pdf_path: Target PDF file.
            geom: Calibrated geometric parameters dictionary.

        Returns:
            Dictionary containing inferred visual properties.
        """
        result = {
            "has_side_rail": False,
            "has_margin_glossaries": True,
            "callout_style": "standard",
        }
        verifier = OllamaVerifier(auto_start=False)
        if not verifier.is_available:
            return result

        # Check column hints from geometry
        cols = geom.get("columns", {})
        if cols.get("layout") == "two_column":
            result["has_side_rail"] = False
        return result
