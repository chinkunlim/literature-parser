"""
Shared Text & Regex Utilities
=============================
Centralized, strongly-typed regex patterns and pure text transformation functions
for academic literature and book processing.

Shared between:
- FormatAuditor (defect detection & scoring)
- FixPlaybook (rule-based repairs)
- OllamaRecipeSynthesizer (context & prompts)
- PromptRegistry (LLM prompt guidelines)
"""

import re
from typing import List, Tuple

# ==============================================================================
# 1. COMPILED REGEX PATTERNS
# ==============================================================================

# Solitary lines with 1-4 digit page numbers (ignoring numbers with leading zeros)
RE_ORPHAN_PAGE_NUMBER = re.compile(r'^\d{1,4}$')

# Currency dollar signs not already escaped (e.g. $25, $1,000, $3.50)
RE_UNESCAPED_CURRENCY = re.compile(r'(?<!\\)\$(?=(\d+(?:,\d{3})*(?:\.\d+)?\b))')

# Inline **References** glued to acknowledgment / disclosure sentence ends
RE_GLUED_REFERENCES = re.compile(r'([\.?!]\s+)\*\*References\*\*\s+([A-Z])')

# OCR corrupted statistical formulas
RE_CORRUPTED_STATS_T = re.compile(r'(\*?[tTF]\*?)\s*ð\s*(\d+)\s*Þ\s*=\s*(\d+[:\.]\s*\d+)')
RE_CORRUPTED_STATS_P = re.compile(r'\*?[pP]\*?\s*o\s*0?[:\.]\s*(\d+)')
RE_CORRUPTED_STATS_M = re.compile(r'(\*?[mM]\*?)\s*=\s*(\d+[:\.]\s*\d+)')
RE_CORRUPTED_STATS_SD = re.compile(r'(?:\*?s\.\s*d\.\*?)\s*=\s*(\d+(?:\.\d+)?)')

# Publisher watermarks masquerading as markdown headings
RE_MANUSCRIPT_WATERMARK = re.compile(
    r'(?m)^#+\s*(?:NIH\s+Public\s+Access|Author\s+Manuscript|HHS\s+Public\s+Access|ARTICLE\s+IN\s+PRESS|RESEARCH\s+ARTICLE)\s*\n+',
    re.IGNORECASE,
)

# Reference entries formatted as Author Year; Title...
RE_UNPARENTHESIZED_REF = re.compile(r'^([A-Z][a-zA-Z\s\.,\-]+?)\s+(\d{4});\s+(.*)')


# ==============================================================================
# 2. PURE TRANSFORMATION FUNCTIONS
# ==============================================================================

def clean_orphan_page_numbers_text(text: str) -> Tuple[str, int]:
    """Strips solitary lines that contain only 1-4 digit page numbers."""
    lines = text.splitlines()
    clean_lines = []
    count = 0
    for line in lines:
        s = line.strip()
        if RE_ORPHAN_PAGE_NUMBER.match(s) and not s.startswith("0"):
            count += 1
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines), count


def escape_currency_katex_text(text: str) -> Tuple[str, int]:
    """Escapes $ currency signs (e.g. $25 -> \\$25) to prevent KaTeX math delimiter collision."""
    new_text, count = RE_UNESCAPED_CURRENCY.subn(r'\\$', text)
    return new_text, count


def separate_glued_references_text(text: str) -> Tuple[str, int]:
    """Splits inline **References** glued to the end of acknowledgment or disclosure sentences."""
    def _repl(m):
        return f"{m.group(1)}\n\n## References\n\n{m.group(2)}"
    new_text, count = RE_GLUED_REFERENCES.subn(_repl, text)
    return new_text, count


def normalize_corrupted_stats_text(text: str) -> Tuple[str, int]:
    """Repairs Elsevier OCR corrupted statistical formulas like t ð 24 Þ -> $t(24)$."""
    count = 0
    new_text = text

    # 1. t ð 24 Þ = 2: 06 -> $t(24) = 2.06$
    def _r1(m):
        nonlocal count
        count += 1
        t_var = m.group(1).replace("*", "").strip()
        df = m.group(2).strip()
        val = m.group(3).replace(" ", "").replace(":", ".")
        return f"${t_var}({df}) = {val}$"
    new_text = RE_CORRUPTED_STATS_T.sub(_r1, new_text)

    # 2. p o 0: 01 -> $p < 0.01$
    def _r2(m):
        nonlocal count
        count += 1
        raw_val = m.group(1).replace(" ", "")
        val = f"0.{raw_val}" if not raw_val.startswith("0.") else raw_val
        return f"$p < {val}$"
    new_text = RE_CORRUPTED_STATS_P.sub(_r2, new_text)

    # 3. M = 4: 46 -> $M = 4.46$
    def _r3(m):
        nonlocal count
        count += 1
        m_var = m.group(1).replace("*", "").strip()
        val = m.group(2).replace(" ", "").replace(":", ".")
        return f"${m_var} = {val}$"
    new_text = RE_CORRUPTED_STATS_M.sub(_r3, new_text)

    # 4. s. d. =2.02 -> $SD = 2.02$
    def _r4(m):
        nonlocal count
        count += 1
        val = m.group(1).strip()
        return f"$SD = {val}$"
    new_text = RE_CORRUPTED_STATS_SD.sub(_r4, new_text)

    return new_text, count


def strip_manuscript_watermarks_text(text: str) -> Tuple[str, int]:
    """Strips NIH Public Access / Author Manuscript / Article In Press watermarks masquerading as headings."""
    new_text, count = RE_MANUSCRIPT_WATERMARK.subn('', text)
    return new_text, count


def normalize_unparenthesized_ref_years_text(text: str) -> Tuple[str, int]:
    """Formats references with unparenthesized author years ending in semicolons (e.g. Author N. 2012;)."""
    count = 0
    lines = text.splitlines()
    new_lines = []
    in_refs = False

    for line in lines:
        if re.match(r'^##\s+(?:References|Literature Cited|Bibliography)', line, re.I):
            in_refs = True
            new_lines.append(line)
            continue
        elif in_refs and line.startswith("## "):
            in_refs = False

        if in_refs:
            m = RE_UNPARENTHESIZED_REF.match(line)
            if m:
                count += 1
                authors, year, rest = m.groups()
                new_lines.append(f"- {authors.strip()} ({year}). {rest.strip()}")
                continue
        new_lines.append(line)

    return "\n".join(new_lines), count
