"""Pedagogical Enclosure Auditor (PedagogicalEnclosureAuditor).
============================================================
Audits the structural enclosure between chapter-opening pedagogical guides
(Learning Objectives / Goals) and chapter-closing syntheses (Summary / Review).
Detects content truncation, lost sub-sections, or premature chapter breaks.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Set

from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


class PedagogicalEnclosureAuditor:
    """Verifies that chapter-opening learning objectives are enclosed by end-of-chapter summaries."""

    @classmethod
    def audit(cls, markdown_text: str) -> List[AuditIssue]:
        """Audits Markdown text for pedagogical objectives vs summary enclosure.

        Args:
            markdown_text: Chapter markdown text to inspect.

        Returns:
            List of detected AuditIssue instances.
        """
        issues: List[AuditIssue] = []

        # 1. Detect Learning Objectives Block
        lo_match = re.search(
            r'(?i)(?:^#+\s*(?:Learning\s+Objectives|Chapter\s+Goals|Objectives)\b)([\s\S]+?)(?=\n#{1,6}\s|\Z)',
            markdown_text,
            re.MULTILINE,
        )
        if not lo_match:
            # If no learning objectives block declared, enclosure check is not applicable
            return issues

        lo_body = lo_match.group(1).strip()
        # Extract individual bullet points or numbered items
        raw_items = re.findall(r'(?:^[-*•]|\d+\.)\s+(.+)$', lo_body, re.MULTILINE)
        objectives = [item.strip() for item in raw_items if len(item.strip()) > 10]

        if not objectives:
            return issues

        # 2. Detect Chapter Summary Block
        sum_match = re.search(
            r'(?i)(?:^#+\s*(?:Chapter\s+Summary|Summary|Chapter\s+Review)\b)([\s\S]+?)(?=\n#{1,6}\s*(?:References|Review\s+Questions|Exercises)|\Z)',
            markdown_text,
            re.MULTILINE,
        )

        if not sum_match:
            issues.append(AuditIssue(
                severity="INFO",
                category="MISSING_EOC_SUMMARY",
                line_num=None,
                snippet=f"Declared {len(objectives)} objectives",
                message="Chapter contains Learning Objectives but has no dedicated Summary or Chapter Review block.",
                auto_fixable=False,
            ))
            return issues

        sum_body = sum_match.group(1).lower()

        # 3. Analyze Coverage of Objectives in Summary
        covered_count = 0
        uncovered_objectives = []

        stopwords = {
            "understand", "examine", "explore", "evaluate", "formulate", "describe",
            "explain", "identify", "analyze", "discuss", "chapter", "student", "learning",
            "about", "their", "these", "which", "after", "reading", "study"
        }

        for obj in objectives:
            words = re.findall(r'[a-zA-Z]{5,}', obj.lower())
            key_words = [w for w in words if w not in stopwords]

            # Check if any key content word of this objective appears in summary
            matched = any(w in sum_body for w in key_words) if key_words else False
            if matched:
                covered_count += 1
            else:
                uncovered_objectives.append(obj)

        coverage = covered_count / len(objectives) if objectives else 1.0

        if coverage < 0.50:
            preview_uncovered = "; ".join(uncovered_objectives[:2])
            issues.append(AuditIssue(
                severity="WARNING",
                category="LO_EOC_UNCLOSED",
                line_num=None,
                snippet=preview_uncovered,
                message=(
                    f"Chapter declared {len(objectives)} Learning Objectives, but the summary covers "
                    f"only {covered_count} ({coverage:.0%}). Possible section truncation or premature chapter break."
                ),
                auto_fixable=False,
            ))

        return issues
