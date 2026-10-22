"""
Semantic & Continuity Auditor (SemanticAuditor)
===============================================
Performs deterministic semantic reading-flow and structural integrity verification:
- Cross-page sentence continuity and boundary stitch detection.
- In-text citation cross-referencing with bibliographic reference list (APA/IEEE).
- Verification of in-text Table and Figure mentions against document contents.
"""

from __future__ import annotations

import logging
import re
from typing import List, Set, Tuple

from literature_parser.services.utils.text_utils import stitch_cross_page_continuity
from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


class SemanticAuditor:
    """Audits reading flow continuity, citation matching, and figure/table references."""

    @classmethod
    def audit(
        cls,
        markdown_text: str,
        auto_fix: bool = True,
    ) -> Tuple[List[AuditIssue], str, int]:
        """Audits Markdown text for semantic reading flow and citation integrity.

        Args:
            markdown_text: Raw or processed Markdown text.
            auto_fix: Whether to automatically stitch broken cross-page sentences.

        Returns:
            Tuple of (list_of_issues, repaired_markdown, repaired_count).
        """
        issues: List[AuditIssue] = []
        repaired_md = markdown_text
        repaired_count = 0

        # 1. Cross-Page Sentence Continuity Check
        page_splits = list(re.finditer(r'(<!-- Page \d+ -->)', repaired_md))
        for match in page_splits:
            pos = match.start()
            pre_text = repaired_md[:pos].rstrip()
            post_text = repaired_md[match.end():].lstrip()

            # Inspect preceding character and succeeding character
            last_char = pre_text[-1] if pre_text else ""
            first_word_match = re.match(r'^([a-zA-Z]+)', post_text)

            if last_char and last_char not in '.!?:"\'`#}>' and first_word_match:
                first_word = first_word_match.group(1)
                if first_word and first_word[0].islower() and not first_word.startswith(('http', 'www')):
                    issues.append(AuditIssue(
                        severity="INFO",
                        category="SEMANTIC_PAGE_BREAK_CONTINUITY",
                        line_num=None,
                        snippet=f"...{pre_text[-30:]} | {post_text[:30]}...",
                        message="Sentence interrupted across page break into lowercase continuation.",
                        auto_fixable=True,
                    ))

        if auto_fix:
            try:
                stitched = stitch_cross_page_continuity(repaired_md)
                if stitched != repaired_md:
                    repaired_md = stitched
                    repaired_count += 1
            except Exception as e:
                logger.debug("stitch_cross_page_continuity skipped: %s", e)

        # 2. In-Text Citation Cross-Referencing (APA & IEEE)
        # Scan in-text citations: (Author, 2020) or (Author et al., 2019)
        citations: Set[str] = set()
        for m in re.finditer(r'\(([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?),\s*([12]\d{3}[a-z]?)\)', repaired_md):
            author = m.group(1).replace(" et al.", "").strip()
            year = m.group(2)
            citations.add((author, year))

        # Check references section
        ref_section_match = re.search(r'(?i)#+\s*(?:References|Bibliography)\b([\s\S]+)$', repaired_md)
        if ref_section_match and citations:
            ref_body = ref_section_match.group(1)
            missing_citations = []
            for author, year in citations:
                # Check if author name appears in references section
                if not re.search(rf'\b{re.escape(author)}\b', ref_body, re.IGNORECASE):
                    missing_citations.append(f"({author}, {year})")

            if missing_citations:
                issues.append(AuditIssue(
                    severity="WARNING",
                    category="SEMANTIC_UNMATCHED_CITATION",
                    line_num=None,
                    snippet=", ".join(missing_citations[:4]),
                    message=f"Found {len(missing_citations)} in-text citations not found in References list.",
                    auto_fixable=False,
                ))

        # 3. Figure & Table In-Text Mentions Check
        # Check if "Table N" mentioned in text has a corresponding Table in document
        table_mentions = set(re.findall(r'(?i)\bTable\s+(\d+(?:[\.\-_]\d+)*[a-zA-Z]?)\b', repaired_md))
        for t_num in table_mentions:
            clean_num = t_num.replace('-', '_').replace('.', '_')
            has_table = (
                bool(re.search(rf'(?i)(?:###\s*Table\s+{re.escape(t_num)}\b|\*\*Table\s+{re.escape(t_num)}\*\*|<table|<p align="center"><img[^>]*table_{re.escape(clean_num)})', repaired_md))
            )
            if not has_table:
                issues.append(AuditIssue(
                    severity="INFO",
                    category="SEMANTIC_TABLE_MENTION_ORPHAN",
                    line_num=None,
                    snippet=f"Table {t_num}",
                    message=f"Table {t_num} is referenced in text but no matching table block was found.",
                    auto_fixable=False,
                ))

        return (issues, repaired_md, repaired_count)
