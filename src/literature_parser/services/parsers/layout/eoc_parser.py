"""
End of Chapter (EOC) Section Parser
===================================
Extracts pedagogical end-of-chapter sections:
- Key Terms and Concepts (with multi-column term table and glossary back-links)
- Related Internet Sites (with link formatting)
- Practice Test, Challenge Exercises, Review Questions, Summary (multi-column uncurled)
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class EndOfChapterParser:
    """Specialized extractor for end-of-chapter textbook pedagogical sections."""

    @classmethod
    def extract_end_of_chapter_sections(
        cls,
        page_elem: Any,
        fonts: dict,
        pw: float,
        ph: float,
        page_num: int,
        style: dict = None,
    ) -> Tuple[List[Dict[str, Any]], Set[Any]]:
        """
        Dynamically extracts end-of-chapter sections from any textbook page.
        Sections are identified by heading patterns defined in style['eoc_heading_patterns'].

        Returns: (list_of_section_dicts, set_of_consumed_elements)
        """
        sections = []
        consumed = set()

        text_elements = page_elem.findall('text')
        eoc_patterns = (style or {}).get("eoc_heading_patterns", [
            r"^Key Terms and Concepts\b",
            r"^Related Internet Sites\b",
            r"^Practice Test\b",
            r"^Challenge Exercises\b",
            r"^Summary\b",
            r"^Review Questions\b",
            r"^Discussion Questions\b",
            r"^Critical Thinking\b",
            r"^Further Reading\b",
        ])

        # 1. Find all EOC section headings on this page
        eoc_headings = []
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            top = float(t.attrib.get('top', 0))
            left = float(t.attrib.get('left', 0))
            if not txt or txt.islower() or txt.endswith(('.', ',', ';')):
                continue

            fid = t.attrib.get('font', '')
            finfo = fonts.get(fid, {'size': 10, 'is_bold': False, 'family': ''})
            raw_xml = ET.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
            is_bold = finfo.get('is_bold', False) or '<b>' in raw_xml or 'bold' in finfo.get('family', '').lower()
            is_large = finfo.get('size', 10.0) >= 12.0
            is_all_caps = txt.isupper() and len(txt) >= 4
            if not (is_bold or is_large or is_all_caps):
                continue

            # Ensure heading is not preceded by text on the same baseline
            has_preceding = any(
                o != t and abs(float(o.attrib.get('top', 0)) - top) <= 4.0 and float(o.attrib.get('left', 0)) < left - 10.0
                for o in text_elements
            )
            if has_preceding:
                continue

            for pat in eoc_patterns:
                if re.match(pat, txt, re.IGNORECASE):
                    eoc_headings.append({'elem': t, 'top': top, 'text': txt, 'pattern': pat})
                    break

        if not eoc_headings:
            # Check if this page is an EOC continuation page (e.g. Ch04 p27 where Challenge Exercises continues)
            if page_num >= 5:
                has_chap_header = any(float(fonts.get(t.attrib.get('font', ''), {}).get('size', 12)) >= 25 for t in text_elements if float(t.attrib.get('top', 0)) < ph * 0.3)
                txt_all = " ".join("".join(t.itertext()).strip() for t in text_elements)
                has_exercise_mentions = bool(re.search(r'\b(?:challenge exercise|review question|practice test)\b', txt_all, re.IGNORECASE))
                has_table_or_fig = bool(re.search(r'\b(?:Table|Figure|Fig\.)\s+\d+', txt_all))
                num_items = [t for t in text_elements if re.match(r'^(?:\*\*)?(?:\d+|[a-e])[\.\)]', ''.join(t.itertext()).strip())]
                if not has_chap_header and has_exercise_mentions and not has_table_or_fig and len(num_items) >= 4:
                    eoc_elems = [t for t in text_elements if ph * 0.05 < float(t.attrib.get('top', 0)) < ph * 0.95 and ''.join(t.itertext()).strip()]
                    sec_md = cls._extract_generic_eoc_section(eoc_elems, fonts, pw)
                    if sec_md:
                        consumed.update(eoc_elems)
                        return [{'top': 0.0, 'markdown': sec_md}], consumed
            return [], set()

        eoc_headings.sort(key=lambda h: h['top'])

        # Check if there are EOC continuation items ABOVE the first heading
        first_h_top = eoc_headings[0]['top']
        above_elems = [t for t in text_elements if 50.0 < float(t.attrib.get('top', 0)) < first_h_top and ''.join(t.itertext()).strip()]
        has_above_items = any(re.match(r'^(?:\*\*)?(?:\d+|[a-e])[\.\)]', ''.join(t.itertext()).strip()) for t in above_elems)
        if has_above_items and len(above_elems) >= 5:
            above_md = cls._extract_generic_eoc_section(above_elems, fonts, pw)
            if above_md:
                sections.append({'top': 0.0, 'markdown': above_md})
                consumed.update(above_elems)

        all_sorted = sorted(text_elements, key=lambda t: float(t.attrib.get('top', 0)))

        for h_idx, heading in enumerate(eoc_headings):
            h_top = heading['top']
            h_text = heading['text']
            h_elem = heading['elem']
            next_h_top = eoc_headings[h_idx + 1]['top'] if h_idx + 1 < len(eoc_headings) else ph + 1

            section_elems = []
            for t in all_sorted:
                top = float(t.attrib.get('top', 0))
                if top <= h_top:
                    continue
                if top >= next_h_top:
                    break
                txt = ''.join(t.itertext()).strip()
                if txt:
                    section_elems.append(t)

            consumed.add(h_elem)
            consumed.update(section_elems)

            # Key Terms and Concepts
            if re.match(r'^Key Terms and Concepts\b', h_text, re.IGNORECASE):
                sec_md = cls._extract_key_terms_section(h_elem, section_elems, pw, ph, style=style)
                if sec_md:
                    sections.append({'top': h_top, 'markdown': sec_md})
                continue

            # Related Internet Sites
            if re.match(r'^Related Internet Sites\b', h_text, re.IGNORECASE):
                sec_md = cls._extract_internet_sites_section(section_elems)
                if sec_md:
                    sections.append({'top': h_top, 'markdown': f"### {h_text}\n\n{sec_md}"})
                continue

            # All other EOC sections
            sec_md = cls._extract_generic_eoc_section(section_elems, fonts, pw)
            if sec_md:
                sections.append({'top': h_top, 'markdown': f"### {h_text}\n\n{sec_md}"})

        return sections, consumed

    @classmethod
    def _extract_key_terms_section(cls, heading_elem, section_elems, pw: float, ph: float, style: dict = None) -> str:
        anchor = (style or {}).get("gloss_backlink_anchor", "key-terms-and-concepts")

        if not section_elems:
            return f'<a id="{anchor}"></a>\n### Key Terms and Concepts\n'

        col_centers = []
        for t in section_elems:
            left = float(t.attrib.get('left', 0))
            placed = False
            for col in col_centers:
                if abs(col['cx'] - left) <= 50:
                    col['elems'].append(t)
                    col['cx'] = sum(float(e.attrib.get('left', 0)) for e in col['elems']) / len(col['elems'])
                    placed = True
                    break
            if not placed:
                col_centers.append({'cx': left, 'elems': [t]})

        col_centers.sort(key=lambda c: c['cx'])
        n_cols = len(col_centers)

        if n_cols == 0:
            return f'<a id="{anchor}"></a>\n### Key Terms and Concepts\n'

        cols = []
        for col in col_centers:
            col_items = []
            for t in sorted(col['elems'], key=lambda e: float(e.attrib.get('top', 0))):
                txt = ''.join(t.itertext()).strip()
                if txt:
                    txt = re.sub(r'\s+p\.\s+(\d+)$', r' *p. \1*', txt)
                    col_items.append(txt)
            cols.append(col_items)

        anchor_prefix = "term-"

        def _link_term(t_str: str) -> str:
            if not t_str:
                return ''
            m = re.match(r'^(.*?)\s*\*p\.\s*(\d+)\*$', t_str)
            if m:
                t_name = m.group(1).strip()
                p_num = m.group(2)
                slug = re.sub(r'[^a-zA-Z0-9]+', '-', t_name.lower()).strip('-')
                return f'[{t_name} *p. {p_num}*](#{anchor_prefix}{slug})'
            return t_str

        max_rows = max(len(c) for c in cols) if cols else 0
        col_header = ' | '.join(['Term'] * n_cols)
        col_sep = ' | '.join(['---'] * n_cols)

        rows = []
        for i in range(max_rows):
            cells = []
            for col in cols:
                cell = col[i] if i < len(col) else ''
                cells.append(_link_term(cell))
            rows.append('| ' + ' | '.join(cells) + ' |')

        kt_md = (
            f'<a id="{anchor}"></a>\n'
            f'### Key Terms and Concepts\n\n'
            f'| {col_header} |\n| {col_sep} |\n'
            + '\n'.join(rows)
        )
        return kt_md

    @classmethod
    def _extract_internet_sites_section(cls, section_elems) -> str:
        if not section_elems:
            return ''
        lines_by_top = sorted(section_elems, key=lambda t: float(t.attrib.get('top', 0)))
        entries = []
        curr_url = None
        curr_desc = []
        for t in lines_by_top:
            txt = ''.join(t.itertext()).strip()
            if not txt:
                continue
            is_url = bool(re.match(r'^https?://|^www\.', txt, re.IGNORECASE))
            if is_url:
                if curr_url:
                    desc = ' '.join(curr_desc).strip()
                    entries.append(f"- <{curr_url}>\n  {desc}" if desc else f"- <{curr_url}>")
                curr_url = txt
                curr_desc = []
            else:
                if curr_url:
                    curr_desc.append(txt)
                else:
                    curr_desc.append(txt)

        if curr_url:
            desc = ' '.join(curr_desc).strip()
            entries.append(f"- <{curr_url}>\n  {desc}" if desc else f"- <{curr_url}>")
        elif curr_desc:
            entries.append(' '.join(curr_desc).strip())

        return '\n\n'.join(entries).strip()

    @classmethod
    def _extract_generic_eoc_section(cls, section_elems, fonts: dict, pw: float = 800.0) -> str:
        if not section_elems:
            return ''

        left_elems = [t for t in section_elems if float(t.attrib.get('left', 0)) < pw * 0.45]
        right_elems = [t for t in section_elems if float(t.attrib.get('left', 0)) >= pw * 0.45]

        def process_elems(elems):
            lines_by_top = sorted(elems, key=lambda t: float(t.attrib.get('top', 0)))
            result_lines = []
            for t in lines_by_top:
                fid = t.attrib.get('font', '')
                finfo = fonts.get(fid, {'is_bold': False, 'size': 12, 'family': ''})

                raw_xml = ET.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
                is_bold = finfo.get('is_bold', False) or '<b>' in raw_xml

                m_inner = re.search(r'^<text[^>]*>(.*)</text>$', raw_xml, re.DOTALL)
                inner = m_inner.group(1) if m_inner else ''.join(t.itertext())
                inner = re.sub(r'</?a[^>]*>', '', inner)
                inner = re.sub(r'<b>\s*(.*?)\s*</b>', r'**\1** ', inner)
                inner = re.sub(r'<i>\s*(.*?)\s*</i>', r'*\1*', inner)
                txt = inner.strip()
                if not txt:
                    continue
                if re.search(r'WCN\s*\d+-\d+|all rights reserved|cengage learning|may not be copied|in whole or in part', txt, re.IGNORECASE):
                    continue

                txt = re.sub(r'^(\*\*\d+\.\*\*|\*\*[a-e]\.\*\*)(\S)', r'\1 \2', txt)

                if re.match(r'^\*\*\d+\.\*\*|^\*\*[a-e]\.\*\*', txt):
                    result_lines.append('')
                    result_lines.append(txt)
                elif is_bold and len(txt) < 80 and re.match(r'^\d+\.', txt):
                    clean_num = re.sub(r'^(\d+\.)\s*', r'**\1** ', txt)
                    result_lines.append(f"\n{clean_num}")
                elif re.match(r'^[a-e][\.\)]\s+\S', txt):
                    result_lines.append(f"{txt}")
                else:
                    result_lines.append(txt)

            output = []
            pending = []
            for line in result_lines:
                if line == '':
                    if pending:
                        output.append(' '.join(pending))
                        pending = []
                    if output and output[-1] != '':
                        output.append('')
                elif re.match(r'^[a-e][\.\)]\s+\S', line) or line.startswith('**') or line.startswith('*') or line.startswith('#'):
                    if pending:
                        output.append(' '.join(pending))
                        pending = []
                    output.append(line)
                else:
                    pending.append(line)
            if pending:
                output.append(' '.join(pending))

            cleaned_res = []
            for l in output:
                if l == '' and cleaned_res and cleaned_res[-1] == '':
                    continue
                cleaned_res.append(l)

            return '\n'.join(cleaned_res).strip()

        has_baseline_crossing = any(
            any(abs(float(r.attrib.get('top', 0)) - float(l.attrib.get('top', 0))) <= 3.5 for r in right_elems)
            for l in left_elems
        )

        if len(left_elems) >= 3 and len(right_elems) >= 3 and not has_baseline_crossing:
            col1_md = process_elems(left_elems)
            col2_md = process_elems(right_elems)
            col1_rstrip = col1_md.rstrip()
            col2_lstrip = col2_md.lstrip()
            if col1_rstrip and not re.search(r'[.?!:;>]$', col1_rstrip) and col2_lstrip and col2_lstrip[0].islower():
                return f"{col1_rstrip} {col2_lstrip}".strip()
            return f"{col1_md}\n\n{col2_md}".strip()
        else:
            return process_elems(section_elems)
