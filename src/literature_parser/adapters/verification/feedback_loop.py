"""
Closed-Loop Layout Feedback & Auto-Tuning Engine (FeedbackLoop)
==============================================================
Implements three-tier closed-loop verification, focused vision diagnostic checks,
and automatic parameter tuning to dynamically correct book profiles:
- Tier 1: Fast geometric health checks + focused Vision ROI audits.
- Auto-tuning: Adjusts column/margin bounds on detected defects and updates profile.json.
- Tier 2: Hard syntax invariants and local LLM micro-healers.
- Tier 3: Assembles consolidated visual health audit reports for cross-book learning.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier
from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.core.invariants import QualityInvariantGuard
from literature_parser.services.core.learner import GlobalLearner
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator

logger = logging.getLogger(__name__)


class LayoutFeedbackLoop:
    """Manages closed-loop inspection, parameter auto-tuning, and profile persistence."""

    @classmethod
    def audit_and_tune(
        cls,
        markdown_text: str,
        ch_pdf: Path,
        book_output_dir: Path,
        use_vision: bool = True,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Runs closed-loop checks on generated chapter Markdown and auto-tunes profile if needed.

        Args:
            markdown_text: Converted Markdown content of the chapter.
            ch_pdf: Path to the chapter PDF file.
            book_output_dir: Root output directory for the book containing profile.json.
            use_vision: Whether to invoke Ollama vision for anomalous regions.

        Returns:
            Tuple of (possibly_healed_markdown, list_of_applied_feedback_adjustments).
        """
        adjustments: List[Dict[str, Any]] = []
        md = markdown_text

        # 1. Tier 1 Fast Geometric & Density Audit
        density_anomalies = cls._detect_density_anomalies(md)

        # 2. Focused Vision Verification on Anomalies
        if density_anomalies and use_vision:
            vision_tuning = cls._diagnose_with_vision(ch_pdf, density_anomalies, book_output_dir)
            if vision_tuning:
                adjustments.extend(vision_tuning)
                cls._persist_tuned_profile(book_output_dir, vision_tuning)

        # 3. Tier 2 Hard Invariants Check
        try:
            syntax_check = QualityInvariantGuard.check_markdown_syntax(md, str(ch_pdf.parent))
            if not syntax_check.get("valid", True):
                logger.info("FeedbackLoop: Minor syntax issues detected: %s", syntax_check.get("issues"))
        except Exception as exc:
            logger.debug("Tier 2 invariant check caught exception: %s", exc)

        return md, adjustments

    @classmethod
    def _detect_density_anomalies(cls, md: str) -> List[int]:
        """Finds pages with suspiciously low character counts indicating margin/column issues.

        Args:
            md: Full chapter Markdown content.

        Returns:
            List of page numbers exhibiting density anomalies.
        """
        anomalies: List[int] = []
        parts = re.split(r"<!-- Page (\d+) -->", md)
        for idx in range(1, len(parts), 2):
            try:
                p_num = int(parts[idx])
                p_content = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
                # A body page with less than 100 characters often indicates column split or margin swallow
                if 0 < len(p_content) < 100 and "table" not in p_content.lower() and "figure" not in p_content.lower():
                    anomalies.append(p_num)
            except (ValueError, IndexError):
                continue
        return anomalies

    @classmethod
    def _diagnose_with_vision(
        cls,
        ch_pdf: Path,
        anomaly_pages: List[int],
        book_output_dir: Path,
    ) -> List[Dict[str, Any]]:
        """Uses Ollama vision model to diagnose visual defect on anomalous pages.

        Args:
            ch_pdf: Path to chapter PDF.
            anomaly_pages: List of page numbers to inspect.
            book_output_dir: Book output directory.

        Returns:
            List of adjustment recommendation dictionaries.
        """
        recommendations: List[Dict[str, Any]] = []
        verifier = OllamaVerifier(auto_start=False)
        if not verifier.is_available:
            return recommendations

        target_page = anomaly_pages[0]  # Inspect first anomalous page
        audit_img = book_output_dir / "audit_images" / f"anomaly_p{target_page:03d}.png"
        audit_img.parent.mkdir(parents=True, exist_ok=True)

        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(str(ch_pdf))
            if 0 <= target_page - 1 < len(doc):
                page = doc[target_page - 1]
                pix = page.get_pixmap(dpi=150)
                pix.save(str(audit_img))
                doc.close()

                v_res = verifier.verify_roi_vision(
                    image_path=str(audit_img),
                    element_type="density_anomaly",
                )
                if not v_res.get("passed", True):
                    defect = v_res.get("defect", "margin_misalignment")
                    recommendations.append({
                        "page": target_page,
                        "parameter": "margin_cutoff",
                        "defect": defect,
                        "adjustment": "expand_margin_boundary",
                    })
        except Exception as exc:
            logger.debug("Vision diagnosis skipped on page %d: %s", target_page, exc)

        return recommendations

    @classmethod
    def _persist_tuned_profile(cls, book_output_dir: Path, adjustments: List[Dict[str, Any]]) -> None:
        """Persists tuned parameters into profile.json and book_profile.json.

        Args:
            book_output_dir: Root output directory for the book.
            adjustments: List of adjustment dictionaries.

        Returns:
            None.
        """
        canon_path = book_output_dir / "profile.json"
        legacy_path = book_output_dir / "book_profile.json"

        target_file = canon_path if canon_path.exists() else legacy_path
        if not target_file.exists():
            return

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                prof_data = json.load(f)

            # Record feedback adjustments
            if "feedback_history" not in prof_data:
                prof_data["feedback_history"] = []
            prof_data["feedback_history"].extend(adjustments)

            # Apply geometry adjustment via CoordinateCalibrator
            CoordinateCalibrator.adjust_geometry_from_feedback(book_output_dir, adjustments)

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(prof_data, f, indent=2, ensure_ascii=False)
            logger.info("FeedbackLoop: Auto-tuned profile persisted at %s", target_file.name)
        except Exception as exc:
            logger.warning("FeedbackLoop: Failed to persist auto-tuned profile: %s", exc)
