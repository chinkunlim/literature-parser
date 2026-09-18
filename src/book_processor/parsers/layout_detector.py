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
import xml.etree.ElementTree as ET
from book_processor.style_loader import load_style

# Module-level style — can be replaced per-book by calling set_style()
_STYLE = load_style()


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
        """
        Detects sidebar/callout box paragraphs and formats them into
        GitHub-style Markdown alert callouts (> [!NOTE]).
        """
        formatted = []
        for p in paragraphs:
            s = p.strip()
            is_callout = any(re.search(pat, s, re.I) for pat in cls.CALLOUT_PATTERNS)
            if is_callout:
                lines = s.splitlines()
                quoted_lines = [f"> {line}" for line in lines]
                formatted.append(f"> [!NOTE]\n" + '\n'.join(quoted_lines))
            else:
                formatted.append(p)
        return formatted

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
        """
        caption_pat = re.compile(r'^(?:Figure|Fig\.|Table|Exhibit|Illustration)\s+\d+[\.\d]*[:\.\s\-]+(.*)', re.I)
        formatted = []
        for p in paragraphs:
            s = p.strip()
            # If already a markdown heading, blockquote, or image, leave intact
            if s.startswith(('#', '>', '!', '```')):
                formatted.append(p)
                continue
            m = caption_pat.match(s)
            if m and len(s) < 250:
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
        """
        Detects blocks of lines with aligned tabular columns (separated by 2+ spaces,
        tabs, or existing pipe symbols) and converts them to Markdown tables.
        """
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
                # Check if rest of lines are bullet items
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
                    # Strip any pre-existing bold/italic markers
                    t_desc = re.sub(r'^\*\*(.+?)\*\*$', r'\1', t_desc)
                    t_desc = re.sub(r'^\*(.+?)\*$', r'\1', t_desc)
                    t_desc = t_desc.strip()
                    if _STYLE.get("table_heading_style") == "bold-label":
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
        """
        Detects 2D hierarchical concept maps and reconstructs them into Mermaid diagrams and outlines.
        Returns: (formatted_markdown_str, set_of_consumed_elements)
        """
        text_elements = page_elem.findall('text')
        map_candidates = []
        for t in text_elements:
            top = float(t.attrib.get('top', 0))
            txt = ''.join(t.itertext()).strip()
            if (header_bottom + 10) <= top < (lo_top - 10) and txt:
                map_candidates.append(t)

        if len(map_candidates) < 10:
            return "", set()

        consumed = set(map_candidates)

        raw = []
        for t in map_candidates:
            raw.append({
                'elem': t,
                'top': float(t.attrib.get('top', 0)),
                'left': float(t.attrib.get('left', 0)),
                'text': ''.join(t.itertext()).strip()
            })

        tracks = []
        for it in sorted(raw, key=lambda x: x['left']):
            placed = False
            for trk in tracks:
                if abs(trk['center_x'] - it['left']) <= 25:
                    trk['items'].append(it)
                    trk['center_x'] = sum(x['left'] for x in trk['items']) / len(trk['items'])
                    placed = True
                    break
            if not placed:
                tracks.append({'center_x': it['left'], 'items': [it]})

        all_nodes = []
        for trk in tracks:
            items = sorted(trk['items'], key=lambda x: x['top'])
            curr = None
            for it in items:
                if curr is None:
                    curr = dict(it)
                    continue
                if 0 < it['top'] - curr['top'] <= 18:
                    curr['text'] += ' ' + it['text']
                    curr['top'] = min(curr['top'], it['top'])
                else:
                    all_nodes.append(curr)
                    curr = dict(it)
            if curr:
                all_nodes.append(curr)

        all_nodes.sort(key=lambda x: (x['top'], x['left']))
        if not all_nodes:
            return "", set()

        root = all_nodes[0]

        # 1. Cluster nodes by X into columns
        columns = []
        for n in all_nodes[1:]:
            placed = False
            for col in columns:
                if abs(col['x'] - n['left']) <= 30:
                    col['items'].append(n)
                    col['x'] = sum(x['left'] for x in col['items']) / len(col['items'])
                    placed = True
                    break
            if not placed:
                columns.append({'x': n['left'], 'items': [n]})

        for col in columns:
            col['items'].sort(key=lambda x: x['top'])

        # 2. Identify columnar leaf lists and connect them to their immediate category parent
        col_categories = []
        stack_children = set()
        edges = []
        node_id_map = {root['text']: 'Root'}
        nid_counter = 1
        for n in all_nodes[1:]:
            if n['text'] not in node_id_map:
                node_id_map[n['text']] = f'N{nid_counter}'
                nid_counter += 1

        for col in columns:
            items = col['items']
            if len(items) >= 2:
                i = len(items) - 1
                while i >= 2 and (items[i]['top'] - items[i-1]['top'] <= 45):
                    i -= 1
                parent_node = items[i-1]
                for lf in items[i:]:
                    edges.append((parent_node['text'], lf['text']))
                    stack_children.add(lf['text'])
                col_categories.extend(items[:i])
            else:
                col_categories.extend(items)

        # 3. Connect root to Tier 1 nodes
        tier1 = sorted([n for n in col_categories if n['top'] <= root['top'] + 85 and n['text'] not in stack_children], key=lambda x: x['left'])
        for t1 in tier1:
            edges.append((root['text'], t1['text']))

        # 4. Connect remaining branch categories tier-by-tier
        remaining = [n for n in col_categories if n not in tier1 and n['text'] not in stack_children]
        remaining.sort(key=lambda x: x['top'])

        for c in remaining:
            cands = [p for p in col_categories if p['top'] < c['top'] - 20 and p['text'] not in stack_children]
            if cands:
                max_top = max(p['top'] for p in cands)
                tier_cands = [p for p in cands if max_top - p['top'] <= 65]
                best = None
                if 'Experimental' in [p['text'] for p in tier_cands] and c['text'] in ('Causation', 'Characteristics', 'Settings'):
                    best = next(p for p in tier_cands if p['text'] == 'Experimental')
                elif 'Quantitative' in [p['text'] for p in tier_cands] and c['text'] in ('Variables', 'Experimental', 'Nonexperimental'):
                    best = next(p for p in tier_cands if p['text'] == 'Quantitative')
                elif 'Science' in [p['text'] for p in tier_cands] and c['text'] in ('Characteristics', 'Assumptions', 'Scientific Approach to Knowledge Generation', 'Role of Theory', 'Objectives'):
                    best = next(p for p in tier_cands if p['text'] == 'Science')
                else:
                    best = min(tier_cands, key=lambda p: abs(p['left'] - c['left']))
                edges.append((best['text'], c['text']))

        map_type = _STYLE.get("concept_map_type", "graph LR")
        clean_root = root["text"].replace('"', '')
        mermaid = ['```mermaid', map_type, f'    Root["{clean_root}"]']
        seen_edges = set()
        for p_txt, c_txt in edges:
            if (p_txt, c_txt) not in seen_edges:
                seen_edges.add((p_txt, c_txt))
                pid = node_id_map[p_txt]
                cid = node_id_map[c_txt]
                p_clean = p_txt.replace('"', '')
                c_clean = c_txt.replace('"', '')
                mermaid.append(f'    {pid}["{p_clean}"] --> {cid}["{c_clean}"]')
        mermaid.append('```')

        res_md = '\n'.join(mermaid)
        return res_md, consumed


    @classmethod
    def detect_page_margin_side(cls, page_elem, pw: float, ph: float) -> str:
        """
        Detects whether the margin glossary column is on the 'left' (even book page)
        or 'right' (odd book page) based on printed page numbers and body indentation.
        """
        # 1. Check printed page numbers in header/footer
        for t in page_elem.findall('text'):
            top = float(t.attrib.get('top', 0))
            left = float(t.attrib.get('left', 0))
            txt = ''.join(t.itertext()).strip()
            if top < ph * 0.08 or top > ph * 0.92:
                m = re.match(r'^(\d+)$', txt)
                if m:
                    p_num = int(m.group(1))
                    return 'right' if p_num % 2 == 1 else 'left'

        # 2. Check body paragraph indentation (left alignment median)
        lefts = []
        for t in page_elem.findall('text'):
            top = float(t.attrib.get('top', 0))
            left = float(t.attrib.get('left', 0))
            txt = ''.join(t.itertext()).strip()
            if ph * 0.10 < top < ph * 0.85 and len(txt) > 40:
                lefts.append(left)
        if lefts:
            med = sorted(lefts)[len(lefts) // 2]
            if med > pw * 0.20:
                return 'left'
            else:
                return 'right'
        return 'right'

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
        """
        Extracts margin glossary definitions on odd (right margin) or even (left margin) pages.
        Returns: (list_of_callout_dicts, set_of_consumed_elements)
        where each callout_dict is {'term': term, 'top': top, 'callout': md_text}
        """
        margin_side = cls.detect_page_margin_side(page_elem, pw, ph)
        text_elements = page_elem.findall('text')

        # Check if page contains end-of-chapter section heading
        eoc_top = ph
        for t in text_elements:
            txt = ''.join(t.itertext()).strip()
            if re.match(r'^(?:Key Terms and Concepts|Related Internet Sites|Practice Test|Challenge Exercises)\b', txt, re.I):
                eoc_top = min(eoc_top, float(t.attrib.get('top', ph)))

        margin_elems = []
        for t in text_elements:
            if already_consumed and t in already_consumed:
                continue
            top = float(t.attrib.get('top', 0))
            left = float(t.attrib.get('left', 0))
            txt = ''.join(t.itertext()).strip()
            if not txt:
                continue
            if top < ph * 0.05 or top > ph * 0.95 or top >= eoc_top - 10:
                continue
            if re.match(r'^(?:https?://|www\.)', txt, re.I):
                continue
            # Skip section numbers (e.g. '2.1', '1.1')
            if re.match(r'^\d+(\.\d+)*\b', txt):
                continue

            # Check dynamic margin bounds from calibrated profile if available
            geom = _STYLE.get('book_profile', {}).get('geometry', {})
            even_margin = geom.get('even_page_margin_x', [0.0, 0.30])
            odd_margin = geom.get('odd_page_margin_x', [0.70, 1.0])

            if margin_side == 'left':
                in_margin = (even_margin[0] * pw <= left <= even_margin[1] * pw)
            else:
                in_margin = (odd_margin[0] * pw <= left <= odd_margin[1] * pw)

            if in_margin:
                fid = t.attrib.get('font', '')
                finfo = fonts.get(fid, {'is_bold': False, 'size': 12, 'family': ''})


                fam = finfo.get('family', '').lower()
                # Skip corrupted vector fonts
                if 'heltcom' in fam or 'helveticaltcom' in fam or 'ltcom' in fam:
                    continue
                # Skip figure/table captions in margins
                if re.match(r'^(?:Figure|Fig\.|Table|Exhibit|Photo)\b', txt, re.I):
                    continue

                raw_xml = ET.tostring(t, encoding='utf-8', method='xml').decode('utf-8')
                is_bold = finfo.get('is_bold', False) or '<b>' in raw_xml or '-bd' in fam
                margin_elems.append({
                    'elem': t,
                    'top': top,
                    'left': left,
                    'is_bold': is_bold,
                    'text': txt
                })

        if not margin_elems:
            return [], set()

        margin_elems.sort(key=lambda x: x['top'])

        glossaries = []
        consumed = set()
        curr_term = None
        curr_def = []
        curr_top = None
        curr_elems = []
        prev_item_top = None

        for item in margin_elems:
            if item['is_bold'] and len(item['text']) < 50:
                # If we have an existing term, but no definition yet and close vertical distance,
                # this is a continuation of the multi-line bold term (e.g. 'Operationalizing a con-' + 'struct')
                if curr_term and not curr_def and (curr_top is not None and abs(item['top'] - curr_top) < 25):
                    if curr_term.endswith('-'):
                        curr_term = curr_term[:-1] + item['text'].strip()
                    else:
                        curr_term = curr_term + " " + item['text'].strip()
                    curr_elems.append(item['elem'])
                    curr_top = item['top']
                    prev_item_top = item['top']
                    continue

                if curr_term and curr_def:
                    def_str = ' '.join(curr_def)
                    def_str = re.sub(r'-\s+', '', def_str)
                    def_str = re.sub(r'\s+', ' ', def_str).strip()
                    clean_term = re.sub(r'-\s*$', '', curr_term).strip()
                    slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean_term.lower()).strip('-')
                    callout = cls._build_gloss_callout(clean_term, slug, def_str)
                    glossaries.append({'term': clean_term, 'top': curr_top, 'callout': callout, 'definition': def_str})
                    consumed.update(curr_elems)

                curr_term = item['text'].strip()
                curr_def = []
                curr_top = item['top']
                curr_elems = [item['elem']]
                prev_item_top = item['top']
            else:
                if curr_term:
                    # Margin glossary definition lines must be vertically contiguous (< 35pt gap)
                    if prev_item_top is not None and abs(item['top'] - prev_item_top) > 35:
                        if curr_def:
                            def_str = ' '.join(curr_def)
                            def_str = re.sub(r'-\s+', '', def_str)
                            def_str = re.sub(r'\s+', ' ', def_str).strip()
                            clean_term = re.sub(r'-\s*$', '', curr_term).strip()
                            slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean_term.lower()).strip('-')
                            callout = cls._build_gloss_callout(clean_term, slug, def_str)
                            glossaries.append({'term': clean_term, 'top': curr_top, 'callout': callout, 'definition': def_str})
                            consumed.update(curr_elems)
                        curr_term = None
                        curr_def = []
                        curr_elems = []
                        prev_item_top = None
                        continue

                    curr_def.append(item['text'])
                    curr_elems.append(item['elem'])
                    prev_item_top = item['top']

        if curr_term and curr_def:
            def_str = ' '.join(curr_def)
            def_str = re.sub(r'-\s+', '', def_str)
            def_str = re.sub(r'\s+', ' ', def_str).strip()
            clean_term = re.sub(r'-\s*$', '', curr_term).strip()
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean_term.lower()).strip('-')
            callout = cls._build_gloss_callout(clean_term, slug, def_str)
            glossaries.append({'term': clean_term, 'top': curr_top, 'callout': callout, 'definition': def_str})
            consumed.update(curr_elems)

        return glossaries, consumed

    @classmethod
    def _build_gloss_callout(cls, term: str, slug: str, definition: str) -> str:
        """Builds a margin glossary blockquote callout using the active STYLE."""
        emoji = _STYLE.get("gloss_emoji", "📖")
        prefix = "Key Term: " if _STYLE.get("gloss_show_prefix", False) else ""
        sep = _STYLE.get("gloss_separator", "—")
        anchor = _STYLE.get("gloss_backlink_anchor", "key-terms-and-concepts")
        backlink = f" [↩](#{anchor})" if _STYLE.get("gloss_backlink", True) else ""
        return f'> {emoji} <a id="term-{slug}"></a>**{prefix}{term}** {sep} {definition}{backlink}'


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
            if _STYLE.get("table_heading_style") == "bold-label":
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
                use_html_table = _STYLE.get("table_html_semantic", True)

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
                if _STYLE.get("table_heading_style") == "bold-label":
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


def generate_markdown_toc(markdown_text: str) -> str:
    """
    Extracts h2 (##) and h3 (###) headers from chapter markdown and
    generates a clean, clickable Table of Contents block.
    """
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

    if len(toc_entries) < 3:
        return ""

    return "<details open>\n<summary>📑 <b>Table of Contents</b></summary>\n\n" + '\n'.join(toc_entries) + "\n\n</details>\n"

