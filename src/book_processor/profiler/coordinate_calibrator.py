"""
Coordinate & Geometry Calibrator
================================
Automatically inspects born-digital or scanned PDF sample pages to calibrate
facing-page margin boundaries (even vs odd page gutters), font size hierarchies,
and writing geometries into book_profile.json.
"""

import json
import logging
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class CoordinateCalibrator:
    """Calibrates geometrical bounds and column layouts for a book."""

    @staticmethod
    def extract_page_xml(pdf_path: str, page_num: int) -> str:
        try:
            res = subprocess.run(
                ['pdftohtml', '-xml', '-nodrm', '-i', '-stdout', '-f', str(page_num), '-l', str(page_num), pdf_path],
                capture_output=True, timeout=15
            )
            return res.stdout.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.debug("XML extraction failed for page %d: %s", page_num, e)
            return ""

    @classmethod
    def calibrate_book_geometry(cls, sample_pdf: str, total_pages: int = 20) -> Dict[str, Any]:
        """
        Samples pages to determine:
        1. Exact page width and height.
        2. Even page margin range (left side).
        3. Odd page margin range (right side).
        4. Heading font size distribution.
        """
        widths = []
        heights = []
        even_margin_lefts = []
        odd_margin_lefts = []
        body_lefts_even = []
        body_lefts_odd = []
        font_sizes = []

        sample_range = range(2, min(total_pages + 1, 15))
        for p in sample_range:
            xml = cls.extract_page_xml(sample_pdf, p)
            if not xml or '<page' not in xml:
                continue
            try:
                page_part = xml[xml.find('<page'):xml.rfind('</page>') + 7]
                root = ET.fromstring(page_part)
            except Exception:
                continue

            pw = float(root.attrib.get('width', 800))
            ph = float(root.attrib.get('height', 1100))
            widths.append(pw)
            heights.append(ph)

            is_even_page = (p % 2 == 0)

            for t in root.findall('text'):
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                w = float(t.attrib.get('width', 0))
                # Skip header/footer
                if top < ph * 0.05 or top > ph * 0.95:
                    continue
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue

                rel_left = left / pw
                rel_width = w / pw

                # Short text on outer bands
                if is_even_page:
                    if rel_left < 0.35 and rel_width < 0.28:
                        even_margin_lefts.append(rel_left + rel_width)
                    elif 0.25 <= rel_left <= 0.40 and rel_width > 0.45:
                        body_lefts_even.append(rel_left)
                else:
                    if rel_left > 0.65 and rel_width < 0.30:
                        odd_margin_lefts.append(rel_left)
                    elif rel_left < 0.20 and rel_width > 0.45:
                        body_lefts_odd.append(rel_left + rel_width)

        median_w = round(sorted(widths)[len(widths) // 2], 1) if widths else 918.0
        median_h = round(sorted(heights)[len(heights) // 2], 1) if heights else 1174.0

        even_margin_bound = round(sorted(even_margin_lefts)[-1], 2) if even_margin_lefts else 0.30
        even_margin_bound = min(max(even_margin_bound, 0.22), 0.35)

        odd_margin_bound = round(sorted(odd_margin_lefts)[0], 2) if odd_margin_lefts else 0.70
        odd_margin_bound = min(max(odd_margin_bound, 0.65), 0.78)

        geometry = {
            "page_width": median_w,
            "page_height": median_h,
            "header_cut_ratio": 0.04,
            "footer_cut_ratio": 0.04,
            "odd_page_margin_x": [odd_margin_bound, 1.0],
            "even_page_margin_x": [0.0, even_margin_bound]
        }
        return geometry

    @classmethod
    def calibrate_and_save_profile(cls, book_dir: Path, sample_pdf: Path) -> Dict[str, Any]:
        """Runs calibration on sample PDF and saves updated geometry to book_profile.json."""
        profile_path = book_dir / "book_profile.json"
        profile = {}
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
            except Exception:
                pass

        geom = cls.calibrate_book_geometry(str(sample_pdf))
        profile["geometry"] = geom
        profile["book_name"] = book_dir.name

        # Auto-detect publisher from page 1 text
        if "publisher" not in profile or not profile["publisher"]:
            try:
                import re
                from book_processor.fingerprinting.publisher_detector import PublisherDetector
                p1_xml = cls.extract_page_xml(str(sample_pdf), 1)
                p1_text = re.sub(r'<[^>]+>', ' ', p1_xml) if p1_xml else ""
                detected_pub = PublisherDetector.detect_from_text(p1_text)
                if detected_pub:
                    profile["publisher"] = detected_pub
                    logger.info("Auto-fingerprinted publisher: %s", detected_pub)
            except Exception as e:
                logger.debug("Publisher auto-detection skipped: %s", e)

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        logger.info("Saved calibrated geometry to %s: %s", profile_path, geom)
        return profile


if __name__ == "__main__":
    import sys
    b_dir = Path("./data/output/books/Research Methods, Design, and Analysis 13th ed")
    ch_pdf = b_dir / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.pdf"
    if ch_pdf.exists():
        geom = CoordinateCalibrator.calibrate_book_geometry(str(ch_pdf))
        print("Calibrated Geometry Result:")
        print(json.dumps(geom, indent=2))
