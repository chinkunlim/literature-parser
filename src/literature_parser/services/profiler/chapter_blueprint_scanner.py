"""
Pre-Conversion Chapter Structural Blueprint Scanner
===================================================
Executes Pass 1 (Pre-Conversion Structural Scan) on a chapter PDF using
PyMuPDF native vector geometry (`page.get_drawings()`, `page.find_tables()`,
sub-chapter PDF outline bookmarks, and chapter-wide font clustering) to
generate a deterministic `ChapterBlueprint` (`chapter_blueprint.json`)
before text conversion begins (Refs: ADR-011).
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from literature_parser.domain.profiler.blueprint_schema import (
    BlueprintHeadingEntry,
    BlueprintTableEntry,
    ChapterBlueprint,
    FontRoleSignature,
    PageLayoutBlueprint,
    PageZone,
)

logger = logging.getLogger(__name__)

_TABLE_HEADER_RE = re.compile(
    r"^(?:Table|TABLE)\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?(?:\s+(.*))?$"
)
_EXHIBIT_HEADER_RE = re.compile(
    r"^(?:Exhibit|EXHIBIT|Box|BOX|Focus\s+Box|Case\s+Study|Clinical\s+Focus)\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?(?:\s+(.*))?$"
)
_FIGURE_HEADER_RE = re.compile(
    r"^(?:Figure|FIGURE|Fig\.)\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?(?:\s+(.*))?$"
)
_PROSE_CONT_RE = re.compile(
    r"^(?:shows|illustrates|depicts|presents|summarizes|lists|compares|provides|gives|contains|is|are|was|were|has|have|can|will|may|should|must|in|on|at|for|from|with|by|to|of|and|or|that|which)\b",
    re.IGNORECASE,
)


class ChapterBlueprintScanner:
    """Scans a chapter PDF to construct an authoritative `ChapterBlueprint` prior to Markdown conversion."""

    @classmethod
    def scan_chapter(
        cls,
        pdf_path: str | Path,
        chapter_name: Optional[str] = None,
        output_dir: Optional[str | Path] = None,
        is_scanned: bool = False,
        specialist_enricher: Optional[Callable[[Path, ChapterBlueprint], ChapterBlueprint]] = None,
    ) -> ChapterBlueprint:
        """Runs Pass 1 structural analysis on `pdf_path` and optionally writes `chapter_blueprint.json`.

        Args:
            pdf_path: Path to the chapter PDF file.
            chapter_name: Optional canonical chapter name (defaults to `pdf_path.stem`).
            output_dir: Optional directory where `chapter_blueprint.json` should be saved.
            is_scanned: Whether the chapter is a scanned image PDF.
            specialist_enricher: Optional callback (e.g. `DoclingBlueprintAdapter.enrich_blueprint`)
                for enriching scanned or complex pages.

        Returns:
            Populated `ChapterBlueprint` instance.
        """
        p_path = Path(pdf_path)
        ch_name = chapter_name or p_path.stem
        blueprint = ChapterBlueprint(
            chapter_name=ch_name,
            page_count=0,
            engine="pymupdf_vector",
        )

        if not p_path.exists():
            return blueprint

        try:
            import pymupdf  # type: ignore
        except ImportError:
            logger.warning("PyMuPDF not available for ChapterBlueprintScanner on %s", p_path)
            return blueprint

        try:
            doc = pymupdf.open(str(p_path))
            if getattr(doc, "is_encrypted", False):
                try:
                    doc.authenticate("")
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("Failed opening PDF for blueprint scan %s: %s", p_path, exc)
            return blueprint

        total_pages = len(doc)
        blueprint.page_count = total_pages

        # 1. Extract sub-chapter PDF outline bookmarks if present
        outline_headings = cls._extract_outline_headings(doc, total_pages)

        # 2. First pass over pages: collect font statistics, vector geometry, and layout zones
        font_counter: Counter = Counter()
        font_meta_map: Dict[Tuple[str, float, bool, bool], int] = {}
        typo_headings: List[BlueprintHeadingEntry] = []
        table_entries: List[BlueprintTableEntry] = []
        seen_table_ids: set = set()

        for p_idx in range(total_pages):
            p_num = p_idx + 1
            page = doc[p_idx]
            page_bp, p_tables, p_headings = cls._scan_single_page(
                page=page,
                page_num=p_num,
                font_counter=font_counter,
                font_meta_map=font_meta_map,
            )
            blueprint.pages[p_num] = page_bp
            for tbl in p_tables:
                t_key = (tbl.table_id, tbl.page_num)
                if t_key not in seen_table_ids:
                    seen_table_ids.add(t_key)
                    table_entries.append(tbl)
            typo_headings.extend(p_headings)

        doc.close()

        # 3. Calibrate modal body font and heading font roles
        body_fam, body_sz = cls._resolve_body_font(font_counter, font_meta_map)
        blueprint.body_font_family = body_fam
        blueprint.body_font_size = body_sz
        blueprint.font_roles = cls._build_font_roles(font_meta_map, body_fam, body_sz)

        # 4. Merge outline bookmarks and calibrated typographic headings
        if outline_headings:
            blueprint.expected_headings = outline_headings
        else:
            filtered_typo = [
                h for h in typo_headings if h.title and len(h.title) >= 3
            ]
            blueprint.expected_headings = filtered_typo

        blueprint.expected_tables = table_entries

        # 5. Optional specialist enrichment (e.g. Docling adapter for scanned PDFs)
        if is_scanned and specialist_enricher is not None:
            try:
                blueprint = specialist_enricher(p_path, blueprint)
            except Exception as enrich_err:
                logger.warning("Specialist blueprint enricher failed for %s: %s", p_path.name, enrich_err)

        if output_dir is not None:
            try:
                blueprint.save_json(output_dir)
            except Exception as save_err:
                logger.warning("Failed saving chapter_blueprint.json to %s: %s", output_dir, save_err)

        return blueprint

    @classmethod
    def _extract_outline_headings(cls, doc: Any, total_pages: int) -> List[BlueprintHeadingEntry]:
        """Extracts authoritative sub-chapter headings from the PDF outline.

        Args:
            doc: Open PyMuPDF Document instance.
            total_pages: Total pages in the chapter PDF.

        Returns:
            List of `BlueprintHeadingEntry` items derived from bookmarks.
        """
        entries: List[BlueprintHeadingEntry] = []
        try:
            toc = doc.get_toc(simple=True) or []
            for item in toc:
                if len(item) >= 3:
                    lvl = max(1, min(4, int(item[0])))
                    title = re.sub(r"[\s\u00a0]+", " ", str(item[1])).strip()
                    pg = int(item[2])
                    if 1 <= pg <= total_pages and title:
                        entries.append(
                            BlueprintHeadingEntry(
                                level=lvl,
                                title=title,
                                page_num=pg,
                                top_y=0.0,
                                source="outline",
                            )
                        )
        except Exception as exc:
            logger.debug("Outline extraction skipped: %s", exc)
        return entries

    @classmethod
    def _scan_single_page(
        cls,
        page: Any,
        page_num: int,
        font_counter: Counter,
        font_meta_map: Dict[Tuple[str, float, bool, bool], int],
    ) -> Tuple[PageLayoutBlueprint, List[BlueprintTableEntry], List[BlueprintHeadingEntry]]:
        """Scans a single PyMuPDF page for vector drawings, tables, columns, and zones.

        Args:
            page: PyMuPDF Page object.
            page_num: 1-indexed page number.
            font_counter: Counter accumulating `(family, size)` character counts.
            font_meta_map: Counter accumulating `(family, size, is_bold, is_italic)` line counts.

        Returns:
            Tuple of `(PageLayoutBlueprint, list_of_tables, list_of_headings)`.
        """
        rect = page.rect
        pw = float(rect.width or 612.0)
        ph = float(rect.height or 792.0)

        # 1. Inspect vector drawings (shaded boxes, border rectangles, horizontal table rules)
        shaded_boxes: List[List[float]] = []
        horiz_rules: List[Tuple[float, float, float]] = []
        drawing_count = 0
        try:
            drawings = page.get_drawings() or []
            drawing_count = len(drawings)
            for d in drawings:
                d_rect = d.get("rect")
                if d_rect is not None:
                    x0, y0, x1, y1 = float(d_rect.x0), float(d_rect.y0), float(d_rect.x1), float(d_rect.y1)
                    w = x1 - x0
                    h = y1 - y0
                    if h <= 3.5 and w >= 60.0:
                        horiz_rules.append((y0, x0, x1))
                    elif w >= 120.0 and 22.0 <= h <= ph * 0.88 and d.get("fill") is not None:
                        shaded_boxes.append([x0, y0, x1, y1])
                for item in d.get("items", []) or []:
                    if len(item) >= 3 and item[0] == "l":
                        p1, p2 = item[1], item[2]
                        if abs(float(p1.y) - float(p2.y)) <= 2.5 and abs(float(p2.x) - float(p1.x)) >= 60.0:
                            horiz_rules.append((float(p1.y), min(float(p1.x), float(p2.x)), max(float(p1.x), float(p2.x))))
                    elif len(item) >= 2 and item[0] == "re":
                        r_box = item[1]
                        rw = float(r_box.x1) - float(r_box.x0)
                        rh = float(r_box.y1) - float(r_box.y0)
                        if rh <= 3.5 and rw >= 60.0:
                            horiz_rules.append((float(r_box.y0), float(r_box.x0), float(r_box.x1)))
        except Exception:
            pass

        # 2. Extract text lines with coordinates, rotation direction, and font styles
        raw_dict = page.get_text("dict")
        blocks = raw_dict.get("blocks", [])
        total_lines = 0
        rotated_lines = 0
        line_records: List[Dict[str, Any]] = []

        for b in blocks:
            if b.get("type", 0) != 0:
                continue
            for line in b.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                dx, dy = line.get("dir", (1.0, 0.0))
                total_lines += 1
                if abs(dx) <= 0.15 and abs(dy) >= 0.85:
                    rotated_lines += 1
                lx0, ly0, lx1, ly1 = line.get("bbox", (0.0, 0.0, 0.0, 0.0))
                if abs(dx) <= 0.15 and abs(dy) >= 0.85 and dy < 0:
                    # Transform 90-degree CCW landscape coordinates
                    nx0, ny0, nx1, ny1 = ph - ly1, lx0, ph - ly0, lx1
                    lx0, ly0, lx1, ly1 = nx0, ny0, nx1, ny1

                txt_parts = []
                max_sz = 0.0
                dom_fam = ""
                is_bold = False
                is_italic = False
                for sp in spans:
                    s_txt = sp.get("text", "").strip()
                    if not s_txt:
                        continue
                    txt_parts.append(s_txt)
                    sz = round(float(sp.get("size", 10.0)), 1)
                    fam = str(sp.get("font", "")).split("+")[-1]
                    flags = int(sp.get("flags", 0))
                    b_flag = bool(flags & 16) or "bold" in fam.lower() or "bd" in fam.lower() or "heavy" in fam.lower()
                    i_flag = bool(flags & 2) or "italic" in fam.lower() or "oblique" in fam.lower()
                    if sz >= max_sz:
                        max_sz = sz
                        dom_fam = fam
                        is_bold = b_flag
                        is_italic = i_flag
                    font_counter[(fam, sz)] += len(s_txt)
                    font_meta_map[(fam, sz, b_flag, i_flag)] = font_meta_map.get((fam, sz, b_flag, i_flag), 0) + 1

                full_line = " ".join(txt_parts).strip()
                if full_line:
                    line_records.append(
                        {
                            "text": full_line,
                            "bbox": [float(lx0), float(ly0), float(lx1), float(ly1)],
                            "size": max_sz,
                            "family": dom_fam,
                            "is_bold": is_bold,
                            "is_italic": is_italic,
                        }
                    )

        is_rotated = total_lines >= 5 and (rotated_lines / total_lines) > 0.65
        eff_pw = ph if is_rotated else pw
        eff_ph = pw if is_rotated else ph

        if not line_records:
            return (
                PageLayoutBlueprint(
                    page_num=page_num,
                    width=eff_pw,
                    height=eff_ph,
                    layout_mode="blank",
                    drawing_rects_count=drawing_count,
                ),
                [],
                [],
            )

        line_records.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))

        # 3. Detect column layout (single_column vs two_column vs rotated_landscape)
        left_spans = [
            r for r in line_records
            if r["bbox"][0] < eff_pw * 0.45 and r["bbox"][2] < eff_pw * 0.49 and len(r["text"]) > 15
        ]
        right_spans = [
            r for r in line_records
            if r["bbox"][0] >= eff_pw * 0.47 and len(r["text"]) > 15
        ]
        has_two_cols = len(left_spans) >= 4 and len(right_spans) >= 4
        layout_mode = (
            "rotated_landscape"
            if is_rotated
            else ("two_column" if has_two_cols else "single_column")
        )
        gutter_x = round(eff_pw * 0.48, 2) if has_two_cols else None

        # 4. Identify Table, Exhibit, Figure, and Heading anchors on this page
        zones: List[PageZone] = []
        page_tables: List[BlueprintTableEntry] = []
        page_headings: List[BlueprintHeadingEntry] = []

        for idx_r, rec in enumerate(line_records):
            txt = rec["text"]
            x0, y0, x1, y1 = rec["bbox"]

            # Check Table header anchor
            m_tbl = _TABLE_HEADER_RE.match(txt)
            if m_tbl and (y1 - y0) >= 7.5:
                t_num = m_tbl.group(1)
                inline_t = (m_tbl.group(2) or "").strip()
                # Look for adjacent title on the same line or wrapped line
                if not inline_t and idx_r + 1 < len(line_records):
                    nxt = line_records[idx_r + 1]
                    if abs(nxt["bbox"][1] - y0) <= 6.5 and nxt["bbox"][0] > x0:
                        inline_t = nxt["text"]
                if inline_t and (
                    inline_t[0].islower()
                    or inline_t.startswith((",", ".", ";", ":", ")", "]"))
                    or _PROSE_CONT_RE.match(inline_t)
                ):
                    continue
                # Check if vector horizontal ruling lines or shaded boxes back this table
                has_rules = any(y0 <= ry <= y0 + 260.0 for ry, _, _ in horiz_rules)
                has_shade = any(
                    abs(sb[1] - y0) <= 50.0 or (sb[1] <= y0 <= sb[3]) for sb in shaded_boxes
                )
                t_bbox = [x0, y0, min(eff_pw, max(x1 + 200.0, eff_pw * 0.85)), min(eff_ph, y0 + 260.0)]
                zones.append(
                    PageZone(
                        zone_type="TABLE_ZONE",
                        page_num=page_num,
                        bbox=t_bbox,
                        identifier=f"Table {t_num}",
                        caption=inline_t,
                        has_border_lines=has_rules,
                        has_shaded_fill=has_shade,
                    )
                )
                page_tables.append(
                    BlueprintTableEntry(
                        table_id=t_num,
                        title=inline_t,
                        page_num=page_num,
                        bbox=t_bbox,
                        has_grid_lines=has_rules,
                        source="pymupdf_vector",
                    )
                )
                continue

            # Check Exhibit / Callout header anchor
            m_ex = _EXHIBIT_HEADER_RE.match(txt)
            if m_ex:
                ex_id = m_ex.group(1)
                ex_title = (m_ex.group(2) or "").strip()
                if not (ex_title and _PROSE_CONT_RE.match(ex_title)):
                    zones.append(
                        PageZone(
                            zone_type="EXHIBIT_ZONE",
                            page_num=page_num,
                            bbox=[x0, y0, min(eff_pw, x1 + 250.0), min(eff_ph, y0 + 220.0)],
                            identifier=f"Exhibit {ex_id}",
                            caption=ex_title,
                            has_shaded_fill=bool(shaded_boxes),
                        )
                    )
                    continue

            # Check Figure header anchor
            m_fig = _FIGURE_HEADER_RE.match(txt)
            if m_fig:
                fig_id = m_fig.group(1)
                fig_title = (m_fig.group(2) or "").strip()
                if not (fig_title and _PROSE_CONT_RE.match(fig_title)):
                    zones.append(
                        PageZone(
                            zone_type="FIGURE_ZONE",
                            page_num=page_num,
                            bbox=[x0, y0, x1, y1],
                            identifier=f"Figure {fig_id}",
                            caption=fig_title,
                        )
                    )
                    continue

            # Check candidate typographic headings (size >= 12.5pt, valid heading syntax)
            if rec["size"] >= 12.5 and eff_ph * 0.05 < y0 < eff_ph * 0.90:
                clean_h = txt.strip("*# ")
                if (
                    len(clean_h) >= 4
                    and clean_h[0].isupper()
                    and not clean_h.endswith((".", ",", ";"))
                    and not re.search(r"[a-z]{2,}\.\s+[A-Z][a-z]", clean_h)
                ):
                    lvl = 1 if rec["size"] >= 18.0 else (2 if rec["size"] >= 14.0 else 3)
                    page_headings.append(
                        BlueprintHeadingEntry(
                            level=lvl,
                            title=clean_h,
                            page_num=page_num,
                            top_y=y0,
                            source="typography",
                        )
                    )

        page_bp = PageLayoutBlueprint(
            page_num=page_num,
            width=eff_pw,
            height=eff_ph,
            layout_mode=layout_mode,
            gutter_x=gutter_x,
            drawing_rects_count=drawing_count,
            zones=zones,
        )
        return page_bp, page_tables, page_headings

    @staticmethod
    def _resolve_body_font(
        font_counter: Counter,
        font_meta_map: Dict[Tuple[str, float, bool, bool], int],
    ) -> Tuple[str, float]:
        """Determines the modal body text font family and size across the chapter.

        Args:
            font_counter: Counter of `(family, size)` weighted by character count.
            font_meta_map: Mapping of `(family, size, is_bold, is_italic)` to line count.

        Returns:
            Tuple of `(body_font_family, body_font_size)`.
        """
        if not font_counter:
            return ("", 10.0)
        for (fam, sz), _ in font_counter.most_common():
            if 8.5 <= sz <= 12.0:
                return (fam, sz)
        top_fam, top_sz = font_counter.most_common(1)[0][0]
        return (top_fam, float(top_sz))

    @staticmethod
    def _build_font_roles(
        font_meta_map: Dict[Tuple[str, float, bool, bool], int],
        body_fam: str,
        body_sz: float,
    ) -> List[FontRoleSignature]:
        """Classifies chapter font styles into semantic roles (`h1`, `h2`, `h3`, `body`, `caption`).

        Args:
            font_meta_map: Counter of `(family, size, is_bold, is_italic)` line occurrences.
            body_fam: Modal body font family name.
            body_sz: Modal body font size in points.

        Returns:
            List of `FontRoleSignature` instances sorted by descending font size.
        """
        roles: List[FontRoleSignature] = []
        for (fam, sz, is_bold, is_italic), count in sorted(
            font_meta_map.items(), key=lambda x: (-x[0][1], -x[1])
        ):
            if count < 2 and sz < 13.0:
                continue
            if fam == body_fam and abs(sz - body_sz) <= 0.5 and not is_bold:
                role = "body"
            elif sz >= body_sz + 7.0:
                role = "h1"
            elif sz >= body_sz + 3.5 or (sz >= body_sz + 2.0 and is_bold):
                role = "h2"
            elif sz >= body_sz + 1.2 and is_bold:
                role = "h3"
            elif sz < body_sz - 0.8:
                role = "caption"
            else:
                continue
            roles.append(
                FontRoleSignature(
                    role=role,
                    font_family=fam,
                    font_size=sz,
                    is_bold=is_bold,
                    is_italic=is_italic,
                    sample_count=count,
                )
            )
        return roles[:15]
