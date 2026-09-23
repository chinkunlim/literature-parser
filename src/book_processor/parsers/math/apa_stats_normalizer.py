"""
APA Statistics & Mathematical Notation Normalizer
=================================================
Transforms inline academic psychological/biomedical statistical test reporting
(e.g., F(2, 82) = 19.2, p < .05, r = .77, ΔR² = .08, β = .32, M = 12.4, SD = 3.1)
into publication-grade inline LaTeX ($...$).
"""

import re


class APAStatsNormalizer:
    """Detects and normalizes APA-style in-text statistics into LaTeX math."""

    # 1. F-tests: F(1, 84) = 14.52, p < .001
    F_PATTERN = re.compile(
        r'\bF\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*([\d\.]+)(?:,\s*p\s*([<>=])\s*([\.\d]+))?',
        re.I
    )

    # 2. t-tests: t(84) = 2.45, p < .05
    T_PATTERN = re.compile(
        r'\bt\s*\(\s*(\d+)\s*\)\s*=\s*([-\d\.]+)(?:,\s*p\s*([<>=])\s*([\.\d]+))?',
        re.I
    )

    # 3. Correlations: r = .45, r(84) = .45, p < .01
    R_PATTERN = re.compile(
        r'\br(?:\s*\(\s*(\d+)\s*\))?\s*=\s*([-\d\.]+)(?:,\s*p\s*([<>=])\s*([\.\d]+))?',
        re.I
    )

    # 4. Chi-square: χ²(2, N = 86) = 5.4, p < .05 or chi-square(2) = 5.4
    CHI_PATTERN = re.compile(
        r'(?:χ²|chi-square|chi\^2)\s*\(\s*(\d+)(?:,\s*N\s*=\s*(\d+))?\s*\)\s*=\s*([\d\.]+)(?:,\s*p\s*([<>=])\s*([\.\d]+))?',
        re.I
    )

    # 5. Delta R-square / R-square change: ΔR² = .08, ΔR^2 = .08
    DELTA_R2_PATTERN = re.compile(
        r'(?:ΔR²|ΔR\^2|Delta\s*R\^2|Delta\s*R²)\s*=\s*([-\d\.]+)',
        re.I
    )

    # 6. Beta coefficients: β = .32, beta = .32
    BETA_PATTERN = re.compile(
        r'(?:β|beta)\s*=\s*([-\d\.]+)',
        re.I
    )

    # 7. Sample size: N = 86, n = 43
    N_PATTERN = re.compile(
        r'\b([Nn])\s*=\s*(\d+)\b'
    )

    # 8. Standalone p-values: p < .05, p = .001, ps > .05
    P_STANDALONE = re.compile(
        r'\bp\s*([<>=])\s*([\.\d]+)\b',
        re.I
    )
    PS_PLURAL = re.compile(
        r'\bps\s*([<>=])\s*([\.\d]+)\b',
        re.I
    )

    # 9. Mean and Standard Deviation: M = 12.4, SD = 3.2
    M_SD_PATTERN = re.compile(
        r'\bM\s*=\s*([-\d\.]+),\s*SD\s*=\s*([\d\.]+)\b'
    )

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalizes plain text containing statistical reports into LaTeX inline math.
        Skips blocks that are already wrapped in $...$ or code blocks.
        """
        if not text:
            return ""

        # Avoid processing code blocks or pre blocks
        if "```" in text or "<pre>" in text:
            return text

        # Helper to avoid double wrapping if already inside $...$
        def is_already_latex(start_pos: int, s: str) -> bool:
            left = s[:start_pos]
            return left.count('$') % 2 == 1

        res = text

        # Normalize M = x, SD = y -> $M = x, SD = y$
        res = cls.M_SD_PATTERN.sub(r'$M = \1, SD = \2$', res)

        # Normalize F-tests
        def replace_f(m):
            df1, df2, val, pop, pval = m.groups()
            if pop and pval:
                return f"$F({df1}, {df2}) = {val}, p {pop} {pval}$"
            return f"$F({df1}, {df2}) = {val}$"
        res = cls.F_PATTERN.sub(replace_f, res)

        # Normalize t-tests
        def replace_t(m):
            df, val, pop, pval = m.groups()
            if pop and pval:
                return f"$t({df}) = {val}, p {pop} {pval}$"
            return f"$t({df}) = {val}$"
        res = cls.T_PATTERN.sub(replace_t, res)

        # Normalize correlations: r = .xx or r(df) = .xx
        def replace_r(m):
            df, val, pop, pval = m.groups()
            df_str = f"({df})" if df else ""
            if pop and pval:
                return f"$r{df_str} = {val}, p {pop} {pval}$"
            return f"$r{df_str} = {val}$"
        res = cls.R_PATTERN.sub(replace_r, res)

        # Normalize Delta R^2
        res = cls.DELTA_R2_PATTERN.sub(r'$\\Delta R^2 = \1$', res)

        # Normalize Beta
        res = cls.BETA_PATTERN.sub(r'$\\beta = \1$', res)

        # Normalize N = xx
        res = cls.N_PATTERN.sub(r'$\1 = \2$', res)

        # Normalize ps > .05
        res = cls.PS_PLURAL.sub(r'$p\\text{s} \1 \2$', res)

        # Clean up any accidental nested $ e.g. $$...$$ inside prose where not intended
        res = re.sub(r'\$\$([^\$]+)\$\$', r'$\1$', res)

        return res
