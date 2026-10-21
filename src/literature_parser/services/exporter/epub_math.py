"""
LaTeX ➔ MathML 轉換器
====================
將 Markdown 內的 LaTeX 數學式（$inline$ 與 $$block$$）轉成 EPUB 3 可用的 MathML。
"""

import logging
import re
from re import Match
from typing import ClassVar

logger = logging.getLogger("EpubExporter")


class LaTeXToMathML:
    """Lightweight, deterministic converter for LaTeX math formulas into EPUB 3 MathML."""

    GREEK_MAP: ClassVar[dict[str, str]] = {
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
        r"\epsilon": "ε", r"\eta": "η", r"\theta": "θ", r"\mu": "μ",
        r"\nu": "ν", r"\xi": "ξ", r"\pi": "π", r"\rho": "ρ",
        r"\sigma": "σ", r"\tau": "τ", r"\phi": "φ", r"\chi": "χ",
        r"\psi": "ψ", r"\omega": "ω", r"\Delta": "Δ", r"\Sigma": "Σ",
    }  # fmt: skip

    SYMBOL_MAP: ClassVar[dict[str, str]] = {
        r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥",
        r"\ne": "≠", r"\neq": "≠", r"\approx": "≈", r"\pm": "±",
        r"\times": "×", r"\div": "÷", r"\cdot": "·", r"\infty": "∞",
        r"\rightarrow": "→", r"\leftarrow": "←", r"\Rightarrow": "⇒",
    }  # fmt: skip

    @classmethod
    def convert_formula(cls, formula: str, display_block: bool = False) -> str:
        """Transforms inline or display LaTeX math into standard MathML.

        Args:
            formula: 原始 LaTeX 公式字串（不含 $ 界定符）。
            display_block: True 時輸出 display="block" 的區塊公式。

        Returns:
            MathML 字串；公式為空白時回傳空字串。
        """
        clean = formula.strip()
        if not clean:
            return ""

        # Normalize common LaTeX tokens
        for token, sym in cls.GREEK_MAP.items():
            clean = clean.replace(token, sym)
        for token, sym in cls.SYMBOL_MAP.items():
            clean = clean.replace(token, sym)

        # Fractions: \frac{num}{den} -> <mfrac><mrow>num</mrow><mrow>den</mrow></mfrac>
        def _frac_sub(m: Match[str]) -> str:
            """Builds an <mfrac> element from a \\frac regex match.

            Args:
                m: 匹配 \\frac{num}{den} 的 regex Match。

            Returns:
                對應的 <mfrac> MathML 字串。
            """
            return f"<mfrac><mrow>{m.group(1)}</mrow><mrow>{m.group(2)}</mrow></mfrac>"

        clean = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", _frac_sub, clean)

        # Superscript: a^{b} or a^b
        clean = re.sub(
            r"([A-Za-z0-9α-ω\)]+)\^\{([^{}]+)\}", r"<msup><mrow>\1</mrow><mrow>\2</mrow></msup>", clean
        )
        clean = re.sub(
            r"([A-Za-z0-9α-ω\)]+)\^([A-Za-z0-9])", r"<msup><mrow>\1</mrow><mrow>\2</mrow></msup>", clean
        )

        # Subscript: a_{b} or a_b
        clean = re.sub(
            r"([A-Za-z0-9α-ω\)]+)_\{([^{}]+)\}", r"<msub><mrow>\1</mrow><mrow>\2</mrow></msub>", clean
        )
        clean = re.sub(
            r"([A-Za-z0-9α-ω\)]+)_([A-Za-z0-9])", r"<msub><mrow>\1</mrow><mrow>\2</mrow></msub>", clean
        )

        # Remove remaining LaTeX styling tokens (\text, \mathit, \mathbf)
        clean = re.sub(r"\\(?:text|mathit|mathbf|mathrm)\{([^{}]+)\}", r"\1", clean)
        clean = clean.replace(r"\,", " ").replace(r"\;", " ").replace(r"\quad", "  ")

        attr = ' display="block"' if display_block else ""
        return f'<math xmlns="http://www.w3.org/1998/Math/MathML"{attr}><mrow>{clean}</mrow></math>'

    @classmethod
    def process_markdown_math(cls, text: str) -> str:
        """Finds all $$block$$ and $inline$ formulas and replaces with MathML.

        Args:
            text: 含 LaTeX 公式的 Markdown 文字。

        Returns:
            公式已替換為 MathML 的文字。
        """
        # 1. Protect currency like $15.50, $100 before math matching
        text = re.sub(r"(?<!\\)\$(\d+(?:\.\d+)?)", r"&#36;\1", text)

        # 2. Block math: $$ ... $$
        def _replace_block(m: Match[str]) -> str:
            """Converts a $$...$$ match into a display-block MathML paragraph.

            Args:
                m: 匹配區塊公式的 regex Match。

            Returns:
                前後各留空行的區塊 MathML 字串。
            """
            return "\n\n" + cls.convert_formula(m.group(1), display_block=True) + "\n\n"

        text = re.sub(r"\$\$(.+?)\$\$", _replace_block, text, flags=re.DOTALL)

        # 3. Inline math: $ ... $ (strictly requiring non-space edges)
        def _replace_inline(m: Match[str]) -> str:
            """Converts a $...$ match into inline MathML.

            Args:
                m: 匹配行內公式的 regex Match。

            Returns:
                行內 MathML 字串。
            """
            content = m.group(1)
            return cls.convert_formula(content, display_block=False)

        text = re.sub(r"(?<![\w\\])\$(?!\s)([^\$\n]+?)(?<!\s)(?<!\\)\$(?!\w)", _replace_inline, text)
        return text
