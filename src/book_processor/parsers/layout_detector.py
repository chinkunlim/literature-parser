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

import re
import logging
import xml.etree.ElementTree as ET
from book_processor.style_loader import load_style

logger = logging.getLogger(__name__)

# Module-level style — can be replaced per-book by calling set_style()
_STYLE = load_style()

from book_processor.parsers.layout.table_parser import TableParser
from book_processor.parsers.layout.concept_map_parser import ConceptMapParser
from book_processor.parsers.layout.margin_parser import MarginParser
from book_processor.parsers.layout.callout_parser import CalloutParser
from book_processor.parsers.layout.list_parser import ListParser
from book_processor.parsers.layout.table_llm_fixer import TableLLMFixer


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
        Identifies bottom-of-page footnote lines (typically bottom 15% of page)
        starting with a numeral or dagger and formats as Markdown footnotes [^X]: ...
        Returns: (body_lines, footnote_markdown_strings)
        """
        body_lines = []
        footnote_lines = []
        bottom_threshold = page_height * 0.85
        in_footnote = False

        for top, left, size, text in lines_with_pos:
            s = text.strip()
            # Check if line is at the bottom of the page and starts with a digit/bracket
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
            body_lines.append((top, left, size, text))

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
        caption_pat = re.compile(r'^(?:Figure|Fig\.|Table|Exhibit|Illustration)\s+\d+[\.\d]*(?:\s*[:\-–—]\s*|\s*\.\s+)(.*)', re.I)
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
            if re.search(r'Learning Objectives', txt, re.I):
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
            m = re.match(r'^(?:EXHIBIT|Exhibit)\s+(\d+[\.\d]*)', txt, re.I)
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
                    if abs(top - h_top) <= 12 and left > h_left:
                        title_parts.append(txt)
                        ex_consumed.append(t)
                    elif 0 < top - h_top <= 25 and sz >= 20 and left < pw * 0.6:
                        title_parts.append(txt)
                        ex_consumed.append(t)
            full_title = re.sub(r'[\s\u00a0]+', ' ', ' '.join(title_parts)).strip()

            # Collect exhibit text elements
            ex_elems = []
            for t in sorted_texts:
                if t in ex_consumed:
                    continue
                top = float(t.attrib.get('top', 0))
                if top < h_top - 5 and not is_continuation:
                    continue
                if top < ph * 0.05 or top > ph * 0.95:
                    continue
                fid = t.attrib.get('font', '')
                fam = fonts.get(fid, {}).get('family', '').lower()
                txt = ''.join(t.itertext()).strip()
                if not txt:
                    continue
                if 'helvetica' in fam or 'ltw1g' in fam:
                    ex_elems.append(t)
                    ex_consumed.append(t)
                elif ('palatino' in fam or 'caecilia' in fam) and top > h_top + 40:
                    break

            if not ex_elems and not title_parts:
                continue

            # Format Exhibit into Markdown
            heading_str = f"### {head_txt} {full_title}".strip() if full_title else f"### {head_txt}".strip()
            md_lines = [heading_str, ""]

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
                split_top = min(float(t.attrib.get('top', 0)) for t in right_elems)
                for t in ex_elems:
                    top = float(t.attrib.get('top', 0))
                    left = float(t.attrib.get('left', 0))
                    w = float(t.attrib.get('width', 0))
                    if top < split_top - 5 and w > pw * 0.5:
                        intro_elems.append(t)
                    elif left < pw * 0.45:
                        c1_elems.append(t)
                    else:
                        c2_elems.append(t)

                def format_col(elems):
                    elems.sort(key=lambda x: float(x.attrib.get('top', 0)))
                    paras = []
                    curr = []
                    last_y = None
                    for e in elems:
                        y = float(e.attrib.get('top', 0))
                        txt = ''.join(e.itertext()).strip()
                        if last_y is not None and (y - last_y > 22 or float(e.attrib.get('left', 0)) > min(float(x.attrib.get('left', 0)) for x in elems) + 20):
                            if curr:
                                paras.append(' '.join(curr))
                                curr = []
                        curr.append(txt)
                        last_y = y
                    if curr:
                        paras.append(' '.join(curr))
                    return paras

                if intro_elems:
                    md_lines.extend(format_col(intro_elems))
                md_lines.extend(format_col(c1_elems))
                md_lines.extend(format_col(c2_elems))
            else:
                elems_sorted = sorted(ex_elems, key=lambda x: float(x.attrib.get('top', 0)))
                paras = []
                curr = []
                last_y = None
                for e in elems_sorted:
                    y = float(e.attrib.get('top', 0))
                    txt = ''.join(e.itertext()).strip()
                    if last_y is not None and y - last_y > 20:
                        if curr:
                            paras.append(' '.join(curr))
                            curr = []
                    curr.append(txt)
                    last_y = y
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
        import subprocess
        from pathlib import Path

        fig_elems = []
        for t in page_elem.findall('text'):
            txt = ''.join(t.itertext()).strip()
            if re.match(r'^(?:Figure|Fig\.)\s+\d+[\.\d]*(?:\s*[:\.\-–—]|\s+[A-Z]|$)', txt):
                if re.match(r'^(?:Figure|Fig\.)\s+\d+[\.\d]*\s+(?:shows|illustrates|depicts|reveals|demonstrates|is|was|can)\b', txt, re.I):
                    continue
                fig_elems.append(t)

        if not pdf_path:
            return [], set()

        img_dir = Path(pdf_path).parent / 'images'
        img_dir.mkdir(exist_ok=True)

        extracted_images = []
        consumed = set()


        for cap_t in fig_elems:
            cap_txt = ''.join(cap_t.itertext()).strip()
            m = re.match(r'^(?:Figure|Fig\.)\s+(\d+[\.\d]*)', cap_txt, re.I)
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
                    # Sidebar figure: circles and text on left side
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
                    # Main-column / full-width figure (e.g. Fig 1.2): boxes, arrows, and flowchart
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
                img_fname = f"figure_{fig_sanitized}.png"
                if (img_dir / img_fname).exists():
                    extracted_images.append({
                        'page': page_num,
                        'filename': img_fname,
                        'caption': full_caption,
                        'top': f_top
                    })
                    consumed.update(cap_consumed)
                    consumed.update(diag_elems)
                    # Consume any text elements located within the cropped figure bounding box
                    for t_box in page_elem.findall('text'):
                        t_b_top = float(t_box.attrib.get('top', 0))
                        t_b_left = float(t_box.attrib.get('left', 0))
                        if (left_b - 10.0 <= t_b_left <= right_b + 10.0) and (top_b - 10.0 <= t_b_top <= bottom_b + 10.0):
                            consumed.add(t_box)
            except subprocess.TimeoutExpired:
                logger.warning("pdftoppm timed out (30s) cropping figure on page %d", page_num)
            except Exception as e:
                logger.debug("Figure crop failed on page %d: %s", page_num, e)

        # Check for uncaptioned vector diagrams (e.g. research notation diagrams like RA -> X -> O)
        # Strictly requires notation tokens (e.g. RA, X, O), unmapped symbol fonts, or a 'where ... denotes' legend
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
                            # Exclude margin text
                            if n_left < pw * 0.25 or n_left > pw * 0.75:
                                continue
                            # Exclude section titles or questions
                            fid = nxt.attrib.get('font', '')
                            sz = float(fonts.get(fid, {}).get('size', 12))
                            if sz >= 18:
                                continue
                            if len(n_txt) <= 20:
                                diag_cands.append(nxt)

                    # Only treat as diagram if we have genuine notation/diagram characteristics
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
                            full_img_name = f"{diag_fname}.png"
                            if (img_dir / full_img_name).exists():
                                extracted_images.append({
                                    'page': page_num,
                                    'filename': full_img_name,
                                    'caption': 'Diagram',
                                    'top': min_y
                                })
                                consumed.update(diag_cands)
                        except subprocess.TimeoutExpired:
                            logger.warning("pdftoppm timed out (30s) cropping diagram on page %d", page_num)
                        except Exception as e:
                            logger.debug("Diagram crop failed on page %d: %s", page_num, e)

        return extracted_images, consumed

    @classmethod
    def extract_page_tables(cls, page_elem, fonts: dict, pw: float, ph: float) -> tuple:
        """Extracts structured tables from page XML coordinates."""
        return TableParser.extract_page_tables(page_elem, fonts, pw, ph, style_config=_STYLE)


    @classmethod
    def extract_end_of_chapter_sections(cls, page_elem, fonts: dict, pw: float, ph: float, page_num: int) -> tuple:
        """
        Dynamically extracts end-of-chapter sections from any textbook page.
        Sections are identified by heading patterns defined in STYLE['eoc_heading_patterns'].

        Supports:
        - Key Terms and Concepts (multi-column term index with page links)
        - Related Internet Sites (URL-like entries)
        - Practice Test / Challenge Exercises / Review Questions (numbered items)
        - Summary / Discussion Questions / References (collected paragraphs)

        Returns: (list_of_section_dicts, set_of_consumed_elements)
        """
        sections = []
        consumed = set()

        text_elements = page_elem.findall('text')
        eoc_patterns = _STYLE.get("eoc_heading_patterns", [
            r"^Key Terms and Concepts\b",
            r"^Related Internet Sites\b",
            r"^Practice Test\b",
            r"^Challenge Exercises\b",
            r"^Summary\b",
            r"^Review Questions\b",
            r"^Discussion Questions\b",
            r"^Critical Thinking\b",
            r"^Further Reading\b",
            r"^References\b",
        ])

        # ── 1. Find all EOC section headings on this page ─────────────────────
        eoc_headings = []
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            top = float(t.attrib.get('top', 0))
            for pat in eoc_patterns:
                if re.match(pat, txt, re.I):
                    eoc_headings.append({'elem': t, 'top': top, 'text': txt, 'pattern': pat})
                    break

        if not eoc_headings:
            # Check if this page is an EOC continuation page (e.g. Ch04 p27 where Challenge Exercises continues)
            if page_num >= 5:
                has_chap_header = any(float(fonts.get(t.attrib.get('font', ''), {}).get('size', 12)) >= 25 for t in text_elements if float(t.attrib.get('top', 0)) < ph * 0.3)
                txt_all = " ".join("".join(t.itertext()).strip() for t in text_elements)
                has_exercise_mentions = bool(re.search(r'\b(?:challenge exercise|review question|practice test)\b', txt_all, re.I))
                has_table_or_fig = bool(re.search(r'\b(?:Table|Figure|Fig\.)\s+\d+', txt_all))
                num_items = [t for t in text_elements if re.match(r'^(?:\*\*)?(?:\d+|[a-e])[\.\)]', ''.join(t.itertext()).strip())]
                if not has_chap_header and has_exercise_mentions and not has_table_or_fig and len(num_items) >= 4:
                    eoc_elems = [t for t in text_elements if ph * 0.05 < float(t.attrib.get('top', 0)) < ph * 0.95 and ''.join(t.itertext()).strip()]
                    sec_md = cls._extract_generic_eoc_section(eoc_elems, fonts, pw)
                    if sec_md:
                        consumed.update(eoc_elems)
                        return [{'top': 0.0, 'markdown': sec_md}], consumed
            return [], set()

        # Sort headings by vertical position
        eoc_headings.sort(key=lambda h: h['top'])

        # ── 1b. Check if there are EOC continuation items ABOVE the first heading (e.g. Ch01 P17) ──
        first_h_top = eoc_headings[0]['top']
        above_elems = [t for t in text_elements if 50.0 < float(t.attrib.get('top', 0)) < first_h_top and ''.join(t.itertext()).strip()]
        has_above_items = any(re.match(r'^(?:\*\*)?(?:\d+|[a-e])[\.\)]', ''.join(t.itertext()).strip()) for t in above_elems)
        if has_above_items and len(above_elems) >= 5:
            above_md = cls._extract_generic_eoc_section(above_elems, fonts, pw)
            if above_md:
                sections.append({'top': 0.0, 'markdown': above_md})
                consumed.update(above_elems)

        # ── 2. For each heading, collect elements until the next EOC heading ──
        all_sorted = sorted(text_elements, key=lambda t: float(t.attrib.get('top', 0)))

        for h_idx, heading in enumerate(eoc_headings):
            h_top = heading['top']
            h_text = heading['text']
            h_elem = heading['elem']
            next_h_top = eoc_headings[h_idx + 1]['top'] if h_idx + 1 < len(eoc_headings) else ph + 1

            # Collect all text elements between this heading and the next
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

            # ── 2a. Key Terms and Concepts — multi-column layout ────────────
            if re.match(r'^Key Terms and Concepts\b', h_text, re.I):
                sec_md = cls._extract_key_terms_section(h_elem, section_elems, pw, ph)
                if sec_md:
                    sections.append({'top': h_top, 'markdown': sec_md})
                continue

            # ── 2b. Related Internet Sites ──────────────────────────────────
            if re.match(r'^Related Internet Sites\b', h_text, re.I):
                sec_md = cls._extract_internet_sites_section(section_elems)
                if sec_md:
                    sections.append({'top': h_top, 'markdown': f"### {h_text}\n\n{sec_md}"})
                continue

            # ── 2c. All other EOC sections — dynamic text extraction ────────
            sec_md = cls._extract_generic_eoc_section(section_elems, fonts, pw)
            if sec_md:
                sections.append({'top': h_top, 'markdown': f"### {h_text}\n\n{sec_md}"})

        return sections, consumed

    @classmethod
    def _extract_key_terms_section(cls, heading_elem, section_elems, pw: float, ph: float) -> str:
        """
        Builds a Key Terms and Concepts section with multi-column term table
        and bidirectional anchor links. Works for any number of columns.
        """
        anchor = _STYLE.get("gloss_backlink_anchor", "key-terms-and-concepts")

        if not section_elems:
            return f'<a id="{anchor}"></a>\n### Key Terms and Concepts\n'

        # Cluster elements into columns by X-coordinate proximity
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

        # Sort each column's elements by vertical position
        cols = []
        for col in col_centers:
            col_items = []
            for t in sorted(col['elems'], key=lambda e: float(e.attrib.get('top', 0))):
                txt = ''.join(t.itertext()).strip()
                if txt:
                    # Normalise "Term p. 12" → "Term *p. 12*"
                    txt = re.sub(r'\s+p\.\s+(\d+)$', r' *p. \1*', txt)
                    col_items.append(txt)
            cols.append(col_items)

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

        anchor_prefix = "term-"
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
        """
        Formats Related Internet Sites entries into clean bullet items with URLs.
        """
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
            is_url = bool(re.match(r'^https?://|^www\.', txt, re.I))
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
        """
        Dynamically extracts any EOC section (Practice Test, Challenge Exercises,
        Review Questions, Summary, etc.) by reading actual PDF content.
        Supports multi-column uncurling (Column 1 then Column 2).
        """
        if not section_elems:
            return ''

        # Check if elements are laid out in two distinct columns
        left_elems = [t for t in section_elems if float(t.attrib.get('left', 0)) < pw * 0.45]
        right_elems = [t for t in section_elems if float(t.attrib.get('left', 0)) >= pw * 0.45]

        def process_elems(elems):
            lines_by_top = sorted(elems, key=lambda t: float(t.attrib.get('top', 0)))
            result_lines = []
            for t in lines_by_top:
                fid = t.attrib.get('font', '')
                finfo = fonts.get(fid, {'is_bold': False, 'size': 12, 'family': ''})

                raw_xml = __import__('xml').etree.ElementTree.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
                is_bold = finfo.get('is_bold', False) or '<b>' in raw_xml

                # Re-parse inner XML for bold/italic
                m_inner = re.search(r'^<text[^>]*>(.*)</text>$', raw_xml, re.DOTALL)
                inner = m_inner.group(1) if m_inner else ''.join(t.itertext())
                inner = re.sub(r'</?a[^>]*>', '', inner)
                inner = re.sub(r'<b>\s*(.*?)\s*</b>', r'**\1** ', inner)
                inner = re.sub(r'<i>\s*(.*?)\s*</i>', r'*\1*', inner)
                txt = inner.strip()
                if not txt:
                    continue

                # Normalise trailing space after bold question numbers: **1.** -> **1.** 
                txt = re.sub(r'^(\*\*\d+\.\*\*|\*\*[a-e]\.\*\*)(\S)', r'\1 \2', txt)

                # Detect bold question numbers: **1.** or **a.**
                if re.match(r'^\*\*\d+\.\*\*|^\*\*[a-e]\.\*\*', txt):
                    result_lines.append('')
                    result_lines.append(txt)
                elif is_bold and len(txt) < 80 and re.match(r'^\d+\.', txt):
                    clean_num = re.sub(r'^(\d+\.)\s*', r'**\1** ', txt)
                    result_lines.append(f"\n{clean_num}")
                # Detect answer choices: "a. Some text", "b. More text"
                elif re.match(r'^[a-e][\.\)]\s+\S', txt):
                    result_lines.append(f"{txt}")
                else:
                    result_lines.append(txt)

            # Join consecutive non-empty, non-choice lines as paragraphs
            output = []
            pending = []
            for line in result_lines:
                if line == '':
                    if pending:
                        output.append(' '.join(pending))
                        pending = []
                    if output and output[-1] != '':
                        output.append('')
                elif re.match(r'^[a-e][\.\)]\s+\S', line):
                    if pending:
                        output.append(' '.join(pending))
                        pending = []
                    # Append answer options contiguously without intervening blank lines
                    output.append(line)
                elif line.startswith('**') or line.startswith('*') or line.startswith('#'):
                    if pending:
                        output.append(' '.join(pending))
                        pending = []
                    output.append(line)
                else:
                    pending.append(line)
            if pending:
                output.append(' '.join(pending))

            # Clean up consecutive empty lines
            cleaned_res = []
            for l in output:
                if l == '' and cleaned_res and cleaned_res[-1] == '':
                    continue
                cleaned_res.append(l)

            return '\n'.join(cleaned_res).strip()

        if len(left_elems) >= 3 and len(right_elems) >= 3:
            col1_md = process_elems(left_elems)
            col2_md = process_elems(right_elems)
            col1_rstrip = col1_md.rstrip()
            col2_lstrip = col2_md.lstrip()
            if col1_rstrip and not re.search(r'[.?!:;>]$', col1_rstrip) and col2_lstrip and col2_lstrip[0].islower():
                return f"{col1_rstrip} {col2_lstrip}".strip()
            return f"{col1_md}\n\n{col2_md}".strip()
        else:
            return process_elems(section_elems)


def fonts_is_bold(t) -> bool:
    """Helper: check if XML element contains a <b> tag."""
    try:
        raw = __import__('xml').etree.ElementTree.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
        return '<b>' in raw
    except Exception:
        return False


def generate_markdown_toc(markdown_text: str, toc_mode: str = "open") -> str:
    """
    Extracts h2 (##) and h3 (###) headers from chapter markdown and
    generates a clean, clickable Table of Contents block.
    Supports toc_mode: 'open' (<details open>), 'close' (<details>), or 'none' ("").
    """
    if toc_mode == "none":
        return ""

    lines = markdown_text.splitlines()
    toc_entries = []
    for line in lines:
        m_h2 = re.match(r'^##\s+(?!🗂️|<!--)(.+)$', line)
        m_h3 = re.match(r'^###\s+(?!<!--)(.+)$', line)
        if m_h2:
            title = m_h2.group(1).strip()
            # Clean title of markdown asterisks/formatting
            clean_title = re.sub(r'[*_`]', '', title)
            slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_title.lower()).strip('-')
            toc_entries.append(f"- [{clean_title}](#{slug})")
        elif m_h3:
            title = m_h3.group(1).strip()
            clean_title = re.sub(r'[*_`]', '', title)
            slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_title.lower()).strip('-')
            toc_entries.append(f"  - [{clean_title}](#{slug})")

    if len(toc_entries) < 2:
        return ""

    details_tag = "<details open>" if toc_mode == "open" else "<details>"
    return f"{details_tag}\n<summary>📑 <b>Table of Contents</b></summary>\n\n" + '\n'.join(toc_entries) + "\n\n</details>\n"


