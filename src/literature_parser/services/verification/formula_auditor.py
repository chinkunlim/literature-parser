"""Mathematical and Statistical Formula Auditor Service.

Verifies LaTeX mathematical formula delimiters, MathML translation compatibility,
APA statistical notation standardization, and currency dollar-sign escape safety.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


class FormulaAuditor:
    """Audits and validates mathematical formulas and statistical expressions in Markdown."""

    @classmethod
    def audit(
        cls,
        markdown_text: str,
        auto_fix: bool = True,
    ) -> Tuple[List[AuditIssue], str, int]:
        """Performs comprehensive formula and statistical notation verification.

        Args:
            markdown_text: Raw Markdown content to audit.
            auto_fix: Whether to automatically repair unescaped currency and statistical notation.

        Returns:
            Tuple of (detected_issues, cleaned_markdown, total_repaired_count).
        """
        issues: List[AuditIssue] = []
        current_md = markdown_text
        repaired_count = 0

        # 1. Currency dollar sign check and escape protection: '$100', '$25.50'
        # An unescaped '$' followed by digits will corrupt inline math parsing in MathML/KaTeX.
        currency_pat = re.compile(r'(?<!\\)\$(\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|trillion))?)\b')
        currency_matches = list(currency_pat.finditer(current_md))
        for m in currency_matches:
            val = m.group(0)
            issues.append(
                AuditIssue(
                    severity="WARNING",
                    category="FORMULA_CURRENCY_UNESCAPED",
                    line_num=None,
                    snippet=val,
                    message=f"Unescaped currency dollar sign '{val}' may trigger unintentional LaTeX math mode.",
                    suggested_fix=f"\\{val}",
                    auto_fixable=True,
                    confidence=0.95,
                )
            )

        if auto_fix and currency_matches:
            current_md = currency_pat.sub(r'\\\$\1', current_md)
            repaired_count += len(currency_matches)

        # 2. Block equation delimiter balance: check '$$' pairs
        double_dollar_count = current_md.count("$$")
        if double_dollar_count % 2 != 0:
            issues.append(
                AuditIssue(
                    severity="ERROR",
                    category="FORMULA_BLOCK_DELIMITER_UNBALANCED",
                    line_num=None,
                    snippet="$$",
                    message=f"Unbalanced block LaTeX math delimiters: found {double_dollar_count} '$$' markers (must be even).",
                    suggested_fix="Close any unclosed '$$' block math tags.",
                    auto_fixable=False,
                    confidence=1.0,
                )
            )

        # 3. Inline equation delimiter balance: check unescaped single '$'
        # Mask out '$$' and valid '\$' before counting single '$'
        masked = re.sub(r'\$\$[\s\S]*?\$\$', '', current_md)
        masked = re.sub(r'\\\$', '', masked)
        single_dollar_count = masked.count("$")
        if single_dollar_count % 2 != 0:
            issues.append(
                AuditIssue(
                    severity="ERROR",
                    category="FORMULA_INLINE_DELIMITER_UNBALANCED",
                    line_num=None,
                    snippet="$",
                    message=f"Unbalanced inline LaTeX math delimiters: found {single_dollar_count} unescaped '$' markers.",
                    suggested_fix="Escape standalone currency dollars with '\\$' or close the inline math tag.",
                    auto_fixable=False,
                    confidence=0.9,
                )
            )

        # 4. APA Statistical notation standardization: t(df), F(df1, df2), p < .05, R^2
        # Auto-standardize raw plain-text statistical test outputs
        stat_patterns = [
            # t-test: t(24) = 2.15 -> *t*(24) = 2.15
            (re.compile(r'(?<!\*)\bt\s*\((\d+)\)\s*=\s*([-+]?\d*\.?\d+)'), r'*t*(\1) = \2'),
            # F-test: F(1, 48) = 4.20 -> *F*(1, 48) = 4.20
            (re.compile(r'(?<!\*)\bF\s*\((\d+),\s*(\d+)\)\s*=\s*([-+]?\d*\.?\d+)'), r'*F*(\1, \2) = \3'),
            # p-value: p < .05, p = .012 -> *p* < .05
            (re.compile(r'(?<!\*)\bp\s*([<>=])\s*(\.?\d+)'), r'*p* \1 \2'),
            # R-squared: R2 = .35 -> *R*² = .35
            (re.compile(r'(?<!\*)\bR2\s*=\s*(\.?\d+)'), r'*R*² = \1'),
        ]

        stat_fixes = 0
        for pat, repl in stat_patterns:
            m_stats = list(pat.finditer(current_md))
            if m_stats:
                stat_fixes += len(m_stats)
                if auto_fix:
                    current_md = pat.sub(repl, current_md)

        if stat_fixes > 0:
            issues.append(
                AuditIssue(
                    severity="INFO",
                    category="FORMULA_APA_STATISTICS_STANDARDIZED",
                    line_num=None,
                    snippet=f"{stat_fixes} statistical expressions",
                    message=f"Standardized {stat_fixes} APA statistical notation occurrences (italicizing t, F, p, R²).",
                    suggested_fix="Standardize statistical test notation to standard APA format.",
                    auto_fixable=True,
                    confidence=1.0,
                )
            )
            if auto_fix:
                repaired_count += stat_fixes

        return issues, current_md, repaired_count
