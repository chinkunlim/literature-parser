"""
Element Cropper for Tables and Figures
======================================
Extracts standalone, high-resolution image crops for every Figure and Table
in the document pages, ensuring:
- Inclusion of Caption, body content, and Notes/legends.
- Symmetric, equal margin padding on all four sides (top, bottom, left, right).
- Consistent semantic naming conventions (e.g. figure_1.png, table_1.png).
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from literature_parser.services.converter.models import CroppedElement

logger = logging.getLogger(__name__)


class ElementCropper:
    """Cropper utility that extracts figures and tables with captions, notes, and equal margins."""

    DEFAULT_MARGIN_PT: float = 16.0
    DEFAULT_DPI: int = 150

    @classmethod
    def compute_padded_bbox(
        cls,
        bbox: Tuple[float, float, float, float],
        page_width: float,
        page_height: float,
        margin_pt: float = DEFAULT_MARGIN_PT,
    ) -> Tuple[float, float, float, float]:
        """Calculates padded bounding box with equal margins on all four sides.

        Args:
            bbox: Tuple of (left, top, right, bottom) coordinates in points.
            page_width: Page width in points.
            page_height: Page height in points.
            margin_pt: Uniform padding in points to add equally to top, bottom, left, right.

        Returns:
            Tuple of (padded_left, padded_top, padded_right, padded_bottom) in points.
        """
        left, top, right, bottom = bbox
        p_left = max(0.0, left - margin_pt)
        p_top = max(0.0, top - margin_pt)
        p_right = min(page_width, right + margin_pt)
        p_bottom = min(page_height, bottom + margin_pt)
        return (p_left, p_top, p_right, p_bottom)

    @classmethod
    def crop_pdf_region(
        cls,
        pdf_path: str | Path,
        page_num: int,
        padded_bbox: Tuple[float, float, float, float],
        output_image_path: Path,
        page_width: float,
        dpi: int = DEFAULT_DPI,
    ) -> bool:
        """Invokes pdftoppm to crop an exact bounding box from a PDF page.

        Args:
            pdf_path: Path to the source PDF document.
            page_num: 1-indexed page number to crop from.
            padded_bbox: Bounding box (left, top, right, bottom) in points.
            output_image_path: Destination path for the resulting image (e.g. file.png).
            page_width: Original page width in points for scaling calibration.
            dpi: Output resolution in dots-per-inch.

        Returns:
            True if image was successfully cropped and saved, False otherwise.
        """
        p_left, p_top, p_right, p_bottom = padded_bbox
        if p_right <= p_left or p_bottom <= p_top:
            logger.warning("Invalid crop dimensions for page %d: %s", page_num, padded_bbox)
            return False

        # Scale from PDF points (1/72 in) to pixel coordinates at requested DPI
        scale = (dpi / 72.0)
        crop_x = int(p_left * scale)
        crop_y = int(p_top * scale)
        crop_w = max(1, int((p_right - p_left) * scale))
        crop_h = max(1, int((p_bottom - p_top) * scale))

        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        # pdftoppm automatically appends .png when -singlefile is used if suffix not given,
        # but with -singlefile, prefix becomes prefix.png
        out_prefix = str(output_image_path.with_suffix(''))

        cmd = [
            'pdftoppm', '-png', '-r', str(dpi),
            '-f', str(page_num), '-l', str(page_num),
            '-x', str(crop_x), '-y', str(crop_y),
            '-W', str(crop_w), '-H', str(crop_h),
            '-singlefile', str(pdf_path), out_prefix
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            target_png = output_image_path if output_image_path.suffix == '.png' else output_image_path.with_suffix('.png')
            if target_png.exists() and target_png.stat().st_size > 0:
                return True
            logger.debug("pdftoppm finished but output missing: %s", target_png)
            return False
        except Exception as e:
            logger.debug("pdftoppm execution failed for page %d (%s): %s", page_num, output_image_path.name, e)
            return False

    @classmethod
    def extract_and_crop_page_tables(
        cls,
        pdf_path: str | Path,
        page_elem: ET.Element,
        page_num: int,
        pw: float,
        ph: float,
        images_dir: Path,
        margin_pt: float = DEFAULT_MARGIN_PT,
        dpi: int = DEFAULT_DPI,
    ) -> List[CroppedElement]:
        """Detects tables on a page, gathers captions and notes, and crops them.

        Args:
            pdf_path: Path to the source PDF document.
            page_elem: Parsed XML Element for the PDF page.
            page_num: 1-indexed page number.
            pw: Calibrated page width in points.
            ph: Calibrated page height in points.
            images_dir: Destination directory for cropped images.
            margin_pt: Uniform padding in points for all 4 sides.
            dpi: Output resolution.

        Returns:
            List of CroppedElement instances representing extracted tables.
        """
        results: List[CroppedElement] = []
        text_elements = page_elem.findall('text')

        # Find candidate Table headings
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            m = re.match(r'^(?:Table|TABLE)\s+(\d+(?:[\.\-_]\d+)*[a-zA-Z]?)\b[:\.]?\s*(.*)', txt)
            if not m:
                continue

            h = float(t.attrib.get('height', 0))
            if h < 8:
                continue

            t_num = m.group(1).replace('-', '_').replace('.', '_')
            t_cap_rest = m.group(2).strip()

            h_top = float(t.attrib.get('top', 0))
            h_left = float(t.attrib.get('left', 0))

            # Gather elements belonging to this table (caption, body, notes)
            # Typically extends downwards within 550pt and within horizontal bounds
            table_elems = [t]
            caption_parts = [txt]
            notes_parts: List[str] = []

            for other in text_elements:
                if other == t:
                    continue
                o_top = float(other.attrib.get('top', 0))
                o_left = float(other.attrib.get('left', 0))
                o_txt = ''.join(other.itertext()).strip()
                if not o_txt:
                    continue

                # Nearby caption line immediately below or horizontally aligned
                if abs(o_top - h_top) <= 12 and o_left > h_left and (o_left - h_left < 300):
                    table_elems.append(other)
                    caption_parts.append(o_txt)
                elif 0 < o_top - h_top <= 25 and abs(o_left - h_left) <= 80:
                    table_elems.append(other)
                    caption_parts.append(o_txt)
                elif 0 < o_top - h_top <= 550:
                    # Check if text looks like a footnote/note or table row
                    if re.match(r'^(?:\*+|Note\b|\.?\s*Source:)', o_txt, re.IGNORECASE):
                        notes_parts.append(o_txt)
                        table_elems.append(other)
                    elif o_left >= min(0.0, h_left - 80) and o_left <= pw * 0.95:
                        table_elems.append(other)

            if len(table_elems) < 3:
                continue

            # Calculate raw unpadded bounding box
            min_x = min(float(elem.attrib.get('left', 0)) for elem in table_elems)
            max_x = max(float(elem.attrib.get('left', 0)) + float(elem.attrib.get('width', 0)) for elem in table_elems)
            min_y = min(float(elem.attrib.get('top', 0)) for elem in table_elems)
            max_y = max(float(elem.attrib.get('top', 0)) + float(elem.attrib.get('height', 0)) for elem in table_elems)

            raw_bbox = (min_x, min_y, max_x, max_y)
            padded_bbox = cls.compute_padded_bbox(raw_bbox, pw, ph, margin_pt=margin_pt)

            identifier = f"table_{t_num}"
            filename = f"{identifier}.png"
            filepath = images_dir / filename

            # Execute crop via pdftoppm
            cropped = cls.crop_pdf_region(
                pdf_path=pdf_path,
                page_num=page_num,
                padded_bbox=padded_bbox,
                output_image_path=filepath,
                page_width=pw,
                dpi=dpi,
            )

            results.append(CroppedElement(
                element_type="table",
                identifier=identifier,
                filename=filename,
                filepath=filepath,
                page_num=page_num,
                bbox=raw_bbox,
                padded_bbox=padded_bbox,
                caption=" ".join(caption_parts).strip(),
                notes=" ".join(notes_parts).strip(),
            ))

        return results

    @classmethod
    def extract_and_crop_page_figures(
        cls,
        pdf_path: str | Path,
        page_elem: ET.Element,
        page_num: int,
        pw: float,
        ph: float,
        images_dir: Path,
        margin_pt: float = DEFAULT_MARGIN_PT,
        dpi: int = DEFAULT_DPI,
    ) -> List[CroppedElement]:
        """Detects figures on a page, gathers captions and notes, and crops them.

        Args:
            pdf_path: Path to the source PDF document.
            page_elem: Parsed XML Element for the PDF page.
            page_num: 1-indexed page number.
            pw: Calibrated page width in points.
            ph: Calibrated page height in points.
            images_dir: Destination directory for cropped images.
            margin_pt: Uniform padding in points for all 4 sides.
            dpi: Output resolution.

        Returns:
            List of CroppedElement instances representing extracted figures.
        """
        results: List[CroppedElement] = []
        text_elements = page_elem.findall('text')

        # Find candidate Figure headings
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            m = re.match(r'^(?:Figure|Fig\.|FIGURE)\s+(\d+(?:[\.\-_]\d+)*[a-zA-Z]?)\b[:\.]?\s*(.*)', txt)
            if not m:
                continue

            h = float(t.attrib.get('height', 0))
            if h < 8:
                continue

            f_num = m.group(1).replace('-', '_').replace('.', '_')
            f_top = float(t.attrib.get('top', 0))
            f_left = float(t.attrib.get('left', 0))

            fig_elems = [t]
            caption_parts = [txt]
            notes_parts: List[str] = []

            # Gather elements associated with figure (including graphic labels, captions, notes)
            for other in text_elements:
                if other == t:
                    continue
                o_top = float(other.attrib.get('top', 0))
                o_left = float(other.attrib.get('left', 0))
                o_txt = ''.join(other.itertext()).strip()
                if not o_txt:
                    continue

                # Captions may be adjacent horizontally or right below
                if abs(o_top - f_top) <= 12 and o_left > f_left and (o_left - f_left < 350):
                    fig_elems.append(other)
                    caption_parts.append(o_txt)
                elif 0 < o_top - f_top <= 30 and abs(o_left - f_left) <= 120:
                    fig_elems.append(other)
                    caption_parts.append(o_txt)
                elif 0 < o_top - f_top <= 400:
                    if re.match(r'^(?:\*+|Note\b|\.?\s*Source:)', o_txt, re.IGNORECASE):
                        notes_parts.append(o_txt)
                        fig_elems.append(other)
                    elif abs(o_left - f_left) <= 250:
                        fig_elems.append(other)

            min_x = min(float(elem.attrib.get('left', 0)) for elem in fig_elems)
            max_x = max(float(elem.attrib.get('left', 0)) + float(elem.attrib.get('width', 0)) for elem in fig_elems)
            min_y = min(float(elem.attrib.get('top', 0)) for elem in fig_elems)
            max_y = max(float(elem.attrib.get('top', 0)) + float(elem.attrib.get('height', 0)) for elem in fig_elems)

            # If figure graphic was above the caption, adjust min_y upward
            if max_y - min_y < 120 and min_y > 100:
                min_y = max(0.0, min_y - 180.0)

            raw_bbox = (min_x, min_y, max_x, max_y)
            padded_bbox = cls.compute_padded_bbox(raw_bbox, pw, ph, margin_pt=margin_pt)

            identifier = f"figure_{f_num}"
            filename = f"{identifier}.png"
            filepath = images_dir / filename

            cls.crop_pdf_region(
                pdf_path=pdf_path,
                page_num=page_num,
                padded_bbox=padded_bbox,
                output_image_path=filepath,
                page_width=pw,
                dpi=dpi,
            )

            results.append(CroppedElement(
                element_type="figure",
                identifier=identifier,
                filename=filename,
                filepath=filepath,
                page_num=page_num,
                bbox=raw_bbox,
                padded_bbox=padded_bbox,
                caption=" ".join(caption_parts).strip(),
                notes=" ".join(notes_parts).strip(),
            ))

        return results
