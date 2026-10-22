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

        for cap_t in fig_elems:
            cap_txt = ''.join(cap_t.itertext()).strip()
            m = re.match(r'^(?:Figure|Fig\.)\s+(\d+[\.\d]*)', cap_txt, re.IGNORECASE)
            if not m:
                continue
            fig_num = m.group(1)
            fig_sanitized = fig_num.replace('.', '_')
            f_top = float(cap_t.attrib.get('top', 0))
            f_left = float(cap_t.attrib.get('left', 0))

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

            # Find associated diagram elements (e.g. vector fonts or within diagram bounding area)
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
                if 'heltcom' in fam or 'helveticaltcom' in fam or 'ltcom' in fam:
                    vec_elems.append(t)

            scale = (612.0 * 150.0 / 72.0) / pw if pw else (150.0 / 72.0)
            cap_bottom = max(float(t.attrib.get('top', 0)) + float(t.attrib.get('height', 15)) for t in cap_consumed)

            if vec_elems:
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
            else:
                diag_elems = []
                for t in page_elem.findall('text'):
                    if t in cap_consumed:
                        continue
                    top = float(t.attrib.get('top', 0))
                    left = float(t.attrib.get('left', 0))
                    txt = ''.join(t.itertext()).strip()
                    if not txt:
                        continue
                    if (0 <= top - f_top <= 300) and (left < pw * 0.45 if f_left < pw * 0.45 else left > pw * 0.55):
                        fid = t.attrib.get('font', '')
                        if fonts.get(fid, {}).get('size', 12) <= 14:
                            diag_elems.append(t)
                if diag_elems:
                    min_x = min(float(t.attrib.get('left', 0)) for t in diag_elems)
                    max_x = max(float(t.attrib.get('left', 0)) + float(t.attrib.get('width', 0)) for t in diag_elems)
                    min_y = min(float(t.attrib.get('top', 0)) for t in diag_elems)
                    max_y = max(float(t.attrib.get('top', 0)) + float(t.attrib.get('height', 0)) for t in diag_elems)
                    crop_x = int(max(0.0, min_x - 15) * scale)
                    crop_y = int(max(cap_bottom + 10.0, min_y - 15) * scale)
                    crop_w = int((max_x + 15 - max(0.0, min_x - 15)) * scale)
                    crop_h = int((max_y + 15 - max(cap_bottom + 10.0, min_y - 15)) * scale)
                else:
                    crop_x = 0 if f_left < pw * 0.40 else int(max(0.0, f_left - 30) * scale)
                    crop_y = int((f_top + 10) * scale)
                    crop_w = int(350.0 * scale)
                    crop_h = int(220.0 * scale)

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
                    if (left_b - 10.0 <= t_b_left <= right_b + 10.0) and (top_b - 10.0 <= t_b_top <= bottom_b + 10.0):
                        consumed.add(t_box)

        # Uncaptioned vector diagrams (e.g. research notation diagrams like RA -> X -> O)
        if pdf_path:
            for i, t in enumerate(page_elem.findall('text')):
                txt = ''.join(t.itertext()).strip()
                if txt.endswith(':') and float(t.attrib.get('top', 0)) > 150:
                    intro_top = float(t.attrib.get('top', 0))
                    diag_cands = []
                    has_where_legend = False
                    for nxt in page_elem.findall('text'):
                        n_top = float(nxt.attrib.get('top', 0))
                        n_left = float(nxt.attrib.get('left', 0))
                        n_txt = ''.join(nxt.itertext()).strip()
                        if nxt in consumed or not n_txt:
                            continue
                        if intro_top < n_top <= intro_top + 200:
                            if n_txt.lower() == 'where' or 'denotes' in n_txt.lower():
                                has_where_legend = True
                                continue
                            if n_txt.startswith('•') or re.match(r'^[a-e][\.\)]\s*', n_txt):
                                continue
                            if n_left < pw * 0.25 or n_left > pw * 0.75:
                                continue
                            fid = nxt.attrib.get('font', '')
                            sz = float(fonts.get(fid, {}).get('size', 12))
                            if sz >= 18:
                                continue
                            if len(n_txt) <= 20:
                                diag_cands.append(nxt)

                    has_vector_font = any('heltcom' in fonts.get(e.attrib.get('font', ''), {}).get('family', '').lower() for e in diag_cands)
                    has_notation_symbol = any(re.match(r'^[A-Z]{1,3}[0-9]?$', ''.join(e.itertext()).strip()) for e in diag_cands)
                    is_genuine_diagram = (has_where_legend or has_vector_font or has_notation_symbol)

                    if len(diag_cands) >= 4 and is_genuine_diagram:
                        min_x = min(float(e.attrib.get('left', 0)) for e in diag_cands)
                        max_x = max(float(e.attrib.get('left', 0)) + float(e.attrib.get('width', 0)) for e in diag_cands)
                        min_y = min(float(e.attrib.get('top', 0)) for e in diag_cands)
                        max_y = max(float(e.attrib.get('top', 0)) + float(e.attrib.get('height', 0)) for e in diag_cands)

                        scale_x = pw / 612.0
                        scale_y = ph / 783.0
                        pad_pt = 15.0

                        x0_pt = max(0.0, (min_x / scale_x) - 25.0)
                        y0_pt = max(0.0, (min_y / scale_y) - pad_pt)
                        x1_pt = min(612.0, (max_x / scale_x) + 25.0)
                        y1_pt = min(783.0, (max_y / scale_y) + pad_pt)

                        scale_150 = 150.0 / 72.0
                        crop_x = int(x0_pt * scale_150)
                        crop_y = int(y0_pt * scale_150)
                        crop_w = int((x1_pt - x0_pt) * scale_150)
                        crop_h = int((y1_pt - y0_pt) * scale_150)

                        diag_fname = f"diagram_p{page_num:02d}_{len(extracted_images)+1:02d}"
                        full_img_name = f"{diag_fname}.png"
                        target_diag_path = img_dir / full_img_name
                        diag_cropped = False
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
                                pix.save(str(target_diag_path))
                                diag_cropped = target_diag_path.exists() and target_diag_path.stat().st_size > 0
                            doc.close()
                        except Exception as e:
                            logger.debug("PyMuPDF diagram crop failed on page %d: %s", page_num, e)

                        if not diag_cropped:
                            out_prefix = img_dir / diag_fname
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
                                logger.warning("pdftoppm timed out (30s) cropping diagram on page %d", page_num)
                            except Exception as e:
                                logger.debug("Diagram crop failed on page %d: %s", page_num, e)

                        if target_diag_path.exists():
                            extracted_images.append({
                                'page': page_num,
                                'filename': full_img_name,
                                'caption': 'Diagram',
                                'top': min_y
                            })
                            consumed.update(diag_cands)

        return extracted_images, consumed
