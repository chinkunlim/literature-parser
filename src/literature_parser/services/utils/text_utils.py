"""
Text Processing Utilities
=========================
"""

import re
from typing import Optional

from literature_parser.config.processor_config import MAX_FILENAME_LEN


def sanitize_filename(name: str, max_len: int = MAX_FILENAME_LEN) -> str:
    """Sanitize string to be safe for filenames and folder names across OS platforms.

    Replaces illegal filesystem characters, slashes, whitespace, and underscores with hyphens.
    Collapses multiple hyphens and trims leading/trailing hyphens and periods.

    Args:
        name: Raw filename or folder title string.
        max_len: Maximum length limit for the sanitized string.

    Returns:
        Hyphen-delimited, clean filename/folder name, or 'untitled' if empty.
    """
    if not name:
        return "untitled"
    # Replace illegal filesystem characters, slashes, commas, and punctuation with hyphens
    name = re.sub(r'[/\\\\:*?\"<>|_,;&]+', '-', name)
    # Replace all whitespace sequences with hyphens
    name = re.sub(r'\s+', '-', name)
    # Collapse multiple hyphens into a single hyphen
    name = re.sub(r'-+', '-', name).strip('-')
    name = name.rstrip('. ')
    if len(name) > max_len:
        name = name[:max_len].rstrip('- ')
    return name or 'untitled'


def repair_hyphens(text: str) -> str:
    """Re-flows line-wrapped words broken by a hyphen (e.g., 'coun-\\n seling' -> 'counseling')."""
    if not text:
        return ""
    return re.sub(r'([a-zA-Z]+)-\s*\n\s*([a-zA-Z]+)', r'\1\2', text)


def repair_drop_caps(text: str) -> str:
    """
    Repairs dropped or orphaned initial drop-caps:
    1. Standalone single uppercase letter on its own line preceding lowercase word
       (e.g., 'Y\\n\\nou are' -> 'You are')
    2. Common dropped initial letters at start of paragraphs:
       (e.g., 'ou are' -> 'You are', 'he first' -> 'The first')
    """
    if not text:
        return ""

    # 1. Orphaned single capital letter on its own line
    text = re.sub(r'(?m)^([A-Z])\s*\n\s*([a-z]{2,}\b)', r'\1\2', text)

    # 2. Known dropped leading letters at paragraph start
    DROP_CAP_MAP = {
        'ou': 'You',
        'n': 'In',
        'he': 'The',
        'his': 'This',
        'hen': 'When',
        'e': 'We',
        't': 'It',
        'f': 'If',
        's': 'As',
        'any': 'Many',
        'ne': 'One',
        'fter': 'After',
        'efore': 'Before',
    }

    def _replace_drop_cap(m):
        prefix = m.group(1)
        word = m.group(2)
        rest = m.group(3)
        repl = DROP_CAP_MAP.get(word.lower())
        if repl:
            return f"{prefix}{repl}{rest}"
        return m.group(0)

    # Only match at start of string or after double newline (start of paragraph)
    text = re.sub(
        r'(^|\n\n)([a-z]+)(\s+[a-z]{2,})',
        _replace_drop_cap,
        text
    )
    return text


def clean_decorative_noise(text: str) -> str:
    """
    Cleans decorative artifacts, dingbat font glitches, and stray running elements:
    - '@ EXAMPLES' or 'm@ EXAMPLES' -> '### Examples'
    - 'm@' / '@' dingbats -> clean bullets
    - Stray 'Continued' or 'Table X Continued'
    - Lone Roman numerals
    """
    if not text:
        return ""

    # Dingbats in Book 2 (Group Counseling)
    text = re.sub(r'(?m)^[ \t]*m?@\s*EXAMPLES?\s*$', '### Examples', text, flags=re.IGNORECASE)
    text = re.sub(r'(?m)^[ \t]*m?@\s*ACTIVITIES\s*$', '### Activities', text, flags=re.IGNORECASE)
    text = re.sub(r'(?m)^[ \t]*m?@\s*([A-Z\s]{3,30})$', r'### \1', text)
    text = re.sub(r'(?m)^[ \t]*m?@\s*', '- ', text)

    # Stray '(Continued)' or 'Table X.X Continued'
    text = re.sub(
        r'(?m)^[ \t]*(?:\(?Continued\)?|Table\s+\d+(?:\.\d+)?\s+Continued|Figure\s+\d+(?:\.\d+)?\s+Continued)\s*$',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Isolated decorative Roman numerals (e.g. solitary 'I', 'II', 'IV' on a line surrounded by empty lines)
    text = re.sub(r'(?m)(?<=\n\n)[ \t]*(?:I|II|III|IV|V|VI|VII|VIII|IX|X)[ \t]*(?=\n\n)', '', text)

    return text


def format_dialogue_lines(text: str) -> str:
    """
    Formats counseling and interview dialogues:
    Lines starting with 'SPEAKER: ...' are formatted as '**SPEAKER:** ...'
    """
    if not text:
        return ""
    # Matches common speakers like LEADER:, COUNSELOR:, CLIENT:, JERRY:, BOBBI:, etc.
    return re.sub(
        r'(?m)^([A-Z][a-zA-Z\s]{1,15}):\s+',
        r'**\1:** ',
        text
    )


def detect_plain_text_headings(raw_text: str) -> str:
    """
    Detects section and subsection headings in raw pdftotext -layout text where
    XML font tags are missing (e.g. GlyphLessFont fallback).
    Converts detected headings to '## ' or '### ' Markdown headers.
    """
    if not raw_text:
        return ""

    lines = raw_text.splitlines()
    new_lines = []

    trailing_prepositions = {
        'for', 'of', 'to', 'in', 'the', 'and', 'with', 'at', 'from', 'by',
        'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between',
        'out', 'against', 'during', 'without', 'before', 'under', 'around', 'among'
    }

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue

        indent = len(line) - len(line.lstrip(' '))
        prev_empty = (i == 0 or not lines[i-1].strip())
        next_empty = (i == len(lines)-1 or not lines[i+1].strip())

        # Check if already a Markdown heading
        if stripped.startswith('#'):
            new_lines.append(stripped)
            continue

        # Handle dingbat headings directly
        if re.match(r'^m?@\s*EXAMPLES?\s*$', stripped, re.IGNORECASE):
            new_lines.append('### Examples')
            continue
        if re.match(r'^[A-Z]?\s*ACTIVITIES\s*$', stripped, re.IGNORECASE):
            new_lines.append('### Activities')
            continue

        is_heading = False
        level = 2

        # Filter out common non-heading patterns
        if (
            3 <= len(stripped) <= 65
            and not re.match(r'^(?:CHAPTER|PART|\d+|http|www|page|\[|\(|-|\*|•|=»|=)', stripped, re.IGNORECASE)
            and (not stripped.endswith(('.', ',', ';', ':')) or stripped.endswith('?'))
            and stripped.split()[-1].lower() not in trailing_prepositions
            and re.match(r'^[A-Z]', stripped)
        ):
            # Condition A: Indented/centered line preceded by a blank line
            if prev_empty and 8 <= indent <= 45:
                is_heading = True
                level = 2 if indent <= 24 else 3
            # Condition B: Short title-cased or upper-cased line surrounded by blank lines
            elif prev_empty and next_empty:
                words = stripped.split()
                # Title case or All-caps
                capitalized_words = [w for w in words if w[0].isupper()]
                if len(capitalized_words) >= max(1, len(words) // 2):
                    is_heading = True
                    level = 2

        if is_heading:
            # Clean internal excessive spacing caused by layout formatting
            clean_title = re.sub(r'[ \t]{2,}', ' ', stripped)
            if new_lines and new_lines[-1].strip():
                new_lines.append('')
            new_lines.append(f"{'#' * level} {clean_title}")
            new_lines.append('')
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)



def reflow_wrapped_lines(text: str) -> str:
    """
    Recombines prose lines broken by hard column wrapping (~70-80 chars) into
    natural Markdown paragraphs while preserving headings, lists, tables,
    blockquotes, code fences, and HTML tags.
    """
    if not text:
        return ""

    paragraphs = re.split(r'\n\s*\n', text)
    reflowed_paragraphs = []

    for para in paragraphs:
        lines = para.splitlines()
        if not lines:
            continue

        # If entire block is a code fence, table, or HTML tag, preserve as-is
        stripped_first = lines[0].strip()
        if stripped_first.startswith(('```', '|', '<table', '<div', '<details', '<summary', '<style', '<!--')):
            reflowed_paragraphs.append('\n'.join(lines))
            continue

        # If block is dialogue
        if any(re.match(r'^\s*\*{0,2}[A-Z][a-zA-Z\s]{1,15}:', l) for l in lines):
            dialogue_lines = []
            for l in lines:
                l_str = l.strip()
                if re.match(r'^\s*(?:\*\*)?[A-Z][a-zA-Z\s]{1,15}:', l_str):
                    dialogue_lines.append(l_str)
                elif dialogue_lines:
                    dialogue_lines[-1] += ' ' + l_str
                else:
                    dialogue_lines.append(l_str)
            reflowed_paragraphs.append('\n'.join(dialogue_lines))
            continue

        cur_para = []
        in_list = False
        for l in lines:
            s = l.strip()
            if not s:
                continue

            # Heading encountered: isolate immediately
            if s.startswith('#'):
                if cur_para:
                    reflowed_paragraphs.append('\n'.join(cur_para))
                    cur_para = []
                reflowed_paragraphs.append(s)
                in_list = False
                continue

            # List bullet item encountered
            is_bullet = bool(re.match(r'^(?:[-*+•=»]|\d+\.|\([a-z0-9]+\))\s+', s))
            if is_bullet:
                if cur_para and not in_list:
                    reflowed_paragraphs.append('\n'.join(cur_para))
                    cur_para = []
                clean_bullet = re.sub(r'^(?:=[»s]?|»)\s*', '- ', s)
                cur_para.append(clean_bullet)
                in_list = True
            elif in_list:
                # If previous bullet ended with punctuation (. ? ! ;) and current line starts with capital letter,
                # transition cleanly to next body paragraph
                if cur_para and cur_para[-1].rstrip().endswith(('.', '?', '!', ';')) and re.match(r'^[A-Z]', s):
                    reflowed_paragraphs.append('\n'.join(cur_para))
                    cur_para = [s]
                    in_list = False
                else:
                    cur_para[-1] += ' ' + s
            else:
                # Regular prose paragraph: reflow lines
                if not cur_para:
                    cur_para.append(s)
                else:
                    last_line = cur_para[-1]
                    if last_line.endswith('-') and re.match(r'^[a-z]', s):
                        cur_para[-1] = last_line[:-1] + s
                    else:
                        cur_para[-1] = last_line + ' ' + s

        if cur_para:
            reflowed_paragraphs.append('\n'.join(cur_para))

    return '\n\n'.join(reflowed_paragraphs)



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

    # Strip standalone page numbers immediately before or after page comment
    text = re.sub(r'(?m)^\s*\d{1,4}\s*\n+(?=<!--\s*Page\s+\d+\s*-->)', '', text)
    text = re.sub(r'(<!--\s*Page\s+\d+\s*-->)\s*\n+\s*\d{1,4}\s*(?:\n|$)', r'\1\n\n', text)

    # 1. Hyphenated word split across page comment
    # Pattern: word- \n+ <!-- Page N --> \n+ lowercase_suffix
    compound_suffixes = {'based', 'related', 'seeking', 'taking', 'report', 'reported', 'level', 'scale', 'matched', 'order', 'wide'}
    def _join_hyphen_across_page(m):
        prefix = m.group(1)
        page_tag = m.group(2)
        suffix = m.group(3)
        if suffix.lower() in compound_suffixes:
            return f"{page_tag}\n{prefix}-{suffix}"
        return f"{page_tag}\n{prefix}{suffix}"

    text = re.sub(
        r'([a-zA-Z]+)-\s*(?:\n+\s*\d{1,4}\s*)?\n+\s*(<!--\s*Page\s+\d+\s*-->)\s*(?:\n+\s*\d{1,4}\s*)?\n+\s*([a-z]+)',
        _join_hyphen_across_page,
        text,
    )

    # 2. Incomplete sentence with intervening callouts, tables, lists, or footnotes
    # Pattern: [incomplete text line] \n\n (callouts/tables/lists/footnotes) \n\n (<!-- Page N -->) \n+ (continuation)
    def _join_sentence_with_intervening(m):
        p1 = m.group('p1').rstrip()
        intervening = m.group('intervening').strip()
        page_tag = m.group('page').strip()
        p2 = m.group('p2').strip()
        if p1.endswith('|') or p1.startswith('|') or p1.startswith(('#', '-', '*', '>', '`', '!')):
            return m.group(0)
        return f"{p1} {p2}\n\n{page_tag}\n\n{intervening}"

    text = re.sub(
        r'(?m)^(?P<p1>(?!(?:[#>`|!]|[-*+][ \t]+))[^\n]+[^.\?!:;\n#`>|\*\-|])\n{2,}'
        r'(?P<intervening>(?:(?:\*\*|#|>|\[\^|[-*•]|<table|\|)[^\n]*\n|[ \t]*\n)+)'
        r'\s*(?P<page><!--\s*Page\s+\d+\s*-->)\s*\n+(?P<p2>[a-z](?:[^\n]|\n(?!\n))*)',
        _join_sentence_with_intervening,
        text,
    )

    # 3. Direct sentence continuation across page comment (no intervening callouts)
    # Pattern: [line with no terminal punct] \n\n <!-- Page N --> \n+ [lowercase letter]
    def _join_direct_sentence(m):
        preceding_text = m.group(1).rstrip()
        page_tag = m.group(2).strip()
        following_char = m.group(3)
        # Avoid joining if preceding line was a heading, list item, code fence, or table row
        last_line = preceding_text.splitlines()[-1].strip() if preceding_text else ""
        if (
            last_line.startswith(('#', '`', '>', '|', '!'))
            or re.match(r'^[-*+][ \t]+', last_line)
            or last_line.endswith('|')
        ):
            return m.group(0)  # leave intact
        return f"{preceding_text} <!-- {page_tag[4:-3].strip()} -->\n{following_char}"

    text = re.sub(
        r'(?m)^((?!(?:[#>`|!]|[-*+][ \t]+))[^\n]+[^.\?!:;\n#`>|\*\-|])\n{2,}\s*(<!--\s*Page\s+\d+\s*-->)\s*\n+([a-z])',
        _join_direct_sentence,
        text,
    )

    # 4. Cleanup orphaned dual-newlines around remaining mid-paragraph page tags (excluding headings)
    text = re.sub(r'(?m)^((?!(?:[#>`|!]|[-*+][ \t]+))[^\n]*[a-zA-Z,])\s*\n{2,}(<!--\s*Page\s+\d+\s*-->)\s*\n{2,}([a-z])', r'\1 \2 \3', text)

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
    text = clean_decorative_noise(text)
    # Standardize dashes
    text = re.sub(r'---', '—', text)
    text = re.sub(r'--', '—', text)
    # Standardize OCR broken bullet glyphs (e.g. =», =s, », •)
    text = re.sub(r'(?m)^[ \t]*(?:=[»s]|»)\s*', '- ', text)
    text = re.sub(r'(?m)^[ \t]*=\s+([A-Z])', r'- \1', text)
    # Remove standalone border ticks often left by table or sidebar borders
    text = re.sub(r'(?m)^[|¦·]\s*$', '', text)
    # Remove vector chart coordinate axis tick leaks (e.g. '5 2 5 2 5 2' or '2 2 2 2 1 1 1 1')
    text = re.sub(r'(?m)^[ \t]*(?:\d{1,3}[ \t]+){2,}\d{1,3}[ \t]*$', '', text)
    text = re.sub(r'(?m)\b(?:\d{1,2}[ \t]+){2,}\d{1,2}[ \t]+(?=[a-z]{3,}\b)', '', text)
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
        if re.search(r'Copyright\s+\d{4}', stripped, re.IGNORECASE) or 'May not be copied' in stripped or 'WCN 02-200' in stripped:
            continue
        filtered.append(l)

    non_empty_indices = [i for i, l in enumerate(filtered) if l.strip()]
    top_to_remove = set()
    for idx in non_empty_indices[:4]:
        line = filtered[idx].strip()
        if re.fullmatch(r'\d+', line) or re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.IGNORECASE) or re.fullmatch(r'\d+\s+(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.IGNORECASE) or re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?\s+\d+', line, re.IGNORECASE) or re.fullmatch(r'[A-Z\s,:\'\-]{3,50}\s+\d+', line) or re.fullmatch(r'\d+\s+[A-Z\s,:\'\-]{3,50}', line) or line.isupper() and len(line) < 40 and not line.endswith(('.', ':', ';')) or re.match(r'^[\'\"]?\s*CHAP\.?\s*ER', line, re.IGNORECASE):
            top_to_remove.add(idx)
        else:
            break

    bottom_to_remove = set()
    for idx in reversed(non_empty_indices[-4:]):
        line = filtered[idx].strip()
        if re.fullmatch(r'\d+', line) or re.fullmatch(r'\d+\s*/\s*[A-Z\s:]+', line) or re.fullmatch(r'[A-Z\s:]+\s*/\s*\d+', line) or re.search(r'(?:CHAPTER|PART)\s+.*?\s*/\s*\d+', line, re.IGNORECASE) or re.search(r'\d+\s*/\s*(?:CHAPTER|PART)', line, re.IGNORECASE) or re.fullmatch(r'(?:CHAPTER|PART)\s*(?:\d+|[A-Z]+)?', line, re.IGNORECASE):
            bottom_to_remove.add(idx)
        else:
            break

    result_lines = [l for i, l in enumerate(filtered) if i not in top_to_remove and i not in bottom_to_remove]
    return '\n'.join(result_lines).strip()




def format_chapter_title(title: str) -> str:
    """Standardizes chapter titles into 'Ch01-Title' format.

    Args:
        title: Raw chapter title string from outline or text.

    Returns:
        Standardized chapter title string with hyphen-separated components.
    """
    if not title:
        return "untitled"
    m = re.search(r'^(?:Chapter\s+)?(\d+)[\.\s:\-]+(.*)', title, re.IGNORECASE)
    if m:
        ch_num = int(m.group(1))
        rest = sanitize_filename(m.group(2).strip())
        return f"Ch{ch_num:02d}-{rest}".strip('-') if rest and rest != "untitled" else f"Ch{ch_num:02d}"
    return sanitize_filename(title)


def format_appendix_title(title: str) -> str:
    """Standardizes appendix titles into 'Appendix-A-Title' format.

    Args:
        title: Raw appendix title string from outline or text.

    Returns:
        Standardized appendix title string with hyphen-separated components.
    """
    if not title:
        return "Appendix"
    clean = title.strip()
    if clean.lower() == 'appendix':
        return "Appendix"
    m = re.search(r'^Appendix\s+([A-Z])[\.\s:\-]+(.*)', clean, re.IGNORECASE)
    if not m:
        m = re.search(r'^([A-Z])[\.\s:\-]+(.*)', clean)
    if m:
        letter = m.group(1)
        rest = sanitize_filename(m.group(2).strip())
        if 'solution' in rest.lower():
            return f"Appendix-{letter}-Solutions"
        elif rest and rest.lower() != 'untitled':
            return f"Appendix-{letter}-{rest}".strip('-')
        return f"Appendix-{letter}"
    cleaned_rest = re.sub(r'^Appendix\s*', '', clean, flags=re.IGNORECASE).strip()
    if not cleaned_rest:
        return "Appendix"
    return f"Appendix-{sanitize_filename(cleaned_rest)}".strip('-')
