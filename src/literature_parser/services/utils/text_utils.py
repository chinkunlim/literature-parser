"""
Text Processing Utilities
=========================
"""

from pathlib import Path
import re
from typing import List, Optional, Tuple

from literature_parser.config.processor_config import MAX_FILENAME_LEN


def sanitize_filename(name: str, max_len: int = MAX_FILENAME_LEN) -> str:
    """Sanitize string to be safe for filenames and folder names across OS platforms.

    Replaces illegal filesystem characters, slashes, whitespace, and underscores with hyphens.
    Collapses multiple hyphens and trims leading/trailing hyphens and periods.
    Enforces a strict character and UTF-8 byte ceiling (<= 120 chars / <= 200 bytes)
    to prevent macOS/Linux Errno 63 (File name too long) crashes on verbose bookmarks.

    Args:
        name: Raw filename or folder title string.
        max_len: Maximum length limit for the sanitized string.

    Returns:
        Hyphen-delimited, clean filename/folder name, or 'untitled' if empty.
    """
    if not name:
        return "untitled"
    # Strip non-printable control characters including null bytes
    name = re.sub(r'[\x00-\x1f\x7f]+', '', name)
    # Replace illegal filesystem characters, slashes, commas, and punctuation with hyphens
    name = re.sub(r'[/\\\\:*?\"<>|_,;&]+', '-', name)
    # Replace all whitespace sequences with hyphens
    name = re.sub(r'\s+', '-', name)
    # Collapse multiple hyphens into a single hyphen
    name = re.sub(r'-+', '-', name).strip('-')
    name = name.rstrip('. ')
    effective_max = min(max_len, 120)
    if len(name) > effective_max:
        cut = name[:effective_max]
        if '-' in cut[effective_max // 2:]:
            cut = cut.rsplit('-', 1)[0]
        name = cut.rstrip('- ')
    while len(name.encode('utf-8')) > 200 and len(name) > 10:
        name = name[:-5].rstrip('- ')
    return name or 'untitled'


def repair_hyphens(text: str) -> str:
    """Re-flows line-wrapped words broken by an ASCII or soft hyphen (U+00AD).

    Args:
        text: Input string potentially containing line-wrapped hyphenated words.

    Returns:
        String with line-broken hyphenated words rejoined and soft hyphens removed.
    """
    if not text:
        return ""
    # Preserve explicit compound hyphen when followed by soft hyphen at line wrap (e.g. 'brain-\xad\nimaging' -> 'brain-imaging')
    text = re.sub(r'([a-zA-Z]+)-\xad[ \t]*\n[ \t]*([a-zA-Z]+)', r'\1-\2', text)
    # Rejoin across page comments: e.g. 'experi-\n<!-- Page 24 -->\nmental' -> 'experimental'
    text = re.sub(r'([a-zA-Z]{2,})[-\xad][ \t]*\n*(?:<![—–-]+\s*Page\s+\d+\s*[—–-]+>\s*\n*)+[ \t]*([a-zA-Z]{2,})', r'\1\2', text)
    # Rejoin standard or soft-hyphen line wraps (Refs: ISSUE-017)
    text = re.sub(r'([a-zA-Z]+)[-\xad][ \t]*\n[ \t]*([a-zA-Z]+)', r'\1\2', text)
    # Rejoin space-separated soft hyphens before standard linguistic suffixes (e.g. 'valu- able', 'educa- tion', 'sec- tion')
    text = re.sub(
        r'\b([a-zA-Z]{3,})[-\xad]\s+(tion|tions|tive|tively|ment|ments|able|ably|ing|ed|ly|ity|ities|ism|al|ally|ic|ical|ically|ness|less|ance|ence|ant|ent|sion|sions|ous|ious|ize|ised|izing|ized|graphic|graphical)\b',
        r'\1\2',
        text,
        flags=re.IGNORECASE,
    )
    return text.replace('\xad', '')


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


def clean_shadow_duplicates(text: str) -> str:
    """Deduplicates repeated words or lines caused by PDF drop-shadow layers and repairs broken capitals.

    Drop-shadow layers in PDF vector art place duplicate identical text elements offset by fractions
    of a point, which results in doubled words like 'CAREER CAREER COUNSELING COUNSELING' or
    doubled lines.

    Args:
        text: The input text containing potential drop-shadow duplicates.

    Returns:
        The cleaned text with duplicated tokens and lines deduplicated.
    """
    if not text:
        return ""

    # 1. Line-level deduplication: consecutive identical non-empty lines (excluding HTML tags)
    lines = text.split("\n")
    deduped_lines: list[str] = []
    for line in lines:
        s_line = line.strip()
        if deduped_lines and s_line and not s_line.startswith("<") and s_line == deduped_lines[-1].strip():
            continue
        deduped_lines.append(line)
    text = "\n".join(deduped_lines)

    # 2. Phrase-level deduplication: repeated multi-word phrases (e.g. 'Career Counseling in Career Counseling in', 'Client Goal or Client Goal or')
    for n in range(5, -1, -1):
        if n == 0:
            pat = re.compile(r"\b([A-Za-z0-9_,-]{2,})\s+\1(?=[,\s]|$)", re.IGNORECASE)
        else:
            pat = re.compile(r"\b([A-Za-z0-9_,-]{2,}(?:\s+[A-Za-z0-9_,-]+){" + str(n) + r"})\s+\1(?=[,\s]|$)", re.IGNORECASE)
        prev = None
        while prev != text:
            prev = text
            text = pat.sub(r"\1", text)

    # 2.5. Concatenated phrase deduplication without space (e.g. 'the 21st Centurythe 21st Century')
    text = re.sub(
        r"([A-Za-z0-9_-]{2,}(?:\s+[A-Za-z0-9_-]{2,}){1,4})\1",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    # 3. Suffix and hyphenation repair for fragmented words from vector art / narrow boxes
    text = re.sub(r"\b(infor)\s+(mation)\b", r"\1\2", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Understand|Clos|Mean|Sett|Find|Train)\s+(ing)\b", r"\1\2", text, flags=re.IGNORECASE)
    text = re.sub(r"\b([A-Za-z]{3,})\s+(ing|tion|tions|ment|ments)\b", r"\1\2", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(reoc-)\s*(curring)\b", "reoccurring", text, flags=re.IGNORECASE)

    # 4. Fix fractured drop-shadow title text: 'A MERICAN OUNSELING C A SSOCIATION' -> 'AMERICAN COUNSELING ASSOCIATION'
    text = re.sub(
        r"\bA\s+MERICAN\s+OUNSELING\s+C\s+A\s*SSOCIATION\b",
        "AMERICAN COUNSELING ASSOCIATION",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bA\s+MERICAN\b", "AMERICAN", text)

    return text


def clean_decorative_noise(text: str) -> str:
    """
    Cleans decorative artifacts, dingbat font glitches, and stray running elements:
    - '@ EXAMPLES' or 'm@ EXAMPLES' -> '### Examples'
    - 'm@' / '@' dingbats -> clean bullets
    - Stray 'Continued' or 'Table X Continued'
    - Lone Roman numerals
    - Cengage / font-glyph decorative symbol lines (e.g. '**11.e;,-4——**', '•~--------')
    """
    if not text:
        return ""

    # Strip leading decorative divider bullets (e.g. '•~-------- 7. How aware...' -> '7. How aware...')
    text = re.sub(r'(?m)^[ \t]*[•~·—\-_]{2,}[ \t]*', '', text)

    # Dingbats in Book 2 (Group Counseling), protecting CSS at-rules
    text = re.sub(r'(?m)^[ \t]*m?@\s*EXAMPLES?\s*$', '### Examples', text, flags=re.IGNORECASE)
    text = re.sub(r'(?m)^[ \t]*m?@\s*ACTIVITIES\s*$', '### Activities', text, flags=re.IGNORECASE)
    text = re.sub(r'(?m)^[ \t]*m?@\s*([A-Z\s]{3,30})$', r'### \1', text)
    text = re.sub(r'(?m)^[ \t]*m?@\s*(?!import\b|media\b|keyframes\b|font-face\b|charset\b)', '- ', text)

    # Stray '(Continued)' or 'Table X.X Continued'
    text = re.sub(
        r'(?m)^[ \t]*(?:\(?Continued\)?|Table\s+\d+(?:\.\d+)?\s+Continued|Figure\s+\d+(?:\.\d+)?\s+Continued)\s*$',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Isolated decorative Roman numerals (e.g. solitary 'I', 'II', 'IV' on a line surrounded by empty lines)
    text = re.sub(r'(?m)(?<=\n\n)[ \t]*(?:I|II|III|IV|V|VI|VII|VIII|IX|X)[ \t]*(?=\n\n)', '', text)

    # Filter out standalone decorative font glyph noise lines (e.g. '**11.e;,-4——**', 'u•~·!t—')
    cleaned_lines = []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r'^\*{0,2}[-•~·!@#$%^&*_=+:;,.<>\/|\\—–\d\w]{3,30}\*{0,2}$', s):
            letters = re.sub(r'[^a-zA-Z]', '', s)
            if len(letters) <= 1 or (re.search(r'[-•~·—–_]{2,}', s) and len(letters) <= 2):
                continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

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

        #Filter out common non-heading patterns
        if (
            3 <= len(stripped) <= 65
            and not re.match(r'^(?:CHAPTER|PART|\d+|http|www|page|\[|\(|-|\*|•|=»|=)', stripped, re.IGNORECASE)
            and (not stripped.endswith(('.', ',', ';', ':')) or stripped.endswith('?'))
            and not re.search(r'[a-z]\.\s+[A-Z]', stripped)
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
                # Detect start of a new APA reference item: Last, F. M. (Year).
                is_ref_item = bool(re.match(r'^[A-Z][a-zA-Z\s\.,&\'’–-]{1,60}\s+\(\d{4}[a-z]?\)\.', s))
                if is_ref_item and cur_para:
                    reflowed_paragraphs.append('\n'.join(cur_para))
                    cur_para = [s]
                elif not cur_para:
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
        r'(?m)^(?P<p1>(?!(?:[#>`|!]|[-*+][ \t]+))[^\n]+[^.\?!:;\n#`>|\-])\n{2,}'
        r'(?P<intervening>(?:[ \t]*(?:(?:\*\*|#|>|\[\^|[-*•]|<table|\|)[^\n]*|[ \t]*)\n){1,20})'
        r'\s*(?P<page><!--\s*Page\s+\d+\s*-->)\s*\n+(?P<p2>[a-z][^\n]*)',
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
        r'(?m)^((?!(?:[#>`|!]|[-*+][ \t]+))[^\n]+[^.\?!:;\n#`>|\-])\n{2,}\s*(<!--\s*Page\s+\d+\s*-->)\s*\n+([a-z])',
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
    """Unpacks PDF typographic ligatures and repairs split ligature tokens.

    Args:
        text: Input string potentially containing Unicode ligatures or split fi/fl words.

    Returns:
        Normalized text with intact words.
    """
    if not text:
        return ""
    for lig, replacement in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, replacement)
    return repair_broken_ligatures(text)


_LIGATURE_STANDALONE_EXCLUSIONS = {"hi", "lofi", "wifi", "scifi", "fi", "fl"}


def repair_broken_ligatures(text: str) -> str:
    """Repairs intra-word spaces introduced by PDF font ligature splitting (e.g. 'identifi cation' -> 'identification').

    Handles multiple ligatures within the same word (e.g. 'fi refi ghter' -> 'firefighter').

    Args:
        text: Input text containing broken ligature gaps.

    Returns:
        Text with broken fi/fl/ffi/ffl ligature words seamlessly rejoined.
    """
    if not text:
        return ""

    def _rejoin(match: re.Match) -> str:
        prefix = match.group(1)
        suffix = match.group(2)
        if prefix.lower() in {"hi", "lofi", "wifi", "scifi"}:
            return match.group(0)
        return f"{prefix}{suffix}"

    # Apply twice to catch double ligatures in one word (e.g. 'fi refi ghter' -> 'firefighter')
    pat = re.compile(r'\b([a-zA-Z]*(?:ffi|ffl|fi|fl))[ \t]+([a-z]{1,15})\b')
    text = pat.sub(_rejoin, text)
    text = pat.sub(_rejoin, text)
    return text


def clean_typography_artifacts(text: str) -> str:
    """Normalizes common PDF extraction typographical quirks while protecting code fences and tables.

    - Smart quotes and dashes (---, -- -> —) outside fenced code blocks and Markdown table dividers
    - Orphaned page-margin artifacts (e.g. solitary '|' or '¦')
    - Font ligatures

    Args:
        text: Raw Markdown or prose string to normalize.

    Returns:
        Typography-normalized string with Mermaid arrows and table dividers preserved.
    """
    if not text:
        return ""
    # Repair soft-hyphen line wraps and strip residual U+00AD characters (Refs: ISSUE-017)
    if "\xad" in text:
        text = re.sub(r"([a-zA-Z]+)-\xad[ \t]*\n[ \t]*([a-zA-Z]+)", r"\1-\2", text)
        text = re.sub(r"([a-zA-Z]+)\xad[ \t]*\n[ \t]*([a-zA-Z]+)", r"\1\2", text)
        text = text.replace("\xad", "")
    text = normalize_ligatures(text)
    text = clean_decorative_noise(text)
    text = clean_shadow_duplicates(text)

    # Protect fenced code blocks (e.g. ```mermaid ... ```), table separator rows (| --- |),
    # and HTML comments (<!-- ... -->) so `--` is never corrupted into em-dashes `—` (Refs: ISSUE-017)
    protected_blocks: list[str] = []

    def _stash(match: re.Match) -> str:
        idx = len(protected_blocks)
        protected_blocks.append(match.group(0))
        return f"\x00PROTECTED_BLOCK_{idx}\x00"

    # Restore any already-corrupted em-dash or multi-hyphen comments back to standard ASCII <!-- ... -->
    text = re.sub(
        r"<![-—–]+\s*OBSIDIAN_NAV_START\s*[-—–]+>",
        "<!-- OBSIDIAN_NAV_START -->",
        text,
    )
    text = re.sub(
        r"<![-—–]+\s*OBSIDIAN_NAV_END\s*[-—–]+>",
        "<!-- OBSIDIAN_NAV_END -->",
        text,
    )
    text = re.sub(
        r"<![-—–]+\s*Page\s+(\d+)\s*[-—–]+>",
        r"<!-- Page \1 -->",
        text,
    )
    text = re.sub(
        r"<![-—–]+([\s\S]*?)[-—–]+>",
        lambda m: f"<!-- {m.group(1).strip('-—– ')} -->",
        text,
    )
    text = re.sub(r"```[\s\S]*?```", _stash, text)
    text = re.sub(r"(?m)^[ \t]*\|[ \t:\-\|]+\|[ \t]*$", _stash, text)
    text = re.sub(r"<!--[\s\S]*?-->", _stash, text)
    text = re.sub(r"<table\b[\s\S]*?</table>", _stash, text, flags=re.IGNORECASE)

    # Standardize dashes in regular prose
    text = re.sub(r"---", "—", text)
    text = re.sub(r"--", "—", text)

    # Restore protected fenced code blocks and table separator rows
    for idx, original in enumerate(protected_blocks):
        text = text.replace(f"\x00PROTECTED_BLOCK_{idx}\x00", original)

    # Standardize OCR broken bullet glyphs (e.g. =», =s, », •)
    text = re.sub(r'(?m)^[ \t]*(?:=[»s]|»)\s*', '- ', text)
    text = re.sub(r'(?m)^[ \t]*=\s+([A-Z])', r'- \1', text)
    # Fix OCR misread of pronoun 'I' as pipe '|' (e.g. '| want' -> 'I want', '[| feel' -> 'I feel') (Refs: ISSUE-017)
    text = re.sub(r'(?m)(^|[ \t>\[\(])\|[ \t]+(?=[a-z]{1,15}\b)', r'\1I ', text)
    text = re.sub(r'(?m)^\[\|[ \t]*', '', text)
    # Remove standalone border ticks often left by table or sidebar borders
    text = re.sub(r'(?m)^[|¦·]\s*$', '', text)
    # Remove vector chart coordinate axis tick leaks (e.g. '5 2 5 2 5 2' or '2 2 2 2 1 1 1 1')
    text = re.sub(r'(?m)^[ \t]*(?:\d{1,3}[ \t]+){2,}\d{1,3}[ \t]*$', '', text)
    text = re.sub(r'(?m)\b(?:\d{1,2}[ \t]+){2,}\d{1,2}[ \t]+(?=[a-z]{3,}\b)', '', text)
    # Strip empty bold/italic tokens (Refs: ISSUE-017)
    text = re.sub(r'\*\*\s*\*\*', '', text)
    text = re.sub(r'\*\*\*\s*\*\*\*', '', text)
    # Separate touching bold and italic markers in numbered items (e.g. **2.***Temporality.* -> **2.** *Temporality.*)
    text = re.sub(r'(?<=\d\.)\*\*\*(?=[a-zA-Z])', r'** *', text)
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


def get_primary_chapter_markdown(ch_dir: Path) -> Optional[Path]:
    """Finds and returns the primary content Markdown file in a chapter directory.

    Strictly ignores auxiliary metadata and quality inspection files such as
    AUDIT.md, audit_report.md, processing_status.md, README.md, and *_Verified.md.
    Prefers exact directory name matches and higher file sizes to ensure true chapter
    text is used rather than reports or stubs.

    Args:
        ch_dir: Path to the chapter folder.

    Returns:
        Path to the primary chapter Markdown file, or None if none found.
    """
    if not ch_dir or not ch_dir.exists() or not ch_dir.is_dir():
        return None

    # Fast path: exact match with directory name
    exact_match = ch_dir / f"{ch_dir.name}.md"
    if exact_match.exists() and exact_match.is_file():
        return exact_match

    # Disallowed non-content filenames
    excluded_names = {
        "audit.md",
        "audit_report.md",
        "processing_status.md",
        "readme.md",
        "index.md",
        "summary.md",
    }
    excluded_suffixes = (
        "_verified.md",
        "_audit.md",
        "_report.md",
        "_summary.md",
        "_test.md",
    )

    candidates: List[Path] = []
    for f in ch_dir.glob("*.md"):
        if not f.is_file():
            continue
        fname_lower = f.name.lower()
        if fname_lower in excluded_names or fname_lower.endswith(excluded_suffixes):
            continue
        candidates.append(f)

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    def score_candidate(path: Path) -> float:
        name_no_ext = path.stem.lower()
        dir_name = ch_dir.name.lower()
        score = 0.0
        if name_no_ext == dir_name:
            score += 1000.0
        elif dir_name in name_no_ext or name_no_ext in dir_name:
            score += 200.0
        if path.name.startswith(("Ch", "00-", "Appendix")):
            score += 50.0
        try:
            score += path.stat().st_size / 1024.0
        except OSError:
            pass
        return score

    candidates.sort(key=score_candidate, reverse=True)
    return candidates[0]


def get_chapter_sort_key(ch_dir_name: str) -> Tuple[int, int, str]:
    """Computes a deterministic sort key ordering book chapters into canonical publication sequence:
    Front matter (00-*) -> Main chapters (Ch01..Ch99) -> Back matter (Appendix, Glossary, Index, References).

    Args:
        ch_dir_name: Directory or file name of the chapter (e.g. '00-01-Cover', 'Ch02-...', 'Appendix').

    Returns:
        Tuple of (tier, order_index, normalized_name) suitable for Python `sorted(..., key=get_chapter_sort_key)`.
    """
    name_l = ch_dir_name.lower().replace("_", "-")
    # Tier 0: Front matter (00-01-Cover, 00-07-TOC, etc.)
    if name_l.startswith("00-"):
        m_num = re.search(r"^00-(\d+)", name_l)
        num = int(m_num.group(1)) if m_num else 0
        return (0, num, name_l)

    # Tier 1: Main matter chapters (Ch01, Chapter 2, etc.)
    m_ch = re.match(r"^ch(?:apter)?0*(\d+)", name_l)
    if m_ch:
        return (1, int(m_ch.group(1)), name_l)

    # Tier 2: Back matter in standard publishing order
    back_matter_order = {
        "appendix": 10,
        "glossary": 20,
        "index": 30,
        "reference": 40,
        "references": 40,
        "afterword": 50,
    }
    for k, order in back_matter_order.items():
        if k in name_l:
            return (2, order, name_l)

    # Tier 3: Unknown or custom sections
    return (3, 999, name_l)


def heal_corrupted_headings(text: str) -> Tuple[str, List[str]]:
    """Repairs headings corrupted by prose intrusion, demoted levels, drop caps, or dingbats.

    - Promotes legitimate top chapter headings (##/### Chapter N) to H1 (#).
    - Demotes spurious mid-chapter H1s that are actually list items or prose sentences.
    - Stitches multi-line split headings.
    - Strips leading decorative dingbats from heading lines.

    Args:
        text: Chapter Markdown source string.

    Returns:
        Tuple of (healed_text, list_of_applied_fixes).
    """
    if not text:
        return "", []

    fixes: List[str] = []

    # 1. Stitch consecutive split headings where the second heading starts with a lowercase connector
    def _stitch_split_headings(match: re.Match) -> str:
        h_hashes = match.group(1)
        part1 = match.group(2).strip()
        part2 = match.group(3).strip()
        fixes.append(f"Stitched split multi-line heading: '{part1} {part2}'")
        return f"{h_hashes} {part1} {part2}"

    text = re.sub(
        r"(?m)^(#{2,5})\s+([^\n]+?)\n{1,2}#{2,6}\s+((?:and|or|of|in|to|for|with|on|at|from|by|as|into|between|the|a|an)\b[^\n]+|[a-z][^\n]{1,55})$",
        _stitch_split_headings,
        text,
    )
    text = re.sub(
        r"(?m)^(#{2,4})\s+([A-Z][A-Z\s,&\-]{2,35})\n{1,2}\1\s+([A-Z][A-Z\s,&\-]{2,45})$",
        _stitch_split_headings,
        text,
    )

    # 1b. Stitch headings ending with a dangling connector/colon or numbered chapter title
    def _stitch_dangling_heading_line(match: re.Match) -> str:
        h_hashes = match.group(1)
        part1 = match.group(2).strip()
        part2 = match.group(3).strip()
        fixes.append(f"Stitched dangling heading continuation: '{part1} {part2}'")
        return f"{h_hashes} {part1} {part2}"

    text = re.sub(
        r"(?m)^(#{2,5})\s+([^\n]*?(?:\b(?:and|or|of|in|to|for|with|on|from|by|the|a|an|&)|:)\s*|Chapter\s+\d+[^\n]*|\d{1,2}\s+[A-Z][^\n]{5,55})\n{1,2}([A-Z][^\n.!?;]{1,65}?)$",
        _stitch_dangling_heading_line,
        text,
    )

    lines = text.split("\n")
    out_lines: List[str] = []
    first_h1_seen = False

    for idx, line in enumerate(lines):
        s = line.strip()
        m_h = re.match(r"^(#{1,6})\s+(.+)$", s)
        if not m_h:
            out_lines.append(line)
            continue

        hashes, h_body = m_h.group(1), m_h.group(2).strip()
        clean_h = re.sub(r"^[\*_`]+|[\*_`]+$", "", h_body).strip()

        # Handle H1 headings: ensure only legitimate chapter title is H1
        if hashes == "#":
            if not first_h1_seen and (
                re.match(r"^(?:Chapter\s+\d+|[A-Z0-9\s,\-\–:\'\"]+$)", clean_h, re.IGNORECASE)
                or len(clean_h) < 60
            ):
                first_h1_seen = True
                out_lines.append(line)
                continue

            # Spurious mid-chapter H1: check adjacent bullet context
            prev_l = lines[idx - 1].strip() if idx > 0 else ""
            prev2_l = lines[idx - 2].strip() if idx > 1 else ""
            next_l = lines[idx + 1].strip() if idx < len(lines) - 1 else ""
            next2_l = lines[idx + 2].strip() if idx < len(lines) - 2 else ""

            is_bullet_ctx = any(
                l.startswith(("- ", "* ", "• ")) or re.match(r"^\d+\.\s+", l)
                for l in [prev_l, prev2_l, next_l, next2_l]
            )

            if is_bullet_ctx:
                fixes.append(f"Demoted spurious list H1 to bullet: '{clean_h[:35]}'")
                out_lines.append(f"- {clean_h.lstrip('-—• ')}")
                continue
            elif len(clean_h) > 50 or clean_h.endswith((".", "?", "!")):
                fixes.append(f"Demoted spurious prose H1 to paragraph: '{clean_h[:35]}'")
                out_lines.append(clean_h)
                continue
            else:
                fixes.append(f"Demoted mid-chapter H1 to H3: '{clean_h[:35]}'")
                out_lines.append(f"### {clean_h}")
                continue

        # Drop decorative symbol headings (e.g. ## •~———)
        if not clean_h or not re.search(r"[A-Za-z0-9]", clean_h):
            fixes.append(f"Removed decorative symbol heading '{s}'")
            continue

        # Strip leading decorative dingbat prefixes from valid headings
        if re.match(r"^[•~—\-]+\s+", clean_h):
            clean_h = re.sub(r"^[•~—\-]+\s+", "", clean_h).strip()
            h_body = clean_h
            line = f"{hashes} {clean_h}"
            fixes.append(f"Stripped leading decorative dingbats from heading '{clean_h[:40]}'")

        # Demote URL headings or 1-2 char non-Index headings
        if re.match(r"^(?:https?://|www\.)", clean_h, re.IGNORECASE) or (
            len(clean_h) < 3 and not re.fullmatch(r"[A-Z]", clean_h)
        ):
            fixes.append(f"Demoted invalid short/URL heading '{s}'")
            out_lines.append(clean_h)
            continue

        # Check if heading starts with lowercase (prose fragment or cross-column merge)
        if clean_h[0].islower():
            m_split = re.search(r"^(.+?[.?!])\s+([A-Z][A-Za-z0-9\s\-\–:,\'’\(\)\?]{3,80})$", clean_h)
            if m_split:
                prose_part = m_split.group(1).strip()
                real_head = m_split.group(2).strip()
                fixes.append(f"Separated leading prose from heading '{real_head}'")
                out_lines.append(prose_part)
                out_lines.append("")
                out_lines.append(f"{hashes} {real_head}")
            else:
                fixes.append(f"Demoted lowercase heading fragment '{clean_h[:50]}'")
                out_lines.append(h_body)
            continue

        # Check for mid-heading sentence period intrusion
        scrubbed = re.sub(
            r"\b(?:e\.g|i\.e|vs|et al|Dr|Mr|Mrs|Ms|Prof|St|Jr|Sr|Inc|Ltd|Co|No|Vol|Ch|Fig|pp|Ed|U\.S|U\.K|Ph\.D|M\.A|B\.A)\.\s+",
            " ",
            clean_h,
            flags=re.IGNORECASE,
        )
        if re.search(r"[a-z]{2,}\.\s+[A-Z][a-z]", scrubbed) or (
            len(clean_h) > 85 and re.search(r"[a-z][.?!]\s+[A-Z]", scrubbed)
        ):
            m_sent = re.match(r"^(.+?[a-z]{2,}[.?!])\s+([A-Z].+)$", clean_h)
            if m_sent:
                part_a = m_sent.group(1).strip()
                part_b = m_sent.group(2).strip()
                if not part_b.endswith(".") and len(part_b) < 75:
                    fixes.append(f"Extracted heading '{part_b}' from merged prose line")
                    out_lines.append(part_a)
                    out_lines.append("")
                    out_lines.append(f"{hashes} {part_b}")
                    continue
            fixes.append(f"Demoted prose-intruded heading '{clean_h[:60]}...'")
            out_lines.append(h_body)
            continue

        out_lines.append(line)

    return "\n".join(out_lines), fixes


