"""
Vector Figure & Diagram Extractor
=================================
Detects vector diagram figures (e.g. Figure 1.1) that have unmapped fonts
or vector shapes, crops them via pdftoppm, and saves to image directory.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class VectorFigureParser:
    """Specialized extractor for vector figures, flowcharts, and uncaptioned notation diagrams."""

    @classmethod
    def extract_vector_figures(
        cls,
        page_elem: Any,
        fonts: dict,
        pdf_path: str,
        page_num: int,
        pw: float,
        ph: float,
        style: dict = None,
    ) -> Tuple[List[Dict[str, Any]], Set[Any]]:
        """
        Detects vector diagram figures (e.g. Figure 1.1) that have unmapped fonts or vector shapes,
        crops them via pdftoppm, and returns:
        (list_of_image_dicts, set_of_consumed_elements)
        """
        fig_elems = []
        for t in page_elem.findall('text'):
            txt = ''.join(t.itertext()).strip()
            if re.match(r'^(?:Figure|Fig\.)\s+\d+[\.\d]*(?:\s*[:\.\-–—]|\s+[A-Z]|$)', txt):
                if re.match(r'^(?:Figure|Fig\.)\s+\d+[\.\d]*\s+(?:shows|illustrates|depicts|reveals|demonstrates|is|was|can)\b', txt, re.IGNORECASE):
                    continue
                fig_elems.append(t)

        if not pdf_path:
            return [], set()

        if style and style.get("images_dir"):
            img_dir = Path(style["images_dir"])
        else:
            img_dir = Path(pdf_path).parent / 'images'
        img_dir.mkdir(exist_ok=True)

        extracted_images = []
        consumed = set()
        fig_elems.sort(key=lambda el: float(el.attrib.get('top', 0)))

        for idx_f, cap_t in enumerate(fig_elems):
            cap_txt = ''.join(cap_t.itertext()).strip()
            m = re.match(r'^(?:Figure|Fig\.)\s+(\d+[\.\d]*)', cap_txt, re.IGNORECASE)
            if not m:
                continue
            fig_num = m.group(1)
            fig_sanitized = fig_num.replace('.', '_')
            f_top = float(cap_t.attrib.get('top', 0))
            f_left = float(cap_t.attrib.get('left', 0))
            next_fig_top = (
                float(fig_elems[idx_f + 1].attrib.get('top', 9999.0))
                if idx_f + 1 < len(fig_elems)
                else 9999.0
            )

            # Caption continuation lines
            cap_lines = [cap_txt]
            cap_consumed = [cap_t]
            for t in page_elem.findall('text'):
                if t == cap_t:
                    continue
                fid = t.attrib.get('font', '')
                fam = fonts.get(fid, {}).get('family', '').lower()
                if 'heltcom' in fam or 'helveticaltcom' in fam or 'ltcom' in fam:
                    continue
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                txt = ''.join(t.itertext()).strip()
                if (0 <= top - f_top <= 45) and abs(left - f_left) < 150:
                    cap_lines.append(txt)
                    cap_consumed.append(t)

            full_caption = ' '.join(cap_lines)

            # Find associated diagram elements bounded between f_top and next_fig_top
            vec_elems = []
            for t in page_elem.findall('text'):
                if t in cap_consumed:
                    continue
                fid = t.attrib.get('font', '')
                fam = fonts.get(fid, {}).get('family', '').lower()
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue
                if top < f_top - 15.0 or top >= next_fig_top - 5.0 or (top - f_top > 320.0):
                    continue
                if 'heltcom' in fam or 'helveticaltcom' in fam or 'ltcom' in fam:
                    vec_elems.append(t)

            scale = (612.0 * 150.0 / 72.0) / pw if pw else (150.0 / 72.0)
            cap_bottom = max(float(t.attrib.get('top', 0)) + float(t.attrib.get('height', 15)) for t in cap_consumed)

            # If there are no unmapped vector/font elements associated with this figure,
            # do not synthesize an artificial crop or consume regular body text.
            if not vec_elems:
                continue

            diag_elems = vec_elems
            min_x = min(float(t.attrib.get('left', 0)) for t in diag_elems)
            max_x = max(float(t.attrib.get('left', 0)) + float(t.attrib.get('width', 0)) for t in diag_elems)
            min_y = min(float(t.attrib.get('top', 0)) for t in diag_elems)
            max_y = max(float(t.attrib.get('top', 0)) + float(t.attrib.get('height', 0)) for t in diag_elems)

            # Differentiate sidebar figures (e.g. Fig 1.1) vs main column figures (e.g. Fig 1.2)
            if max_x <= pw * 0.46:
                content_min_x = min_x - 23.0
                content_max_x = max_x + 14.0
                content_min_y = min_y - 6.0
                content_max_y = max_y + 37.0
                col_right_limit = pw * 0.46
                uniform_pad = 13.0
                left_b = max(0.0, content_min_x - uniform_pad)
                right_b = min(col_right_limit, content_max_x + uniform_pad)
                top_b = max(cap_bottom + 1.0, content_min_y - uniform_pad)
                bottom_b = content_max_y + uniform_pad
            else:
                content_min_x = min_x - 21.0
                content_max_x = max_x + 29.0
                content_min_y = min_y - 15.0
                content_max_y = max_y + 13.0
                col_left_limit = pw * 0.28 if min_x > pw * 0.25 else 0.0
                left_b = max(col_left_limit, content_min_x)
                right_b = min(pw, content_max_x)
                top_b = max(cap_bottom + 5.0, content_min_y)
                bottom_b = content_max_y

            crop_x = int(left_b * scale)
            crop_y = int(top_b * scale)
            crop_w = int((right_b - left_b) * scale)
            crop_h = int((bottom_b - top_b) * scale)

            img_fname = f"figure_{fig_sanitized}.png"
            target_img_path = img_dir / img_fname
            cropped = False
            try:
                import pymupdf  # type: ignore
                doc = pymupdf.open(pdf_path)
                p_idx = max(0, min(page_num - 1, len(doc) - 1))
                page = doc[p_idx]
                zoom = 150.0 / 72.0
                mat = pymupdf.Matrix(zoom, zoom)
                clip_rect = pymupdf.Rect(
                    max(0.0, crop_x / zoom),
                    max(0.0, crop_y / zoom),
                    min(page.rect.width, (crop_x + crop_w) / zoom),
                    min(page.rect.height, (crop_y + crop_h) / zoom),
                )
                if clip_rect.width > 1.0 and clip_rect.height > 1.0:
                    pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
                    pix.save(str(target_img_path))
                    cropped = target_img_path.exists() and target_img_path.stat().st_size > 0
                doc.close()
            except Exception as e:
                logger.debug("PyMuPDF figure crop failed on page %d: %s", page_num, e)

            if not cropped:
                out_prefix = img_dir / f"figure_{fig_sanitized}"
                cmd = [
                    'pdftoppm', '-png', '-r', '150',
                    '-f', str(page_num), '-l', str(page_num),
                    '-x', str(crop_x), '-y', str(crop_y),
                    '-W', str(crop_w), '-H', str(crop_h),
                    '-singlefile', pdf_path, str(out_prefix)
                ]
                try:
                    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
                except subprocess.TimeoutExpired:
                    logger.warning("pdftoppm timed out (30s) cropping figure on page %d", page_num)
                except Exception as e:
                    logger.debug("Figure crop failed on page %d: %s", page_num, e)

            if target_img_path.exists():
                extracted_images.append({
                    'page': page_num,
                    'filename': img_fname,
                    'caption': full_caption,
                    'top': f_top
                })
                consumed.update(cap_consumed)
                consumed.update(diag_elems)
                for t_box in page_elem.findall('text'):
                    t_b_top = float(t_box.attrib.get('top', 0))
                    t_b_left = float(t_box.attrib.get('left', 0))
                    t_b_w = float(t_box.attrib.get('width', 0))
                    # Guardrail: never consume body prose or headings from another column
                    if f_left < pw * 0.38 and t_b_left >= pw * 0.38:
                        continue
                    if f_left >= pw * 0.55 and (t_b_left + t_b_w) <= pw * 0.50:
                        continue
                    if t_b_w >= pw * 0.35:
                        continue
                    fid = t_box.attrib.get('font', '')
                    f_info = fonts.get(fid, {})
                    if f_info.get('size', 10) >= 11.0:
                        continue
                    if (left_b - 5.0 <= t_b_left <= right_b + 5.0) and (top_b - 5.0 <= t_b_top <= bottom_b + 5.0):
                        consumed.add(t_box)

        # Uncaptioned random diagram cropping (`diagram_pXX_XX.png`) removed per ADR/ISSUE-016:
        # Only explicitly captioned Figures/Exhibits or genuine embedded PDF raster images are extracted.
        return extracted_images, consumed
