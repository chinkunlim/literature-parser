"""
Mathematical & Statistical Formula Detector and LaTeX Converter
===============================================================
Converts mathematical expressions, Greek symbols, and statistical notations
into standard LaTeX ($...$ inline and $$...$$ display block). Never uses screenshots.
"""

import re

# Greek symbols to LaTeX mappings
GREEK_MAP = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
    'ε': r'\epsilon', 'θ': r'\theta', 'λ': r'\lambda', 'μ': r'\mu',
    'π': r'\pi', 'ρ': r'\rho', 'σ': r'\sigma', 'τ': r'\tau',
    'φ': r'\phi', 'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
    'Δ': r'\Delta', 'Σ': r'\Sigma', 'Ω': r'\Omega'
}

# Math operators to LaTeX mappings
MATH_SYMBOLS = {
    '≤': r'\le', '≥': r'\ge', '≠': r'\neq', '≈': r'\approx',
    '±': r'\pm', '×': r'\times', '÷': r'\div', '∑': r'\sum',
    '∏': r'\prod', '√': r'\sqrt', '∞': r'\infty', '∫': r'\int'
}

# Combined character→latex map for run-grouping
_ALL_MATH_CHARS = {**GREEK_MAP, **MATH_SYMBOLS}


class MathLaTeXConverter:
    """Detects and converts math formulas to clean LaTeX syntax."""

    @classmethod
    def convert_symbols(cls, text: str) -> str:
        """
        Replaces unicode math characters with LaTeX equivalents.

        Adjacent math symbols (e.g. ``α + β``) are grouped into a single
        ``$...$ `` span instead of producing colliding ``$\\alpha$$\\beta$``.
        """
        if not any(ch in text for ch in _ALL_MATH_CHARS):
            return text

        result = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in _ALL_MATH_CHARS:
                # Collect a contiguous run of math chars and ASCII math operators
                run = []
                j = i
                while j < len(text):
                    c = text[j]
                    if c in _ALL_MATH_CHARS:
                        run.append(_ALL_MATH_CHARS[c])
                        j += 1
                    elif c in ('+', '-', '/', '*', '=', '<', '>', ' ', '(', ')') and j > i:
                        # Allow these ASCII chars inside the run (context)
                        # but only between math chars, not as trailing
                        # peek ahead: is the next non-space char also a math char?
                        k = j + 1
                        while k < len(text) and text[k] == ' ':
                            k += 1
                        if k < len(text) and text[k] in _ALL_MATH_CHARS:
                            run.append(c)
                            j += 1
                        else:
                            break
                    else:
                        break
                result.append('$' + ''.join(run) + '$')
                i = j
            else:
                result.append(ch)
                i += 1

        return ''.join(result)

    @classmethod
    def format_statistical_notations(cls, text: str) -> str:
        """
        Formats standard APA/textbook statistical notations into LaTeX math.
        e.g., 'p < .05' -> '$p < .05$', 't(28) = 2.45' -> '$t(28) = 2.45$', 'R^2 = .45' -> '$R^2 = .45$'
        """
        # p-value: p < .05, p = .001, p > .10
        text = re.sub(
            r'(?<!\w)(?:\*|_)?\b([pP])(?:\*|_)?\s*([<>=≤≥≠≈])\s*(\.?\d+)',
            lambda m: f"${m.group(1)} {m.group(2)} {m.group(3)}$",
            text
        )

        # t-test, F-test, r-value, d-value, z-score: t(28) = 2.45, F(1, 40) = 5.12
        text = re.sub(
            r'(?<!\w)(?:\*|_)?\b([tFrRzd])(?:\*|_)?\s*\(([^)]+)\)\s*=\s*([-+]?\d*\.?\d+)',
            lambda m: f"${m.group(1)}({m.group(2)}) = {m.group(3)}$",
            text
        )

        # r = .45, d = 0.8, z = 1.41
        text = re.sub(
            r'(?<!\w)(?:\*|_)?([rdz])(?:\*|_)?\s*=\s*([-+]?\d*\.?\d+)',
            lambda m: f"${m.group(1)} = {m.group(2)}$",
            text
        )

        # Superscripts: x^2, N^2, R^2, eta^2
        text = re.sub(r'\b([a-zA-Z])\^(\d+)', r'$\1^{\2}$', text)

        return text

    @classmethod
    def heal_shattered_math(cls, text: str) -> str:
        r"""
        Heals shattered formula fragments where vertical offsets (superscripts/subscripts)
        split math into isolated single-character lines or interleaved words.
        """
        if not text:
            return ""

        # 1. Pearson r formula fragments:
        # Matches shattered versions like:
        # Z \n+ Z \n+ ) \n+ sum of the cross products ... n
        pearson_pattern = (
            r'(?:Z\s*\n+\s*Z\s*\n+\s*\)\s*\n+)?'
            r'sum\s+of\s+(?:the\s+)?cross\s+products\s+of\s+the\s+'
            r'(?:z\s+)?scores\s*(?:\(i\.e\.,\s*)?'
            r'(?:[ZXY\s\n\)\(\,r\.\:\;]*?)'
            r'(?:number\s+of\s+cases\s*\n+\s*n|n\s*\n+\s*where)'
        )
        text = re.sub(
            pearson_pattern,
            lambda m: r'$$\displaystyle r = \dfrac{\text{sum of cross products of } z \text{ scores}}{n} = \dfrac{\sum(Z_X Z_Y)}{n}$$' + '\n\n',
            text,
            flags=re.I
        )

        # 2. Heal isolated single-variable subscript splits:
        # 'Z \n\n X' -> '$Z_X$', 'Z \n\n Y' -> '$Z_Y$'
        text = re.sub(r'(?m)^Z\s*\n{1,3}\s*X\s*$', r'$Z_X$', text)
        text = re.sub(r'(?m)^Z\s*\n{1,3}\s*Y\s*$', r'$Z_Y$', text)
        text = re.sub(r'(?m)^Z\s*\n{1,3}\s*Z\s*\n{1,3}\s*\)', r'$Z_X Z_Y)$', text)

        # 3. Heal runs of 3+ single-character lines:
        # e.g., 'X \n Y \n = \n 1' -> '$X Y = 1$'
        def _collapse_char_lines(m):
            block = m.group(0)
            chars = [l.strip() for l in block.splitlines() if l.strip()]
            joined = ' '.join(chars)
            return f"${joined}$"

        text = re.sub(
            r'(?m)(?:^[a-zA-Z0-9\(\)\=\+\-\/\*]\s*$\n?){3,}',
            _collapse_char_lines,
            text
        )

        return text

    @classmethod
    def repair_symbol_artifacts(cls, text: str) -> str:
        r"""
        Repairs symbol collisions:
        1. Infix Greek symbols inside words (e.g. 'popula$\mu$tion' -> 'population $\mu$')
        2. Detached exponents (e.g. '$\chi$ 2' -> '$\chi^2$', '$\eta$ 2' -> '$\eta^2$', '$R$ 2' -> '$R^2$')
        """
        if not text:
            return ""

        # Detached superscripts: '$\chi$ 2' -> '$\chi^2$', '$R$ 2' -> '$R^2$'
        text = re.sub(r'\$([a-zA-Z\\]+)\$\s*(\d+)', r'$\1^{\2}$', text)
        text = re.sub(r'(?<![a-zA-Z\\])(\\chi|\\eta|R|r)\s*\^?\s*2\b', r'$\1^2$', text)

        # Infix Greek symbols inside English words
        def _fix_infix(m):
            prefix = m.group(1)
            sym = m.group(2)
            suffix = m.group(3)
            # Recombine word and place math symbol after it
            return f"{prefix}{suffix} ${sym}$"

        text = re.sub(
            r'([a-zA-Z]{2,})\$([\\a-zA-Z]+)\$([a-zA-Z]{2,})',
            _fix_infix,
            text
        )

        return text

    @classmethod
    def format_textbook_equations(cls, text: str) -> str:
        r"""
        Reconstructs common textbook statistical formulas as display LaTeX math.
        Enforces \dfrac and \displaystyle to guarantee uniform 100% font sizing
        without shrinking fraction numerators/denominators.
        """
        # First heal shattered fragments and repair symbol artifacts
        text = cls.heal_shattered_math(text)
        text = cls.repair_symbol_artifacts(text)

        # z-score general formula
        text = re.sub(
            r'(?:\*z\*|z)\s+score\s*=\s*(?:raw\s+score\s+mean|raw\s+score\s*-\s*mean)\s+standard\s+deviation\s*=\s*\*?X\*?\s*\*?X\*?\s*\*?SD\*?',
            lambda m: r'$$\displaystyle \text{z score} = \dfrac{\text{raw score} - \text{mean}}{\text{standard deviation}} = \dfrac{X - \bar{X}}{SD}$$',
            text, flags=re.I
        )
        # z-score calculation step
        text = re.sub(
            r'(?:\*z\*|z)\s+score\s*=\s*(?:raw\s+score\s+mean|raw\s+score\s*-\s*mean)\s+standard\s+deviation\s*=\s*(\d+)\s+(\d+)\s+([\d\.]+)\s*=\s*(\d+)\s+([\d\.]+)\s*=\s*([-\d\.]+)',
            lambda m: r'$$\displaystyle \text{z score} = \dfrac{' + m.group(1) + ' - ' + m.group(2) + '}{' + m.group(3) + r'} = \dfrac{' + m.group(4) + '}{' + m.group(5) + '} = ' + m.group(6) + '$$',
            text, flags=re.I
        )
        # Cohen's d formula
        text = re.sub(
            r'(?:\*d\*|d)\s*=\s*mean\s+difference\s+standard\s+deviation\s*=\s*\*?M\*?\s*1\s*\*?M\*?\s*2\s*\*?SD\*?',
            lambda m: r'$$\displaystyle d = \dfrac{\text{mean difference}}{\text{standard deviation}} = \dfrac{M_1 - M_2}{SD}$$',
            text, flags=re.I
        )
        # Mean formula
        text = re.sub(
            r'Mean\s*=\s*(?:a|\$\\sum\$|\\sum)\s*\*?X\*?\s*\*?n\*?\s*=\s*1\s*\+\s*2\s*\+\s*3\s*3\s*=\s*6\s*3\s*=\s*2',
            lambda m: r'$$\displaystyle \text{Mean} = \dfrac{\sum X}{n} = \dfrac{1 + 2 + 3}{3} = \dfrac{6}{3} = 2$$',
            text, flags=re.I
        )
        # Pearson r formula
        text = re.sub(
            r'(?:\*r\*|r)\s*=\s*sum of the cross products of the (?:\*z\*|z) scores number of cases\s*=\s*(?:a|\$\\sum\$|\\sum)\s*\(\s*\*?Z\*?\s*\*?X\*?\s*\*?Z\*?\s*\*?Y\*?\s*\)\s*\*?n\*?',
            lambda m: r'$$\displaystyle r = \dfrac{\text{sum of cross products of } z \text{ scores}}{n} = \dfrac{\sum(Z_X Z_Y)}{n}$$',
            text, flags=re.I
        )
        return text


    @classmethod
    def ensure_uniform_fraction_sizing(cls, text: str) -> str:
        r"""
        Converts any remaining standard \frac into \dfrac and prepends \displaystyle
        to display math blocks containing fractions to keep all font sizes identical.
        """
        # Upgrade any \frac to \dfrac
        text = re.sub(r'\\frac\{', r'\\dfrac{', text)

        # Inside $$...$$, if dfrac is used and \displaystyle is not yet present, add it
        def _add_displaystyle(match):
            content = match.group(1).strip()
            if r'\dfrac' in content and not content.startswith(r'\displaystyle'):
                return f"$$\\displaystyle {content}$$"
            return f"$${content}$$"

        text = re.sub(r'\$\$(.*?)\$\$', _add_displaystyle, text, flags=re.DOTALL)
        return text

    @classmethod
    def format_display_equations(cls, text: str) -> str:
        """
        Detects standalone formula lines and encloses in display math ($$...$$).
        e.g., 'Y = beta_0 + beta_1 * X'
        """
        lines = text.splitlines()
        formatted_lines = []
        for line in lines:
            s = line.strip()
            # If line is a pure equation: starts with variable, contains '=' and math operators
            if re.match(r'^[a-zA-Z]\s*=\s*[-+a-zA-Z0-9\s\\*\/^_()]+$', s) and not s.endswith('.'):
                if not (s.startswith('$') and s.endswith('$')):
                    # Check if contains operators like +, -, *, /, ^
                    if any(op in s for op in ('+', '-', '*', '/', '^', '\\')):
                        formatted_lines.append(f"\n$$\\displaystyle {s}$$\n")
                        continue
            formatted_lines.append(line)
        return '\n'.join(formatted_lines)

    @classmethod
    def check_equation_balance(cls, text: str) -> dict:
        """
        Validates LaTeX math delimiter parity and brace balancing.
        Returns a dict: {'balanced': bool, 'issues': list}
        """
        issues = []
        # Check $$ parity
        double_dollars = text.count('$$')
        if double_dollars % 2 != 0:
            issues.append(f"Unpaired display math delimiter '$$' (count: {double_dollars})")

        # Strip display math to test single $ inline math parity
        cleaned_for_inline = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
        single_dollars = cleaned_for_inline.count('$')
        if single_dollars % 2 != 0:
            issues.append(f"Unpaired inline math delimiter '$' (count: {single_dollars})")

        # Check brace balance inside math blocks
        for block in re.findall(r'\$\$(.*?)\$\$', text, flags=re.DOTALL):
            if block.count('{') != block.count('}'):
                issues.append(f"Mismatched curly braces in display formula: {block[:60]}...")

        return {
            'balanced': len(issues) == 0,
            'issues': issues
        }

    @classmethod
    def process_text(cls, text: str) -> str:
        """Full pipeline for mathematical formula normalization with uniform font sizing."""
        from book_processor.parsers.math.apa_stats_normalizer import APAStatsNormalizer
        text = cls.convert_symbols(text)
        text = APAStatsNormalizer.normalize_text(text)
        text = cls.format_textbook_equations(text)
        text = cls.format_statistical_notations(text)
        text = cls.format_display_equations(text)
        text = cls.ensure_uniform_fraction_sizing(text)
        return text
