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
from typing import Any, Dict, List, Optional, Tuple

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
        """Runs calibration on sample PDF and saves updated geometry to profile.json and book_profile.json.

        Args:
            book_dir: Output directory path for the book.
            sample_pdf: Path to sample PDF file for geometry extraction.

        Returns:
            Calibrated profile dictionary.
        """
        p_canon = book_dir / "profile.json"
        p_legacy = book_dir / "book_profile.json"
        profile_path = p_canon if p_canon.exists() else p_legacy
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
        profile["archetype"] = "textbook"

        # Auto-detect publisher from page 1 text
        if "publisher" not in profile or not profile["publisher"]:
            try:
                import re

                from literature_parser.services.fingerprinting.publisher_detector import (
                    PublisherDetector,
                )
                p1_xml = cls.extract_page_xml(str(sample_pdf), 1)
                p1_text = re.sub(r'<[^>]+>', ' ', p1_xml) if p1_xml else ""
                detected_pub = PublisherDetector.detect_from_text(p1_text)
                if detected_pub:
                    profile["publisher"] = detected_pub
                    logger.info("Auto-fingerprinted publisher: %s", detected_pub)
            except Exception as e:
                logger.debug("Publisher auto-detection skipped: %s", e)

        for path in (p_canon, p_legacy):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

        logger.info("Saved calibrated geometry to %s: %s", p_canon, geom)
        return profile

    @classmethod
    def calibrate_literature_geometry(cls, sample_pdf: str, total_pages: int = 10) -> Dict[str, Any]:
        """
        Samples pages of academic literature to calibrate:
        1. Exact page width and height.
        2. Running header cutoff Y and ratio.
        3. Running footer cutoff Y and ratio.
        4. Single-column vs two-column layout and gutter split coordinates.
        5. Page 1 content start Y coordinate (below journal banner/issn/doi).
        """
        sample_pages = range(1, min(total_pages + 1, 6))
        pw, ph = 600.0, 800.0
        header_cutoffs = []
        footer_cutoffs = []
        p1_content_start_y = None

        wide_count = 0
        left_count = 0
        right_count = 0

        for p in sample_pages:
            xml = cls.extract_page_xml(sample_pdf, p)
            if not xml or '<page' not in xml:
                continue
            try:
                page_part = xml[xml.find('<page'):xml.rfind('</page>') + 7]
                root = ET.fromstring(page_part)
            except Exception:
                continue

            pw = float(root.attrib.get('width', pw))
            ph = float(root.attrib.get('height', ph))

            texts = root.findall('text')
            for t in texts:
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                w = float(t.attrib.get('width', 0))
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue

                if p > 1:
                    if top < ph * 0.10:
                        header_cutoffs.append(top)
                    elif top > ph * 0.88:
                        footer_cutoffs.append(top)
                    else:
                        if w > pw * 0.60:
                            wide_count += 1
                        elif left + w <= pw * 0.52:
                            left_count += 1
                        elif left >= pw * 0.48:
                            right_count += 1
                else:
                    if top > ph * 0.08 and p1_content_start_y is None:
                        p1_content_start_y = top

        is_two_col = (left_count >= 15 and right_count >= 15 and (left_count + right_count) > wide_count * 1.2)
        layout = 'two_column' if is_two_col else 'single_column'

        hdr_cut = min(max(header_cutoffs) + 5.0, ph * 0.12) if header_cutoffs else ph * 0.06
        ftr_cut = max(min(footer_cutoffs) - 5.0, ph * 0.88) if footer_cutoffs else ph * 0.92

        return {
            'page_dimensions': {'width': round(pw, 2), 'height': round(ph, 2)},
            'margins': {
                'header_cutoff_y': round(hdr_cut, 2),
                'header_cutoff_ratio': round(hdr_cut / ph, 3),
                'footer_cutoff_y': round(ftr_cut, 2),
                'footer_cutoff_ratio': round(ftr_cut / ph, 3)
            },
            'columns': {
                'layout': layout,
                'column_count': 2 if is_two_col else 1,
                'column_split_x': round(pw * 0.48, 2),
                'gutter_bounds': [round(pw * 0.46, 2), round(pw * 0.54, 2)]
            },
            'content_start': {
                'page_1_content_start_y': round(p1_content_start_y or ph * 0.15, 2),
                'page_1_content_start_ratio': round((p1_content_start_y or ph * 0.15) / ph, 3)
            }
        }

    @classmethod
    def calibrate_and_save_literature_profile(cls, doc_dir: Path, sample_pdf: Path, total_pages: int = 10) -> Dict[str, Any]:
        """Calibrates coordinates for an academic literature document and saves profile.json.

        Args:
            doc_dir: Target output directory for the literature document.
            sample_pdf: Path to the literature PDF document.
            total_pages: Total number of pages to sample from.

        Returns:
            Calibrated profile dictionary.
        """
        p_canon = doc_dir / "profile.json"
        p_legacy = doc_dir / "document_profile.json"
        profile_path = p_canon if p_canon.exists() else p_legacy
        profile = {
            "archetype": "literature",
            "doc_name": doc_dir.name
        }
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
            except Exception:
                pass

        geom = cls.calibrate_literature_geometry(str(sample_pdf), total_pages=total_pages)
        profile["geometry"] = geom

        # Detect publisher
        try:
            from literature_parser.services.fingerprinting.publisher_detector import (
                PublisherDetector,
            )
            p1_xml = cls.extract_page_xml(str(sample_pdf), 1)
            p1_text = re.sub(r'<[^>]+>', ' ', p1_xml) if p1_xml else ""
            pub = PublisherDetector.detect_from_text(p1_text)
            if pub:
                profile["publisher"] = pub
        except Exception as e:
            logger.debug("Publisher detection skipped in literature profiler: %s", e)

        for path in (p_canon, p_legacy):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

        logger.info("Saved literature profile to %s", p_canon)
        return profile

    @classmethod
    def adjust_geometry_from_feedback(
        cls,
        target_dir: Optional[Path] = None,
        anomaly_type: str = "",
        details: Optional[Dict[str, Any]] = None,
        *,
        book_dir: Optional[Path] = None,
    ) -> bool:
        """Applies closed-loop feedback to dynamically adjust profile geometry boundaries.

        Args:
            target_dir: Book or literature output directory holding profile.json.
            anomaly_type: Detected anomaly ('LEAKED_HEADER', 'LEAKED_FOOTER', 'GUTTER_OVERFLOW').
            details: Optional dictionary containing specific delta adjustments.
            book_dir: Alias for target_dir for backward compatibility.

        Returns:
            True if geometry was successfully adjusted and persisted, False otherwise.
        """
        from literature_parser.domain.profiler.profile_schema import DocumentProfile

        actual_dir = target_dir or book_dir
        if not actual_dir:
            return False

        p_canon = actual_dir / "profile.json"
        p_doc = actual_dir / "document_profile.json"
        p_book = actual_dir / "book_profile.json"

        target_file = None
        for cand in (p_canon, p_doc, p_book):
            if cand.exists():
                target_file = cand
                break
        if not target_file:
            return False

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            doc_profile = DocumentProfile.from_dict(raw_data)
            adjusted = doc_profile.apply_feedback(anomaly_type, details)
            if not adjusted:
                return False

            updated_data = doc_profile.to_dict()
            # Update canonical profile.json and whatever legacy mirror files exist
            paths_to_update = {p_canon, target_file}
            if p_book.exists() or (not p_doc.exists()):
                paths_to_update.add(p_book)
            if p_doc.exists():
                paths_to_update.add(p_doc)

            for path in paths_to_update:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)
            logger.info("Closed-loop feedback applied (%s) to %s", anomaly_type, target_file)
            return True
        except Exception as e:
            logger.warning("Failed applying closed-loop feedback to %s: %s", target_file, e)
            return False
