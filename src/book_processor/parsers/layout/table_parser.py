"""
Table Parser & Formatter
========================
Extracts structured tables from page XML coordinates or aligns in-paragraph tabular rows,
with fallback support for local Ollama table reconstruction.
"""

import re
import logging
from typing import List, Tuple, Set, Dict, Any, Optional

from book_processor.style_loader import load_style

logger = logging.getLogger(__name__)
_DEFAULT_STYLE = load_style()


class TableParser:
    """Specialized parser for academic and textbook tables."""

    @classmethod
    def detect_and_format_tables(cls, paragraphs: list, style_config: dict = None) -> list:
        """
        Detects blocks of lines with aligned tabular columns (separated by 2+ spaces,
        tabs, or existing pipe symbols) and converts them to Markdown tables.
        """
        style = style_config or {}
        formatted = []
        for p in paragraphs:
            s = p.strip()
            lines = [l.strip() for l in s.splitlines() if l.strip()]
            if not lines:
                formatted.append(p)
                continue

            # Skip existing code blocks, quotes, image links, or existing markdown tables
            if s.startswith(('>', '!', '```', '|')) or re.search(r'\|\s*:?-+:?\s*\|', s) or any(l.startswith('|') for l in lines) or (s.startswith('#') and not re.match(r'^#+\s*Table\b', s, re.I)):
                formatted.append(p)
                continue

            if len(lines) < 3:
                formatted.append(p)
                continue

            # 1. Multi-column aligned table
            row_cols = []
            is_table = True
            for line in lines:
                cols = [c.strip() for c in re.split(r'\s{2,}|\t', line) if c.strip()]
                if len(cols) < 2:
                    is_table = False
                    break
                row_cols.append(cols)

            if is_table and len(row_cols) >= 3:
                col_counts = [len(r) for r in row_cols]
                mode_cols = max(set(col_counts), key=col_counts.count)
                if mode_cols >= 2 and col_counts.count(mode_cols) >= len(col_counts) * 0.7:
                    header = row_cols[0]
                    header = (header + [''] * mode_cols)[:mode_cols]
                    sep = ['---'] * mode_cols
                    md_rows = [
                        '| ' + ' | '.join(header) + ' |',
                        '| ' + ' | '.join(sep) + ' |'
                    ]
                    for r in row_cols[1:]:
                        padded = (r + [''] * mode_cols)[:mode_cols]
                        md_rows.append('| ' + ' | '.join(padded) + ' |')
                    formatted.append('\n'.join(md_rows))
                    continue

            # 2. Check if this is a Table X.X with bullet-point list items
            m_table_title = re.match(r'^(?:###|\*\*)?\s*Table\s+(\d+[\.\d]*)\s*(?:\*\*)?\s*:?\s*(.*)', lines[0], re.I)
            if m_table_title and len(lines) >= 3:
                bullet_rows = []
                for line in lines[1:]:
                    if line.startswith('|'):
                        bullet_rows = []
                        break
                    m_b = re.match(r'^[-*•]\s*(.*)', line)
                    if m_b and m_b.group(1).strip():
                        bullet_rows.append(m_b.group(1).strip())
                if len(bullet_rows) >= 2:
                    t_num = m_table_title.group(1)
                    t_desc = m_table_title.group(2).strip()
                    t_desc = re.sub(r'^\*\*(.+?)\*\*$', r'\1', t_desc)
                    t_desc = re.sub(r'^\*(.+?)\*$', r'\1', t_desc)
                    t_desc = t_desc.strip()
                    if style.get("table_heading_style") == "bold-label":
                        header_line = f"**Table {t_num}** *{t_desc}*".strip() if t_desc else f"**Table {t_num}**"
                    else:
                        header_line = f"### Table {t_num} {t_desc}".strip()
                    md_rows = [header_line, ""]
                    for r in bullet_rows:
                        md_rows.append(f"- {r}")
                    formatted.append('\n'.join(md_rows))
                    continue

            formatted.append(p)
        return formatted

    @classmethod
    def extract_page_tables(cls, page_elem, fonts: dict, pw: float, ph: float, style_config: dict = None) -> tuple:
        style = style_config if style_config is not None else _DEFAULT_STYLE
        """
        Extracts structured tables (e.g. Table 1.1, Table 1.2, Table 2.1) from page XML.
        Supports both multi-column grid tables and bullet/numbered list tables.
        Returns: (list_of_table_dicts, set_of_consumed_elements)
        where each dict is {'top': top, 'markdown': md_text}
        """
        tables = []
        consumed = set()

        text_elements = page_elem.findall('text')
        table_headers = []
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            m = re.match(r'^(?:Table|TABLE)\s+(\d+[\.\d]*)$', txt)
            if m and float(t.attrib.get('height', 0)) >= 18:
                table_headers.append((t, m.group(1)))

        for head_t, t_num in table_headers:
            h_top = float(head_t.attrib.get('top', 0))
            h_left = float(head_t.attrib.get('left', 0))
            table_consumed = [head_t]

            # Find table title (adjacent horizontally or immediately below, before table rows start)
            title_candidates = []
            for t in text_elements:
                if t == head_t:
                    continue
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue
                # Line 1: adjacent horizontally on the same line
                if abs(top - h_top) <= 10 and left > h_left and left - h_left < 350:
                    title_candidates.append((top, left, txt, t))
                # Line 2+: wrapped immediately below (within 28pt) and not a bullet or row
                elif (0 < top - h_top <= 28) and (abs(left - h_left) <= 50 or left > h_left):
                    if not re.match(r'^(?:[•\-\*]|\d+[\.\)])\s*', txt):
                        title_candidates.append((top, left, txt, t))

            title_candidates.sort(key=lambda x: (x[0], x[1]))
            title_parts = []
            for _, _, txt, t in title_candidates:
                title_parts.append(txt)
                table_consumed.append(t)
            title = re.sub(r'[\s\u00a0]+', ' ', ' '.join(title_parts)).strip()

            # Find table rows: elements below table header
            row_candidates = []
            for t in text_elements:
                if t in table_consumed:
                    continue
                top = float(t.attrib.get('top', 0))
                left = float(t.attrib.get('left', 0))
                h = float(t.attrib.get('height', 0))
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue
                if (0 < top - h_top <= 450) and (abs(left - h_left) <= 60 or left >= h_left):
                    fid = t.attrib.get('font', '')
                    fsize = float(fonts.get(fid, {}).get('size', 12))
                    if fsize >= 20 or h >= 25:
                        break
                    row_candidates.append(t)

            if not row_candidates:
                continue

            # Check if this is a multi-column grid table (e.g. Table 2.1)
            top_band = sorted(set(float(t.attrib.get('top', 0)) for t in row_candidates if float(t.attrib.get('top', 0)) - h_top <= 60))
            is_grid = False
            first_top = top_band[0] if top_band else 0.0
            header_cells = []
            if top_band:
                header_cells = [t for t in row_candidates if abs(float(t.attrib.get('top', 0)) - first_top) <= 6]
                header_cells.sort(key=lambda x: float(x.attrib.get('left', 0)))
                if len(header_cells) >= 2:
                    col_bounds = [float(c.attrib.get('left', 0)) for c in header_cells]
                    if all(c2 - c1 >= 60 for c1, c2 in zip(col_bounds, col_bounds[1:])):
                        is_grid = True

            clean_title = title.strip()
            clean_title = re.sub(r'^\*\*(.+?)\*\*$', r'\1', clean_title)
            clean_title = re.sub(r'^\*(.+?)\*$', r'\1', clean_title)
            clean_title = clean_title.strip()
            if style.get("table_heading_style") == "bold-label":
                tbl_header = f"**Table {t_num}** *{clean_title}*" if clean_title else f"**Table {t_num}**"
            else:
                tbl_header = f"### Table {t_num} {clean_title}".strip()

            if is_grid:
                # Multi-column grid table
                def get_col_idx(x):
                    for idx, (b1, b2) in enumerate(zip(col_bounds, col_bounds[1:])):
                        if x < (b1 + b2) / 2:
                            return idx
                    return len(col_bounds) - 1

                raw_grid_data = [t for t in row_candidates if float(t.attrib.get('top', 0)) > first_top + 6]
                raw_grid_data.sort(key=lambda t: float(t.attrib.get('top', 0)))

                # Enforce table boundary: stop at excessive vertical gaps or multi-column paragraph spans
                grid_data = []
                col0_max_x = (col_bounds[1] + 20.0) if len(col_bounds) > 1 else 9999.0
                curr_row_top = first_top
                for d in raw_grid_data:
                    d_top = float(d.attrib.get('top', 0))
                    d_left = float(d.attrib.get('left', 0))
                    d_w = float(d.attrib.get('width', 0))
                    d_txt = ''.join(d.itertext()).strip()
                    # Stop if gap between consecutive table rows exceeds 35pt
                    if d_top - curr_row_top > 35.0:
                        break
                    # Allow footnote lines starting with *
                    if not d_txt.startswith('*'):
                        if d_left < (col_bounds[0] + col_bounds[1]) / 2 and (d_left + d_w > col0_max_x or d_w > 250.0):
                            break
                    grid_data.append(d)
                    curr_row_top = max(curr_row_top, d_top)

                row_starts = sorted(set(float(d.attrib.get('top', 0)) for d in grid_data if get_col_idx(float(d.attrib.get('left', 0))) == 0 and not ''.join(d.itertext()).strip().startswith('*')))
                header_titles = [''.join(c.itertext()).strip() for c in header_cells]

                grid_consumed = list(table_consumed) + header_cells
                fn_texts = []
                parsed_rows = []

                for i, r_top in enumerate(row_starts):
                    next_top = row_starts[i+1] if i + 1 < len(row_starts) else (r_top + 70)
                    row_cells = [[] for _ in range(len(header_titles))]
                    for d in grid_data:
                        d_top = float(d.attrib.get('top', 0))
                        d_left = float(d.attrib.get('left', 0))
                        d_txt = ''.join(d.itertext()).strip()
                        if d_txt.startswith('*'):
                            if d not in grid_consumed:
                                fn_texts.append(d_txt)
                                grid_consumed.append(d)
                            continue
                        if r_top - 3 <= d_top < next_top - 3:
                            c_idx = get_col_idx(d_left)
                            row_cells[c_idx].append(d_txt)
                            grid_consumed.append(d)

                    cell_strs = [' '.join(c).strip() for c in row_cells]
                    parsed_rows.append(cell_strs)

                # Also collect any remaining footnote in grid_data
                for d in grid_data:
                    d_txt = ''.join(d.itertext()).strip()
                    if d_txt.startswith('*') and len(d_txt) > 2 and d not in grid_consumed:
                        fn_texts.append(d_txt)
                        grid_consumed.append(d)

                clean_fn = [f for f in fn_texts if f != '*']
                note_str = ' '.join(clean_fn).lstrip('*').strip() if clean_fn else ""

                table_lines = []
                use_html_table = style.get("table_html_semantic", True)

                if use_html_table:
                    table_lines.append(tbl_header)
                    table_lines.append("")
                    table_lines.append('<table class="textbook-table">')
                    table_lines.append('  <thead>')
                    table_lines.append('    <tr>')
                    for th in header_titles:
                        table_lines.append(f'      <th>{th}</th>')
                    table_lines.append('    </tr>')
                    table_lines.append('  </thead>')
                    table_lines.append('  <tbody>')
                    for r in parsed_rows:
                        if r[0] and not any(r[1:]):
                            colspan = len(header_titles)
                            table_lines.append(f'    <tr class="category-header"><td colspan="{colspan}"><strong>{r[0]}</strong></td></tr>')
                        else:
                            table_lines.append('    <tr>')
                            for c in r:
                                table_lines.append(f'      <td>{c}</td>')
                            table_lines.append('    </tr>')
                    table_lines.append('  </tbody>')
                    if note_str:
                        colspan = len(header_titles)
                        table_lines.append('  <tfoot>')
                        table_lines.append(f'    <tr class="table-notes"><td colspan="{colspan}"><em>* {note_str}</em></td></tr>')
                        table_lines.append('  </tfoot>')
                    table_lines.append('</table>')
                else:
                    # GFM pipe table fallback
                    table_lines.append(tbl_header)
                    table_lines.append("")
                    table_lines.append('| ' + ' | '.join(header_titles) + ' |')
                    table_lines.append('| ' + ' | '.join(['---'] * len(header_titles)) + ' |')
                    for r in parsed_rows:
                        if r[0] and not any(r[1:]):
                            colspan = len(header_titles)
                            table_lines.append(f'<tr style="background-color: #f6f8fa; font-weight: bold;"><td colspan="{colspan}">{r[0]}</td></tr>')
                        else:
                            table_lines.append('| ' + ' | '.join(r) + ' |')
                    if note_str:
                        table_lines.append("")
                        table_lines.append(f"> *Note: {note_str}*")

                consumed.update(grid_consumed)
                tables.append({
                    'top': h_top,
                    'markdown': '\n'.join(table_lines)
                })
                continue

            # Check if this is a Criterion-based table (e.g. Table 2.2: Criterion 1, Criterion 2, Criterion 3)
            crit_elems = [t for t in row_candidates if re.match(r'^Criterion\s+\d+:', ''.join(t.itertext()).strip(), re.I)]
            if len(crit_elems) >= 2:
                crit_rows = []
                grid_consumed = list(table_consumed)
                for i, c_el in enumerate(crit_elems):
                    c_top = float(c_el.attrib.get('top', 0))
                    c_txt = ''.join(c_el.itertext()).strip()
                    grid_consumed.append(c_el)
                    next_c_top = float(crit_elems[i+1].attrib.get('top', 0)) if i + 1 < len(crit_elems) else 9999.0
                    desc_parts = []
                    for t in row_candidates:
                        t_top = float(t.attrib.get('top', 0))
                        t_txt = ''.join(t.itertext()).strip()
                        if t != c_el and c_top - 3 <= t_top < next_c_top - 3:
                            desc_parts.append(t_txt)
                            grid_consumed.append(t)
                    desc_str = ' '.join(desc_parts).strip()
                    desc_str = re.sub(r'\s+', ' ', desc_str)
                    crit_rows.append((c_txt, desc_str))

                table_lines = [
                    tbl_header, "",
                    '| Criterion | Description |',
                    '| --- | --- |'
                ]
                for c_txt, desc_str in crit_rows:
                    table_lines.append(f'| **{c_txt}** | {desc_str} |')

                consumed.update(grid_consumed)
                tables.append({
                    'top': h_top,
                    'markdown': '\n'.join(table_lines)
                })
                continue

            row_candidates.sort(key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0))))
            items = []
            curr_item = []
            for t in row_candidates:
                txt = ''.join(t.itertext()).strip()
                is_num = bool(re.match(r'^\d+[\.\)]\s*', txt))
                is_bullet = bool(re.match(r'^[•\-\*]\s*', txt))
                if is_num or is_bullet:
                    if curr_item:
                        items.append(' '.join(curr_item))
                    curr_item = [txt]
                    table_consumed.append(t)
                elif curr_item:
                    curr_item.append(txt)
                    table_consumed.append(t)
                elif not items and ('evaluate' in txt.lower() or 'answer' in txt.lower() or 'question' in txt.lower()):
                    table_consumed.append(t)

            if curr_item:
                items.append(' '.join(curr_item))

            if len(items) >= 2:
                consumed.update(table_consumed)
                has_numbers = all(re.match(r'^\d+[\.\)]\s*', it) for it in items)
                # Build table heading per STYLE — strip pre-existing bold/italic first
                clean_title = title.strip()
                clean_title = re.sub(r'^\*\*(.+?)\*\*$', r'\1', clean_title)
                clean_title = re.sub(r'^\*(.+?)\*$', r'\1', clean_title)
                clean_title = clean_title.strip()
                if style.get("table_heading_style") == "bold-label":
                    if clean_title:
                        tbl_header = f"**Table {t_num}** *{clean_title}*"
                    else:
                        tbl_header = f"**Table {t_num}**"
                else:
                    tbl_header = f"### Table {t_num} {clean_title}".strip()
                md_table = [tbl_header, ""]

                if has_numbers:
                    for it in items:
                        m_num = re.match(r'^(\d+)[\.\)]\s*(.*)', it)
                        if m_num:
                            n_str = m_num.group(1)
                            desc = m_num.group(2).strip()
                            desc = re.sub(r'\s+', ' ', desc)
                            md_table.append(f"{n_str}. {desc}")
                        else:
                            clean_it = re.sub(r'\s+', ' ', clean_it)
                            md_table.append(f"1. {clean_it}")
                else:
                    for it in items:
                        clean_it = re.sub(r'^[•\-\*]\s*', '', it).strip()
                        clean_it = re.sub(r'\s+', ' ', clean_it)
                        md_table.append(f"- {clean_it}")

                tables.append({
                    'top': h_top,
                    'markdown': '\n'.join(md_table)
                })


        return tables, consumed

