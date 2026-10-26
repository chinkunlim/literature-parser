"""
Table Parser & Formatter
========================
Extracts structured tables from page XML coordinates or aligns in-paragraph tabular rows,
ensuring every Table block is rendered as a semantic HTML <table> or GFM pipe table
and never degraded into a naked bullet or numbered list.
"""

import html as html_mod
import logging
import re

from literature_parser.services.style_loader import load_style

logger = logging.getLogger(__name__)
_DEFAULT_STYLE = load_style()

_PROSE_CONTINUATION_RE = re.compile(
    r"^(?:is|are|was|were|has|have|had|can|may|will|would|should|could|"
    r"shows?|reveals?|indicates?|demonstrates?|illustrates?|summarizes?|lists?|"
    r"presents?|provides?|gives?|describes?|outlines?|compares?|contains?|"
    r"displays?|offers?|reports?|depicts?|identifies?|examines?|explains?|"
    r"in|on|at|from|with|by|for|to|of|and|or|as|that|which|where|when|because|if)\b",
    re.IGNORECASE,
)


class TableParser:
    """Specialized parser for academic and textbook tables."""

    @staticmethod
    def _render_items_as_html_table(
        tbl_header: str,
        items: list[str],
        clean_title: str = "",
        intro_text: str = "",
    ) -> str:
        """Renders a list of bulleted, numbered, or key-value table items as a semantic HTML table.

        Args:
            tbl_header: Formatted Markdown/bold heading line for the table.
            items: List of item strings belonging to the table.
            clean_title: Optional table title string used for column heading fallback.
            intro_text: Optional introductory instruction text inside the table.

        Returns:
            Formatted Markdown + HTML `<table class="textbook-table">` string.
        """
        lines = [tbl_header, ""]
        lines.append(
            '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">'
        )
        if intro_text:
            lines.append(f"  <caption>{intro_text}</caption>")

        # Check if items follow a 2-column pattern:
        # (a) "1. Term — Description" or "Term — Description"
        # (b) "Step 1. ..." or "1. ..."
        # (c) "Criterion 1: ..."
        dash_pairs = []
        num_pairs = []
        for it in items:
            s_it = re.sub(r"^[•\-\*❏☐☑]\s*", "", it.strip()).strip()
            m_dash = re.match(
                r"^((?:\d+[\.\)]\s*)?[A-Z][A-Za-z0-9\s\-\–\/\(\)]{1,45}?)\s*(?:—|–|\s-\s|:\s+)\s*(.+)$",
                s_it,
            )
            if m_dash:
                dash_pairs.append((m_dash.group(1).strip(), m_dash.group(2).strip()))
            m_num = re.match(r"^(?:❏\s*)?((?:Step\s+)?\d+[\.\)]?)\s+(.+)$", it.strip(), re.IGNORECASE)
            if m_num:
                num_pairs.append((m_num.group(1).strip(), m_num.group(2).strip()))

        if len(dash_pairs) >= max(2, int(len(items) * 0.6)):
            lines.append("  <thead>")
            lines.append("    <tr>")
            lines.append("      <th>Term / Category</th>")
            lines.append("      <th>Description</th>")
            lines.append("    </tr>")
            lines.append("  </thead>")
            lines.append("  <tbody>")
            for it in items:
                s_it = re.sub(r"^[•\-\*❏☐☑]\s*", "", it.strip()).strip()
                m_dash = re.match(
                    r"^((?:\d+[\.\)]\s*)?[A-Z][A-Za-z0-9\s\-\–\/\(\)]{1,45}?)\s*(?:—|–|\s-\s|:\s+)\s*(.+)$",
                    s_it,
                )
                if m_dash:
                    lines.append("    <tr>")
                    lines.append(f"      <td><strong>{m_dash.group(1).strip()}</strong></td>")
                    lines.append(f"      <td>{m_dash.group(2).strip()}</td>")
                    lines.append("    </tr>")
                else:
                    lines.append(
                        f'    <tr class="category-header"><td colspan="2"><strong>{s_it}</strong></td></tr>'
                    )
            lines.append("  </tbody>")
        elif len(num_pairs) >= max(2, int(len(items) * 0.6)):
            lines.append("  <thead>")
            lines.append("    <tr>")
            lines.append("      <th>#</th>")
            lines.append(f"      <th>{clean_title or 'Item / Statement'}</th>")
            lines.append("    </tr>")
            lines.append("  </thead>")
            lines.append("  <tbody>")
            for it in items:
                s_it = it.strip()
                m_num = re.match(
                    r"^(?:❏\s*)?((?:Step\s+)?\d+[\.\)]?)\s+(.+)$", s_it, re.IGNORECASE
                )
                if m_num:
                    lines.append("    <tr>")
                    lines.append(f"      <td>{m_num.group(1).strip()}</td>")
                    lines.append(f"      <td>{m_num.group(2).strip()}</td>")
                    lines.append("    </tr>")
                else:
                    s_clean = re.sub(r"^[•\-\*❏☐☑]\s*", "", s_it).strip()
                    lines.append(
                        f'    <tr class="category-header"><td colspan="2"><strong>{s_clean}</strong></td></tr>'
                    )
            lines.append("  </tbody>")
        else:
            col_hdr = clean_title if clean_title else "Key Points"
            lines.append("  <thead>")
            lines.append("    <tr>")
            lines.append(f"      <th>{col_hdr}</th>")
            lines.append("    </tr>")
            lines.append("  </thead>")
            lines.append("  <tbody>")
            for it in items:
                s_clean = re.sub(r"^[•\-\*❏☐☑]\s*", "", it.strip()).strip()
                lines.append("    <tr>")
                lines.append(f"      <td>{s_clean}</td>")
                lines.append("    </tr>")
            lines.append("  </tbody>")

        lines.append("</table>")
        return "\n".join(lines)

    @classmethod
    def detect_and_format_tables(cls, paragraphs: list, style_config: dict = None) -> list:
        """Detects blocks of lines with aligned tabular columns or Table headings with list items
        and converts them into structured Markdown or semantic HTML tables.

        Args:
            paragraphs: List of paragraph strings from the page parser.
            style_config: Optional style configuration dictionary.

        Returns:
            Updated list of paragraph strings with tables formatted.
        """
        style = style_config or _DEFAULT_STYLE or {}
        formatted = []
        for p in paragraphs:
            s = p.strip()
            lines = [line.strip() for line in s.splitlines() if line.strip()]
            if not lines:
                formatted.append(p)
                continue

            if (
                s.startswith((">", "!", "```", "|", "<table"))
                or re.search(r"\|\s*:?-+:?\s*\|", s)
                or any(line.startswith("|") or "<table" in line for line in lines)
                or (
                    s.startswith("#")
                    and not re.match(r"^#+\s*Table\b", s, re.IGNORECASE)
                )
            ):
                formatted.append(p)
                continue

            if len(lines) < 3:
                formatted.append(p)
                continue

            # 1. Multi-column aligned table
            row_cols = []
            is_table = True
            for line in lines:
                cols = [c.strip() for c in re.split(r"\s{2,}|\t", line) if c.strip()]
                if len(cols) < 2:
                    is_table = False
                    break
                row_cols.append(cols)

            if is_table and len(row_cols) >= 3:
                col_counts = [len(r) for r in row_cols]
                mode_cols = max(set(col_counts), key=col_counts.count)
                if mode_cols >= 2 and col_counts.count(mode_cols) >= len(col_counts) * 0.7:
                    header = row_cols[0]
                    header = (header + [""] * mode_cols)[:mode_cols]
                    sep = ["---"] * mode_cols
                    md_rows = [
                        "| " + " | ".join(header) + " |",
                        "| " + " | ".join(sep) + " |",
                    ]
                    for r in row_cols[1:]:
                        padded = (r + [""] * mode_cols)[:mode_cols]
                        md_rows.append("| " + " | ".join(padded) + " |")
                    formatted.append("\n".join(md_rows))
                    continue

            # 2. Check if this is a Table X.X with bullet-point or numbered list items
            m_table_title = re.match(
                r"^(?:###|\*\*)?\s*Table\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?\s*(?:\*\*)?\s*:?\s*(.*)",
                lines[0],
                re.IGNORECASE,
            )
            if m_table_title and len(lines) >= 3:
                item_rows = []
                for line in lines[1:]:
                    if line.startswith("|") or "<table" in line:
                        item_rows = []
                        break
                    m_b = re.match(r"^(?:[-*•❏☐☑]|\d+[\.\)]|Step\s+\d+[\.\):]?)\s*(.*)", line, re.IGNORECASE)
                    if m_b and line.strip():
                        item_rows.append(line.strip())
                if len(item_rows) >= 2:
                    t_num = m_table_title.group(1)
                    t_desc = m_table_title.group(2).strip()
                    t_desc = re.sub(r"^\*\*(.+?)\*\*$", r"\1", t_desc)
                    t_desc = re.sub(r"^\*(.+?)\*$", r"\1", t_desc)
                    t_desc = t_desc.strip()
                    if style.get("table_heading_style") == "bold-label":
                        header_line = (
                            f"**Table {t_num}** *{t_desc}*".strip()
                            if t_desc
                            else f"**Table {t_num}**"
                        )
                    else:
                        header_line = f"### Table {t_num} {t_desc}".strip()
                    formatted.append(
                        cls._render_items_as_html_table(
                            header_line, item_rows, clean_title=t_desc
                        )
                    )
                    continue

            formatted.append(p)
        return formatted

    @classmethod
    def extract_page_tables(
        cls,
        page_elem,
        fonts: dict,
        pw: float,
        ph: float,
        style_config: dict = None,
    ) -> tuple:
        """Extracts structured tables from page XML elements and renders them as semantic HTML tables.

        Args:
            page_elem: ElementTree Element for the `<page>`.
            fonts: Mapping of font id to font metadata (`{'size': ..., 'family': ...}`).
            pw: Page width in points.
            ph: Page height in points.
            style_config: Optional style configuration dictionary.

        Returns:
            Tuple of `(list_of_table_dicts, set_of_consumed_elements)` where each dict is
            `{'top': top, 'markdown': md_text}`.
        """
        style = style_config if style_config is not None else _DEFAULT_STYLE
        tables = []
        consumed = set()

        # Sort text elements top-to-bottom, left-to-right so out-of-order PDF streams never break early
        text_elements = sorted(
            page_elem.findall("text"),
            key=lambda el: (
                float(el.attrib.get("top", 0)),
                float(el.attrib.get("left", 0)),
            ),
        )

        table_headers = []
        for t in text_elements:
            txt = "".join(t.itertext()).strip()
            m = re.match(
                r"^(?:Table|TABLE)\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?(?:\s+(.*))?$",
                txt,
            )
            if not m:
                continue
            t_num = m.group(1)
            inline_title = (m.group(2) or "").strip()
            h = float(t.attrib.get("height", 0))
            top_v = float(t.attrib.get("top", 0))
            left_v = float(t.attrib.get("left", 0))
            width_v = float(t.attrib.get("width", 0))
            if h < 8.0:
                continue

            # Reject if there is prose text to the left on the same horizontal line (within the same column)
            preceders = [
                p
                for p in text_elements
                if p != t
                and abs(float(p.attrib.get("top", 0)) - top_v) <= 5.0
                and float(p.attrib.get("left", 0)) < left_v - 5.0
                and (left_v - (float(p.attrib.get("left", 0)) + float(p.attrib.get("width", 0))) < 40.0)
                and "".join(p.itertext()).strip()
            ]
            if preceders:
                continue

            # Check inline continuation or adjacent follower on the same line
            followers = [
                f
                for f in text_elements
                if f != t
                and abs(float(f.attrib.get("top", 0)) - top_v) <= 5.0
                and float(f.attrib.get("left", 0)) > left_v
                and (float(f.attrib.get("left", 0)) - (left_v + width_v) <= 30.0)
                and "".join(f.itertext()).strip()
            ]
            check_after = inline_title
            if not check_after and followers:
                check_after = "".join(followers[0].itertext()).strip()

            if check_after:
                if (
                    check_after[0].islower()
                    or check_after.startswith((",", ".", ";", ":", ")", "]", "—", "-"))
                    or _PROSE_CONTINUATION_RE.match(check_after)
                ):
                    continue

            table_headers.append((t, t_num, inline_title))

        for head_t, t_num, inline_title in table_headers:
            if head_t in consumed:
                continue
            h_top = float(head_t.attrib.get("top", 0))
            h_left = float(head_t.attrib.get("left", 0))
            h_width = float(head_t.attrib.get("width", 0))
            table_consumed = [head_t]

            # 1. Collect table title on the same line (Line 1) and optional wrapped title line (Line 2)
            line1_elems = [
                t
                for t in text_elements
                if t != head_t
                and t not in consumed
                and abs(float(t.attrib.get("top", 0)) - h_top) <= 6.5
                and float(t.attrib.get("left", 0)) > h_left
            ]
            line1_elems.sort(key=lambda el: float(el.attrib.get("left", 0)))

            title_parts = [inline_title] if inline_title else []
            cur_right = h_left + h_width
            for el in line1_elems:
                el_left = float(el.attrib.get("left", 0))
                el_w = float(el.attrib.get("width", 0))
                el_txt = "".join(el.itertext()).strip()
                if not el_txt:
                    table_consumed.append(el)
                    continue
                # Stop if horizontal gap exceeds 35pt (e.g., jumping to right column Figure/prose)
                if el_left - cur_right > 35.0:
                    break
                if re.match(r"^(?:Figure|Exhibit|Box)\s+\d+", el_txt, re.IGNORECASE):
                    break
                title_parts.append(el_txt)
                table_consumed.append(el)
                cur_right = max(cur_right, el_left + el_w)

            title_bottom = max(float(el.attrib.get("top", h_top)) for el in table_consumed)
            # Check for a wrapped second line of the title (within 15pt vertically)
            line2_elems = [
                t
                for t in text_elements
                if t not in table_consumed
                and t not in consumed
                and 4.0 < float(t.attrib.get("top", 0)) - h_top <= 15.5
                and float(t.attrib.get("left", 0)) >= h_left - 65.0
                and float(t.attrib.get("left", 0)) <= max(cur_right, h_left + 180.0)
                and "".join(t.itertext()).strip()
            ]
            if line2_elems:
                # Only treat as wrapped title if the elements on line2 are contiguous (single column)
                # and not a multi-column header row
                line2_elems.sort(key=lambda el: float(el.attrib.get("left", 0)))
                is_multi_col_line2 = False
                for e1, e2 in zip(line2_elems, line2_elems[1:]):
                    gap = float(e2.attrib.get("left", 0)) - (
                        float(e1.attrib.get("left", 0)) + float(e1.attrib.get("width", 0))
                    )
                    if gap > 22.0:
                        is_multi_col_line2 = True
                        break
                first_l2_txt = "".join(line2_elems[0].itertext()).strip()
                line1_str = " ".join(title_parts).strip()
                line1_continues = bool(
                    not line1_str
                    or cur_right - h_left >= 180.0
                    or re.search(
                        r"\b(?:of|and|for|in|to|with|by|on|the|a|an|from|or|as|into|between|among)\s*$",
                        line1_str,
                        re.IGNORECASE,
                    )
                )
                if (
                    not is_multi_col_line2
                    and line1_continues
                    and not re.match(r"^(?:[•\-\*❏☐☑]|\(?\d+[\.\)]|Step\s+\d+)\s*", first_l2_txt)
                ):
                    for el in line2_elems:
                        el_txt = "".join(el.itertext()).strip()
                        title_parts.append(el_txt)
                        table_consumed.append(el)
                        title_bottom = max(title_bottom, float(el.attrib.get("top", 0)))
                        cur_right = max(
                            cur_right,
                            float(el.attrib.get("left", 0)) + float(el.attrib.get("width", 0)),
                        )

            title = re.sub(r"[\s\u00a0]+", " ", " ".join(title_parts)).strip()

            # 2. Determine horizontal boundaries (table_left_min and table_right_max)
            # Check if this table is confined to the left/center portion of a multi-column page
            table_right_max = pw
            if h_left < pw * 0.35 and cur_right <= pw * 0.65:
                right_col_intruders = [
                    t
                    for t in text_elements
                    if t not in table_consumed
                    and float(t.attrib.get("left", 0)) >= max(cur_right + 35.0, pw * 0.48)
                    and (h_top - 40.0 <= float(t.attrib.get("top", 0)) <= title_bottom + 40.0)
                    and "".join(t.itertext()).strip()
                ]
                if right_col_intruders:
                    table_right_max = min(float(t.attrib.get("left", pw)) for t in right_col_intruders) - 10.0

            # Determine table_left_min: support centered headers (Career Counseling where h_left~229 and col0~51)
            # while excluding left-margin glossaries (Research Methods where h_left~189 and glossary~39)
            first_band_lefts = [
                float(t.attrib.get("left", 0))
                for t in text_elements
                if t not in table_consumed
                and t not in consumed
                and 0 < float(t.attrib.get("top", 0)) - title_bottom <= 65.0
                and float(t.attrib.get("left", 0)) < table_right_max
                and "".join(t.itertext()).strip()
            ]
            table_left_min = h_left - 15.0
            if first_band_lefts:
                max_left_shift = 200.0 if h_left >= pw * 0.25 else 115.0
                cand_lefts = [
                    lx for lx in first_band_lefts if lx >= 35.0 and (h_left - lx <= max_left_shift)
                ]
                if cand_lefts:
                    table_left_min = min(h_left, min(cand_lefts)) - 15.0

            # 3. Collect row candidates below title_bottom within [table_left_min, table_right_max]
            row_candidates = []
            for t in text_elements:
                if t in table_consumed or t in consumed:
                    continue
                top = float(t.attrib.get("top", 0))
                left = float(t.attrib.get("left", 0))
                w = float(t.attrib.get("width", 0))
                h = float(t.attrib.get("height", 0))
                txt = "".join(t.itertext()).strip()
                if not txt:
                    continue
                if top <= title_bottom or top > ph - 38.0:
                    continue
                if re.search(
                    r"\b(?:All rights reserved|Further reproduction is prohibited|WCN\s*\d+-\d+|may not be copied)\b",
                    txt,
                    re.IGNORECASE,
                ):
                    continue
                if left < table_left_min or left >= table_right_max:
                    continue
                if top - title_bottom > 580.0:
                    break

                fid = t.attrib.get("font", "")
                fsize = float(fonts.get(fid, {}).get("size", 10.0))
                # Stop if encountering a major section heading or another Table/Figure/Box header
                if fsize >= 16.0 or h >= 16.0:
                    break
                if re.match(
                    r"^(?:Table|TABLE|Figure|FIGURE|Box|BOX|Study Questions?|Journal Prompt|LO\s+\d+)\s+\d+",
                    txt,
                ):
                    break
                row_candidates.append(t)

            if not row_candidates:
                continue

            clean_title = title.strip()
            clean_title = re.sub(r"^\*\*(.+?)\*\*$", r"\1", clean_title)
            clean_title = re.sub(r"^\*(.+?)\*$", r"\1", clean_title)
            clean_title = clean_title.strip()
            if style.get("table_heading_style") == "bold-label":
                tbl_header = (
                    f"**Table {t_num}** *{clean_title}*"
                    if clean_title
                    else f"**Table {t_num}**"
                )
            else:
                tbl_header = f"### Table {t_num} {clean_title}".strip()

            # 4. Pre-skip optional table-wide intro note lines before the column headers
            # (e.g., "(Note: Cell means are inside...)" or "N stands for the size...")
            intro_notes = []
            intro_consumed = []
            scan_candidates = list(row_candidates)
            while scan_candidates:
                first_y = float(scan_candidates[0].attrib.get("top", 0))
                first_row_els = [
                    el
                    for el in scan_candidates
                    if abs(float(el.attrib.get("top", 0)) - first_y) <= 4.5
                ]
                joined_line = " ".join("".join(el.itertext()).strip() for el in first_row_els).strip()
                max_w = max(float(el.attrib.get("width", 0)) for el in first_row_els)
                is_intro_line = bool(
                    re.match(
                        r"^(?:\(?Note\b|\([a-zA-Z]\)\s+|Below is a list|If you have a client|The following statements|My racial/ethnic|My client’s racial|N\s+stands\s+for|The sample sizes are based|Check all|ac-\s*cording|ABILITY TO|anticipated)",
                        joined_line,
                        re.IGNORECASE,
                    )
                    or (len(first_row_els) == 1 and max_w > 240.0 and not re.search(r"—|–", joined_line))
                )
                if is_intro_line and first_y - title_bottom <= 115.0:
                    intro_notes.append(joined_line)
                    for el in first_row_els:
                        intro_consumed.append(el)
                        scan_candidates.remove(el)
                else:
                    break

            # 5. Detect multi-column grid table (including multi-line bottom-aligned headers)
            ref_top = (
                float(intro_consumed[-1].attrib.get("top", title_bottom))
                if intro_consumed
                else title_bottom
            )
            top_band_elems = [
                t
                for t in scan_candidates
                if float(t.attrib.get("top", 0)) - ref_top <= 50.0
                and float(t.attrib.get("height", 0)) >= 7.5
                and "".join(t.itertext()).strip() not in ("*", "a", "b", "c", "†")
            ]
            # Cluster top_band_elems into distinct horizontal lines (within 4.5pt)
            band_lines = []
            for el in top_band_elems:
                el_top = float(el.attrib.get("top", 0))
                for bl in band_lines:
                    if abs(bl["top"] - el_top) <= 4.5:
                        bl["elems"].append(el)
                        break
                else:
                    band_lines.append({"top": el_top, "elems": [el]})

            def merge_line_cells(elems_on_line):
                sorted_els = sorted(elems_on_line, key=lambda x: float(x.attrib.get("left", 0)))
                merged = []
                for c in sorted_els:
                    c_left = float(c.attrib.get("left", 0))
                    c_w = float(c.attrib.get("width", 0))
                    c_txt = "".join(c.itertext()).strip()
                    if merged and (c_left - (merged[-1]["left"] + merged[-1]["width"]) <= 14.0):
                        sep = " " if c_left - (merged[-1]["left"] + merged[-1]["width"]) > 2.5 else ""
                        merged[-1]["text"] += sep + c_txt
                        merged[-1]["width"] = max(
                            merged[-1]["width"], (c_left + c_w) - merged[-1]["left"]
                        )
                        merged[-1]["elements"].append(c)
                    else:
                        merged.append(
                            {
                                "left": c_left,
                                "width": c_w,
                                "text": c_txt,
                                "elements": [c],
                            }
                        )
                return merged

            is_grid = False
            header_bottom_top = 0.0
            header_cells = []
            col_bounds = []
            header_titles = []

            if band_lines:
                # Consider consecutive header band lines only where each line is within 13.5pt of the previous line,
                # or up to 16.5pt if the upper header line is a 1-cell spanning super-header (e.g. 'Time' above 4 columns in Table 13.2, Refs: ISSUE-016)
                first_band_top = band_lines[0]["top"]
                header_band_lines = [band_lines[0]]
                for bl_cand in band_lines[1:3]:
                    prev_cells_count = len(merge_line_cells(header_band_lines[-1]["elems"]))
                    max_hdr_gap = 16.5 if prev_cells_count < 2 else 13.5
                    if bl_cand["top"] - header_band_lines[-1]["top"] <= max_hdr_gap:
                        header_band_lines.append(bl_cand)
                    else:
                        break
                # Find the anchor line with the most horizontal cells (>= 2)
                best_idx = 0
                best_merged = merge_line_cells(header_band_lines[0]["elems"])
                for idx_bl, bl in enumerate(header_band_lines):
                    m_bl = merge_line_cells(bl["elems"])
                    # Only promote a lower line as anchor if the upper lines have fewer cells and don't look like data rows
                    if len(m_bl) > len(best_merged) and all(
                        len(merge_line_cells(header_band_lines[k]["elems"])) < len(m_bl)
                        for k in range(idx_bl)
                    ):
                        best_idx = idx_bl
                        best_merged = m_bl

                # Reject if the candidate header row is actually a bulleted/numbered list item or Term — Description row
                first_cell_txt = best_merged[0]["text"] if best_merged else ""
                looks_like_list_or_dash = bool(
                    re.match(r"^(?:[•\-\*❏☐☑]|\d+[\.\)]|Criterion\s+\d+|Step\s+\d+)\s*", first_cell_txt)
                    or any("—" in m["text"] or m["text"].startswith("—") for m in best_merged)
                )

                if len(best_merged) >= 2 and not looks_like_list_or_dash:
                    header_bottom_top = header_band_lines[best_idx]["top"]
                    # Attach any upper header lines (0 .. best_idx - 1) to the nearest column in best_merged
                    for k in range(best_idx):
                        upper_merged = merge_line_cells(header_band_lines[k]["elems"])
                        for um in upper_merged:
                            u_center = um["left"] + um["width"] / 2.0
                            nearest = min(
                                best_merged,
                                key=lambda bm: abs((bm["left"] + bm["width"] / 2.0) - u_center),
                            )
                            nearest["text"] = (um["text"] + " " + nearest["text"]).strip()
                            nearest["left"] = min(nearest["left"], um["left"])
                            nearest["elements"].extend(um["elements"])

                    # Attach any superscripts (like Scale*) on the header band
                    for sc in scan_candidates:
                        sc_top = float(sc.attrib.get("top", 0))
                        if first_band_top - 4.0 <= sc_top <= header_bottom_top + 5.0:
                            if all(sc not in bm["elements"] for bm in best_merged):
                                sc_txt = "".join(sc.itertext()).strip()
                                sc_left = float(sc.attrib.get("left", 0))
                                if sc_txt in ("*", "a", "b", "c", "†", "0", "1", "2"):
                                    nearest = min(
                                        best_merged,
                                        key=lambda bm: abs((bm["left"] + bm["width"]) - sc_left),
                                    )
                                    nearest["text"] += sc_txt
                                    nearest["elements"].append(sc)

                    col_bounds = [m["left"] for m in best_merged]
                    leftmost_row_left = min(
                        [
                            float(t.attrib.get("left", 0))
                            for t in scan_candidates
                            if float(t.attrib.get("top", 0)) > header_bottom_top + 5.5
                        ]
                        or [9999.0]
                    )
                    if leftmost_row_left < col_bounds[0] - 35.0:
                        col_bounds.insert(0, leftmost_row_left)
                        header_titles = [""] + [m["text"] for m in best_merged]
                    else:
                        header_titles = [m["text"] for m in best_merged]
                    header_cells = [elem for m in best_merged for elem in m["elements"]]
                    is_grid = True

            if is_grid:
                def get_col_idx(x: float) -> int:
                    for idx_c, (b1, b2) in enumerate(zip(col_bounds, col_bounds[1:])):
                        if x < (b1 + b2) / 2.0:
                            return idx_c
                    return len(col_bounds) - 1

                raw_grid_data = [
                    t
                    for t in scan_candidates
                    if float(t.attrib.get("top", 0)) > header_bottom_top + 5.0
                    and t not in header_cells
                ]
                raw_grid_data.sort(
                    key=lambda t: (
                        float(t.attrib.get("top", 0)),
                        float(t.attrib.get("left", 0)),
                    )
                )

                grid_data = []
                curr_row_top = header_bottom_top
                fn_start_top = None
                for d in raw_grid_data:
                    d_top = float(d.attrib.get("top", 0))
                    d_left = float(d.attrib.get("left", 0))
                    d_w = float(d.attrib.get("width", 0))
                    d_txt = "".join(d.itertext()).strip()
                    d_fid = d.attrib.get("font", "")
                    d_fsize = float(fonts.get(d_fid, {}).get("size", 9.0))

                    max_grid_gap = 46.0 if not grid_data else 40.0
                    if d_top - curr_row_top > max_grid_gap:
                        break
                    if re.match(
                        r"^(?:Steps?:?|\(?\d+\)?\s*Insert|\(?\d+\)?\s*Calculate)\b",
                        d_txt,
                        re.IGNORECASE,
                    ):
                        break
                    is_fn_start = (d_top > header_bottom_top + 25.0) and bool(
                        re.match(
                            r"^(?:\*+[A-Za-z]|Note\b|\.?\s*BART indicates\b|a\s*See\s+)",
                            d_txt,
                            re.IGNORECASE,
                        )
                    )
                    if is_fn_start and fn_start_top is None:
                        fn_start_top = d_top

                    is_fn = fn_start_top is not None and d_top >= fn_start_top
                    if not is_fn:
                        # Stop if a full-width main body prose paragraph starts below the table
                        if d_w > 280.0 and d_fsize >= 9.4 and (d_top - curr_row_top > 13.0):
                            break
                        if (
                            len(col_bounds) >= 2
                            and d_left < col_bounds[0] + 25.0
                            and d_w > max(295.0, (col_bounds[-1] - col_bounds[0]) + 40.0)
                        ):
                            break
                    grid_data.append(d)
                    curr_row_top = max(curr_row_top, d_top)

                row_lines = []
                for d in grid_data:
                    d_top = float(d.attrib.get("top", 0))
                    d_txt = "".join(d.itertext()).strip()
                    if fn_start_top is not None and d_top >= fn_start_top:
                        continue
                    if re.match(r"^(?:\*+[A-Za-z]|Note\b|\.?\s*BART indicates\b)", d_txt, re.IGNORECASE):
                        continue
                    for r in row_lines:
                        if abs(r["top"] - d_top) <= 4.8:
                            r["elements"].append(d)
                            break
                    else:
                        row_lines.append({"top": d_top, "elements": [d]})

                grid_consumed = (
                    list(table_consumed)
                    + list(intro_consumed)
                    + list(header_cells)
                    + list(grid_data)
                )
                fn_texts = []
                parsed_rows = []
                prev_row_top = None

                # Check if header_cells were actually data Row 1 of a headless 2-column table (e.g. Table 14.1 REM sleep)
                header_has_bold = any(
                    elem.find("b") is not None for elem in header_cells
                )
                if (
                    not header_has_bold
                    and len(header_titles) == 2
                    and any(w in header_titles[0].lower() for w in ("sleep", "stage", "step"))
                ):
                    parsed_rows.append(list(header_titles))
                    header_titles = ["Term / Category", "Description"]

                for r in row_lines:
                    row_cells = [[] for _ in range(len(header_titles))]
                    for d in r["elements"]:
                        d_top = float(d.attrib.get("top", 0))
                        d_left = float(d.attrib.get("left", 0))
                        d_txt = "".join(d.itertext()).strip()
                        if fn_start_top is not None and d_top >= fn_start_top:
                            continue
                        if re.match(r"^(?:\*+[A-Za-z]|Note\b)", d_txt, re.IGNORECASE):
                            fn_texts.append(d_txt)
                            continue
                        c_idx = get_col_idx(d_left)
                        row_cells[c_idx].append(d_txt)

                    cell_strs = [" ".join(c).strip() for c in row_cells]
                    joined_row = "".join(cell_strs).strip()
                    if re.fullmatch(r"^[ac\s\.\,\-]+$", joined_row) and len(joined_row) <= 4:
                        continue
                    if not any(cell_strs):
                        continue

                    # Stitch multi-line wrapped cell continuations into the previous row (Refs: ISSUE-016)
                    row_max_top = max(float(el.attrib.get("top", r["top"])) for el in r["elements"])
                    gap_from_prev = (r["top"] - prev_row_top) if prev_row_top is not None else 999.0
                    if prev_row_top is not None and gap_from_prev <= 15.0 and parsed_rows:
                        prev_r = parsed_rows[-1]
                        prev_is_banner = bool(prev_r[0] and not any(prev_r[1:]))
                        cur_has_no_col0 = (not cell_strs[0] and any(cell_strs[1:])) and gap_from_prev <= 11.5
                        cur_col0_wraps = (
                            bool(cell_strs[0])
                            and (
                                cell_strs[0][0].islower()
                                or cell_strs[0].startswith(("(", "or ", "and ", "to ", "of ", "with "))
                                or prev_r[0].endswith(("-", "/", ",", ";", "and", "or", "of", "for", "with", "to", "in", "the", "a", "an", "that", "work"))
                            )
                        )
                        any_col_mid_sentence = False
                        for ci_chk, cs_chk in enumerate(cell_strs):
                            prev_c = prev_r[ci_chk] if ci_chk < len(prev_r) else ""
                            if cs_chk and (
                                cs_chk[0].islower()
                                or cs_chk.startswith(("•", ")"))
                            ):
                                any_col_mid_sentence = True
                                break
                            if prev_c and cs_chk and (
                                prev_c.endswith(("-", ",", ";", "/", "to be", "and", "or", "of", "for", "in", "with", "by", "on", "the", "a", "an", "from"))
                                or (prev_c.count("“") > prev_c.count("”"))
                            ):
                                any_col_mid_sentence = True
                                break

                        if not prev_is_banner and (cur_has_no_col0 or cur_col0_wraps or any_col_mid_sentence):
                            is_stub_trait_table = (header_titles[0] == "" and len(header_titles) >= 5)
                            for ci, cs in enumerate(cell_strs):
                                if cs:
                                    if not prev_r[ci]:
                                        prev_r[ci] = cs
                                    elif prev_r[ci].endswith("-") and cs[0].islower():
                                        prev_r[ci] = prev_r[ci][:-1] + cs
                                    elif cs.startswith("•"):
                                        prev_r[ci] = f"{prev_r[ci]}<br>{cs}"
                                    elif cs.startswith("“") and prev_r[ci].endswith((".”", "!”", "?”", '"')):
                                        prev_r[ci] = f"{prev_r[ci]}<br>{cs}"
                                    elif (
                                        is_stub_trait_table
                                        and ci >= 1
                                        and cs[0].isupper()
                                        and not prev_r[ci].endswith(("-", ",", "and", "or", "of", "in", "to"))
                                    ):
                                        prev_r[ci] = f"{prev_r[ci]}<br>{cs}"
                                    else:
                                        prev_r[ci] = (prev_r[ci] + " " + cs).strip()
                            prev_row_top = row_max_top
                            continue

                    parsed_rows.append(cell_strs)
                    prev_row_top = row_max_top

                if fn_start_top is not None:
                    fn_elements = [
                        d
                        for d in grid_data
                        if float(d.attrib.get("top", 0)) >= fn_start_top
                    ]
                    fn_elements.sort(
                        key=lambda t: (
                            float(t.attrib.get("top", 0)),
                            float(t.attrib.get("left", 0)),
                        )
                    )
                    for d in fn_elements:
                        d_txt = "".join(d.itertext()).strip()
                        if d_txt and d_txt not in fn_texts:
                            fn_texts.append(d_txt)

                clean_fn = [f for f in fn_texts if f not in ("*", "·", "•", ":")]
                raw_note = " ".join(clean_fn).lstrip("*").strip() if clean_fn else ""
                note_str = re.sub(r"^\.?\s*", "", raw_note)
                if note_str.lower().startswith("note"):
                    note_str = re.sub(r"^note\s*[:\.]?\s*", "Note. ", note_str, flags=re.IGNORECASE)

                if parsed_rows:
                    table_lines = [tbl_header, ""]
                    table_lines.append(
                        '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">'
                    )
                    if intro_notes:
                        table_lines.append(
                            f"  <caption>{' '.join(intro_notes)}</caption>"
                        )
                    table_lines.append("  <thead>")
                    table_lines.append("    <tr>")
                    for th in header_titles:
                        table_lines.append(f"      <th>{th}</th>")
                    table_lines.append("    </tr>")
                    table_lines.append("  </thead>")
                    table_lines.append("  <tbody>")
                    for r in parsed_rows:
                        is_cat_banner = (
                            bool(r[0])
                            and not any(r[1:])
                            and len(r[0]) < 65
                            and not r[0].endswith(".")
                        )
                        if is_cat_banner:
                            colspan = len(header_titles)
                            table_lines.append(
                                f'    <tr class="category-header"><td colspan="{colspan}"><strong>{r[0]}</strong></td></tr>'
                            )
                        else:
                            table_lines.append("    <tr>")
                            for c in r:
                                table_lines.append(f"      <td>{c}</td>")
                            if len(r) < len(header_titles):
                                for _ in range(len(header_titles) - len(r)):
                                    table_lines.append("      <td>—</td>")
                            table_lines.append("    </tr>")
                    table_lines.append("  </tbody>")
                    if note_str:
                        colspan = len(header_titles)
                        table_lines.append("  <tfoot>")
                        table_lines.append(
                            f'    <tr class="table-notes"><td colspan="{colspan}"><em>* {note_str}</em></td></tr>'
                        )
                        table_lines.append("  </tfoot>")
                    table_lines.append("</table>")

                    consumed.update(grid_consumed)
                    tables.append({"top": h_top, "markdown": "\n".join(table_lines)})
                    continue

            # 6. Check if this is a Criterion-based table (e.g. Table 2.2: Criterion 1, Criterion 2, Criterion 3)
            crit_elems = [
                t
                for t in row_candidates
                if re.match(r"^Criterion\s+\d+:", "".join(t.itertext()).strip(), re.IGNORECASE)
            ]
            if len(crit_elems) >= 2:
                crit_rows = []
                grid_consumed = list(table_consumed) + list(intro_consumed)
                for i, c_el in enumerate(crit_elems):
                    c_top = float(c_el.attrib.get("top", 0))
                    c_txt = "".join(c_el.itertext()).strip()
                    grid_consumed.append(c_el)
                    next_c_top = (
                        float(crit_elems[i + 1].attrib.get("top", 0))
                        if i + 1 < len(crit_elems)
                        else 9999.0
                    )
                    desc_parts = []
                    for t in row_candidates:
                        t_top = float(t.attrib.get("top", 0))
                        t_txt = "".join(t.itertext()).strip()
                        if t != c_el and c_top - 3 <= t_top < next_c_top - 3:
                            desc_parts.append(t_txt)
                            grid_consumed.append(t)
                    desc_str = re.sub(r"\s+", " ", " ".join(desc_parts)).strip()
                    crit_rows.append((c_txt, desc_str))

                table_lines = [
                    tbl_header,
                    "",
                    '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">',
                ]
                if intro_notes:
                    table_lines.append(f"  <caption>{' '.join(intro_notes)}</caption>")
                table_lines.extend(
                    [
                        "  <thead>",
                        "    <tr><th>Criterion</th><th>Description</th></tr>",
                        "  </thead>",
                        "  <tbody>",
                    ]
                )
                for c_txt, desc_str in crit_rows:
                    table_lines.append(
                        f"    <tr><td><strong>{c_txt}</strong></td><td>{desc_str}</td></tr>"
                    )
                table_lines.extend(["  </tbody>", "</table>"])

                consumed.update(grid_consumed)
                tables.append({"top": h_top, "markdown": "\n".join(table_lines)})
                continue

            # 7. Check if this is Archetype 2: Comparison Table (e.g. Strengths and Weaknesses)
            banner_nodes = [
                t
                for t in row_candidates
                if re.match(
                    r"^(?:Strengths|Weaknesses|Advantages|Disadvantages)(?:\s+of\b|:)",
                    "".join(t.itertext()).strip(),
                    re.IGNORECASE,
                )
            ]
            if len(banner_nodes) >= 1 or re.search(
                r"\b(?:Strengths\s+and\s+Weaknesses|Advantages\s+and\s+Disadvantages)\b",
                clean_title,
                re.IGNORECASE,
            ):
                banner_sections = []
                current_banner_title = ""
                current_banner_items = []
                grid_consumed = list(table_consumed)

                for t in row_candidates:
                    txt = "".join(t.itertext()).strip()
                    if not txt:
                        continue
                    m_b = re.match(
                        r"^(?:Strengths|Weaknesses|Advantages|Disadvantages)(?:\s+of\b|:).*",
                        txt,
                        re.IGNORECASE,
                    )
                    if m_b:
                        if current_banner_title or current_banner_items:
                            banner_sections.append((current_banner_title, current_banner_items))
                        current_banner_title = txt
                        current_banner_items = []
                        grid_consumed.append(t)
                    else:
                        is_bullet = bool(re.match(r"^[•\-\*]\s*", txt))
                        if is_bullet:
                            clean_it = re.sub(r"^[•\-\*]\s*", "", txt).strip()
                            current_banner_items.append(clean_it)
                            grid_consumed.append(t)
                        elif current_banner_items:
                            current_banner_items[-1] += " " + txt
                            grid_consumed.append(t)
                        elif current_banner_title:
                            current_banner_items.append(txt)
                            grid_consumed.append(t)

                if current_banner_title or current_banner_items:
                    banner_sections.append((current_banner_title, current_banner_items))

                if len(banner_sections) >= 1 and sum(len(it) for _, it in banner_sections) >= 2:
                    table_lines = [
                        tbl_header,
                        "",
                        '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">',
                        "  <thead>",
                        f"    <tr><th>{clean_title or 'Comparison'}</th></tr>",
                        "  </thead>",
                        "  <tbody>",
                    ]
                    for b_title, b_items in banner_sections:
                        if b_title:
                            table_lines.append(
                                f'    <tr class="category-header"><td><strong>{b_title}</strong></td></tr>'
                            )
                        for it in b_items:
                            clean_it = re.sub(r"\s+", " ", it).strip()
                            if clean_it:
                                table_lines.append(f"    <tr><td>• {clean_it}</td></tr>")
                    table_lines.extend(["  </tbody>", "</table>"])

                    consumed.update(grid_consumed)
                    tables.append({"top": h_top, "markdown": "\n".join(table_lines)})
                    continue

            # 8. General structured row/item table (bullets, numbered steps, checklists, Term — Description)
            # Group remaining scan_candidates into visual lines by top (within 4.8pt)
            visual_lines = []
            local_consumed = list(table_consumed) + list(intro_consumed)
            prev_v_top = ref_top
            for t in scan_candidates:
                t_top = float(t.attrib.get("top", 0))
                t_w = float(t.attrib.get("width", 0))
                t_fid = t.attrib.get("font", "")
                t_fsize = float(fonts.get(t_fid, {}).get("size", 9.0))
                max_v_gap = 45.0 if not visual_lines else 35.0
                if t_top - prev_v_top > max_v_gap:
                    break
                if t_w > 310.0 and t_fsize >= 9.8 and (t_top - prev_v_top > 13.5) and visual_lines:
                    break
                for vl in visual_lines:
                    if abs(vl["top"] - t_top) <= 4.8:
                        vl["elems"].append(t)
                        break
                else:
                    visual_lines.append({"top": t_top, "elems": [t]})
                local_consumed.append(t)
                prev_v_top = max(prev_v_top, t_top)

            items = []
            curr_item = []
            prev_vl_top = None
            for vl in visual_lines:
                vl["elems"].sort(key=lambda el: float(el.attrib.get("left", 0)))
                line_txt = " ".join(
                    "".join(el.itertext()).strip()
                    for el in vl["elems"]
                    if "".join(el.itertext()).strip()
                ).strip()
                if not line_txt:
                    continue
                v_gap = (vl["top"] - prev_vl_top) if prev_vl_top is not None else 0.0
                is_new_entry = bool(
                    re.match(
                        r"^(?:[•\-\*❏☐☑]|\(?\d+[\.\)]|Step\s+\d+[\.\):]?|Phase\s+\d+[\.\):]?|Stage\s+\d+[\.\):]?|Decision\s+Rule\s+\d+:?|If:|Then:|Conclusion:|[IVX]+\.\s+[A-Z])\s*",
                        line_txt,
                    )
                    or re.match(r"^[A-Z][A-Za-z\-\s]{2,40}\s*(?:—|–)\s*", line_txt)
                    or (line_txt.isupper() and len(line_txt) >= 4)
                    or (v_gap >= 17.5 and line_txt[0].isupper())
                )
                prev_vl_top = vl["top"]
                if is_new_entry:
                    if curr_item:
                        items.append(" ".join(curr_item))
                    curr_item = [line_txt]
                elif curr_item:
                    if curr_item[-1].endswith("-") and line_txt and line_txt[0].islower():
                        curr_item[-1] = curr_item[-1][:-1] + line_txt
                    else:
                        curr_item.append(line_txt)
                else:
                    curr_item = [line_txt]

            if curr_item:
                items.append(" ".join(curr_item))

            if len(items) >= 2:
                consumed.update(local_consumed)
                html_tbl = cls._render_items_as_html_table(
                    tbl_header,
                    items,
                    clean_title=clean_title,
                    intro_text=" ".join(intro_notes),
                )
                tables.append({"top": h_top, "markdown": html_tbl})

        # 9. Detect embedded Box sub-tables (e.g. "Transferable Skills: Skills | Specific Operations" in Career Counseling Box 9-1..9-6)
        for t in text_elements:
            if t in consumed:
                continue
            txt = "".join(t.itertext()).strip()
            if txt == "Transferable Skills":
                ts_top = float(t.attrib.get("top", 0))
                # Check if "Skills" and "Specific Operations" appear within 22pt below
                sub_cands = [
                    el
                    for el in text_elements
                    if el not in consumed
                    and el != t
                    and 0 < float(el.attrib.get("top", 0)) - ts_top <= 160.0
                    and "".join(el.itertext()).strip()
                ]
                has_skills_hdr = any(
                    "".join(el.itertext()).strip() == "Skills"
                    and float(el.attrib.get("top", 0)) - ts_top <= 22.0
                    for el in sub_cands
                )
                if not has_skills_hdr:
                    continue
                ts_consumed = [t]
                col_split_x = 175.0
                ts_rows: list[list[str]] = []
                hdr_bottom = ts_top + 18.0
                for el in sub_cands:
                    el_top = float(el.attrib.get("top", 0))
                    el_left = float(el.attrib.get("left", 0))
                    el_txt = "".join(el.itertext()).strip()
                    if el_txt in ("Possible Life Career Themes",) or el_txt.startswith("Box "):
                        break
                    if el_top - ts_top <= 22.0 and (el_txt == "Skills" or "Operations" in el_txt):
                        ts_consumed.append(el)
                        hdr_bottom = max(hdr_bottom, el_top)
                        if "Operations" in el_txt:
                            col_split_x = float(el.attrib.get("left", 180.0)) - 10.0
                        continue
                    if el_top <= hdr_bottom:
                        continue
                    ts_consumed.append(el)
                    is_col0 = el_left < col_split_x
                    is_new_num = bool(re.match(r"^\d+\.\s+", el_txt))
                    if is_col0 and is_new_num:
                        ts_rows.append([el_txt, ""])
                    elif not is_col0 and is_new_num:
                        if ts_rows and not ts_rows[-1][1]:
                            ts_rows[-1][1] = el_txt
                        else:
                            ts_rows.append(["", el_txt])
                    elif ts_rows:
                        c_i = 0 if is_col0 else 1
                        if ts_rows[-1][c_i].endswith("-") and el_txt[0].islower():
                            ts_rows[-1][c_i] = ts_rows[-1][c_i][:-1] + el_txt
                        else:
                            ts_rows[-1][c_i] = (ts_rows[-1][c_i] + " " + el_txt).strip()
                if ts_rows:
                    consumed.update(ts_consumed)
                    ts_html = [
                        "**Transferable Skills**",
                        "",
                        '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.0em 0;">',
                        "  <thead>",
                        "    <tr><th>Skills</th><th>Specific Operations</th></tr>",
                        "  </thead>",
                        "  <tbody>",
                    ]
                    for r0, r1 in ts_rows:
                        ts_html.append(f"    <tr><td>{r0}</td><td>{r1}</td></tr>")
                    ts_html.extend(["  </tbody>", "</table>"])
                    tables.append({"top": ts_top, "markdown": "\n".join(ts_html)})

        return tables, consumed

    @classmethod
    def format_matrix_to_table(cls, matrix: list) -> str:
        """Formats a 2D string matrix into a clean standard GFM Markdown pipe table.

        Args:
            matrix: 2D list of cell strings [row][col].

        Returns:
            Formatted Markdown table string.
        """
        if not matrix:
            return ""
        header = matrix[0]
        col_count = len(header)
        sep = ["---"] * col_count
        lines = [
            "| " + " | ".join(str(c) for c in header) + " |",
            "| " + " | ".join(sep) + " |",
        ]
        for row in matrix[1:]:
            padded = (list(row) + [""] * col_count)[:col_count]
            lines.append("| " + " | ".join(str(c) for c in padded) + " |")
        return "\n".join(lines)

    @classmethod
    def format_spanned_matrix_to_html(
        cls,
        cell_spans: dict,
        num_rows: int,
        num_cols: int,
        table_class: str = "book-table",
        caption: str = "",
    ) -> str:
        """Formats a cell matrix containing colspan or rowspan into semantic HTML.

        Args:
            cell_spans: Mapping of (row_idx, col_idx) to {'text': ..., 'colspan': int, 'rowspan': int}.
            num_rows: Total rows in the table.
            num_cols: Total columns in the table.
            table_class: CSS class for the table (default: 'book-table').
            caption: Optional table caption.

        Returns:
            Semantic HTML <table> string.
        """
        lines = [f'<table class="{table_class}">']
        if caption:
            lines.append(f"  <caption>{caption}</caption>")

        covered: set = set()
        for r in range(num_rows):
            row_cells = []
            for c in range(num_cols):
                if (r, c) in covered:
                    continue
                info = cell_spans.get((r, c), {"text": "", "colspan": 1, "rowspan": 1})
                text = str(info.get("text", "")).strip()
                colspan = info.get("colspan", 1)
                rowspan = info.get("rowspan", 1)

                for dr in range(rowspan):
                    for dc in range(colspan):
                        if dr != 0 or dc != 0:
                            covered.add((r + dr, c + dc))

                tag = "th" if r == 0 else "td"
                attrs = []
                if colspan > 1:
                    attrs.append(f'colspan="{colspan}"')
                if rowspan > 1:
                    attrs.append(f'rowspan="{rowspan}"')
                attr_str = (" " + " ".join(attrs)) if attrs else ""
                row_cells.append(f"<{tag}{attr_str}>{text}</{tag}>")

            if row_cells:
                lines.append(f"  <tr>{''.join(row_cells)}</tr>")

        lines.append("</table>")
        return "\n".join(lines)
