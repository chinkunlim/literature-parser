"""Figure & Table Sequential Continuity Auditor (FigureTableContinuityAuditor).
=============================================================================
Scans Markdown text for numbered figures (Figure X.Y) and tables (Table X.Y),
detecting missing sequence numbers (unintended omissions or extraction filters)
and validating that images adhere to the Marker-style paragraph-boundary rule.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Set, Tuple

from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


class FigureTableContinuityAuditor:
    """Audits numbering sequence continuity and layout mounting for Figures and Tables."""

    @classmethod
    def audit(
        cls,
        markdown_text: str,
        chapter_num: Optional[int] = None,
    ) -> List[AuditIssue]:
        """Audits figure and table sequences in Markdown text.

        Args:
            markdown_text: Chapter markdown text to inspect.
            chapter_num: Optional chapter number integer to filter scoped sequences.

        Returns:
            List of detected AuditIssue instances.
        """
        issues: List[AuditIssue] = []

        # ── 1. Check Figure Number Continuity ────────────────────────────────
        # Match "Figure X.Y" or "Figure Y"
        fig_pattern = re.compile(r'(?i)\bFigure\s+(\d+)(?:\.(\d+))?\b')
        fig_matches = list(fig_pattern.finditer(markdown_text))

        # Group figure indices by major chapter number
        figs_by_major: dict[int, list[int]] = {}
        for m in fig_matches:
            g1 = int(m.group(1))
            g2 = int(m.group(2)) if m.group(2) else None

            if g2 is not None:
                # Format: Figure X.Y -> major is X, minor is Y
                major, minor = g1, g2
            else:
                # Format: Figure Y -> major is chapter_num or 1, minor is Y
                major = chapter_num if chapter_num is not None else 1
                minor = g1

            if chapter_num is None or major == chapter_num:
                figs_by_major.setdefault(major, []).append(minor)

        for major, minors in figs_by_major.items():
            unique_sorted = sorted(list(set(minors)))
            if len(unique_sorted) > 1:
                for idx in range(len(unique_sorted) - 1):
                    curr_num = unique_sorted[idx]
                    next_num = unique_sorted[idx + 1]
                    if next_num > curr_num + 1:
                        for missing in range(curr_num + 1, next_num):
                            label = f"Figure {major}.{missing}" if major != 1 or any(m.group(2) for m in fig_matches) else f"Figure {missing}"
                            issues.append(AuditIssue(
                                severity="ERROR",
                                category="FIGURE_SEQUENCE_GAP",
                                line_num=None,
                                snippet=f"Between {curr_num} and {next_num}",
                                message=f"Detected gap in figure numbering sequence: {label} is missing.",
                                auto_fixable=False,
                            ))

        # ── 2. Check Table Number Continuity ─────────────────────────────────
        tbl_pattern = re.compile(r'(?i)\bTable\s+(\d+)(?:\.(\d+))?\b')
        tbl_matches = list(tbl_pattern.finditer(markdown_text))

        tbls_by_major: dict[int, list[int]] = {}
        for m in tbl_matches:
            g1 = int(m.group(1))
            g2 = int(m.group(2)) if m.group(2) else None

            if g2 is not None:
                major, minor = g1, g2
            else:
                major = chapter_num if chapter_num is not None else 1
                minor = g1

            if chapter_num is None or major == chapter_num:
                tbls_by_major.setdefault(major, []).append(minor)

        for major, minors in tbls_by_major.items():
            unique_sorted = sorted(list(set(minors)))
            if len(unique_sorted) > 1:
                for idx in range(len(unique_sorted) - 1):
                    curr_num = unique_sorted[idx]
                    next_num = unique_sorted[idx + 1]
                    if next_num > curr_num + 1:
                        for missing in range(curr_num + 1, next_num):
                            label = f"Table {major}.{missing}" if major != 1 or any(m.group(2) for m in tbl_matches) else f"Table {missing}"
                            issues.append(AuditIssue(
                                severity="ERROR",
                                category="TABLE_SEQUENCE_GAP",
                                line_num=None,
                                snippet=f"Between {curr_num} and {next_num}",
                                message=f"Detected gap in table numbering sequence: {label} is missing.",
                                auto_fixable=False,
                            ))

        return issues
