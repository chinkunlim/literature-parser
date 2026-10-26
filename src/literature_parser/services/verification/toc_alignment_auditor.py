"""TOC Heading Tree Bi-directional Alignment Auditor (TocAlignmentAuditor).
========================================================================
Parses publisher Table of Contents (TOC) into an authoritative structural
skeleton (Part -> Chapter -> Section), and aligns chapter Markdown headings
against this ground-truth tree.
Detects missing sections (leakage/truncation), surplus headings (misclassified
boxes/quotes), and automatically heals misaligned heading levels.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


@dataclass
class TocNode:
    """Represents a single node in the Table of Contents hierarchy.

    Attributes:
        title: Normalized title string of the section.
        level: Heading level (e.g. 1 for Chapter, 2 for Major Section, 3 for Sub-section).
        page_num: Optional source page number.
        children: Subordinate sections nested under this node.
    """

    title: str
    level: int = 2
    page_num: Optional[int] = None
    children: List[TocNode] = field(default_factory=list)


@dataclass
class TocChapter:
    """Represents a chapter entry in the TOC skeleton.

    Attributes:
        chapter_num: Chapter integer identifier or string (e.g. 1, "01").
        title: Clean title of the chapter.
        sections: List of major sections (H2) expected in the chapter.
    """

    chapter_num: str
    title: str
    sections: List[TocNode] = field(default_factory=list)


@dataclass
class TocSkeleton:
    """Represents the complete hierarchical TOC skeleton for a book.

    Attributes:
        chapters: Ordered list of TocChapter objects.
    """

    chapters: List[TocChapter] = field(default_factory=list)


class TocAlignmentAuditor:
    """Audits and heals chapter headings against authoritative TOC skeletons."""

    @classmethod
    def normalize_title(cls, text: str) -> str:
        """Normalizes title strings for fuzzy-resistant matching.

        Args:
            text: Raw title text with formatting or symbols.

        Returns:
            Normalized lowercase string with punctuation and extra whitespace stripped.
        """
        clean = re.sub(r'[*_#`]', '', text)
        clean = re.sub(r'^\s*[-*•\d\.]+\s*', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip().lower()
        return clean

    @classmethod
    def parse_toc_markdown(cls, toc_markdown: str) -> TocSkeleton:
        """Parses a TOC Markdown document into a structured TocSkeleton.

        Args:
            toc_markdown: Markdown source of the TOC document.

        Returns:
            Structured TocSkeleton containing all chapters and expected sections.
        """
        skeleton = TocSkeleton()
        current_chapter: Optional[TocChapter] = None

        lines = toc_markdown.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for Chapter heading (## Chapter N: Title or # Chapter N)
            ch_match = re.match(r'^(?:#+|\*\*)\s*(?:Chapter\s+(\d+|[A-Z]+)[:\s\.\-]*)(.+?)(?:\*\*)?$', stripped, re.IGNORECASE)
            if ch_match:
                ch_num = ch_match.group(1).strip()
                ch_title = ch_match.group(2).strip()
                current_chapter = TocChapter(chapter_num=ch_num, title=ch_title)
                skeleton.chapters.append(current_chapter)
                continue

            # Check for Section entry under current chapter (- Section Title or ### Section Title)
            if current_chapter is not None:
                sec_match = re.match(r'^(?:[-*•]\s+|\#{2,4}\s+)(.+?)(?:\s*\.{2,}|\s+\d+)?$', stripped)
                if sec_match:
                    sec_title = sec_match.group(1).strip()
                    # Filter out metadata lines like "Summary", "References", "Key Terms"
                    if not re.match(r'^(?:Chapter\s+\d+|Part\s+\d+|Contents|Table of Contents)', sec_title, re.IGNORECASE):
                        current_chapter.sections.append(TocNode(title=sec_title, level=2))

        return skeleton

    @classmethod
    def align_chapter(
        cls,
        markdown_text: str,
        expected_sections: List[TocNode],
        auto_fix: bool = True,
    ) -> Tuple[List[AuditIssue], str, int]:
        """Aligns Markdown headings with expected TOC sections and repairs discrepancies.

        Args:
            markdown_text: Chapter Markdown text to inspect.
            expected_sections: List of TocNode items expected in this chapter.
            auto_fix: Whether to automatically heal demoted headings to H2.

        Returns:
            Tuple of (audit_issues, repaired_markdown, repair_count).
        """
        issues: List[AuditIssue] = []
        repaired_md = markdown_text
        repaired_count = 0

        if not expected_sections:
            return (issues, repaired_md, repaired_count)

        # 1. Extract existing Markdown headings
        lines = repaired_md.splitlines()
        md_headings: List[Tuple[int, int, str]] = []  # (line_idx, level, title)
        for idx, line in enumerate(lines):
            h_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if h_match:
                level = len(h_match.group(1))
                title = h_match.group(2).strip()
                md_headings.append((idx, level, title))

        # Build lookup table of normalized expected section titles
        norm_expected = {cls.normalize_title(sec.title): sec for sec in expected_sections}
        matched_expected: set[str] = set()

        # 2. Check each heading in Markdown
        for line_idx, level, raw_title in md_headings:
            norm_raw = cls.normalize_title(raw_title)

            # Match against expected sections
            matching_key = None
            for key in norm_expected:
                if key == norm_raw or (len(key) > 6 and (key in norm_raw or norm_raw in key)):
                    matching_key = key
                    break

            if matching_key:
                matched_expected.add(matching_key)
                exp_sec = norm_expected[matching_key]

                # Check if heading level is demoted (e.g. H3 instead of H2)
                if level > exp_sec.level and auto_fix:
                    orig_line = lines[line_idx]
                    fixed_line = f"{'#' * exp_sec.level} {raw_title}"
                    lines[line_idx] = fixed_line
                    repaired_count += 1
                    logger.debug("Healed demoted heading level: %s -> %s", orig_line, fixed_line)
            else:
                # If it's a major H2 heading and not in TOC, flag as surplus
                if level == 2 and not raw_title.lower().startswith(('summary', 'references', 'chapter summary', 'review')):
                    issues.append(AuditIssue(
                        severity="WARNING",
                        category="TOC_SURPLUS_HEADING",
                        line_num=line_idx + 1,
                        snippet=f"## {raw_title}",
                        message=f"H2 heading '{raw_title}' found in text but not present in TOC skeleton.",
                        auto_fixable=False,
                    ))

        # 3. Detect missing TOC sections
        for key, exp_sec in norm_expected.items():
            if key not in matched_expected:
                issues.append(AuditIssue(
                    severity="ERROR",
                    category="TOC_MISSING_SECTION",
                    line_num=None,
                    snippet=exp_sec.title,
                    message=f"Expected TOC section '{exp_sec.title}' was not found in chapter text.",
                    auto_fixable=False,
                ))

        if repaired_count > 0:
            repaired_md = "\n".join(lines)

        return (issues, repaired_md, repaired_count)
