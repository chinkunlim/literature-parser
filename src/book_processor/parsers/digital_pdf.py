"""
Born-Digital Vector PDF Parser
==============================
Parses born-digital PDFs using pdftohtml XML output to preserve font styling
(bold, italic, font weight), structural paragraphs, and LaTeX math formulas.
"""

import logging
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from book_processor.parsers.layout_detector import LayoutDetector
from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.parsers.math.apa_stats_normalizer import APAStatsNormalizer
from book_processor.style_loader import load_style
from book_processor.fingerprinting.document_classifier import DocumentClassifier
from book_processor.utils.text_utils import (
    clean_punctuation_spacing, repair_hyphens, clean_page_text_artifacts,
    detect_plain_text_headings, reflow_wrapped_lines, repair_drop_caps,
    format_dialogue_lines, clean_typography_artifacts
)

logger = logging.getLogger(__name__)
_STYLE = load_style()


def set_style(style: dict) -> None:
    """Override the module-level style (call once per book from the orchestrator)."""
    global _STYLE
    _STYLE = style

import threading

_thread_state = threading.local()


class _ChapterStateMeta(type):
    """Ensures chapter glossaries and inline terms are strictly thread-local during parallel runs."""
    @property
    def _chapter_glossaries(cls):
        if not hasattr(_thread_state, 'glossaries'):
            _thread_state.glossaries = []
        return _thread_state.glossaries

    @_chapter_glossaries.setter
    def _chapter_glossaries(cls, val):
        _thread_state.glossaries = val

    @property
    def _chapter_inline_terms(cls):
        if not hasattr(_thread_state, 'inline_terms'):
            _thread_state.inline_terms = []
        return _thread_state.inline_terms

    @_chapter_inline_terms.setter
    def _chapter_inline_terms(cls, val):
        _thread_state.inline_terms = val


class DigitalPDFParser(metaclass=_ChapterStateMeta):
    """Extracts structured text from born-digital vector PDFs preserving bold & italic styles."""

    set_style = staticmethod(set_style)
    set_active_style = staticmethod(set_style)

    @classmethod
    def reset_chapter_state(cls) -> None:
        """Resets the accumulated per-chapter state (margin glossaries + inline terms)."""
        cls._chapter_glossaries = []
        cls._chapter_inline_terms = []

    @classmethod
    def get_chapter_glossaries(cls) -> list:
        """Returns margin-column glossary terms accumulated across the chapter."""
        return list(cls._chapter_glossaries)

    @classmethod
    def collect_inline_bold_terms(cls, markdown_text: str, page_num: int) -> None:
        """
        Scans a page's markdown output for **Term** bold markers in body prose
        and records them as inline glossary candidates. Terms already present
        in margin glossaries (_chapter_glossaries) are skipped to avoid duplicates.
        Filters out structural labels, section headers, speakers, and non-terms.
        """
        existing_terms  = {g['term'].lower() for g in cls._chapter_glossaries}
        existing_inline = {g['term'].lower() for g in cls._chapter_inline_terms}

        NON_TERM_PATTERN = re.compile(
            r'^(?:Table|Figure|Exhibit|Appendix|Photo|Step|Study\s*Questions?|Criterion|'
            r'Ask\s*yourself|Leader|Client|Counselor|Speaker|Tip|Note|Important|Caution|'
            r'Example|Box|Section|Chapter|\d+)',
            re.I
        )

        for m in re.finditer(r'\*\*([A-Z][a-zA-Z][^*]{1,40}?)\*\*', markdown_text):
            raw = m.group(1).strip()
            # Skip blacklisted terms, pure uppercase acronyms, or non-term labels
            if NON_TERM_PATTERN.match(raw):
                continue
            if len(raw) < 3 or len(raw) > 35 or raw.isupper():
                continue
            if raw.endswith((':', '.', '?', '!', ';', ',')):
                continue

            term_key = raw.lower()
            if term_key not in existing_terms and term_key not in existing_inline:
                cls._chapter_inline_terms.append({
                    'term': raw,
                    'definition': None,   # no margin definition — prompt reader to recall
                    'page': page_num,
                    'source': 'inline_bold',
                })
                existing_inline.add(term_key)


    @classmethod
    def get_chapter_all_terms(cls) -> list:
        """
        Returns merged, deduplicated list of all flashcard terms:
          1. Margin glossary terms (with definitions) — shown first
          2. Inline bold terms (no definition) — shown after with a recall prompt
        """
        seen     = {g['term'].lower() for g in cls._chapter_glossaries}
        combined = list(cls._chapter_glossaries)
        for it in cls._chapter_inline_terms:
            if it['term'].lower() not in seen:
                combined.append(it)
                seen.add(it['term'].lower())
        return combined

    @staticmethod
    def _is_running_header(top: float, ph: float, txt: str = "", font_size: float = 12.0) -> bool:
        """Determines if a text element is part of the top running header."""
        if font_size >= 18.0:
            return False
        if top < ph * 0.04:
            return True
        if top < ph * 0.11:
            clean = txt.strip()
            if re.match(r'^\d+$', clean):
                return True
            if re.search(r'\b(?:ARTICLE IN PRESS|Journal of [A-Za-z]+|EXPERIMENTAL AND CLINICAL PSYCHOPHARMACOLOGY)\b', clean, re.I):
                return True
            if re.search(r'\bTEST-RETEST CHARACTERISTICS\b', clean):
                return True
            if re.search(r'\b(?:et al\.\s*/|WHITE,\s*LEJUEZ,\s*AND\s*DE\s*WIT|Downloaded from https?://)\b', clean, re.I):
                return True
            if clean.isupper() and len(clean) > 5 and font_size <= 14.0:
                return True
        return False

    @staticmethod
    def _is_running_footer(top: float, ph: float, txt: str, footer_ratio: float = 0.06) -> bool:
        """Determines if a text element is part of the bottom running footer."""
        cut_ratio = max(footer_ratio, 0.06)
        if top > ph * (1.0 - cut_ratio):
            return bool(re.match(r'^\d+$', txt) or 'copyright' in txt.lower())
        return False

    @staticmethod
    def extract_page_xml(pdf_path: str, page_num: int) -> str:
        """Extracts pdftohtml XML representation of a single page."""
        try:
            proc = subprocess.run(
                ['pdftohtml', '-xml', '-nodrm', '-i', '-stdout', '-f', str(page_num), '-l', str(page_num), pdf_path],
                capture_output=True, check=True, timeout=30
            )
            return proc.stdout.decode('utf-8', errors='ignore')
        except subprocess.TimeoutExpired:
            logger.warning("pdftohtml timed out (30s) extracting page %d XML from '%s'", page_num, pdf_path)
            return ""
        except subprocess.CalledProcessError as e:
            logger.warning("pdftohtml failed with exit code %d on page %d: %s", e.returncode, page_num, e)
            return ""
        except Exception as e:
            logger.debug("pdftohtml failed on page %d: %s", page_num, e)
            return ""

    @classmethod
    def parse_page_to_markdown(cls, pdf_path: str, page_num: int, page_images: list) -> str:
        """
        Parses a born-digital page:
        1. Reads XML tags <b> and <i> and fontspec styles.
        2. Filters out running headers & footers.
        3. Re-flows paragraphs and joins hyphenated line wraps.
        4. Reconstructs LaTeX formulas.
        5. Inserts genuine figure images.
        """
        xml_content = cls.extract_page_xml(pdf_path, page_num)
        if not xml_content or '<page' not in xml_content:
            # Fallback to pdftotext if XML extraction fails
            try:
                raw = subprocess.check_output(
                    ['pdftotext', '-f', str(page_num), '-l', str(page_num), pdf_path, '-'],
                    stderr=subprocess.DEVNULL, timeout=30
                ).decode('utf-8', errors='ignore')
                return MathLaTeXConverter.process_text(raw.strip())
            except subprocess.TimeoutExpired:
                logger.warning("pdftotext timed out (30s) on page %d: '%s'", page_num, pdf_path)
                return ""
            except subprocess.CalledProcessError as e:
                logger.warning("pdftotext failed with exit code %d on page %d: %s", e.returncode, page_num, e)
                return ""
            except Exception as e:
                logger.debug("pdftotext fallback failed on page %d: %s", page_num, e)
                return ""

        try:
            # Extract page element
            start = xml_content.find('<page')
            end = xml_content.rfind('</page>') + len('</page>')
            page_elem = ET.fromstring(xml_content[start:end])
        except Exception:
            return ""

        # Map font styles: bold / italic / math from fontspec
        fonts = {}
        for fontspec in page_elem.findall('fontspec'):
            f_id = fontspec.attrib.get('id')
            family = fontspec.attrib.get('family', '').lower()
            size = float(fontspec.attrib.get('size', '12'))
            is_bold = 'bold' in family or '-bd' in family or '_b' in family
            is_italic = 'italic' in family or 'oblique' in family or '-it' in family
            is_math = any(k in family for k in ('math', 'symbol', 'pi'))
            fonts[f_id] = {
                'is_bold': is_bold,
                'is_italic': is_italic,
                'is_math': is_math,
                'family': family,
                'size': size
            }

        ph = float(page_elem.attrib.get('height', '1100'))
        pw = float(page_elem.attrib.get('width', '800'))

        # Strip bleed / imposition elements outside visible page boundary
        for el in list(page_elem):
            if el.tag in ('text', 'image'):
                l = float(el.attrib.get('left', 0))
                t = float(el.attrib.get('top', 0))
                if l < 0 or l >= pw or t < 0 or t >= ph:
                    page_elem.remove(el)

        # Check if page has zero text elements (e.g. GlyphLessFont / scanned page with raster layer)
        visible_texts = [t for t in page_elem.findall('text') if ''.join(t.itertext()).strip()]
        if not visible_texts:
            # Fallback to pdftotext
            try:
                raw = subprocess.check_output(
                    ['pdftotext', '-layout', '-f', str(page_num), '-l', str(page_num), pdf_path, '-'],
                    stderr=subprocess.DEVNULL, timeout=30
                ).decode('utf-8', errors='ignore')
                # 1. Detect plain text headings using raw layout indentation
                cleaned = detect_plain_text_headings(raw)
                # 2. Clean page artifacts (running headers / footers)
                cleaned = clean_page_text_artifacts(cleaned, page_num=page_num)
                # 3. Clean typography & dingbat bullets
                cleaned = clean_typography_artifacts(cleaned)
                # 4. Format counseling dialogues
                cleaned = format_dialogue_lines(cleaned)
                # 5. Reflow wrapped lines separating headings, lists, and prose
                cleaned = reflow_wrapped_lines(cleaned)
                # 6. Clean punctuation spacing
                cleaned = clean_punctuation_spacing(cleaned)
                # 7. Repair hyphens and drop caps
                cleaned = repair_hyphens(cleaned)
                cleaned = repair_drop_caps(cleaned)
                if cleaned:
                    page_elem.clear()
                    return MathLaTeXConverter.process_text(cleaned)
            except subprocess.TimeoutExpired:
                logger.warning("pdftotext -layout timed out (30s) on page %d: '%s'", page_num, pdf_path)
            except subprocess.CalledProcessError as e:
                logger.warning("pdftotext -layout failed with exit code %d on page %d: %s", e.returncode, page_num, e)
            except Exception as e:
                logger.debug("pdftotext fallback failed on page %d: %s", page_num, e)

        is_journal = _STYLE.get("is_journal_article", False) or DocumentClassifier.is_journal_article(pdf_path)

        # 1. Pre-extract Learning Objectives (textbooks only)
        lo_md, lo_consumed = "", set()
        if not is_journal:
            try:
                lo_md, lo_consumed = LayoutDetector.extract_learning_objectives(page_elem, fonts)
            except Exception as e:
                logger.warning("extract_learning_objectives failed on page %d: %s", page_num, e)
                lo_md, lo_consumed = "", set()

        # 2. Pre-extract Concept Map (Only if page has Learning Objectives or chapter title on page 1)
        # Never run concept map on back-matter sections or journal articles
        pdf_path_lower = pdf_path.lower()
        sec_rules = _STYLE.get("section_rules", {})
        skip_concept_map = is_journal
        if any(k in pdf_path_lower for k in ("appendix", "glossary", "index", "reference")):
            skip_concept_map = True
        for sec_name, rules in sec_rules.items():
            if sec_name.lower() in pdf_path_lower and rules.get("skip_concept_map"):
                skip_concept_map = True
        if not _STYLE.get("features", {}).get("concept_map", True):
            skip_concept_map = True

        map_md = ""
        map_consumed = set()
        if not skip_concept_map and (lo_consumed or page_num == 1):
            try:
                lo_top = 9999.0
                if lo_consumed:
                    lo_top = min(float(t.attrib.get('top', 0)) for t in lo_consumed)
                header_bottom = 0.0
                for t in page_elem.findall('text'):
                    top = float(t.attrib.get('top', 0))
                    h = float(t.attrib.get('height', 20))
                    fid = t.attrib.get('font', '')
                    sz = fonts.get(fid, {}).get('size', 12)
                    if top < lo_top and sz >= 25:
                        header_bottom = max(header_bottom, top + h)
                map_md, map_consumed = LayoutDetector.reconstruct_concept_map(page_elem, fonts, header_bottom, lo_top)
            except Exception as e:
                logger.warning("reconstruct_concept_map failed on page %d: %s", page_num, e)
                map_md, map_consumed = "", set()

        # 3. Pre-extract Page Tables (e.g. Table 1.1, Table 2.1, Table 2.2) - priority over margin notes
        try:
            page_tables, tbl_consumed = LayoutDetector.extract_page_tables(page_elem, fonts, pw, ph)
        except Exception as e:
            logger.warning("extract_page_tables failed on page %d: %s", page_num, e)
            page_tables, tbl_consumed = [], set()

        # 4. Pre-extract Exhibits (e.g. Exhibit 3.1, Exhibit 4.1)
        try:
            page_exhibits, ex_consumed = LayoutDetector.extract_exhibits(page_elem, fonts, pw, ph, page_num)
        except Exception as e:
            logger.warning("extract_exhibits failed on page %d: %s", page_num, e)
            page_exhibits, ex_consumed = [], set()

        # 5. Pre-extract Margin Glossaries (Odd = Right margin, Even = Left margin)
        # Tables and exhibits already consumed elements so they won't be stolen by margin notes
        glossaries, g_consumed = LayoutDetector.extract_margin_glossaries(
            page_elem, fonts, pw, ph, page_num,
            already_consumed=lo_consumed | map_consumed | tbl_consumed | ex_consumed
        )
        if glossaries:
            for g in glossaries:
                g_item = dict(g)
                g_item['page'] = page_num
                if not any(cg['term'].lower() == g_item['term'].lower() for cg in cls._chapter_glossaries):
                    cls._chapter_glossaries.append(g_item)

        # 6. Pre-extract Vector Figures (e.g. Figure 1.1, Figure 1.2)
        vec_images, vec_consumed = LayoutDetector.extract_vector_figures(page_elem, fonts, pdf_path, page_num, pw, ph)
        if page_images and vec_images:
            for r_img, v_img in zip(page_images, vec_images):
                if v_img.get('caption') and not r_img.get('caption'):
                    r_img['caption'] = v_img['caption']
        else:
            page_images = list(page_images) + vec_images

        # 7. Pre-extract End-of-Chapter Sections (e.g. Pages 16-17; textbooks only)
        eoc_sections, eoc_consumed = LayoutDetector.extract_end_of_chapter_sections(page_elem, fonts, pw, ph, page_num) if not is_journal else ([], set())

        all_consumed = lo_consumed | map_consumed | tbl_consumed | ex_consumed | g_consumed | vec_consumed | eoc_consumed

        # 7. Extract remaining text elements
        raw_lines = []
        for text_el in page_elem.findall('text'):
            if text_el in all_consumed:
                continue

            top = float(text_el.attrib.get('top', '0'))
            left = float(text_el.attrib.get('left', '0'))
            w = float(text_el.attrib.get('width', '0'))
            font_id = text_el.attrib.get('font', '')
            font_info = fonts.get(font_id, {'is_bold': False, 'is_italic': False, 'is_math': False, 'family': '', 'size': 12})

            txt_raw = ''.join(text_el.itertext()).strip()
            # Check running header (top 4% to 11%)
            if cls._is_running_header(top, ph, txt_raw, font_info.get('size', 12)):
                continue
            # Check running footer: drop if pure page number digit or copyright at bottom 6%
            footer_ratio = _STYLE.get("footer_cut_ratio", 0.06)
            if cls._is_running_footer(top, ph, txt_raw, footer_ratio):
                continue

            # Filter rotated or vertical margin watermarks
            if w == 0 and (left < pw * 0.10 or left > pw * 0.90):
                continue

            # Filter unmapped vector font noise strings
            fam_l = font_info.get('family', '').lower()
            if 'heltcom' in fam_l or 'helveticaltcom' in fam_l or 'ltcom' in fam_l:
                continue
            if re.search(r'\b(?:8GTDCN|1RGTCVKQ|5JGKUCIQQF|UCNGURGTUQP|UGNNUOCP|CUUKUVUYKVJ|1DUGTXCVKQPU|6JGQT|TGGCTEJ|&CVCFTKXGP)\b', txt_raw):
                continue
            if re.search(r'This document is copyrighted|intended solely for the personal use|text and data mining|AI training|allied publishers|disseminated broadly|All rights, including for text|American Psychological Association|American Psychological|reserved\.?', txt_raw, re.I):
                continue

            # Convert inner XML tags <b> and <i> to Markdown
            raw_inner = ET.tostring(text_el, encoding='utf-8', method='xml').decode('utf-8')
            m = re.search(r'^<text[^>]*>(.*)</text>$', raw_inner, re.DOTALL)
            inner = m.group(1) if m else ''.join(text_el.itertext())

            inner = re.sub(r'</?a[^>]*>', '', inner)
            inner = re.sub(r'<b>\s*(.*?)\s*</b>', r'**\1**', inner)
            inner = re.sub(r'<i>\s*(.*?)\s*</i>', r'*\1*', inner)

            # Map mathematical font symbols
            if font_info.get('is_math'):
                fam = font_info['family']
                stripped_inner = inner.strip()
                if 'pearsonmathpro07' in fam and stripped_inner == 'a':
                    inner = r'$\sum$'
                elif 'pearsonmathpro02' in fam:
                    if stripped_inner == 'd':
                        inner = r'$\cdot$'
                    elif stripped_inner == 'S':
                        inner = r'$\approx$'
                    elif stripped_inner == '-':
                        inner = '-'
                    elif stripped_inner == '+':
                        inner = '+'
                    elif stripped_inner == '=':
                        inner = '='

            # Normalise bold and italic tags without internal whitespace
            clean_inner = inner.strip()
            if font_info['is_bold'] and not clean_inner.startswith('**'):
                clean_inner = f"**{clean_inner.strip('* ')}**"
            elif font_info['is_italic'] and not clean_inner.startswith('*'):
                clean_inner = f"*{clean_inner.strip('* ')}*"

            w = float(text_el.attrib.get('width', '0'))
            if clean_inner:
                raw_lines.append((top, left, w, font_info['size'], clean_inner))

        if not raw_lines and not map_md and not lo_md and not page_tables and not eoc_sections and not page_exhibits:
            return ""

        # Baseline clustering: cluster text elements within 4.5pt vertically into baseline lines
        raw_lines.sort(key=lambda x: x[0])
        clusters = []
        for item in raw_lines:
            matched_c = None
            for c in clusters:
                c_top = sum(x[0] for x in c) / len(c)
                if abs(c_top - item[0]) <= 5.0:
                    matched_c = c
                    break
            if matched_c is not None:
                matched_c.append(item)
            else:
                clusters.append([item])

        # Merge horizontal line fragments in each baseline cluster
        merged_same_y = []
        for c in clusters:
            c_sorted = sorted(c, key=lambda x: x[1])
            cur_line = []
            for item in c_sorted:
                top_val, left_val, width_val, size_val, txt_val = item
                if not cur_line:
                    cur_line = [top_val, left_val, width_val, size_val, txt_val]
                else:
                    prev_top, prev_left, prev_width, prev_size, prev_txt = cur_line
                    prev_right = prev_left + prev_width
                    gap = left_val - prev_right
                    is_diff_col = (gap > 20) and ((prev_left < pw * 0.48 and left_val >= pw * 0.48) or (gap > 60 and left_val < prev_left))
                    if is_diff_col:
                        merged_same_y.append(tuple(cur_line))
                        cur_line = [top_val, left_val, width_val, size_val, txt_val]
                    else:
                        is_arrow = False
                        if 18 <= gap <= 60:
                            if re.search(r'\b(?:arrows?|relationship as follows|meaning causes|causes?|as in [A-Z])\b', prev_txt, re.I) or \
                               re.search(r'^(?:lung cancer|tissue damage|[B-Z]\b|[B-Z]\))', txt_val, re.I):
                                is_arrow = True
                        separator = r" $\rightarrow$ " if is_arrow else " "
                        new_width = (left_val + width_val) - prev_left
                        new_txt = prev_txt + separator + txt_val
                        cur_line = [min(prev_top, top_val), prev_left, new_width, max(prev_size, size_val), new_txt]
            if cur_line:
                merged_same_y.append(tuple(cur_line))

        # Separate bottom-of-page footnotes after horizontal merging
        lines, footnotes = LayoutDetector.separate_footnotes(merged_same_y, ph)

        gutter_left = pw * 0.42
        gutter_right = pw * 0.58

        classified = []
        for item in lines:
            top, left, width, size, text = item[0], item[1], item[2], item[3], item[4]
            right = left + width
            if left < gutter_left and right > gutter_right and width > pw * 0.48:
                cls_type = 'span'
            elif left < pw * 0.48:
                cls_type = 'left'
            else:
                cls_type = 'right'
            classified.append((top, left, size, text, cls_type))

        left_count = sum(1 for c in classified if c[4] == 'left')
        right_count = sum(1 for c in classified if c[4] == 'right')

        if left_count >= 5 and right_count >= 5:
            # Multi-column page: group spanning elements into bands
            span_intervals = []
            for top, left, size, text, cls_type in classified:
                if cls_type == 'span':
                    span_intervals.append((top, top + size * 1.5))

            merged_spans = []
            for s, e in sorted(span_intervals):
                if not merged_spans or s > merged_spans[-1][1] + 25:
                    merged_spans.append([s, e])
                else:
                    merged_spans[-1][1] = max(merged_spans[-1][1], e)

            boundaries = [0.0]
            for s, e in merged_spans:
                boundaries.append(s - 2)
                boundaries.append(e + 2)
            boundaries.append(ph + 100)

            ordered_lines = []
            for i in range(0, len(boundaries) - 1, 2):
                b_start, b_end = boundaries[i], boundaries[i+1]
                in_band = [c for c in classified if b_start <= c[0] < b_end]
                lefts = [c for c in in_band if c[4] == 'left']
                rights = [c for c in in_band if c[4] == 'right']
                if len(lefts) >= 2 and len(rights) >= 2:
                    ordered_lines.extend([(c[0], c[1], c[2], c[3]) for c in sorted(lefts, key=lambda x: (x[0], x[1]))])
                    ordered_lines.extend([(c[0], c[1], c[2], c[3]) for c in sorted(rights, key=lambda x: (x[0], x[1]))])
                else:
                    ordered_lines.extend([(c[0], c[1], c[2], c[3]) for c in sorted(in_band, key=lambda x: (x[0], x[1]))])

                if i + 1 < len(boundaries) - 1:
                    s_start, s_end = boundaries[i+1], boundaries[i+2]
                    in_span = [c for c in classified if s_start <= c[0] < s_end]
                    ordered_lines.extend([(c[0], c[1], c[2], c[3]) for c in sorted(in_span, key=lambda x: (x[0], x[1]))])
        else:
            ordered_lines = sorted([(l[0], l[1], l[3], l[4]) for l in lines], key=lambda x: (x[0], x[1]))

        # Detect base body size and column-relative base margins
        body_sizes = [l[2] for l in ordered_lines if 11 <= l[2] <= 16]
        body_size = max(set(body_sizes), key=body_sizes.count) if body_sizes else 14.0

        left_col_lefts = [l[1] for l in ordered_lines if l[1] < gutter_left and abs(l[2] - body_size) < 1.0 and len(l[3]) > 30]
        col1_base_left = min(left_col_lefts) if left_col_lefts else 0.0
        base_left = col1_base_left

        right_col_lefts = [l[1] for l in ordered_lines if l[1] >= gutter_left and abs(l[2] - body_size) < 1.0 and len(l[3]) > 30]
        col2_base_left = min(right_col_lefts) if right_col_lefts else 0.0

        blocks = []
        curr_p = []
        curr_p_lefts = []
        last_top = None

        def flush_p():
            nonlocal curr_p, curr_p_lefts
            if curr_p:
                p_text = clean_punctuation_spacing(' '.join(curr_p))
                # True blockquote has ALL lines indented significantly (>= 25pt) from their respective column base (textbooks only)
                is_bq = False
                if not is_journal and curr_p_lefts and len(p_text) > 40:
                    indents = []
                    for l_val in curr_p_lefts:
                        base = col2_base_left if (col2_base_left and l_val >= gutter_left - 20) else col1_base_left
                        indents.append(l_val - base)
                    if all(ind >= 25 for ind in indents):
                        is_bq = True
                if is_bq:
                    p_text = f"> {p_text}"
                blocks.append(p_text)
                curr_p = []
                curr_p_lefts = []



        for top, left, size, text in ordered_lines:
            if is_journal:
                text = re.sub(r'Association or one of its allied publishers\.?', '', text)
                text = re.sub(r'AI training, and similar technologies, are reserved\.?', '', text)
                text = re.sub(r'This article is intended solely for the personal use.*?publisher\.?', '', text)
                text = re.sub(r'ARTICLE IN PRESS\b', '', text)
                text = re.sub(r'American Psychological Association\.?', '', text)
                text = re.sub(r'All rights, including for text and data mining.*', '', text)
                text = APAStatsNormalizer.normalize_text(text)
            clean_t = re.sub(r'[*_]', '', text).strip()
            if not clean_t:
                continue

            # Check if major section heading (size >= 28 or journal academic section heading)
            is_journal_head = is_journal and (
                clean_t in ('Abstract', 'Method', 'Methods', 'Results', 'Discussion', 'References', 'Conclusion', 'Conclusions') or
                bool(re.match(r'^\d+\.\s+[A-Z]', clean_t))
            )
            is_journal_subhead = is_journal and (
                bool(re.match(r'^\d+\.\d+\.?\s+[A-Z]', clean_t)) or
                (clean_t in ('Participants', 'Procedure', 'Data Analysis', 'Measures', 'Apparatus', 'Statistical Analysis'))
            )
            is_h2 = (size >= 28.0 and len(clean_t) < 100) or is_journal_head
            # Check if subsection heading (20 <= size < 28) or Chapter N in Appendix or journal subhead
            is_h3 = ((20.0 <= size < 28.0 and len(clean_t) < 80) or bool(re.match(r'^(?:\*\*)?Chapter\s+\d+(?:\*\*)?$', text.strip(), re.I))) or is_journal_subhead
            # Check if objective heading (1.1 Compare ...) - only for textbooks
            is_obj = not is_journal and bool(re.match(r'^(?:\*\*)?\d+\.\d+(?:\*\*)?(?:\s+|$)', text.strip()))

            # Check if continuation of previous objective banner
            if blocks and re.search(r'[-*>] 🎯', blocks[-1]) and (last_top is not None and top - last_top < 30):
                if not re.search(r'[.?!:]$', blocks[-1].strip()):
                    flush_p()
                    blocks[-1] = blocks[-1] + " " + clean_t
                    last_top = top
                    continue

            # Study Question(s) detection
            m_sq = re.match(r'^(?:\*\*)?(Study Questions?)\s+(\d+[\.\d]*)\s*(?:\*\*)?\s*(.*)', clean_t, re.I)
            if m_sq:
                flush_p()
                sq_label = m_sq.group(1).title()
                sq_num = m_sq.group(2)
                sq_body = m_sq.group(3).strip()
                blocks.append(f"### {sq_label} {sq_num}")
                if sq_body:
                    curr_p.append(sq_body)
                last_top = top
                continue

            if is_h2:
                flush_p()
                if blocks and blocks[-1].startswith('## ') and (top - last_top < 75):
                    if len(blocks[-1]) + len(clean_t) < 80 and not re.search(r'[.?!:]$', blocks[-1]):
                        blocks[-1] = blocks[-1] + " " + clean_t
                    else:
                        blocks.append(f"## {clean_t}")
                else:
                    blocks.append(f"## {clean_t}")
                last_top = top
                continue
            elif is_h3:
                flush_p()
                if blocks and blocks[-1].startswith('### ') and (top - last_top < 45):
                    if len(blocks[-1]) + len(clean_t) < 70 and not re.search(r'[.?!:]$', blocks[-1]):
                        blocks[-1] = blocks[-1] + " " + clean_t
                    else:
                        blocks.append(f"### {clean_t}")
                else:
                    blocks.append(f"### {clean_t}")
                last_top = top
                continue
            elif is_obj:
                flush_p()
                obj_m = re.match(r'^(?:\*\*)?(\d+\.\d+)(?:\*\*)?\s*(.*)', text)
                use_bullets = _STYLE.get("lo_use_bullets", False)
                bullet_prefix = "- " if use_bullets else ""
                if obj_m:
                    o_num = obj_m.group(1)
                    o_title = obj_m.group(2).strip('*_ :')
                    lo_emoji = _STYLE.get("lo_emoji", "🎯")
                    num_fmt = _STYLE.get("lo_number_format", "**{num}**")
                    colon = ":" if _STYLE.get("lo_colon_after_number", False) else ""
                    num_rendered = num_fmt.format(num=o_num)
                    blocks.append(f"{bullet_prefix}{lo_emoji} {num_rendered}{colon} {o_title}".strip())
                else:
                    blocks.append(f"{bullet_prefix}{_STYLE.get('lo_emoji', '🎯')} {clean_t}".strip())
                last_top = top
                continue

            # Table detection
            m_table = re.match(r'^(?:\*\*)?Table\s+(\d+[\.\d]*)\s*(?:\*\*)?\s*:?\s*(.*)', clean_t, re.I)
            if m_table:
                t_num = m_table.group(1)
                t_title = m_table.group(2).strip()
                # A true table title must NOT begin with lowercase (prose continuation like 'because...', 'is...'),
                # and must not be preceded by an incomplete sentence in curr_p (e.g. 'summarized in Table 2.1')
                is_mid_sentence = bool(curr_p and not re.search(r'[.?!:]\s*$', curr_p[-1].strip()))
                starts_lowercase = bool(t_title and t_title[0].islower())
                is_prose_table = is_mid_sentence or starts_lowercase or re.match(
                    r'^(?:shows|reveals|illustrates|demonstrates|depicts|provides|lists|is|was|presents|summarizes|gives|indicates|identifies|describes|contains|displays|outlines|compares|reports|because|that|which|when|if|as)\b',
                    t_title, re.I
                )
                if not is_prose_table:
                    flush_p()
                    t_title = re.sub(r'^\*\*(.+?)\*\*$', r'\1', t_title)   # **Title** → Title
                    t_title = re.sub(r'^\*(.+?)\*$', r'\1', t_title)         # *Title* → Title
                    t_title = t_title.strip()
                    if _STYLE.get("table_heading_style") == "bold-label":
                        tbl_head = f"**Table {t_num}** *{t_title}*".strip() if t_title else f"**Table {t_num}**"
                    else:
                        tbl_head = f"### Table {t_num} {t_title}".strip()
                    blocks.append(tbl_head)
                    last_top = top
                    continue



            # Bullet list item detection
            is_bullet = bool(re.match(r'^[•\-\*]\s+', clean_t))
            if is_bullet:
                flush_p()
                clean_bullet = re.sub(r'^[•\-\*]\s*', '', text).strip()
                curr_p.append(f"- {clean_bullet}")
                last_top = top
                continue

            # Paragraph splitting on indentation or spacing (never split if continuing with lowercase letter)
            is_lowercase = bool(clean_t and clean_t[0].islower())
            cur_base = col2_base_left if (col2_base_left and left >= gutter_left - 20) else col1_base_left
            is_indent = (left - cur_base >= 18) and abs(size - body_size) < 1.5 and not is_lowercase
            # If current line has the same left indentation as previous line (e.g. blockquote), don't split
            if curr_p_lefts and abs(left - curr_p_lefts[-1]) <= 6:
                is_indent = False
            is_gap = last_top is not None and (top - last_top > body_size * 1.5) and not is_lowercase

            if (is_indent or is_gap) and curr_p:
                flush_p()

            # Un-hyphenate with previous line
            if curr_p and curr_p[-1].endswith('-'):
                curr_p[-1] = curr_p[-1][:-1] + text
            else:
                curr_p.append(text)
                curr_p_lefts.append(left)
            last_top = top

        flush_p()

        # Assemble final blocks with pre-extracted elements
        final_blocks = []
        if page_num == 1 and (map_md or lo_md):
            ch_heads = [b for b in blocks if b.startswith('# ') or b.startswith('## ')]
            remaining = [b for b in blocks if b not in ch_heads]
            final_blocks.extend(ch_heads)
            if map_md:
                final_blocks.append(map_md)
            if lo_md:
                final_blocks.append(lo_md)
            final_blocks.extend(remaining)
        else:
            final_blocks.extend(blocks)

        # Place margin glossaries adjacent to their relevant text block (unless configured for chapter_end)
        if glossaries and _STYLE.get("gloss_placement", "inline") != "chapter_end":
            with_glossaries = []
            placed_glossaries = set()
            # 1. Primary pass: match paragraph where term is introduced in bold (**term**)
            for idx, b in enumerate(final_blocks):
                with_glossaries.append(b)
                # Don't place callout after an incomplete sentence at the bottom of the page
                is_mid_sentence = bool(b and not re.search(r'[.?!:"\'\)]\s*$', b.strip()) and not b.strip().startswith('#'))
                if is_mid_sentence and idx == len(final_blocks) - 1:
                    continue
                matched = []
                for g in glossaries:
                    if g['term'] in placed_glossaries:
                        continue
                    t = g['term']
                    bold_pat = re.compile(r'\*\*' + re.escape(t) + r'\*\*', re.I)
                    if bold_pat.search(b):
                        matched.append(g['callout'])
                        placed_glossaries.add(t)
                if matched:
                    for m in matched:
                        with_glossaries.append(m)

            # 2. Secondary pass: match paragraph where term appears as whole word
            second_pass = []
            for idx, b in enumerate(with_glossaries):
                second_pass.append(b)
                is_mid_sentence = bool(b and not re.search(r'[.?!:"\'\)]\s*$', b.strip()) and not b.strip().startswith('#'))
                if is_mid_sentence and idx == len(with_glossaries) - 1:
                    continue
                matched2 = []
                for g in glossaries:
                    if g['term'] in placed_glossaries:
                        continue
                    t = g['term']
                    word_pat = re.compile(r'\b' + re.escape(t) + r'\b', re.I)
                    if word_pat.search(b):
                        matched2.append(g['callout'])
                        placed_glossaries.add(t)
                if matched2:
                    for m in matched2:
                        second_pass.append(m)

            # 3. Fallback: append any remaining glossaries
            remaining = [g['callout'] for g in glossaries if g['term'] not in placed_glossaries]
            for rem in remaining:
                second_pass.append(rem)
            final_blocks = second_pass

        # Insert page tables at their corresponding positions
        if page_tables:
            with_tables = []
            placed_tables = set()
            for b in final_blocks:
                with_tables.append(b)
                for tbl in page_tables:
                    if tbl['top'] in placed_tables:
                        continue
                    m_tbl = re.search(r'\bTable\s+(\d+[\.\d]*)', tbl['markdown'], re.I)
                    if m_tbl:
                        t_ref = f"Table {m_tbl.group(1)}"
                        if t_ref in b and not b.startswith('#'):
                            with_tables.append(tbl['markdown'])
                            placed_tables.add(tbl['top'])
            for tbl in page_tables:
                if tbl['top'] not in placed_tables:
                    if tbl['top'] < 250:
                        # If first block is a lowercase continuation from previous page, keep it at top
                        if with_tables and re.match(r'^[a-z]', with_tables[0].strip()):
                            with_tables.insert(1, tbl['markdown'])
                        else:
                            with_tables.insert(0, tbl['markdown'])
                    else:
                        with_tables.append(tbl['markdown'])
            final_blocks = with_tables

        # Insert page exhibits at their corresponding positions
        if page_exhibits:
            with_exhibits = []
            placed_exhibits = set()
            for b in final_blocks:
                with_exhibits.append(b)
                for ex in page_exhibits:
                    if ex['top'] in placed_exhibits:
                        continue
                    m_ex = re.search(r'\bExhibit\s+(\d+[\.\d]*)', ex['markdown'], re.I)
                    if m_ex:
                        ex_ref = f"Exhibit {m_ex.group(1)}"
                        if ex_ref in b and not b.startswith('#'):
                            with_exhibits.append(ex['markdown'])
                            placed_exhibits.add(ex['top'])
            for ex in page_exhibits:
                if ex['top'] not in placed_exhibits:
                    if ex['top'] < 250:
                        with_exhibits.insert(0, ex['markdown'])
                    else:
                        with_exhibits.append(ex['markdown'])
            final_blocks = with_exhibits

        # Insert end-of-chapter sections
        if eoc_sections:
            final_blocks.extend([s['markdown'] for s in eoc_sections])

        # Format Study Questions / Review Questions as GitHub Alert Callouts
        sq_callout_type = _STYLE.get("study_question_callout", "[!TIP]")
        formatted_sq = []
        sq_idx = 0
        while sq_idx < len(final_blocks):
            b = final_blocks[sq_idx]
            m_sq = re.match(r'^###\s*(Study Questions?\s+[\d\.]+)\s*$', b, re.I)
            if m_sq:
                sq_title = m_sq.group(1).title()
                sq_idx += 1
                sq_parts = []
                while sq_idx < len(final_blocks):
                    nxt = final_blocks[sq_idx]
                    if nxt.startswith(('#', '> [!', '> 🎯', '> 📖', '- 🎯')) or re.match(r'^(?:> 🎯|- 🎯|\*\*?\d+\.\d+)', nxt):
                        break
                    # Strip any existing leading '>' indentation so we never produce nested '> >' blockquotes
                    clean_nxt = '\n'.join(re.sub(r'^[ \t]*>[ \t]?', '', line) for line in nxt.splitlines())
                    sq_parts.append(clean_nxt)
                    sq_idx += 1

                sq_text = '\n\n'.join(sq_parts).strip()
                quoted = [f"> {l}" if l.strip() else ">" for l in sq_text.splitlines()]
                callout = f"> {sq_callout_type} **{sq_title}**\n" + '\n'.join(quoted)
                formatted_sq.append(callout)
            else:
                formatted_sq.append(b)
                sq_idx += 1
        final_blocks = formatted_sq

        # Format sidebars / callout boxes
        final_blocks = LayoutDetector.format_callout_boxes(final_blocks)

        # Group Table headings with their immediately subsequent bullet items for table formatting
        # Match both ### Table heading style and **Table X** bold-label style
        tbl_heading_pat = re.compile(
            r'^(?:###\s*Table\s+\d+|\*\*Table\s+[\d\.]+\*\*)', re.I
        )
        merged_for_tables = []
        i = 0
        while i < len(final_blocks):
            b = final_blocks[i]
            if tbl_heading_pat.match(b):
                tbl_lines = [b]
                i += 1
                while i < len(final_blocks) and re.match(r'^[-*•]\s+', final_blocks[i].strip()):
                    tbl_lines.append(final_blocks[i].strip())
                    i += 1
                merged_for_tables.append('\n'.join(tbl_lines))
            else:
                merged_for_tables.append(b)
                i += 1
        final_blocks = merged_for_tables


        # Format tables
        final_blocks = LayoutDetector.detect_and_format_tables(final_blocks)
        # Format figure & table captions
        final_blocks = LayoutDetector.format_figure_captions(final_blocks)

        # Link in-text footnote references
        if footnotes:
            fn_nums = re.findall(r'\[\^(\d+)\]:', '\n'.join(footnotes))
            for fn_num in fn_nums:
                pat = re.compile(rf'(\b[a-zA-Z0-9\.\,\;\:\?\!]+)\s+{fn_num}\s+([A-Z])')
                for idx, b in enumerate(final_blocks):
                    if not b.startswith(('#', '>', '!')):
                        if pat.search(b):
                            final_blocks[idx] = pat.sub(rf'\1[^{fn_num}] \2', b)
                            break

        # Place genuine images
        remaining_images = list(page_images)
        top_images = [img for img in remaining_images if img.get('top', 9999) < ph * 0.35]
        bottom_images = [img for img in remaining_images if img.get('top', 9999) >= ph * 0.35]

        # Resolve figure caption from surrounding blocks if available (e.g. *Figure 1.1 ...)
        def resolve_caption(img_obj):
            if img_obj.get('caption') and img_obj['caption'] != 'Illustration':
                return img_obj['caption']
            for blk in final_blocks:
                m_fig = re.search(r'^(?:\*|_)?\s*(Figure\s+[\d\.]+.*?)(?:\*|_)?$', blk, re.I | re.M)
                if m_fig:
                    return m_fig.group(1).strip('*_ ')
            return 'Illustration'

        placed_img_blocks = []
        is_lit_or_jrnl = is_journal or _STYLE.get("is_journal") or str(_STYLE.get("archetype", "")).startswith("literature")

        # Prepend top-of-page figures (e.g. Figure 1.1) so they don't split bottom sentences
        for img in top_images:
            img_caption = resolve_caption(img)
            fname = img.get('filename', f"{img.get('page', page_num):03d}_img.{img.get('ext', 'png')}")
            if is_lit_or_jrnl:
                from book_processor.parsers.literature.figure_formatter import FigureFormatter
                placed_img_blocks.append(FigureFormatter.render_figure_html(f"images/{fname}", img_caption))
            else:
                placed_img_blocks.append(f"![{img_caption}](images/{fname})\n\n*{img_caption}*")

        for b in final_blocks:
            placed_img_blocks.append(b)

        for img in bottom_images:
            img_caption = resolve_caption(img)
            fname = img.get('filename', f"{img.get('page', page_num):03d}_img.{img.get('ext', 'png')}")
            if is_lit_or_jrnl:
                from book_processor.parsers.literature.figure_formatter import FigureFormatter
                placed_img_blocks.append(FigureFormatter.render_figure_html(f"images/{fname}", img_caption))
            else:
                placed_img_blocks.append(f"![{img_caption}](images/{fname})\n\n*{img_caption}*")


        # Append extracted footnotes at the bottom of the page
        if footnotes:
            placed_img_blocks.append('\n'.join(footnotes))

        full_md = '\n\n'.join(placed_img_blocks).strip()
        # Detect and format lists
        full_md = LayoutDetector.detect_and_format_lists(full_md)
        # Detect code blocks
        full_md = LayoutDetector.detect_and_format_code_blocks(full_md)
        # Normalise math notation to LaTeX
        result_md = MathLaTeXConverter.process_text(full_md)

        # Collect inline bold terms for chapter-end Flashcard deck (deduped against margin glossaries)
        if _STYLE.get("gloss_placement") == "chapter_end" and _STYLE.get("collect_inline_bold", False):
            cls.collect_inline_bold_terms(result_md, page_num)

        page_elem.clear()
        return result_md



