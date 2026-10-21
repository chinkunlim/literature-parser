"""
Validation Rules for Content Accuracy
=====================================
"""

import re

from literature_parser.config.processor_config import FOOTER_NOISE_PATTERNS


def is_valid_dictionary_word(token: str, dict_words: set) -> bool:
    """Checks if token is a valid word, number, roman numeral, or hyphenated compound."""
    clean = token.strip(".,;:!?\"'()[]{}/*#–-—’“”‘$").lower()
    if not clean:
        return True
    # Strip possessive 's or ’s
    clean = re.sub(r"['’]s$", "", clean)
    # Numbers, years, page refs (e.g. 1964, 2018, 166, 1.1)
    if re.match(r'^\d+(\.\d+)?$', clean):
        return True
    # Roman numerals
    if re.match(r'^[ivxlcdm]+$', clean):
        return True
    # Direct dictionary match
    if clean in dict_words:
        return True
    # Common academic & psychological terms
    if clean in {'doi', 'bart', 'retest', 'psychopharmacology', 'chicago', 'keywords', 'impulsivity', 'delinquency', 'bilingual', 'bilingualism', 'cognitive', 'taxidriving', 'fMRI', 'prefrontal', 'et', 'al', 'longterm', 'alzheimer', 'psychol', 'exp', 'author'}:
        return True
    # English inflectional & derivational morphology
    if clean.endswith('ies') and clean[:-3] + 'y' in dict_words:
        return True
    if clean.endswith('ing'):
        stem = clean[:-3]
        if stem in dict_words or stem + 'e' in dict_words:
            return True
        if len(stem) > 2 and stem[-1] == stem[-2] and stem[:-1] in dict_words:
            return True
    if clean.endswith('ed'):
        stem = clean[:-2]
        if stem in dict_words or stem + 'e' in dict_words:
            return True
        if len(stem) > 2 and stem[-1] == stem[-2] and stem[:-1] in dict_words:
            return True
    # British vs American English (e.g. organisation -> organization)
    if 'sation' in clean and clean.replace('sation', 'zation') in dict_words:
        return True
    if 'ise' in clean and clean.replace('ise', 'ize') in dict_words:
        return True
    # Standard prefixes (re-, un-, non-, co-)
    for prefix in ('re', 'un', 'non', 'co'):
        if clean.startswith(prefix) and clean[len(prefix):] in dict_words:
            return True
    # Plural or standard endings ('s, s, ed, ing, ly, etc.)
    for suffix in ('s', 'es', 'ed', 'ing', 'ly', 'er', 'est', 'tion', 'ment', 'able', 'ize', 'ized', 'izing', 'ical', 'ology', 'ability'):
        if clean.endswith(suffix) and clean[:-len(suffix)] in dict_words:
            return True
    # Hyphenated compound words
    if '-' in clean:
        parts = clean.split('-')
        if all(is_valid_dictionary_word(p, dict_words) for p in parts if p):
            return True
    return False


def check_noise_strings(content: str) -> list:
    """Detects if any copyright/running footer noise strings leaked into the markdown."""
    found = []
    for line in content.splitlines():
        line_clean = line.strip()
        # Skip legitimate bibliographic / abstract records (e.g. PsycINFO Database Record, APA article meta)
        if re.search(r'\b(?:psycinfo|database record|journal abstract|american psychological association)\b', line_clean, re.IGNORECASE):
            continue
        # Running header/footer artifacts appear on short standalone lines (<140 chars)
        if line_clean and len(line_clean) < 140:
            for pat in FOOTER_NOISE_PATTERNS:
                matches = re.findall(pat, line_clean, re.IGNORECASE)
                if matches:
                    found.extend(matches)
    return found



def check_heading_ratio(content: str) -> tuple:
    """Computes heading line count vs total line count to detect over-heading bugs."""
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    headings = [l for l in lines if l.startswith('#')]
    ratio = (len(headings) / len(lines) * 100) if lines else 0
    passed = ratio < 40.0 or len(lines) < 15
    return len(headings), len(lines), ratio, passed


# ---------------------------------------------------------------------------
# Content Continuity Rules
# ---------------------------------------------------------------------------

_ABRUPT_CUT_PATTERN = re.compile(
    r'(?<![.?!:;])(?<![.?!:;][)"\'’”])(?<![*#`>|])\n'  # newline not preceded by terminal punctuation/quotes
    r'[ \t]*(?:<!--[^>]*-->)?'                         # optional page comment
    r'[ \t]*\n'                                        # blank line (paragraph break)
    r'[ \t]*([a-z](?![.\)]\s))',                       # next line starts with lowercase, not a choice letter like 'c. '
    re.MULTILINE
)


# A "page boundary sentence break": text ending in the middle of a sentence
# right before a <!-- Page N --> marker.
_PAGE_BREAK_INCOMPLETE = re.compile(
    r'([a-z,;]{3,})\s*\n\s*<!--\s*Page\s+\d+\s*-->\s*\n\s*([a-z])',
    re.MULTILINE | re.IGNORECASE
)

# Lines that are suspiciously short and don't end with punctuation
# (likely a truncated line at page boundary)
_ORPHAN_FRAGMENT = re.compile(
    r'^(?!#|!\[|-|\*|\d+\.)([A-Z][a-zA-Z, ]{3,40}[^.?!:\n])$',
    re.MULTILINE
)


def check_content_continuity(content: str) -> dict:
    """
    Detects content continuity problems that indicate the text was cut
    at page boundaries without proper re-flowing:

    1. **Cross-page abrupt cuts**: A paragraph ends mid-sentence and the next
       paragraph continues with a lowercase word (no capital = continuation).
    2. **Incomplete sentences at page breaks**: Text ending without punctuation
       immediately before a ``<!-- Page N -->`` comment, with continuation on
       the next page starting lowercase.
    3. **Orphaned fragments**: Very short lines that look like trailing sentence
       fragments (< 50 chars, no terminal punctuation).

    Returns:
        {
          'passed': bool,
          'abrupt_cuts': int,
          'page_break_cuts': int,
          'orphan_fragments': int,
          'examples': list[str],   # up to 5 example snippets for debugging
        }
    """
    examples = []
    issues = 0

    # 1. Abrupt paragraph breaks where next para starts lowercase
    abrupt_cuts = _ABRUPT_CUT_PATTERN.findall(content)
    if abrupt_cuts:
        issues += len(abrupt_cuts)
        # Find context around each match for reporting
        for m in _ABRUPT_CUT_PATTERN.finditer(content):
            snippet = content[max(0, m.start() - 60): m.end() + 60].replace('\n', '↵')
            examples.append(f"[ABRUPT CUT] ...{snippet}...")
            if len(examples) >= 5:
                break

    # 2. Page-break sentence splits: text→page marker→lowercase continuation
    page_break_cuts = list(_PAGE_BREAK_INCOMPLETE.finditer(content))
    if page_break_cuts:
        issues += len(page_break_cuts)
        for m in page_break_cuts[:5]:
            snippet = content[max(0, m.start() - 40): m.end() + 40].replace('\n', '↵')
            if len(examples) < 5:
                examples.append(f"[PAGE BREAK CUT] ...{snippet}...")

    # 3. Orphaned short fragments (these are soft warnings, not hard failures)
    orphan_hits = _ORPHAN_FRAGMENT.findall(content)
    orphan_count = len(orphan_hits)
    # Only count as issue if there are many (> 5 per chapter is suspicious)
    orphan_issue = max(0, orphan_count - 5)
    issues += orphan_issue

    passed = (len(abrupt_cuts) == 0 and len(page_break_cuts) == 0 and orphan_issue == 0)

    return {
        'passed': passed,
        'abrupt_cuts': len(abrupt_cuts),
        'page_break_cuts': len(page_break_cuts),
        'orphan_fragments': orphan_count,
        'examples': examples,
    }


def check_sentence_completeness(content: str) -> dict:
    """
    Checks that the chapter starts and ends with complete sentences, and that
    no paragraph ends with a coordinating conjunction or preposition
    (strong indicator of a forced page-boundary cut).

    Returns:
        {
          'passed': bool,
          'incomplete_endings': list[str],
          'incomplete_openings': list[str],
        }
    """
    # Conjunctions / prepositions that commonly appear at forced line breaks
    _DANGLING = re.compile(
        r'\b(and|or|but|the|a|an|in|on|at|to|for|of|with|by|from|as|into|'
        r'through|during|before|after|above|below|between|under|'
        r'since|until|unless|although|because|while|if|that|which|'
        r'this|these|those|their|its)\s*$',
        re.IGNORECASE | re.MULTILINE
    )

    # Strip markdown code fences and LaTeX blocks to avoid false positives
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'\$\$.*?\$\$', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', cleaned) if p.strip()]

    incomplete_endings = []
    incomplete_openings = []

    for para in paragraphs:
        # Skip headings, bullet items, image references
        if para.startswith(('#', '-', '*', '!', '|')):
            continue
        if len(para) < 20:
            continue

        # Check paragraph ends with a dangling word
        m = _DANGLING.search(para)
        if m and m.end() == len(para):
            snippet = para[-80:].replace('\n', ' ')
            incomplete_endings.append(f"'...{snippet}'")

        # Check paragraph opens mid-sentence (lowercase, not a list item)
        first_word_match = re.match(r'^([a-z])', para)
        if first_word_match:
            snippet = para[:80].replace('\n', ' ')
            incomplete_openings.append(f"'{snippet}...'")

    passed = len(incomplete_endings) == 0 and len(incomplete_openings) == 0

    return {
        'passed': passed,
        'incomplete_endings': incomplete_endings[:5],
        'incomplete_openings': incomplete_openings[:5],
    }


def check_numeric_coordinate_noise(content: str) -> dict:
    """
    Detects vector diagram coordinate tick leaks (e.g. '5 2 5 2 5 2' or '20 20 20 20 1 1')
    that bleed into prose text outside of tables, math blocks, and code fences.
    """
    # Strip tables, code fences, and math blocks
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'\$\$.*?\$\$', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<table.*?>.*?</table>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<div class="framed-card">.*?</div>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<div class="comparison-card">.*?</div>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

    noise_matches = []

    # 1. Identical repeated number tick runs: e.g. '2 2 2 2 2' or '20 20 20 20'
    for m in re.finditer(r'\b(\d+)(?:[ \t]+\1){3,}\b', cleaned):
        noise_matches.append(m.group(0).strip())

    # 2. Alternating repetitive tick runs: e.g. '5 2 5 2 5 2'
    for m in re.finditer(r'\b(\d+)[ \t]+(\d+)[ \t]+\1[ \t]+\2[ \t]+\1[ \t]+\2\b', cleaned):
        noise_matches.append(m.group(0).strip())

    # 3. Excessive isolated numbers on a single line (> 7 numbers)
    for line in cleaned.splitlines():
        s = line.strip()
        if re.match(r'^(?:\d{1,3}[ \t]+){7,}\d{1,3}$', s):
            noise_matches.append(s)

    # 4. Inline coordinate leaks bleeding directly into lowercase prose words
    for m in re.finditer(r'(?m)\b(?:\d{1,2}[ \t]+){2,}\d{1,2}[ \t]+(?=[a-z]{3,}\b)', cleaned):
        noise_matches.append(m.group(0).strip())

    return {
        'passed': len(noise_matches) == 0,
        'count': len(noise_matches),
        'examples': noise_matches[:5],
    }


def check_shattered_math(content: str) -> dict:
    """
    Detects sequences of isolated 1-2 character lines indicating broken mathematical formulas
    that were shattered by vertical superscript/subscript offsets.
    """
    # Strip markdown lists and code fences
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'<style>.*?</style>', '', cleaned, flags=re.DOTALL)

    shattered_blocks = []
    for m in re.finditer(r'(?m)(?:^[a-zA-Z0-9\(\)\=\+\-\/\*]\s*$\n?){4,}', cleaned):
        snippet = m.group(0).replace('\n', ' ')
        shattered_blocks.append(snippet.strip())

    return {
        'passed': len(shattered_blocks) == 0,
        'count': len(shattered_blocks),
        'examples': shattered_blocks[:5],
    }


def check_infix_math_in_words(content: str) -> dict:
    """
    Detects words split by LaTeX math symbol insertions (e.g. 'popula$\\mu$tion').
    """
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    infix_matches = []
    for m in re.finditer(r'\b([a-zA-Z]{2,})\$([\\a-zA-Z]+)\$([a-zA-Z]{2,})\b', cleaned):
        infix_matches.append(m.group(0))

    return {
        'passed': len(infix_matches) == 0,
        'count': len(infix_matches),
        'examples': infix_matches[:5],
    }


def check_heading_prose_intrusion(content: str) -> dict:
    """
    Detects headings that have absorbed following body prose sentences due to
    multi-column order or aggressive cross-page concatenation (length > 80 chars
    with multiple full sentences).
    """
    bad_headings = []
    for line in content.splitlines():
        s = line.strip()
        if s.startswith(('## ', '### ', '#### ')):
            header_text = s.lstrip('#').strip()
            # If header is long and contains sentence ending punctuation followed by capital letters
            if len(header_text) > 85 and re.search(r'[.?!]\s+[A-Z]', header_text):
                bad_headings.append(header_text[:100] + '...')

    return {
        'passed': len(bad_headings) == 0,
        'count': len(bad_headings),
        'examples': bad_headings[:5],
    }


def check_table_banner_integrity(content: str) -> dict:
    """
    Detects comparison tables where 'Strengths' or 'Weaknesses' banners collapsed
    into the middle of a bullet item or disappeared.
    """
    collapsed_banners = []
    # Pattern: a bullet item containing 'Weaknesses of' or 'Strengths of' mid-text
    for m in re.finditer(r'(?m)^[-*•]\s+.*?\b(Strengths|Weaknesses|Advantages|Disadvantages)\s+of\s+.*', content):
        line = m.group(0)
        if not line.startswith(('- **Strengths', '- **Weaknesses', '- **Advantages', '- **Disadvantages')):
            collapsed_banners.append(line[:90] + '...')

    return {
        'passed': len(collapsed_banners) == 0,
        'count': len(collapsed_banners),
        'examples': collapsed_banners[:5],
    }


def check_heading_density(content: str, word_count: int, is_front_matter: bool = False, is_journal: bool = False) -> dict:
    """
    Validates that substantial textbook chapters have sufficient heading hierarchy.
    """
    if is_front_matter or is_journal or word_count < 1000:
        return {'passed': True, 'heading_count': len([l for l in content.splitlines() if l.strip().startswith(('## ', '### '))]), 'word_count': word_count}

    headings = [l for l in content.splitlines() if l.strip().startswith(('## ', '### '))]
    passed = len(headings) >= 2

    return {
        'passed': passed,
        'heading_count': len(headings),
        'word_count': word_count,
    }


def check_excessive_hard_wraps(content: str) -> dict:
    """
    Detects unwrapped / hard-column wrapped prose where short lines terminate with single
    newlines instead of reflowing into CommonMark paragraphs.
    """
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'<table.*?>.*?</table>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

    paras = re.split(r'\n{2,}', cleaned)
    unreflowed_paras = 0

    for p in paras:
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        if len(lines) >= 4:
            # Check if all lines are ~60-80 chars and not starting with lists/quotes/code
            if all(not l.startswith(('#', '-', '*', '>', '|', '!')) for l in lines):
                line_lens = [len(l) for l in lines[:-1]]  # ignore last line
                if line_lens and all(50 <= ll <= 85 for ll in line_lens):
                    unreflowed_paras += 1

    # Warning if more than 3 paragraphs remain unreflowed in the chapter
    return {
        'passed': unreflowed_paras <= 2,
        'unreflowed_paragraphs': unreflowed_paras,
    }


def check_latex_and_symbol_integrity(content: str) -> dict:
    """
    Validates mathematical formulas, KaTeX compatibility, and symbol safety:
    - Delimiter parity ($ and $$)
    - Unescaped currency amounts ($3, $50, etc.)
    - Triple/quadruple unescaped dollars ($$$)
    - Unescaped percent signs inside inline math ($50%)
    - Unbalanced curly braces inside math blocks
    """
    issues = []

    # 1. Check for unescaped $$$
    triple_dollars = re.findall(r'(?<!\\)\${3,}', content)
    if triple_dollars:
        issues.append(f"Found {len(triple_dollars)} unescaped multi-dollar sequence(s) (e.g. '$$$' breaks KaTeX)")

    # 2. Strip code fences to avoid false positives in code blocks
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)

    # 3. Check for unescaped percent sign inside LaTeX math
    for math_block in re.findall(r'\$(.+?)\$', cleaned):
        if re.search(r'(?<!\\)%', math_block):
            issues.append(f"Unescaped percent sign % inside LaTeX math: ${math_block[:40]}$ (comments out closing $)")

    # 4. Check display math $$ parity
    double_dollars = cleaned.count("$$")
    if double_dollars % 2 != 0:
        issues.append(f"Unpaired display math delimiter '$$' (count: {double_dollars})")

    # 5. Check for unescaped currency or stray dollars outside valid math
    no_display_math = re.sub(r'\$\$.*?\$\$', '', cleaned, flags=re.DOTALL)
    # Strip valid inline math: $(non-space)...(non-space)$
    stripped_valid_math = re.sub(r'\$(?!\s)(?:\\.|[^\$\n])+?(?<!\s)\$', '[MATH]', no_display_math)
    # Strip already escaped dollars \$
    stray_dollars_text = stripped_valid_math.replace(r'\$', '')
    stray_dollars = re.findall(r'\$', stray_dollars_text)
    if stray_dollars:
        issues.append(f"Found {len(stray_dollars)} stray or unescaped dollar sign(s) (e.g. '$3' or unpaired '$') which break KaTeX parser")

    # 6. Check curly braces inside formulas
    for block in re.findall(r'\$(.+?)\$', cleaned):
        if block.count('{') != block.count('}'):
            issues.append(f"Mismatched curly braces in math block: ${block[:50]}$")

    return {
        'passed': len(issues) == 0,
        'count': len(issues),
        'issues': issues,
    }



def check_table_column_integrity(content: str) -> dict:
    """
    Validates HTML table structure:
    - Counts header columns (accounting for colspan)
    - Verifies that tbody rows match the header column count
    - Detects phantom empty column runs (e.g. <th></th> runs)
    """
    issues = []
    tables = re.findall(r'<table\b[^>]*>(.*?)</table>', content, re.DOTALL | re.IGNORECASE)

    for t_idx, table_html in enumerate(tables, start=1):
        # Extract thead rows
        thead_match = re.search(r'<thead\b[^>]*>(.*?)</thead>', table_html, re.DOTALL | re.IGNORECASE)
        expected_cols = None
        if thead_match:
            th_rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', thead_match.group(1), re.DOTALL | re.IGNORECASE)
            # Find the max cols across thead rows (taking colspan and rowspan into account)
            row_cols = []
            for r in th_rows:
                cols = 0
                for cell in re.findall(r'<t[hd]([^>]*)>', r, re.IGNORECASE):
                    m = re.search(r'colspan=[\"\'](\d+)[\"\']', cell, re.IGNORECASE)
                    cols += int(m.group(1)) if m else 1
                row_cols.append(cols)
            if row_cols:
                expected_cols = max(row_cols)

        # Check for phantom empty columns in header
        phantom_ths = re.findall(r'<th[^>]*>\s*</th>\s*<th[^>]*>\s*</th>', table_html, re.IGNORECASE)
        if phantom_ths:
            issues.append(f"Table {t_idx}: detected phantom empty header columns")

        # Verify tbody rows
        tbody_match = re.search(r'<tbody\b[^>]*>(.*?)</tbody>', table_html, re.DOTALL | re.IGNORECASE)
        if tbody_match and expected_cols:
            tb_rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL | re.IGNORECASE)
            for r_idx, r in enumerate(tb_rows, start=1):
                cols = 0
                for cell in re.findall(r'<t[hd]([^>]*)>', r, re.IGNORECASE):
                    m = re.search(r'colspan=[\"\'](\d+)[\"\']', cell, re.IGNORECASE)
                    cols += int(m.group(1)) if m else 1
                # If row is a section divider spanning the full table, cols should equal expected_cols
                if cols != expected_cols:
                    issues.append(f"Table {t_idx} Row {r_idx}: column count mismatch (found {cols}, expected {expected_cols})")
                    break  # report first mismatch per table to avoid spam

    return {
        'passed': len(issues) == 0,
        'count': len(issues),
        'issues': issues,
    }


def check_unescaped_special_chars(content: str) -> dict:
    """
    Detects risky raw Markdown/HTML character leaks:
    - Raw unescaped angle brackets like 'p < .05' in prose (outside math mode and HTML tags)
    - Stray '#' at line start that are item numbers rather than Markdown headings
    """
    issues = []

    # Strip code blocks, math blocks, and HTML tags
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    cleaned = re.sub(r'\$\$.*?\$\$', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\$.*?\$', '', cleaned)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)

    # 1. Raw statistical angle brackets outside math
    raw_p_angles = re.findall(r'\b(?:p|ps)\s*([<>])\s*\.\d+', cleaned, re.IGNORECASE)
    if raw_p_angles:
        issues.append(f"Found {len(raw_p_angles)} raw statistical angle bracket(s) (e.g. 'p < .05') outside LaTeX math")

    # 2. Numbered item starting with # at line start (e.g. '#15. Drug')
    fake_h1 = re.findall(r'(?m)^#\s*(\d+[\.\)].*)', cleaned)
    if fake_h1:
        issues.append(f"Found {len(fake_h1)} line(s) starting with '#' as item numbers instead of headings (e.g. '{fake_h1[0][:40]}')")

    return {
        'passed': len(issues) == 0,
        'count': len(issues),
        'issues': issues,
    }


