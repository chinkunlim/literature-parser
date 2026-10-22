"""
Lexical & Formula Auditor (LexicalAuditor)
=========================================
Audits vocabulary health, dictionary coverage, OCR hyphenation repairs,
and LaTeX formula syntax:
- Hybrid dictionary verification with English morphological derivation.
- Automatic healing of line-wrap hyphens (e.g. bio- logy -> biology).
- Drop-cap fragmentation repair.
- LaTeX delimiter symmetry ($ and $$) and shattered statistics normalization.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from literature_parser.config.processor_config import DEFAULT_DICT_PATH
from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)

# Common academic, psychological, and scientific vocabulary whitelist
ACADEMIC_WHITELIST: Set[str] = {
    'doi', 'bart', 'retest', 'psychopharmacology', 'chicago', 'keywords', 'impulsivity',
    'delinquency', 'bilingual', 'bilingualism', 'cognitive', 'taxidriving', 'fmri',
    'prefrontal', 'et', 'al', 'longterm', 'alzheimer', 'psychol', 'exp', 'author',
    'anova', 'mri', 'p-value', 'sd', 'sem', 'deg', 'ci', 'df', 'iq', 'dna', 'rna',
    'posthoc', 'cronbach', 'likert', 'imrad', 'dataset', 'datasets', 'subscale', 'subscales',
}


class LexicalAuditor:
    """Audits spelling health, word repairs, and LaTeX mathematical delimiters."""

    def __init__(self, dict_path: Optional[str] = None):
        """Initializes LexicalAuditor with dictionary wordlist.

        Args:
            dict_path: Optional path to custom dictionary file.
        """
        self.dict_words: Set[str] = set()
        resolved_dict = dict_path or DEFAULT_DICT_PATH
        if os.path.exists(resolved_dict):
            try:
                with open(resolved_dict, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        w = line.strip().lower()
                        if w:
                            self.dict_words.add(w)
            except Exception as e:
                logger.debug("Failed loading dictionary from %s: %s", resolved_dict, e)

    def is_valid_word(self, token: str) -> bool:
        """Determines if token is a valid dictionary word, academic term, or derivative.

        Args:
            token: Raw word token.

        Returns:
            True if word is valid, False if suspect.
        """
        clean = token.strip(".,;:!?\"'()[]{}/*#–-—’“”‘$").lower()
        if not clean or re.match(r'^\d+(\.\d+)?$', clean) or re.match(r'^[ivxlcdm]+$', clean):
            return True

        clean = re.sub(r"['’]s$", "", clean)
        if clean in self.dict_words or clean in ACADEMIC_WHITELIST:
            return True

        # Morphological analysis (-ies, -ing, -ed, -s, -ly, prefixes)
        if clean.endswith('ies') and (clean[:-3] + 'y' in self.dict_words):
            return True
        if clean.endswith('ing') and (clean[:-3] in self.dict_words or clean[:-3] + 'e' in self.dict_words):
            return True
        if clean.endswith('ed') and (clean[:-2] in self.dict_words or clean[:-2] + 'e' in self.dict_words):
            return True
        if clean.endswith('s') and clean[:-1] in self.dict_words:
            return True
        if clean.endswith('ly') and clean[:-2] in self.dict_words:
            return True

        for pfx in ('re', 'un', 'non', 'co', 'anti', 'pre', 'post', 'sub'):
            if clean.startswith(pfx) and clean[len(pfx):] in self.dict_words:
                return True

        if '-' in clean:
            parts = clean.split('-')
            if all(self.is_valid_word(p) for p in parts if p):
                return True

        return False

    def audit(
        self,
        markdown_text: str,
        auto_fix: bool = True,
    ) -> Tuple[List[AuditIssue], str, int, float]:
        """Audits Markdown text for lexical, OCR, and LaTeX mathematical issues.

        Args:
            markdown_text: Raw or processed Markdown text.
            auto_fix: Whether to automatically repair line-wrap hyphens and formulas.

        Returns:
            Tuple of (list_of_issues, repaired_markdown, repaired_count, coverage_ratio).
        """
        issues: List[AuditIssue] = []
        repaired_md = markdown_text
        repaired_count = 0

        # 1. Broken Hyphenation at Line Breaks (e.g. bio-\nlogy -> biology)
        def fix_hyphen(match):
            nonlocal repaired_count
            w1 = match.group(1)
            w2 = match.group(2)
            joined = f"{w1}{w2}"
            if self.is_valid_word(joined):
                repaired_count += 1
                return joined
            return f"{w1}-{w2}"

        pattern_hyphen = re.compile(r'([a-zA-Z]{2,})-\s*\n+\s*([a-zA-Z]{2,})')
        if auto_fix:
            repaired_md = pattern_hyphen.sub(fix_hyphen, repaired_md)

        # 2. Broken Drop-Caps (e.g. T\n\nhis -> This)
        pattern_dropcap = re.compile(r'(?m)^([A-Z])\s*\n+\s*([a-z]{2,}\b)')
        def fix_dropcap(match):
            nonlocal repaired_count
            repaired_count += 1
            return f"{match.group(1)}{match.group(2)}"

        if auto_fix:
            repaired_md = pattern_dropcap.sub(fix_dropcap, repaired_md)

        # 3. LaTeX Delimiter Balance Check ($...$ and $$...$$)
        # Exclude escaped currency \$
        text_without_escaped_dollars = re.sub(r'\\\$', '', repaired_md)
        double_dollars = len(re.findall(r'\$\$', text_without_escaped_dollars))
        if double_dollars % 2 != 0:
            issues.append(AuditIssue(
                severity="ERROR",
                category="LEXICAL_LATEX_UNMATCHED_BLOCK",
                line_num=None,
                snippet="$$ ...",
                message=f"Unmatched display math $$ delimiters: found {double_dollars} instances.",
                auto_fixable=False,
            ))

        text_without_display_math = re.sub(r'\$\$.*?\$\$', '', text_without_escaped_dollars, flags=re.DOTALL)
        single_dollars = len(re.findall(r'\$', text_without_display_math))
        if single_dollars % 2 != 0:
            issues.append(AuditIssue(
                severity="WARNING",
                category="LEXICAL_LATEX_UNMATCHED_INLINE",
                line_num=None,
                snippet="$ ...",
                message=f"Odd count of inline math $ delimiters ({single_dollars}); possible unescaped currency.",
                suggested_fix="Escape unescaped currency symbols with \\$",
                auto_fixable=False,
            ))

        # 4. Shattered Statistical Math Normalization
        # e.g. F ( 2 , 4 0 ) -> F(2, 40)
        def fix_f_stat(m):
            nonlocal repaired_count
            df1 = re.sub(r'\s+', '', m.group(1))
            df2 = re.sub(r'\s+', '', m.group(2))
            val = m.group(3)
            repaired_count += 1
            return f"F({df1}, {df2}) = {val}"

        pattern_f = re.compile(r'\bF\s*\(\s*([\d\s]+?)\s*,\s*([\d\s]+?)\s*\)\s*=\s*(\d+(?:\.\d+)?)')
        if auto_fix:
            repaired_md = pattern_f.sub(fix_f_stat, repaired_md)

        # 5. Vocabulary Health & Dictionary Coverage
        words = re.findall(r'\b[a-zA-Z]{3,}\b', repaired_md)
        valid_words = 0
        suspect_words = []

        if self.dict_words and words:
            for w in words:
                if self.is_valid_word(w):
                    valid_words += 1
                else:
                    suspect_words.append(w)

            coverage = valid_words / len(words)
            if coverage < 0.90:
                issues.append(AuditIssue(
                    severity="WARNING",
                    category="LEXICAL_DICTIONARY_COVERAGE",
                    line_num=None,
                    snippet=", ".join(suspect_words[:8]),
                    message=f"Dictionary vocabulary coverage ({coverage:.1%}) is below expected 90% threshold.",
                    auto_fixable=False,
                ))
        else:
            coverage = 1.0

        return (issues, repaired_md, repaired_count, coverage)
