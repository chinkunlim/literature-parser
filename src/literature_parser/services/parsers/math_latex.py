"""
Mathematical & Statistical Formula Detector and LaTeX Converter
===============================================================
Converts mathematical expressions, Greek symbols, and statistical notations
into standard LaTeX ($...$ inline and $$...$$ display block). Never uses screenshots.
"""

import re
from typing import Any

# Greek symbols to LaTeX mappings
GREEK_MAP: dict[str, str] = {
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\epsilon",
    "θ": r"\theta",
    "λ": r"\lambda",
    "μ": r"\mu",
    "π": r"\pi",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "φ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    "Δ": r"\Delta",
    "Σ": r"\Sigma",
    "Ω": r"\Omega",
}

MATH_SYMBOLS: dict[str, str] = {
    "≤": r"\le",
    "≥": r"\ge",
    "≠": r"\neq",
    "≈": r"\approx",
    "±": r"\pm",
    "×": r"\times",
    "÷": r"\div",
    "∑": r"\sum",
    "∏": r"\prod",
    "√": r"\sqrt",
    "∞": r"\infty",
    "∫": r"\int",
    "⫽": "=",
    "⫹": "+",
    "⬍": "<",
    "ⱕ": r"\le",
    "␳": r"\rho",
    "ⴱ": "*",
    "¼": "=",
    "⫾": r"\pm",
}

# Combined character→latex map for run-grouping
_ALL_MATH_CHARS: dict[str, str] = {**GREEK_MAP, **MATH_SYMBOLS}


class MathLaTeXConverter:
    """Detects and converts math formulas to clean LaTeX syntax."""

    @staticmethod
    def _consume_math_run(text: str, start: int) -> tuple[str, int]:
        """Consumes a contiguous run of math characters and bridging ASCII operators.

        Args:
            text: Full input text string.
            start: Starting index where a math character was detected.

        Returns:
            Tuple of (formatted inline LaTeX string, next index after the run).
        """
        run: list[str] = []
        j = start
        while j < len(text):
            c = text[j]
            if c in _ALL_MATH_CHARS:
                run.append(_ALL_MATH_CHARS[c])
                j += 1
            elif c in ("+", "-", "/", "*", "=", "<", ">", " ", "(", ")") and j > start:
                k = j + 1
                while k < len(text) and text[k] == " ":
                    k += 1
                if k < len(text) and text[k] in _ALL_MATH_CHARS:
                    run.append(c)
                    j += 1
                else:
                    break
            else:
                break
        return "$" + "".join(run) + "$", j

    @classmethod
    def convert_symbols(cls, text: str) -> str:
        """Replaces unicode math characters with LaTeX equivalents.

        Adjacent math symbols (e.g. ``α + β``) are grouped into a single
        ``$...$`` span instead of producing colliding ``$\\alpha$$\\beta$``.

        Args:
            text: Input text containing unicode math or Greek characters.

        Returns:
            Text with unicode math symbols converted to inline LaTeX spans.
        """
        if not any(ch in text for ch in _ALL_MATH_CHARS):
            return text

        result: list[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in _ALL_MATH_CHARS:
                span, i = cls._consume_math_run(text, i)
                result.append(span)
            else:
                result.append(ch)
                i += 1

        return "".join(result)

    @classmethod
    def format_statistical_notations(cls, text: str) -> str:
        """Formats standard APA/textbook statistical notations into LaTeX math.

        e.g., 'p < .05' -> '$p < .05$', 't(28) = 2.45' -> '$t(28) = 2.45$', 'R^2 = .45' -> '$R^2 = .45$'

        Args:
            text: Input text containing raw statistical notations.

        Returns:
            Text with statistical expressions wrapped in inline LaTeX math.
        """
        # p-value: p < .05, p = .001, p > .10
        text = re.sub(
            r"(?<!\w)(?:\*|_)?\b([pP])(?:\*|_)?\s*([<>=≤≥≠≈])\s*(\.?\d+)",
            lambda m: f"${m.group(1)} {m.group(2)} {m.group(3)}$",
            text,
        )

        # t-test, F-test, r-value, d-value, z-score: t(28) = 2.45, F(1, 40) = 5.12
        text = re.sub(
            r"(?<!\w)(?:\*|_)?\b([tFrRzd])(?:\*|_)?\s*\(([^)]+)\)\s*=\s*([-+]?\d*\.?\d+)",
            lambda m: f"${m.group(1)}({m.group(2)}) = {m.group(3)}$",
            text,
        )

        # r = .45, d = 0.8, z = 1.41
        text = re.sub(
            r"(?<!\w)(?:\*|_)?([rdz])(?:\*|_)?\s*=\s*([-+]?\d*\.?\d+)",
            lambda m: f"${m.group(1)} = {m.group(2)}$",
            text,
        )

        # Superscripts: x^2, N^2, R^2, eta^2
        text = re.sub(r"\b([a-zA-Z])\^(\d+)", r"$\1^{\2}$", text)

        return text

    @classmethod
    def heal_shattered_math(cls, text: str) -> str:
        r"""Heals shattered formula fragments where vertical offsets split math into single-character lines.

        Args:
            text: Input Markdown text that may contain shattered multi-line formula fragments.

        Returns:
            Text with shattered math fragments reassembled into LaTeX math expressions.
        """
        if not text:
            return ""

        # 1. Pearson r formula fragments:
        pearson_pattern = (
            r"(?:Z\s*\n+\s*Z\s*\n+\s*\)\s*\n+)?"
            r"sum\s+of\s+(?:the\s+)?cross\s+products\s+of\s+the\s+"
            r"(?:z\s+)?scores\s*(?:\(i\.e\.,\s*)?"
            r"(?:[ZXY\s\n\)\(\,r\.\:\;]*?)"
            r"(?:number\s+of\s+cases\s*\n+\s*n|n\s*\n+\s*where)"
        )
        text = re.sub(
            pearson_pattern,
            lambda m: (
                r"$$\displaystyle r = \dfrac{\text{sum of cross products of } z \text{ scores}}{n}"
                r" = \dfrac{\sum(Z_X Z_Y)}{n}$$" + "\n\n"
            ),
            text,
            flags=re.IGNORECASE,
        )

        # 2. Heal isolated single-variable subscript splits:
        text = re.sub(r"(?m)^Z\s*\n{1,3}\s*X\s*$", r"$Z_X$", text)
        text = re.sub(r"(?m)^Z\s*\n{1,3}\s*Y\s*$", r"$Z_Y$", text)
        text = re.sub(r"(?m)^Z\s*\n{1,3}\s*Z\s*\n{1,3}\s*\)", r"$Z_X Z_Y)$", text)

        # 3. Heal runs of 3+ single-character lines:
        def _collapse_char_lines(m: re.Match[str]) -> str:
            """Collapses a regex match of single-character lines into an inline LaTeX span.

            Args:
                m: Regex match object containing consecutive single-character lines.

            Returns:
                Single-line inline LaTeX expression.
            """
            block = m.group(0)
            chars = [line.strip() for line in block.splitlines() if line.strip()]
            joined = " ".join(chars)
            return f"${joined}$"

        text = re.sub(
            r"(?m)(?:^[a-zA-Z0-9\(\)\=\+\-\/\*]\s*$\n?){3,}",
            _collapse_char_lines,
            text,
        )

        return text

    @classmethod
    def repair_symbol_artifacts(cls, text: str) -> str:
        r"""Repairs symbol collisions such as infix Greek symbols inside words and detached exponents.

        1. Infix Greek symbols inside words (e.g. 'popula$\mu$tion' -> 'population $\mu$')
        2. Detached exponents (e.g. '$\chi$ 2' -> '$\chi^2$', '$\eta$ 2' -> '$\eta^2$', '$R$ 2' -> '$R^2$')

        Args:
            text: Input text containing symbol collision artifacts.

        Returns:
            Repaired text with properly placed LaTeX symbols and superscripts.
        """
        if not text:
            return ""

        # Detached superscripts: '$\chi$ 2' -> '$\chi^2$', '$R$ 2' -> '$R^2$'
        text = re.sub(r"\$([a-zA-Z\\]+)\$\s*(\d+)", r"$\1^{\2}$", text)
        text = re.sub(r"(?<![a-zA-Z\\])(\\chi|\\eta|R|r)\s*\^?\s*2\b", r"$\1^2$", text)

        # Infix Greek symbols inside English words
        def _fix_infix(m: re.Match[str]) -> str:
            """Moves an inline math symbol out of the middle of an English word.

            Args:
                m: Regex match with (word_prefix, math_symbol, word_suffix) groups.

            Returns:
                Recombined English word followed by the inline math symbol.
            """
            prefix = m.group(1)
            sym = m.group(2)
            suffix = m.group(3)
            return f"{prefix}{suffix} ${sym}$"

        text = re.sub(
            r"([a-zA-Z]{2,})\$([\\a-zA-Z]+)\$([a-zA-Z]{2,})",
            _fix_infix,
            text,
        )

        return text

    @classmethod
    def format_textbook_equations(cls, text: str) -> str:
        r"""Reconstructs common textbook statistical formulas as display LaTeX math.

        Enforces \dfrac and \displaystyle to guarantee uniform 100% font sizing
        without shrinking fraction numerators/denominators.

        Args:
            text: Input Markdown text containing textbook statistical equations.

        Returns:
            Text with standard textbook formulas converted to display LaTeX blocks.
        """
        text = cls.heal_shattered_math(text)
        text = cls.repair_symbol_artifacts(text)

        # z-score general formula
        text = re.sub(
            r"(?:\*z\*|z)\s+score\s*=\s*(?:raw\s+score\s+mean|raw\s+score\s*-\s*mean)\s+"
            r"standard\s+deviation\s*=\s*\*?X\*?\s*\*?X\*?\s*\*?SD\*?",
            lambda m: (
                r"$$\displaystyle \text{z score} = \dfrac{\text{raw score} - \text{mean}}"
                r"{\text{standard deviation}} = \dfrac{X - \bar{X}}{SD}$$"
            ),
            text,
            flags=re.IGNORECASE,
        )
        # z-score calculation step
        text = re.sub(
            r"(?:\*z\*|z)\s+score\s*=\s*(?:raw\s+score\s+mean|raw\s+score\s*-\s*mean)\s+"
            r"standard\s+deviation\s*=\s*(\d+)\s+(\d+)\s+([\d\.]+)\s*=\s*(\d+)\s+([\d\.]+)\s*=\s*([-\d\.]+)",
            lambda m: (
                r"$$\displaystyle \text{z score} = \dfrac{"
                + m.group(1)
                + " - "
                + m.group(2)
                + "}{"
                + m.group(3)
                + r"} = \dfrac{"
                + m.group(4)
                + "}{"
                + m.group(5)
                + "} = "
                + m.group(6)
                + "$$"
            ),
            text,
            flags=re.IGNORECASE,
        )
        # Cohen's d formula
        text = re.sub(
            r"(?:\*d\*|d)\s*=\s*mean\s+difference\s+standard\s+deviation\s*=\s*\*?M\*?\s*1\s*\*?M\*?\s*2\s*\*?SD\*?",
            lambda m: (
                r"$$\displaystyle d = \dfrac{\text{mean difference}}{\text{standard deviation}}"
                r" = \dfrac{M_1 - M_2}{SD}$$"
            ),
            text,
            flags=re.IGNORECASE,
        )
        # Mean formula
        text = re.sub(
            r"Mean\s*=\s*(?:a|\$\\sum\$|\\sum)\s*\*?X\*?\s*\*?n\*?\s*=\s*1\s*\+\s*2\s*\+\s*3\s*3\s*=\s*6\s*3\s*=\s*2",
            lambda m: r"$$\displaystyle \text{Mean} = \dfrac{\sum X}{n} = \dfrac{1 + 2 + 3}{3} = \dfrac{6}{3} = 2$$",
            text,
            flags=re.IGNORECASE,
        )
        # Pearson r formula
        text = re.sub(
            r"(?:\*r\*|r)\s*=\s*sum of the cross products of the (?:\*z\*|z) scores number of cases"
            r"\s*=\s*(?:a|\$\\sum\$|\\sum)\s*\(\s*\*?Z\*?\s*\*?X\*?\s*\*?Z\*?\s*\*?Y\*?\s*\)\s*\*?n\*?",
            lambda m: (
                r"$$\displaystyle r = \dfrac{\text{sum of cross products of } z \text{ scores}}{n}"
                r" = \dfrac{\sum(Z_X Z_Y)}{n}$$"
            ),
            text,
            flags=re.IGNORECASE,
        )
        return text

    @classmethod
    def ensure_uniform_fraction_sizing(cls, text: str) -> str:
        r"""Converts standard \frac into \dfrac and prepends \displaystyle to display math blocks.

        Args:
            text: Input text containing LaTeX math expressions.

        Returns:
            Text with uniform display-style fraction sizing applied.
        """
        # Upgrade any \frac to \dfrac
        text = re.sub(r"\\frac\{", r"\\dfrac{", text)

        def _add_displaystyle(match: re.Match[str]) -> str:
            r"""Prepends \displaystyle to a display math block if it contains \dfrac.

            Args:
                match: Regex match for a ``$$...$$`` display math block.

            Returns:
                Display math block string with ``\displaystyle`` ensured when needed.
            """
            content = match.group(1).strip()
            if r"\dfrac" in content and not content.startswith(r"\displaystyle"):
                return f"$$\\displaystyle {content}$$"
            return f"$${content}$$"

        text = re.sub(r"\$\$(.*?)\$\$", _add_displaystyle, text, flags=re.DOTALL)
        return text

    @classmethod
    def format_display_equations(cls, text: str) -> str:
        """Detects standalone formula lines and encloses them in display math ($$...$$).

        e.g., 'Y = beta_0 + beta_1 * X'

        Args:
            text: Input multi-line text to scan for standalone equations.

        Returns:
            Text with standalone equation lines wrapped in ``$$\\displaystyle ...$$``.
        """
        lines = text.splitlines()
        formatted_lines: list[str] = []
        for line in lines:
            s = line.strip()
            is_eq = bool(re.match(r"^[a-zA-Z]\s*=\s*[-+a-zA-Z0-9\s\\*\/^_()]+$", s)) and not s.endswith(".")
            is_wrapped = s.startswith("$") and s.endswith("$")
            has_op = any(op in s for op in ("+", "-", "*", "/", "^", "\\"))
            if is_eq and not is_wrapped and has_op:
                formatted_lines.append(f"\n$$\\displaystyle {s}$$\n")
            else:
                formatted_lines.append(line)
        return "\n".join(formatted_lines)

    @classmethod
    def check_equation_balance(cls, text: str) -> dict[str, Any]:
        """Validates LaTeX math delimiter parity and brace balancing.

        Args:
            text: Markdown text containing inline and display LaTeX math.

        Returns:
            Dictionary with keys ``balanced`` (bool) and ``issues`` (list of strings).
        """
        issues: list[str] = []
        # Check $$ parity
        double_dollars = text.count("$$")
        if double_dollars % 2 != 0:
            issues.append(f"Unpaired display math delimiter '$$' (count: {double_dollars})")

        # Strip display math to test single $ inline math parity
        cleaned_for_inline = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
        single_dollars = cleaned_for_inline.count("$")
        if single_dollars % 2 != 0:
            issues.append(f"Unpaired inline math delimiter '$' (count: {single_dollars})")

        # Check brace balance inside math blocks
        for block in re.findall(r"\$\$(.*?)\$\$", text, flags=re.DOTALL):
            if block.count("{") != block.count("}"):
                issues.append(f"Mismatched curly braces in display formula: {block[:60]}...")

        return {
            "balanced": len(issues) == 0,
            "issues": issues,
        }

    @classmethod
    def escape_currency_dollars(cls, text: str) -> str:
        r"""Escapes literal currency amounts and non-math triple dollar signs to HTML entity &#36;.

        Prevents KaTeX from misparsing currency and Markdown previewers from showing backslashes.
        e.g., '$3', '$$$' -> '&#36;3', '&#36;&#36;&#36;'

        Args:
            text: Input text that may contain currency dollar signs.

        Returns:
            Text with literal currency dollar signs replaced by ``&#36;``.
        """
        if not text:
            return ""
        # 1. Escape runs of $$$ (e.g. "Collect $$$")
        text = re.sub(r"(?<!\\)\${3,}", lambda m: "&#36;" * len(m.group(0)), text)
        # 2. Escape currency amounts like $3, $5, $100, $25.50 when not inside LaTeX math
        text = re.sub(r"(?<!\\)\$(?=\d+(?:[\.,]\d+)?\b(?!\$))", "&#36;", text)
        return text

    @classmethod
    def process_text(cls, text: str) -> str:
        """Runs the full pipeline for mathematical formula normalization with uniform font sizing.

        Args:
            text: Input Markdown text to normalize.

        Returns:
            Text with symbols, statistical notations, and equations converted to LaTeX.
        """
        from literature_parser.services.parsers.math.apa_stats_normalizer import APAStatsNormalizer

        text = cls.escape_currency_dollars(text)
        text = cls.convert_symbols(text)
        text = APAStatsNormalizer.normalize_text(text)
        text = cls.format_textbook_equations(text)
        text = cls.format_statistical_notations(text)
        text = cls.format_display_equations(text)
        text = cls.ensure_uniform_fraction_sizing(text)
        return text
