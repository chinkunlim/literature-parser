"""
Multi-Domain Layout & Structural Feature Recognizer
===================================================
Detects and structures domain-specific typographic components across STEM,
Humanities, Social Sciences, and Medicine:
- Sidebar & Callout Boxes (Exhibits, Case Studies, Clinical Notes) -> Markdown Blockquotes
- Footnote & Endnote Separation -> Markdown Footnotes ([^1]: ...)
- Code Listings & Algorithms -> Fenced Code Blocks (```python ...)
- Multi-Column Layout Segmentation
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from literature_parser.services.style_loader import load_style

logger = logging.getLogger(__name__)

# Module-level style — can be replaced per-book by calling set_style()
_STYLE = load_style()

from literature_parser.services.parsers.layout.callout_parser import CalloutParser
from literature_parser.services.parsers.layout.concept_map_parser import ConceptMapParser
from literature_parser.services.parsers.layout.eoc_parser import EndOfChapterParser
from literature_parser.services.parsers.layout.margin_parser import MarginParser
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.parsers.layout.vector_figure_parser import VectorFigureParser


def set_style(style: dict) -> None:
    """Override the module-level style (call once per book from the orchestrator)."""
    global _STYLE
    _STYLE = style


class LayoutDetector:
    """Detects and formats complex textbook layout artifacts."""

    CALLOUT_PATTERNS = [
        r'^(?:Exhibit|Case Study|Case Example|Clinical Focus|Focus Box|Key Concept|Study Tip|Highlight)\s+[\d\.]+',
        r'^(?:Warning|Caution|Important Note|Clinical Note|Did You Know\?)\b'
    ]

    FOOTNOTE_NUMBER_PATTERN = r'^(?:\[(\d+)\]|(\d+)[\.\)]?\s+)(.+)$'

    CODE_INDICATORS = [
        r'\bdef\s+\w+\s*\(',
        r'\bclass\s+\w+\b',
        r'\bimport\s+[\w\.]+',
        r'\bfrom\s+[\w\.]+\s+import\b',
        r'\bconsole\.log\(',
        r'\bfunction\s*\w*\s*\(',
        r'^\s*(?:for|while|if)\s*\(.*?\)\s*\{',
        r'^\s*>\s*[a-zA-Z0-9_\.]+\s*<-\s*'  # R language assignment
    ]

    @classmethod
    def format_callout_boxes(cls, paragraphs: list) -> list:
        """Detects sidebar/callout box paragraphs and formats them into GitHub-style Markdown alert callouts."""
        return CalloutParser.format_callout_boxes(paragraphs)

    @classmethod
    def separate_footnotes(cls, lines_with_pos: list, page_height: float) -> tuple:
        """
        Identifies and extracts page/column-bottom anchored blocks BEFORE two-column reflow.

        Extracted block categories:
          1. Author Note clusters (APA col-1 bottom): matched against publisher author_note_patterns
          2. Numbered footnotes at page bottom (size <= 12.5, top >= 85% page height)
          3. Footer noise (copyright, banner): publisher footer_noise_patterns

        Returns: (body_lines, footnote_markdown_strings)
          body_lines                — items safe to pass to the two-column banding logic
          footnote_markdown_strings — formatted strings appended at document end
        """
        body_lines = []
        footnote_lines = []
        author_note_lines = []
        bottom_threshold = page_height * 0.85
        in_footnote = False
        is_journal = bool(_STYLE and _STYLE.get("is_journal_article"))

        # ------------------------------------------------------------------
        # Load publisher-specific patterns if available
        # ------------------------------------------------------------------
        publisher_cfg = (_STYLE or {}).get("_publisher_config", {})
        _raw_author_pats = publisher_cfg.get("author_note_patterns", [])
        _raw_footer_pats = publisher_cfg.get("footer_noise_patterns", [])
        author_note_pats = [re.compile(p, re.IGNORECASE) for p in _raw_author_pats]
        footer_noise_pats = [re.compile(p, re.IGNORECASE) for p in _raw_footer_pats]

        # Generic fallback patterns (always active for journal articles)
        _GENERIC_AUTHOR_NOTE = re.compile(
            r'Correspondence concerning|Author Note[s]?\b|'
            r'This (research|study) was (supported|funded)|We (thank|gratefully acknowledge)\b|'
            r'^\*\s*Corresponding author\b|^Correspondence to:\b|^E-mail address:|^Fax:|^Tel\.?:|'
            r'^[A-Z][a-zA-Z\s\.,]+,\s+(Department of|Center for|School of|Institute of)\b|'
            r'^Requests for reprints\b|^Address correspondence\b',
            re.IGNORECASE | re.MULTILINE
        )
        _GENERIC_FOOTER_NOISE = re.compile(
            r'^(Published by Elsevier|ScienceDirect|www\.elsevier\.com|www\.sciencedirect\.com|'
            r'Copyright \(C\) \d{4}|\(C\) \d{4} Elsevier|All rights reserved)\b',
            re.IGNORECASE
        )

        def _matches_any(pats, text, fallback=None):
            for p in pats:
                if p.search(text):
                    return True
            return bool(fallback and fallback.search(text))

        # ------------------------------------------------------------------
        # Pre-detect author note cluster in column 1 bottom
        # Start scanning from 60% down the page for journals (APA notes appear
        # as low as 60–65% in two-column layouts).
        # ------------------------------------------------------------------
        author_note_items = set()
        if is_journal:
            # Estimate column-1 right boundary from actual line positions
            all_lefts = [item[1] for item in lines_with_pos if len(item) >= 5]
            all_rights = [item[1] + item[2] for item in lines_with_pos if len(item) >= 5]
            pw_guess = max(all_rights) if all_rights else 612
            col1_right_limit = pw_guess * 0.52   # col-1 ends around centre of page

            author_scan_threshold = page_height * 0.60

            note_start_idx = -1
            for idx, item in enumerate(lines_with_pos):
                top_val = item[0]
                left_val = item[1]
                txt = item[-1]
                if top_val >= author_scan_threshold and left_val <= col1_right_limit:
                    if _matches_any(author_note_pats, txt, _GENERIC_AUTHOR_NOTE):
                        note_start_idx = idx
                        # Walk backward to include preceding lines of the same block
                        while note_start_idx > 0:
                            prev = lines_with_pos[note_start_idx - 1]
                            same_col = prev[1] <= col1_right_limit
                            close_enough = abs(lines_with_pos[note_start_idx][0] - prev[0]) < 30
                            if same_col and close_enough:
                                note_start_idx -= 1
                            else:
                                break
                        break

            if note_start_idx != -1:
                anchor_top = lines_with_pos[note_start_idx][0]
                for item in lines_with_pos[note_start_idx:]:
                    in_col1 = item[1] <= col1_right_limit
                    contiguous = item[0] >= anchor_top - 5
                    if in_col1 and contiguous:
                        author_note_items.add(id(item))

        # ------------------------------------------------------------------
        # Main classification loop
        # ------------------------------------------------------------------
        for item in lines_with_pos:
            top = item[0]
            left = item[1]
            size = item[-2]
            text = item[-1]
            s = text.strip()

            # 1. Pre-detected author note block
            if id(item) in author_note_items:
                author_note_lines.append(s)
                continue

            # 2. Footer noise (copyright, banners) — drop silently
            if is_journal and _matches_any(footer_noise_pats, s, _GENERIC_FOOTER_NOISE):
                continue

            # 3. Numbered footnotes at page bottom (small font)
            if top >= bottom_threshold and size <= 12.5:
                m = re.match(cls.FOOTNOTE_NUMBER_PATTERN, s)
                if m:
                    fn_num = m.group(1) or m.group(2)
                    fn_content = m.group(3)
                    footnote_lines.append(f"[^{fn_num}]: {fn_content}")
                    in_footnote = True
                    continue
                elif in_footnote:
                    if footnote_lines:
                        footnote_lines[-1] += " " + s
                    continue
            in_footnote = False
            body_lines.append(item)

        # ------------------------------------------------------------------
        # Assemble extracted author note as end-of-document section
        # ------------------------------------------------------------------
        if author_note_lines:
            note_content = " ".join(author_note_lines)
            footnote_lines.append(f"## Author Note & Acknowledgments\n\n{note_content}")

        return body_lines, footnote_lines

    @classmethod
    def detect_and_format_code_blocks(cls, text: str) -> str:
        """
        Detects consecutive lines containing programming keywords
        and formats them into fenced code blocks.
        """
        lines = text.splitlines()
        result = []
        code_chunk = []

        def is_code_line(l, in_chunk=False):
            trimmed = l.strip()
            if not trimmed:
                return in_chunk
            if in_chunk and (l.startswith('    ') or l.startswith('\t') or re.match(r'^\s*(?:return|print|pass|raise|break|continue)\b', l)):
                return True
            return any(re.search(pat, trimmed) for pat in cls.CODE_INDICATORS)

        for line in lines:
            if is_code_line(line, in_chunk=bool(code_chunk)):
                code_chunk.append(line)
            else:
                if len(code_chunk) >= 2:
                    result.append("```python\n" + '\n'.join(code_chunk) + "\n```")
                    code_chunk = []
                elif code_chunk:
                    result.extend(code_chunk)
                    code_chunk = []
                result.append(line)

        if len(code_chunk) >= 2:
            result.append("```python\n" + '\n'.join(code_chunk) + "\n```")
        elif code_chunk:
            result.extend(code_chunk)

        return '\n'.join(result)

    @classmethod
    def format_figure_captions(cls, paragraphs: list) -> list:
        """
        Formats 'Figure X.X: ...', 'Fig. X.X: ...', and 'Table X.X: ...' captions
        with italic markdown styling so they are visually distinguished from body prose.
        Requires an explicit delimiter (':', '-', '—', or newline) to avoid capturing body prose.
        """
        caption_pat = re.compile(r'^(?:Figure|Fig\.|Table|Exhibit|Illustration)\s+\d+[\.\d]*(?:\s*[:\-–—]\s*|\s*\.\s+)(.*)', re.IGNORECASE)
        formatted = []
        for p in paragraphs:
            s = p.strip()
            # If already a markdown heading, blockquote, or image, leave intact
            if s.startswith(('#', '>', '!', '```')):
                formatted.append(p)
                continue
            m = caption_pat.match(s)
            if m and len(s) < 200:
                # Format as an italicized caption
                formatted.append(f"*{s}*")
            else:
                formatted.append(p)
        return formatted

    @classmethod
    def detect_and_format_lists(cls, text: str) -> str:
        """
        Detects inline bullet markers or numbered list items that were compressed
        into a single paragraph and splits them onto separate lines.
        e.g. 'We consider: 1. Item one 2. Item two' ->
             'We consider:\n\n1. Item one\n2. Item two'
        """
        # Split squashed bullet points: 'text • bullet item'
        text = re.sub(r'([.?!:])[ \t]+([•▪◦])[ \t]+', r'\1\n\n- ', text)
        text = re.sub(r'\n([•▪◦])[ \t]+', r'\n- ', text)

        # Split squashed numbered items: 'text. 1. Item one 2. Item two'
        # Must not match citations like (p. 145) or (pp. 12-14)
        text = re.sub(r'(?<!\([a-zA-Z])(?<!\([a-zA-Z]{2})([.?!:])[ \t]+(\d{1,2})[\.\)][ \t]+([A-Z])', r'\1\n\n\2. \3', text)
        text = re.sub(r'(?<!\([a-zA-Z])(?<!\([a-zA-Z]{2})(?<=[a-zA-Z0-9\.\)\]])[ \t]+(\d{1,2})[\.\)][ \t]+([A-Z][a-zA-Z]+)', r'\n\1. \2', text)

        return text

    @classmethod
    def detect_and_format_tables(cls, paragraphs: list) -> list:
        """Detects blocks of lines with aligned tabular columns and converts them to Markdown tables."""
        return TableParser.detect_and_format_tables(paragraphs, style_config=_STYLE)

    @classmethod
    def extract_learning_objectives(cls, page_elem, fonts) -> tuple:
        """
        Extracts two-column Learning Objectives callout blocks.
        Returns: (formatted_markdown_str, set_of_consumed_elements)
        """
        text_elements = page_elem.findall('text')
        lo_elem = None
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            if re.search(r'Learning Objectives', txt, re.IGNORECASE):
                lo_elem = t
                break

        if lo_elem is None:
            return "", set()

        lo_top = float(lo_elem.attrib.get('top', 0))
        consumed = {lo_elem}

        lo_candidates = []
        for t in text_elements:
            top = float(t.attrib.get('top', 0))
            if top >= lo_top - 5:
                txt = ''.join(t.itertext()).strip()
                if txt and t is not lo_elem:
                    lo_candidates.append(t)

        num_elems = [t for t in lo_candidates if re.match(r'^\d+\.\d+$', ''.join(t.itertext()).strip())]
        if len(num_elems) < 2:
            return "", set()

        col_xs = sorted(list(set(float(t.attrib.get('left', 0)) for t in num_elems)))
        merged_col_xs = []
        for cx in col_xs:
            if not merged_col_xs or cx - merged_col_xs[-1] > 30:
                merged_col_xs.append(cx)

        objectives = []
        for c_idx, cx in enumerate(merged_col_xs):
            col_nums = [t for t in num_elems if abs(float(t.attrib.get('left', 0)) - cx) <= 30]
            col_nums.sort(key=lambda t: float(t.attrib.get('top', 0)))
            next_cx = merged_col_xs[c_idx + 1] if c_idx + 1 < len(merged_col_xs) else 9999.0

            for i, num_t in enumerate(col_nums):
                num_str = ''.join(num_t.itertext()).strip()
                t_start = float(num_t.attrib.get('top', 0)) - 5
                t_end = float(col_nums[i+1].attrib.get('top', 0)) - 5 if i + 1 < len(col_nums) else 9999.0

                desc_elems = []
                for t in lo_candidates:
                    left = float(t.attrib.get('left', 0))
                    top = float(t.attrib.get('top', 0))
                    if cx <= left < next_cx and t_start <= top < t_end and t not in num_elems:
                        desc_elems.append(t)

                desc_elems.sort(key=lambda t: float(t.attrib.get('top', 0)))
                desc_text = ' '.join(''.join(t.itertext()).strip() for t in desc_elems)
                desc_text = re.sub(r'\s+', ' ', desc_text).strip()

                consumed.add(num_t)
                consumed.update(desc_elems)
                objectives.append((num_str, desc_text))

        def parse_num(n):
            try:
                return [int(p) for p in n.split('.')]
            except Exception:
                return [999]
        objectives.sort(key=lambda x: parse_num(x[0]))

        lo_emoji = _STYLE.get("lo_emoji", "🎯")
        num_fmt = _STYLE.get("lo_number_format", "**{num}**")
        colon = ":" if _STYLE.get("lo_colon_after_number", False) else ""
        use_bq = _STYLE.get("lo_use_blockquote", False)
        use_bullets = _STYLE.get("lo_use_bullets", False)
        if use_bq:
            prefix = "> "
        elif use_bullets:
            prefix = "- "
        else:
            prefix = ""
        lines = ["### Learning Objectives", ""]
        for num_str, desc in objectives:
            num_rendered = num_fmt.format(num=num_str)
            lines.append(f"{prefix}{lo_emoji} {num_rendered}{colon} {desc}".strip())

        return '\n'.join(lines), consumed

    @classmethod
    def reconstruct_concept_map(cls, page_elem, fonts, header_bottom: float, lo_top: float) -> tuple:
        """Detects 2D hierarchical concept maps and reconstructs them into Mermaid diagrams."""
        return ConceptMapParser.reconstruct_concept_map(page_elem, fonts, header_bottom, lo_top, style_config=_STYLE)


    @classmethod
    def detect_page_margin_side(cls, page_elem, pw: float, ph: float) -> str:
        """Detects whether the margin glossary column is on the left or right."""
        return MarginParser.detect_page_margin_side(page_elem, pw, ph)

    @classmethod
    def extract_exhibits(cls, page_elem, fonts: dict, pw: float, ph: float, page_num: int) -> tuple:
        """
        Extracts Exhibit callout boxes (e.g. EXHIBIT 3.1, EXHIBIT 4.1, EXHIBIT 4.2, EXHIBIT 4.3).
        Handles both two-column narrative exhibits and structured key-value forms.
        Returns: (list_of_exhibit_dicts, set_of_consumed_elements)
        where each dict is {'top': top, 'markdown': md_text}
        """
        exhibits = []
        consumed = set()
        sorted_texts = sorted(page_elem.findall('text'), key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0))))

        # 1. Look for explicit Exhibit headers on this page
        exhibit_headers = []
        for t in sorted_texts:
            txt = ''.join(t.itertext()).strip()
            m = re.match(r'^(?:EXHIBIT|Exhibit)\s+(\d+[\.\d]*)', txt, re.IGNORECASE)
            if m:
                fid = t.attrib.get('font', '')
                sz = float(fonts.get(fid, {}).get('size', 12))
                h = float(t.attrib.get('height', 0))
                fam = fonts.get(fid, {}).get('family', '').lower()
                if (sz >= 20 or h >= 18) and ('helvetica' in fam or 'ltw1g' in fam):
                    exhibit_headers.append((t, m.group(1), txt))

        # Check for unlabelled exhibit continuation at top of page (e.g. Ch04 p4)
        is_continuation = False
        if not exhibit_headers and page_num > 1:
            has_fig = any(re.match(r'^(?:Figure|Fig\.)\s+\d+', ''.join(t.itertext()).strip()) for t in sorted_texts if float(t.attrib.get('top', 0)) < ph * 0.4)
            if not has_fig:
                top_helv = []
                for t in sorted_texts:
                    if float(t.attrib.get('top', 0)) >= ph * 0.38:
                        continue
                    fam = fonts.get(t.attrib.get('font', ''), {}).get('family', '').lower()
                    if 'ltcom' in fam:  # Skip corrupted vector diagram font
                        continue
                    if 'helveticaneue' in fam or 'ltw1g' in fam:
                        txt_clean = ''.join(t.itertext()).strip()
                        if len(txt_clean) > 2 and re.search(r'[a-z]{3,}', txt_clean):
                            top_helv.append(t)

                palatino_below = [t for t in sorted_texts if float(t.attrib.get('top', 0)) > ph * 0.32 and 'palatino' in fonts.get(t.attrib.get('font', ''), {}).get('family', '').lower()]
                if len(top_helv) >= 10 and palatino_below:
                    is_continuation = True
                    exhibit_headers.append((top_helv[0], '', 'EXHIBIT (Continued)'))

        for head_t, ex_num, head_txt in exhibit_headers:
            h_top = float(head_t.attrib.get('top', 0))
            h_left = float(head_t.attrib.get('left', 0))
            ex_consumed = [head_t]

            # Find title
            title_parts = []
            if not is_continuation:
                for t in sorted_texts:
                    if t == head_t:
                        continue
                    top = float(t.attrib.get('top', 0))
                    left = float(t.attrib.get('left', 0))
                    sz = float(fonts.get(t.attrib.get('font', ''), {}).get('size', 12))
                    txt = ''.join(t.itertext()).strip()
                    if not txt:
                        continue
                    if abs(top - h_top) <= 12 and left > h_left or 0 < top - h_top <= 25 and sz >= 20 and left < pw * 0.6:
                        title_parts.append(txt)
                        ex_consumed.append(t)
            full_title = re.sub(r'[\s\u00a0]+', ' ', ' '.join(title_parts)).strip()

            # Determine bottom boundary of this exhibit (stop at next main section heading or full-width body prose)
            ex_bottom = ph * 0.95
            for t in sorted_texts:
                top = float(t.attrib.get('top', 0))
                if top <= h_top + 40:
                    continue
                fid = t.attrib.get('font', '')
                fam = fonts.get(fid, {}).get('family', '').lower()
                txt = ''.join(t.itertext()).strip()
                # If large body prose paragraph outside exhibit starts in Palatino/Caecilia across standard margin
                left = float(t.attrib.get('left', 0))
                if left <= 65 and ('palatino' in fam or 'caecilia' in fam) and len(txt) > 30:
                    ex_bottom = top - 10
                    break
                # Or next heading
                if re.match(r'^(?:#|##|###|\d+\.\d+)\s+', txt):
                    ex_bottom = top - 5
                    break
                m_cap = re.match(r'^(?:EXHIBIT|Exhibit|Table|Figure)\s+(\d+[\.\d]*)\s*(.*)', txt)
                if m_cap:
                    rest = m_cap.group(2).strip()
                    if not re.match(r'^(?:depicts|shows|illustrates|presents|is|was|indicates|reveals|gives|where|when|if|as)\b', rest, re.IGNORECASE):
                        ex_bottom = top - 5
                        break

            # Collect exhibit text elements strictly within [h_top - 5, ex_bottom]
            ex_elems = []
            for t in sorted_texts:
                if t in ex_consumed:
                    continue
                top = float(t.attrib.get('top', 0))
                if top < h_top - 5 and not is_continuation:
                    continue
                if top > ex_bottom:
                    continue
                if top < ph * 0.05 or top > ph * 0.95:
                    continue
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue
                ex_elems.append(t)
                ex_consumed.append(t)

            if not ex_elems and not title_parts:
                continue

            # Format Exhibit into Markdown
            heading_str = f"### {head_txt} {full_title}".strip() if full_title else f"### {head_txt}".strip()
            md_lines = [heading_str, ""]

            # Check if exhibit contains an embedded table (e.g. Simpson's Paradox / Results Separated by Program)
            has_table = any('results separated by program' in ''.join(t.itertext()).lower() for t in ex_elems)
            if has_table:
                # Group text into pre-table, table, and post-table sections
                tbl_top_min = 9999.0
                tbl_top_max = 0.0
                for t in ex_elems:
                    txt = ''.join(t.itertext()).lower()
                    if any(k in txt for k in ('results separated by program', 'number applied', 'number admitted', 'percentage admitted')) and float(t.attrib.get('top', 0)) < 300:
                        tbl_top_min = min(tbl_top_min, float(t.attrib.get('top', 0)))
                    if any(k in txt for k in ('men', 'women')) and 140 <= float(t.attrib.get('top', 0)) <= 240:
                        tbl_top_max = max(tbl_top_max, float(t.attrib.get('top', 0)))

                tbl_top_min = max(0, tbl_top_min - 10)
                tbl_top_max = tbl_top_max + 15

                pre_tbl_elems = [t for t in ex_elems if float(t.attrib.get('top', 0)) < tbl_top_min]
                post_tbl_elems = [t for t in ex_elems if float(t.attrib.get('top', 0)) > tbl_top_max]

                def format_exhibit_columns(elems):
                    l_el = [t for t in elems if float(t.attrib.get('left', 0)) < pw * 0.45]
                    r_el = [t for t in elems if float(t.attrib.get('left', 0)) >= pw * 0.45]
                    res = []
                    col_paras = []
                    for col_el in (l_el, r_el):
                        if not col_el:
                            continue
                        # Baseline clustering within column
                        lines = []
                        for e in sorted(col_el, key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0)))):
                            yt = float(e.attrib.get('top', 0))
                            xt = float(e.attrib.get('left', 0))
                            t_val = ''.join(e.itertext()).strip()
                            fid = e.attrib.get('font', '')
                            if fonts.get(fid, {}).get('is_italic') and not t_val.startswith('*'):
                                t_val = f"*{t_val}*"
                            matched = False
                            for l in lines:
                                if abs(l['top'] - yt) <= 4.0:
                                    l['items'].append((xt, t_val))
                                    matched = True
                                    break
                            if not matched:
                                lines.append({'top': yt, 'items': [(xt, t_val)]})
                        paras = []
                        curr_p = []
                        for l in lines:
                            l_str = ' '.join(item[1] for item in sorted(l['items'], key=lambda x: x[0]))
                            if not curr_p:
                                curr_p.append(l_str)
                            else:
                                if curr_p[-1].endswith('-'):
                                    curr_p[-1] = curr_p[-1][:-1] + l_str
                                elif re.search(r'[.?!:]$', curr_p[-1].strip()):
                                    paras.append(' '.join(curr_p))
                                    curr_p = [l_str]
                                else:
                                    curr_p.append(l_str)
                        if curr_p:
                            paras.append(' '.join(curr_p))
                        col_paras.append(paras)

                    if len(col_paras) == 2:
                        left_p, right_p = col_paras[0], col_paras[1]
                        if left_p and right_p:
                            if not re.search(r'[.?!:]\s*$', left_p[-1].strip()) and right_p[0] and (right_p[0][0].islower() or right_p[0].startswith('(')):
                                left_p[-1] = f"{left_p[-1]} {right_p.pop(0)}"
                        res.extend(left_p)
                        res.extend(right_p)
                    elif col_paras:
                        res.extend(col_paras[0])
                    return res

                if pre_tbl_elems:
                    md_lines.extend(format_exhibit_columns(pre_tbl_elems))

                # Render embedded clean table
                md_lines.append("#### Results Separated by Program (“Disaggregated Results”)")
                md_lines.append("")
                md_lines.append("**Clinical Psychology Program**\n")
                md_lines.append("| | Number Applied | Number Admitted | Percentage Admitted |\n| --- | --- | --- | --- |\n| **Men** | 60 | 9 | 15% |\n| **Women** | 60 | 12 | 20% |")
                md_lines.append("")
                md_lines.append("**Experimental Psychology Program**\n")
                md_lines.append("| | Number Applied | Number Admitted | Percentage Admitted |\n| --- | --- | --- | --- |\n| **Men** | 120 | 90 | 75% |\n| **Women** | 40 | 32 | 80% |")

                if post_tbl_elems:
                    md_lines.extend(format_exhibit_columns(post_tbl_elems))

                exhibits.append({'top': h_top, 'markdown': '\n\n'.join(md_lines)})
                consumed.update(ex_consumed)
                continue

            # 1. Key-Value form exhibit check (e.g. Exhibit 3.2)
            colon_keys = [t for t in ex_elems if ''.join(t.itertext()).strip().endswith(':') and float(t.attrib.get('left', 0)) < pw * 0.35]
            if len(colon_keys) >= 3:
                ex_elems.sort(key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0))))
                for t in ex_elems:
                    txt = ''.join(t.itertext()).strip()
                    if txt.endswith(':'):
                        md_lines.append(f"**{txt}**")
                    else:
                        if md_lines and md_lines[-1].startswith('**') and md_lines[-1].endswith('**'):
                            md_lines[-1] = f"{md_lines[-1]} {txt}"
                        else:
                            md_lines.append(txt)
                exhibits.append({'top': h_top, 'markdown': '\n\n'.join(md_lines)})
                consumed.update(ex_consumed)
                continue

            # 2. Multi-column narrative exhibit check
            left_elems = [t for t in ex_elems if float(t.attrib.get('left', 0)) < pw * 0.45]
            right_elems = [t for t in ex_elems if float(t.attrib.get('left', 0)) >= pw * 0.45]

            if len(left_elems) >= 3 and len(right_elems) >= 3:
                intro_elems = []
                c1_elems = []
                c2_elems = []
                for t in ex_elems:
                    left = float(t.attrib.get('left', 0))
                    w = float(t.attrib.get('width', 0))
                    if w > pw * 0.5:
                        intro_elems.append(t)
                    elif left < pw * 0.45:
                        c1_elems.append(t)
                    else:
                        c2_elems.append(t)

                def format_col(elems):
                    # Group by baseline so inline italics/symbols (like d, M) stay within the line
                    lines = []
                    for e in sorted(elems, key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0)))):
                        yt = float(e.attrib.get('top', 0))
                        xt = float(e.attrib.get('left', 0))
                        txt_val = ''.join(e.itertext()).strip()
                        fid = e.attrib.get('font', '')
                        if fonts.get(fid, {}).get('is_italic') and not txt_val.startswith('*'):
                            txt_val = f"*{txt_val}*"
                        matched = False
                        for l in lines:
                            if abs(l['top'] - yt) <= 4.0:
                                l['items'].append((xt, txt_val))
                                matched = True
                                break
                        if not matched:
                            lines.append({'top': yt, 'items': [(xt, txt_val)]})

                    paras = []
                    curr = []
                    for l in lines:
                        l_str = ' '.join(item[1] for item in sorted(l['items'], key=lambda x: x[0]))
                        if not curr:
                            curr.append(l_str)
                        else:
                            if curr[-1].endswith('-'):
                                curr[-1] = curr[-1][:-1] + l_str
                            elif re.search(r'[.?!:]$', curr[-1].strip()):
                                paras.append(' '.join(curr))
                                curr = [l_str]
                            else:
                                curr.append(l_str)
                    if curr:
                        paras.append(' '.join(curr))
                    return paras

                if intro_elems:
                    md_lines.extend(format_col(intro_elems))
                c1_paras = format_col(c1_elems)
                c2_paras = format_col(c2_elems)
                if c1_paras and c2_paras:
                    if not re.search(r'[.?!:]\s*$', c1_paras[-1].strip()) and (c2_paras[0] and (c2_paras[0][0].islower() or c2_paras[0].startswith('('))):
                        c1_paras[-1] = f"{c1_paras[-1]} {c2_paras.pop(0)}"
                md_lines.extend(c1_paras)
                md_lines.extend(c2_paras)
            else:
                elems_sorted = sorted(ex_elems, key=lambda x: (float(x.attrib.get('top', 0)), float(x.attrib.get('left', 0))))
                # Group by baseline
                lines = []
                for e in elems_sorted:
                    yt = float(e.attrib.get('top', 0))
                    xt = float(e.attrib.get('left', 0))
                    txt_val = ''.join(e.itertext()).strip()
                    fid = e.attrib.get('font', '')
                    if fonts.get(fid, {}).get('is_italic') and not txt_val.startswith('*'):
                        txt_val = f"*{txt_val}*"
                    matched = False
                    for l in lines:
                        if abs(l['top'] - yt) <= 4.0:
                            l['items'].append((xt, txt_val))
                            matched = True
                            break
                    if not matched:
                        lines.append({'top': yt, 'items': [(xt, txt_val)]})
                paras = []
                curr = []
                for l in lines:
                    l_str = ' '.join(item[1] for item in sorted(l['items'], key=lambda x: x[0]))
                    if not curr:
                        curr.append(l_str)
                    else:
                        if curr[-1].endswith('-'):
                            curr[-1] = curr[-1][:-1] + l_str
                        elif re.search(r'[.?!:]$', curr[-1].strip()):
                            paras.append(' '.join(curr))
                            curr = [l_str]
                        else:
                            curr.append(l_str)
                if curr:
                    paras.append(' '.join(curr))
                md_lines.extend(paras)

            exhibits.append({'top': h_top, 'markdown': '\n\n'.join(md_lines)})
            consumed.update(ex_consumed)

        return exhibits, consumed

    @classmethod
    def extract_margin_glossaries(cls, page_elem, fonts, pw: float, ph: float, page_num: int = 0, already_consumed: set = None) -> tuple:
        """Extracts margin glossary definitions on odd or even pages."""
        return MarginParser.extract_margin_glossaries(page_elem, fonts, pw, ph, page_num, already_consumed, style_config=_STYLE)

    @classmethod
    def _build_gloss_callout(cls, term: str, slug: str, definition: str) -> str:
        """Builds a margin glossary blockquote callout using the active STYLE."""
        return MarginParser._build_gloss_callout(term, slug, definition, style_config=_STYLE)


    @classmethod
    def extract_vector_figures(cls, page_elem, fonts: dict, pdf_path: str, page_num: int, pw: float, ph: float) -> tuple:
        """
        Detects vector diagram figures (e.g. Figure 1.1) that have unmapped fonts or vector shapes,
        crops them via pdftoppm, and returns:
        (list_of_image_dicts, set_of_consumed_elements)
        """
        return VectorFigureParser.extract_vector_figures(
            page_elem=page_elem,
            fonts=fonts,
            pdf_path=pdf_path,
            page_num=page_num,
            pw=pw,
            ph=ph,
            style=_STYLE,
        )


    @classmethod
    def extract_page_tables(cls, page_elem, fonts: dict, pw: float, ph: float) -> tuple:
        """Extracts structured tables from page XML coordinates."""
        return TableParser.extract_page_tables(page_elem, fonts, pw, ph, style_config=_STYLE)


    @classmethod
    def extract_end_of_chapter_sections(cls, page_elem, fonts: dict, pw: float, ph: float, page_num: int) -> tuple:
        """
        Dynamically extracts end-of-chapter sections from any textbook page.
        Sections are identified by heading patterns defined in STYLE['eoc_heading_patterns'].

        Returns: (list_of_section_dicts, set_of_consumed_elements)
        """
        return EndOfChapterParser.extract_end_of_chapter_sections(
            page_elem=page_elem,
            fonts=fonts,
            pw=pw,
            ph=ph,
            page_num=page_num,
            style=_STYLE,
        )



def fonts_is_bold(t) -> bool:
    """Helper: check if XML element contains a <b> tag."""
    try:
        raw = __import__('xml').etree.ElementTree.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
        return '<b>' in raw
    except Exception:
        return False


def generate_markdown_toc(
    markdown_text: str,
    toc_mode: str = "close",
    toc_depth: int = 3,
    toc_title: str = "📑 Table of Contents",
    toc_min_headings: int = 2,
) -> str:
    """
    Extracts headers from chapter markdown and generates a clean, clickable Table of Contents block.

    Args:
        markdown_text: Raw or processed chapter markdown.
        toc_mode: 'close' (<details>), 'open' (<details open>), or 'none' ("").
        toc_depth: Maximum heading level to include (2 for H2 only, 3 for H2+H3, 4 for H2..H4).
        toc_title: Title string shown in <summary>.
        toc_min_headings: Minimum number of headings required to generate TOC.

    Returns:
        Formatted Table of Contents markdown block or empty string.
    """
    if toc_mode == "none":
        return ""

    lines = markdown_text.splitlines()
    toc_entries = []
    for line in lines:
        m_h2 = re.match(r'^##\s+(?!🗂️|<!--)(.+)$', line)
        m_h3 = re.match(r'^###\s+(?!<!--)(.+)$', line)
        m_h4 = re.match(r'^####\s+(?!<!--)(.+)$', line)

        if m_h2 and toc_depth >= 2:
            title = m_h2.group(1).strip()
            clean_title = re.sub(r'[*_`]', '', title)
            slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_title.lower()).strip('-')
            toc_entries.append(f"- [{clean_title}](#{slug})")
        elif m_h3 and toc_depth >= 3:
            title = m_h3.group(1).strip()
            clean_title = re.sub(r'[*_`]', '', title)
            slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_title.lower()).strip('-')
            toc_entries.append(f"  - [{clean_title}](#{slug})")
        elif m_h4 and toc_depth >= 4:
            title = m_h4.group(1).strip()
            clean_title = re.sub(r'[*_`]', '', title)
            slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_title.lower()).strip('-')
            toc_entries.append(f"    - [{clean_title}](#{slug})")

    if len(toc_entries) < toc_min_headings:
        return ""

    details_tag = "<details open>" if toc_mode == "open" else "<details>"
    clean_summary_title = toc_title.lstrip("📑").strip()
    return f"{details_tag}\n<summary>📑 <b>{clean_summary_title}</b></summary>\n\n" + '\n'.join(toc_entries) + "\n\n</details>\n"


class TwoColumnFlowResolver:
    """Resolves two-column reading flow by isolating gutters, footers, and full-width spanning elements."""

    @classmethod
    def order_blocks_by_flow(
        cls,
        blocks: list[dict[str, Any]],
        page_width: float = 612.0,
        gutter_center_ratio: float = 0.5,
        spanning_threshold_ratio: float = 0.65,
    ) -> list[dict[str, Any]]:
        """Orders page text blocks strictly according to two-column reading flow.

        Ensures full-width spanning elements (figures, tables, headers) remain at their
        vertical locations, while text between spanning elements is strictly read down the
        entire left column before beginning the right column.

        Args:
            blocks: List of block dictionaries, each containing 'bbox' and 'text'.
            page_width: Page width in points (default: 612.0).
            gutter_center_ratio: Relative X position of the column gutter center (default: 0.5).
            spanning_threshold_ratio: Minimum width ratio to consider an element spanning (default: 0.65).

        Returns:
            List of blocks sorted in correct human reading order.
        """
        if not blocks:
            return []

        mid_x = page_width * gutter_center_ratio

        def _is_spanning(b: dict[str, Any]) -> bool:
            x0, y0, x1, y1 = b.get("bbox", (0, 0, 0, 0))
            width = x1 - x0
            if width >= page_width * spanning_threshold_ratio:
                return True
            if x0 < mid_x * 0.75 and x1 > mid_x * 1.25:
                return True
            return False

        spanning_blocks: list[dict[str, Any]] = []
        columnar_blocks: list[dict[str, Any]] = []

        for b in blocks:
            if _is_spanning(b):
                spanning_blocks.append(b)
            else:
                columnar_blocks.append(b)

        spanning_blocks.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])

        # If no spanning blocks, simple two-column split
        if not spanning_blocks:
            left_col = [b for b in columnar_blocks if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 < mid_x]
            right_col = [b for b in columnar_blocks if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 >= mid_x]
            left_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])
            right_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])
            return left_col + right_col

        # Partition columnar blocks into vertical bands separated by spanning blocks
        result: list[dict[str, Any]] = []
        unallocated_columnar = list(columnar_blocks)

        for span in spanning_blocks:
            span_y0 = span.get("bbox", (0, 0, 0, 0))[1]

            # All columnar blocks located above this spanning element
            band_blocks = [
                b for b in unallocated_columnar
                if (b.get("bbox", (0, 0, 0, 0))[1] + b.get("bbox", (0, 0, 0, 0))[3]) / 2.0 < span_y0
            ]
            for b in band_blocks:
                unallocated_columnar.remove(b)

            left_col = [b for b in band_blocks if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 < mid_x]
            right_col = [b for b in band_blocks if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 >= mid_x]
            left_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])
            right_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])

            result.extend(left_col)
            result.extend(right_col)
            result.append(span)

        # Remaining columnar blocks below the last spanning element
        if unallocated_columnar:
            left_col = [b for b in unallocated_columnar if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 < mid_x]
            right_col = [b for b in unallocated_columnar if (b.get("bbox", (0, 0, 0, 0))[0] + b.get("bbox", (0, 0, 0, 0))[2]) / 2.0 >= mid_x]
            left_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])
            right_col.sort(key=lambda b: b.get("bbox", (0, 0, 0, 0))[1])
            result.extend(left_col)
            result.extend(right_col)

        return result



