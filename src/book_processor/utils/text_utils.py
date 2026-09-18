"""
Text Processing Utilities
=========================
"""

import re
from typing import Optional
from book_processor.config import MAX_FILENAME_LEN


def sanitize_filename(name: str, max_len: int = MAX_FILENAME_LEN) -> str:
    """Sanitize string to be safe for filenames across OS platforms."""
    if not name:
        return "untitled"
    name = re.sub(r'[/\\\\:*?\"<>|]', ' - ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.rstrip('. ')
    if len(name) > max_len:
        name = name[:max_len].rstrip('. ')
    return name or 'untitled'


def repair_hyphens(text: str) -> str:
    """Re-flows line-wrapped words broken by a hyphen (e.g., 'coun-\\n seling' -> 'counseling')."""
    if not text:
        return ""
    return re.sub(r'([a-zA-Z]+)-\s*\n\s*([a-zA-Z]+)', r'\1\2', text)


def stitch_cross_page_continuity(text: str) -> str:
    """
    Re-flows text across page boundaries (<!-- Page N --> comments) so sentences
    are not artificially split into broken paragraphs:

    1. Joins words hyphenated across page boundaries:
       e.g. 'develop-\\n\\n<!-- Page 2 -->\\n\\nment' -> '<!-- Page 2 -->\\ndevelopment'
    2. Joins sentences spanning across page boundaries:
       When the text before <!-- Page N --> ends without terminal punctuation
       and the text after starts with a lowercase continuation, repositions the
       comment or joins the text with a single line break so CommonMark renders
       them as part of the exact same paragraph.
    """
    if not text:
        return ""

    # 1. Hyphenated word split across page comment
    # Pattern: word- \n+ <!-- Page N --> \n+ lowercase_suffix
    def _join_hyphen_across_page(m):
        prefix = m.group(1)
        page_tag = m.group(2)
        suffix = m.group(3)
        return f"{page_tag}\n{prefix}{suffix}"

    text = re.sub(
        r'([a-zA-Z]+)-\s*\n+\s*(<!--\s*Page\s+\d+\s*-->)\s*\n+\s*([a-z]+)',
        _join_hyphen_across_page,
        text,
    )

    # 2. Incomplete sentence with intervening callouts, tables, lists, or footnotes
    # Pattern: [incomplete text] \n\n (callouts/tables/lists/footnotes) \n\n (<!-- Page N -->) \n+ (continuation)
    def _join_sentence_with_intervening(m):
        p1 = m.group('p1').rstrip()
        intervening = m.group('intervening').strip()
        page_tag = m.group('page').strip()
        p2 = m.group('p2').strip()
        if p1.endswith('|') or p1.startswith('|'):
            return m.group(0)
        return f"{p1} {p2}\n\n{page_tag}\n\n{intervening}"

    text = re.sub(
        r'(?P<p1>[^\n#`>|\*\-][^\n]*?[^.\?!:;\n#`>|\*\-|])\n{2,}'
        r'(?P<intervening>(?:(?:\*\*|#|>|\[\^|[-*•]|<table|\|)[^\n]*\n|[ \t]*\n)+)'
        r'\s*(?P<page><!--\s*Page\s+\d+\s*-->)\s*\n+(?P<p2>[a-z](?:[^\n]|\n(?!\n))*)',
        _join_sentence_with_intervening,
        text,
    )

    # 3. Direct sentence continuation across page comment (no intervening callouts)
    # Pattern: [word with no terminal punct] \n\n <!-- Page N --> \n+ [lowercase letter]
    def _join_direct_sentence(m):
        preceding_text = m.group(1).rstrip()
        page_tag = m.group(2).strip()
        following_char = m.group(3)
        # Avoid joining if preceding line was a heading, list item, code fence, or table row
        last_line = preceding_text.splitlines()[-1].strip() if preceding_text else ""
        if last_line.startswith(('#', '-', '*', '`', '>', '|', '!')) or last_line.endswith('|'):
            return m.group(0)  # leave intact
        # Place page_tag right after preceding_text with single newline (same paragraph in markdown)
        return f"{preceding_text} <!-- {page_tag[4:-3].strip()} -->\n{following_char}"

    text = re.sub(
        r'([^.\?!:;\n#`>|\*\-][^\n]*?[^.\?!:;\n#`>|\*\-|])\n{2,}\s*(<!--\s*Page\s+\d+\s*-->)\s*\n+([a-z])',
        _join_direct_sentence,
        text,
    )

    # 4. Cleanup orphaned dual-newlines around remaining mid-paragraph page tags
    text = re.sub(r'([a-zA-Z,])\s*\n{2,}(<!--\s*Page\s+\d+\s*-->)\s*\n{2,}([a-z])', r'\1 \2 \3', text)

    return text




LIGATURE_MAP = {
    '\ufb00': 'ff',
    '\ufb01': 'fi',
    '\ufb02': 'fl',
    '\ufb03': 'ffi',
    '\ufb04': 'ffl',
    '\ufb05': 'ft',
    '\ufb06': 'st',
    'æ': 'ae',
    'Æ': 'AE',
    'œ': 'oe',
    'Œ': 'OE',
}


def normalize_ligatures(text: str) -> str:
    """
    Unpacks PDF typographic ligatures (fi, fl, ffi, ffl, etc.) into constituent characters.
    Prevents OCR and vocabulary check degradation caused by font ligature collapsing.
    """
    if not text:
        return ""
    for lig, replacement in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, replacement)
    return text


def clean_typography_artifacts(text: str) -> str:
    """
    Normalizes common PDF extraction typographical quirks:
    - Smart quotes and dashes (---, -- -> —)
    - Orphaned page-margin artifacts (e.g. solitary '|' or '¦')
    - Font ligatures
    """
    if not text:
        return ""
    text = normalize_ligatures(text)
    # Standardize dashes
    text = re.sub(r'---', '—', text)
    text = re.sub(r'--', '—', text)
    # Standardize OCR broken bullet glyphs (e.g. =», =s, = )
    text = re.sub(r'(?m)^[ \t]*=[»s]\s*', '- ', text)
    text = re.sub(r'(?m)^[ \t]*=\s+([A-Z])', r'- \1', text)
    # Remove standalone border ticks often left by table or sidebar borders
    text = re.sub(r'(?m)^[|¦·]\s*$', '', text)
    return text



def clean_punctuation_spacing(text: str) -> str:
    """Fixes punctuation spacing artifacts, un-collapses ligatures, and cleans typography."""
    if not text:
        return ""
    text = clean_typography_artifacts(text)
    text = re.sub(r'\s+([,.:;?!])', r'\1', text)
    # Fix trailing page-number colons at end-of-line (e.g. '166:' → '166')
    # Only strip colon when the digit is the very last token on the line (i.e. a running footer artifact)
    text = re.sub(r'(?m)^(\d+)\s*:\s*$', r'\1', text)
    return text


def clean_page_text_artifacts(raw: str, page_num: Optional[int] = None) -> str:
    """
    Strips publisher copyright disclaimers, top running headers, and bottom running footers
    from raw text pages (e.g. extracted via pdftotext) so paragraphs flow cleanly.
    """
    if not raw:
        return ""
    lines = raw.splitlines()
    filtered = []
    for l in lines:
        stripped = l.strip()
        if re.search(r'Copyright\s+\d{4}', stripped, re.I) or 'May not be copied' in stripped or 'WCN 02-200' in stripped:
            continue
        filtered.append(l)

    non_empty_indices = [i for i, l in enumerate(filtered) if l.strip()]
    top_to_remove = set()
    for idx in non_empty_indices[:4]:
        line = filtered[idx].strip()
        if re.fullmatch(r'\d+', line):
            top_to_remove.add(idx)
        elif re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.I):
            top_to_remove.add(idx)
        elif re.fullmatch(r'\d+\s+(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.I):
            top_to_remove.add(idx)
        elif re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?\s+\d+', line, re.I):
            top_to_remove.add(idx)
        elif re.fullmatch(r'[A-Z\s,:\'\-]{3,50}\s+\d+', line) or re.fullmatch(r'\d+\s+[A-Z\s,:\'\-]{3,50}', line):
            top_to_remove.add(idx)
        elif line.isupper() and len(line) < 40 and not line.endswith(('.', ':', ';')):
            top_to_remove.add(idx)
        elif re.match(r'^[\'\"]?\s*CHAP\.?\s*ER', line, re.I):
            top_to_remove.add(idx)
        else:
            break

    bottom_to_remove = set()
    for idx in reversed(non_empty_indices[-4:]):
        line = filtered[idx].strip()
        if re.fullmatch(r'\d+', line):
            bottom_to_remove.add(idx)
        elif re.fullmatch(r'\d+\s*/\s*[A-Z\s:]+', line) or re.fullmatch(r'[A-Z\s:]+\s*/\s*\d+', line):
            bottom_to_remove.add(idx)
        elif re.search(r'(?:CHAPTER|PART)\s+.*?\s*/\s*\d+', line, re.I) or re.search(r'\d+\s*/\s*(?:CHAPTER|PART)', line, re.I):
            bottom_to_remove.add(idx)
        elif re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.I):
            bottom_to_remove.add(idx)
        else:
            break

    result_lines = [l for i, l in enumerate(filtered) if i not in top_to_remove and i not in bottom_to_remove]
    return '\n'.join(result_lines).strip()




def format_chapter_title(title: str) -> str:
    """Standardizes chapter titles into 'Ch01 Title' format."""
    if not title:
        return "untitled"
    m = re.search(r'^(?:Chapter\s+)?(\d+)[\.\s:\-]+(.*)', title, re.I)
    if m:
        ch_num = int(m.group(1))
        rest = sanitize_filename(m.group(2).strip())
        return f"Ch{ch_num:02d} {rest}".strip()
    return sanitize_filename(title)


def format_appendix_title(title: str) -> str:
    """Standardizes appendix titles into 'Appendix A Title' format."""
    if not title:
        return "Appendix"
    clean = title.strip()
    if clean.lower() == 'appendix':
        return "Appendix"
    m = re.search(r'^Appendix\s+([A-Z])[\.\s:\-]+(.*)', clean, re.I)
    if not m:
        m = re.search(r'^([A-Z])[\.\s:\-]+(.*)', clean)
    if m:
        letter = m.group(1)
        rest = sanitize_filename(m.group(2).strip())
        if 'solution' in rest.lower():
            return f"Appendix {letter} Solutions"
        elif rest and rest.lower() != 'untitled':
            return f"Appendix {letter} {rest}".strip()
        return f"Appendix {letter}"
    cleaned_rest = re.sub(r'^Appendix\s*', '', clean, flags=re.I).strip()
    if not cleaned_rest:
        return "Appendix"
    return f"Appendix {sanitize_filename(cleaned_rest)}".strip()
