"""
List, Code Block & Footnote Parser
==================================
Handles ordered/unordered list detection, indented code blocks, and page bottom footnotes.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ListParser:
    """Specialized formatter for lists, code blocks, and footnotes."""

    FOOTNOTE_NUMBER_PATTERN = r'^(?:\[(\d+)\]|\b(\d+)\b)\s+(.*)'
    CODE_INDICATORS = [
        r'\b(?:def\s+\w+\(|class\s+\w+:|import\s+\w+|from\s+\w+\s+import)\b',
        r'^\s*(?:if|elif|else|for|while|try|except|finally|with)\s+.*:$',
        r'^\s*(?:var|let|const|function)\s+\w+',
        r'^\s*(?:public|private|protected)\s+(?:class|static|void|int|double)',
    ]

    @classmethod
    def separate_footnotes(cls, lines_with_pos: list, page_height: float) -> tuple:
        """
        Identifies bottom-of-page footnote lines (typically bottom 15% of page)
        starting with a numeral or dagger and formats as Markdown footnotes [^X]: ...
        Returns: (body_lines, footnote_markdown_strings)
        """
        body_lines = []
        footnote_lines = []
        bottom_threshold = page_height * 0.85
        in_footnote = False

        for top, left, size, text in lines_with_pos:
            s = text.strip()
            if top >= bottom_threshold and size <= 12.5:
                m = re.match(cls.FOOTNOTE_NUMBER_PATTERN, s)
                if m:
                    fn_num = m.group(1) or m.group(2)
                    fn_content = m.group(3)
                    footnote_lines.append(f"[^{fn_num}]: {fn_content}")
                    in_footnote = True
                    continue
                elif in_footnote:
                    if footnote_lines:
                        footnote_lines[-1] += " " + s
                    continue
            in_footnote = False
            body_lines.append((top, left, size, text))

        return body_lines, footnote_lines

    @classmethod
    def detect_and_format_code_blocks(cls, text: str) -> str:
        """
        Detects consecutive lines containing programming keywords
        and formats them into fenced code blocks.
        """
        lines = text.splitlines()
        result = []
        code_chunk = []

        def is_code_line(l, in_chunk=False):
            trimmed = l.strip()
            if not trimmed:
                return in_chunk
            if in_chunk and (l.startswith('    ') or l.startswith('\t') or re.match(r'^\s*(?:return|print|pass|raise|break|continue)\b', l)):
                return True
            return any(re.search(pat, trimmed) for pat in cls.CODE_INDICATORS)

        for line in lines:
            if is_code_line(line, in_chunk=bool(code_chunk)):
                code_chunk.append(line)
            else:
                if len(code_chunk) >= 2:
                    result.append("```python\n" + '\n'.join(code_chunk) + "\n```")
                    code_chunk = []
                elif code_chunk:
                    result.extend(code_chunk)
                    code_chunk = []
                result.append(line)

        if len(code_chunk) >= 2:
            result.append("```python\n" + '\n'.join(code_chunk) + "\n```")
        elif code_chunk:
            result.extend(code_chunk)

        return '\n'.join(result)

    @classmethod
    def detect_and_format_lists(cls, text: str) -> str:
        """
        Ensures consistent bullet and numbering characters:
        - Replaces non-standard bullets ('•', '▪', '‣', '–') with '-'
        - Normalizes list items that don't have a space after digit
        """
        lines = text.splitlines()
        formatted = []
        for idx, line in enumerate(lines):
            s = line.strip()
            # Bullet list items: must not start with lowercase letter (which indicates hyphenated prose or en-dash)
            m_bullet = re.match(r'^[•▪‣–]\s*(.*)', s)
            if m_bullet:
                bullet_body = m_bullet.group(1).strip()
                if bullet_body and bullet_body[0].islower():
                    formatted.append(line)
                    continue
                indent = ' ' * (len(line) - len(line.lstrip()))
                formatted.append(f"{indent}- {m_bullet.group(1)}")
                continue

            # Numbered list items e.g., '1.Item' -> '1. Item'
            m_num = re.match(r'^(\d+)\.([^\s].*)', s)
            if m_num:
                indent = ' ' * (len(line) - len(line.lstrip()))
                formatted.append(f"{indent}{m_num.group(1)}. {m_num.group(2)}")
                continue

            formatted.append(line)
        return '\n'.join(formatted)
