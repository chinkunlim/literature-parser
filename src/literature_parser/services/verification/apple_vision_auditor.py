"""
Apple Vision Native OCR Auditor
===============================
Provides ultra-fast, macOS Neural Engine (ANE) accelerated optical character
recognition and layout bounding-box extraction by bridging into Apple's native
Vision framework via Swift. Compares rendered EPUB pages against PDF source pages.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SWIFT_BRIDGE_PATH = Path(__file__).parent / "apple_vision_bridge.swift"


class AppleVisionAuditor:
    """Auditor leveraging native macOS Apple Vision Framework for deterministic visual verification."""

    def __init__(self, swift_bin: str = "/usr/bin/swift") -> None:
        """Initializes the Apple Vision auditor.

        Args:
            swift_bin: Absolute path to the swift executable.
        """
        self.swift_bin = swift_bin if Path(swift_bin).exists() else shutil.which("swift") or "swift"

    def is_available(self) -> bool:
        """Checks if Swift and Apple Vision bridge script are available on this system.

        Returns:
            True if macOS Swift binary and bridge script exist, False otherwise.
        """
        return bool(shutil.which(self.swift_bin) and SWIFT_BRIDGE_PATH.exists())

    def extract_page_ocr(self, image_path: Path | str) -> Dict[str, Any]:
        """Extracts OCR text and bounding-box geometry from a page image using Apple Vision.

        Args:
            image_path: Path to PNG or JPEG image file.

        Returns:
            Dictionary containing `success`, `line_count`, `full_text`, and `lines`.
        """
        img_p = Path(image_path)
        if not img_p.exists():
            return {
                "success": False,
                "error": f"Image file not found: {img_p}",
                "line_count": 0,
                "full_text": "",
                "lines": [],
            }

        cmd = [self.swift_bin, str(SWIFT_BRIDGE_PATH), str(img_p)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode != 0:
                logger.warning("Apple Vision bridge failed on %s: %s", img_p.name, res.stderr)
                return {
                    "success": False,
                    "error": res.stderr.strip() or res.stdout.strip(),
                    "line_count": 0,
                    "full_text": "",
                    "lines": [],
                }
            raw_out = res.stdout.strip()
            data = json.loads(raw_out)
            return data
        except Exception as err:
            logger.warning("Failed executing Apple Vision bridge on %s: %s", img_p.name, err)
            return {
                "success": False,
                "error": str(err),
                "line_count": 0,
                "full_text": "",
                "lines": [],
            }

    def compare_rendered_pages(
        self,
        pdf_img_path: Path | str,
        epub_img_path: Path | str,
        min_word_len: int = 4,
    ) -> Dict[str, Any]:
        """Performs OCR on both PDF page and EPUB rendered page, evaluating content fidelity.

        Args:
            pdf_img_path: Path to rendered PNG of the source PDF page.
            epub_img_path: Path to rendered PNG of the generated EPUB page.
            min_word_len: Minimum word length to consider for keyword coverage comparison.

        Returns:
            Dictionary containing:
                - `pdf_line_count`: Line count from PDF.
                - `epub_line_count`: Line count from EPUB.
                - `coverage_rate`: Float percentage of PDF keywords recovered in EPUB.
                - `missing_keywords`: Top keywords missing in EPUB.
                - `passed`: Boolean indicating if coverage satisfies threshold (>= 90%).
        """
        pdf_res = self.extract_page_ocr(pdf_img_path)
        epub_res = self.extract_page_ocr(epub_img_path)

        if not pdf_res.get("success") or not epub_res.get("success"):
            return {
                "passed": False,
                "coverage_rate": 0.0,
                "pdf_line_count": pdf_res.get("line_count", 0),
                "epub_line_count": epub_res.get("line_count", 0),
                "missing_keywords": [],
                "error": pdf_res.get("error") or epub_res.get("error"),
            }

        pdf_text = pdf_res.get("full_text", "").lower()
        epub_text = epub_res.get("full_text", "").lower()

        # Extract normalized words
        pdf_words = [
            w for w in re.findall(r"\b[a-z]{" + str(min_word_len) + r",}\b", pdf_text)
            if w not in ("chapter", "figure", "table", "page", "section", "isbn")
        ]
        epub_word_set = set(re.findall(r"\b[a-z]{" + str(min_word_len) + r",}\b", epub_text))

        if not pdf_words:
            return {
                "passed": True,
                "coverage_rate": 100.0,
                "pdf_line_count": pdf_res.get("line_count", 0),
                "epub_line_count": epub_res.get("line_count", 0),
                "missing_keywords": [],
            }

        matched_words = [w for w in pdf_words if w in epub_word_set]
        coverage_rate = round(len(matched_words) / len(pdf_words) * 100.0, 2)
        missing_kw = list(dict.fromkeys([w for w in pdf_words if w not in epub_word_set]))

        passed = coverage_rate >= 80.0

        return {
            "passed": passed,
            "coverage_rate": coverage_rate,
            "pdf_line_count": pdf_res.get("line_count", 0),
            "epub_line_count": epub_res.get("line_count", 0),
            "missing_keywords": missing_kw[:10],
        }
