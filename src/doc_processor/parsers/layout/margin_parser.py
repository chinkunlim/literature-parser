"""
Margin Glossary & Notes Parser
==============================
Extracts margin terms, vocabulary glossaries, and sidebars, outputting
structured markdown callouts, anchors, and Anki recall cards.
"""

import re
import logging
import xml.etree.ElementTree as ET
from typing import Tuple, Set, List, Dict, Any
from doc_processor.style_loader import load_style

logger = logging.getLogger(__name__)
_DEFAULT_STYLE = load_style()


class MarginParser:
    """Specialized extractor for textbook margin notes and glossaries."""

    @classmethod
    def detect_page_margin_side(cls, page_elem, pw: float, ph: float) -> str:
        """
        Detects whether the margin glossary column is on the 'left' (even book page)
        or 'right' (odd book page) based on printed page numbers and body indentation.
        """
        # 1. Check printed page numbers in header/footer
        for t in page_elem.findall('text'):
            top = float(t.attrib.get('top', 0))
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
    def extract_margin_glossaries(cls, page_elem, fonts, pw: float, ph: float, page_num: int = 0, already_consumed: set = None, style_config: dict = None) -> tuple:
        style = style_config if style_config is not None else _DEFAULT_STYLE
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
            geom = style.get('book_profile', {}).get('geometry', {})
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
                    callout = cls._build_gloss_callout(clean_term, slug, def_str, style_config=style)
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
                            callout = cls._build_gloss_callout(clean_term, slug, def_str, style_config=style)
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
            callout = cls._build_gloss_callout(clean_term, slug, def_str, style_config=style)
            glossaries.append({'term': clean_term, 'top': curr_top, 'callout': callout, 'definition': def_str})
            consumed.update(curr_elems)

        return glossaries, consumed

    @classmethod
    def _build_gloss_callout(cls, term: str, slug: str, definition: str, style_config: dict = None) -> str:
        """Builds a margin glossary blockquote callout using the active STYLE."""
        style = style_config if style_config is not None else _DEFAULT_STYLE
        emoji = style.get("gloss_emoji", "📖")
        prefix = "Key Term: " if style.get("gloss_show_prefix", False) else ""
        sep = style.get("gloss_separator", "—")
        anchor = style.get("gloss_backlink_anchor", "key-terms-and-concepts")
        backlink = f" [↩](#{anchor})" if style.get("gloss_backlink", True) else ""
        return f'> {emoji} <a id="term-{slug}"></a>**{prefix}{term}** {sep} {definition}{backlink}'

