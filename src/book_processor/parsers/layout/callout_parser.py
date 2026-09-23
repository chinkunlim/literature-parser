"""
Callout, Exhibit & Figure Caption Formatter
===========================================
Detects pedagogical sidebar boxes, exhibits, callout alerts (> [!NOTE]),
and caption formatting.
"""

import re
import logging
from typing import List, Tuple, Set, Dict, Any

logger = logging.getLogger(__name__)


class CalloutParser:
    """Specialized formatter for callouts, alert boxes, and figure captions."""

    CALLOUT_PATTERNS = [
        r'^(?:Exhibit|Case Study|Case Example|Clinical Focus|Focus Box|Key Concept|Study Tip|Highlight)\s+[\d\.]+',
        r'^(?:Note|Warning|Caution|Important Note|Clinical Note|Did You Know\?)(?::|\b)'
    ]

    @classmethod
    def format_callout_boxes(cls, paragraphs: list) -> list:
        """
        Detects sidebar/callout box paragraphs and formats them into
        GitHub-style Markdown alert callouts (> [!NOTE]).
        """
        formatted = []
        for p in paragraphs:
            s = p.strip()
            is_callout = any(re.search(pat, s, re.I) for pat in cls.CALLOUT_PATTERNS)
            if is_callout:
                lines = s.splitlines()
                quoted_lines = [f"> {line}" for line in lines]
                formatted.append(f"> [!NOTE]\n" + '\n'.join(quoted_lines))
            else:
                formatted.append(p)
        return formatted

    @classmethod
    def format_figure_captions(cls, paragraphs: list) -> list:
        """
        Formats 'Figure X.X: ...', 'Fig. X.X: ...', and 'Table X.X: ...' captions
        with italic markdown styling so they are visually distinguished from body prose.
        """
        caption_pat = re.compile(r'^(?:Figure|Fig\.|Table|Exhibit|Illustration)\s+\d+[\.\d]*(?:\s*[:\-–—]\s*|\s*\.\s+)(.*)', re.I)
        formatted = []
        for p in paragraphs:
            s = p.strip()
            if s.startswith(('#', '>', '!', '```')):
                formatted.append(p)
                continue
            m = caption_pat.match(s)
            if m and len(s) < 200:
                formatted.append(f"*{s}*")
            else:
                formatted.append(p)
        return formatted
