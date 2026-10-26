"""Unit tests for TocAlignmentAuditor (TOC Heading Tree Bi-directional Alignment).
"""

from __future__ import annotations

import unittest
from literature_parser.services.verification.toc_alignment_auditor import (
    TocAlignmentAuditor,
    TocSkeleton,
    TocNode,
)


class TestTocAlignmentAuditor(unittest.TestCase):
    """Verifies TOC skeleton extraction and bidirectional heading alignment."""

    def setUp(self):
        self.sample_toc_md = """# Contents

## Chapter 1: Introduction to Career Counseling
- The Evolution of Career Development
- The Meaning of Work
- Ethical Standards in Practice

## Chapter 2: Career Theories
- Holland's RIASEC Model
- Super's Life-Span Theory
"""

    def test_parse_toc_skeleton(self):
        """Verifies parsing of TOC markdown into hierarchical skeleton."""
        skeleton = TocAlignmentAuditor.parse_toc_markdown(self.sample_toc_md)
        self.assertEqual(len(skeleton.chapters), 2)
        
        ch1 = skeleton.chapters[0]
        self.assertIn("Career Counseling", ch1.title)
        self.assertEqual(len(ch1.sections), 3)
        self.assertEqual(ch1.sections[0].title, "The Evolution of Career Development")
        self.assertEqual(ch1.sections[1].title, "The Meaning of Work")
        self.assertEqual(ch1.sections[2].title, "Ethical Standards in Practice")

    def test_align_perfect_chapter(self):
        """Verifies that a chapter matching all TOC headings passes with 0 issues."""
        skeleton = TocAlignmentAuditor.parse_toc_markdown(self.sample_toc_md)
        ch1 = skeleton.chapters[0]

        perfect_md = """# Chapter 1: Introduction to Career Counseling

Welcome to the chapter.

## The Evolution of Career Development

History of career guidance.

### Early Vocational Guidance
Historical details...

## The Meaning of Work

Philosophy of work.

## Ethical Standards in Practice

Codes of ethics.
"""
        issues, aligned_md, repaired_count = TocAlignmentAuditor.align_chapter(
            markdown_text=perfect_md,
            expected_sections=ch1.sections,
            auto_fix=True,
        )
        self.assertEqual(len(issues), 0)
        self.assertEqual(repaired_count, 0)

    def test_detect_missing_toc_section(self):
        """Verifies that a missing section from TOC is detected as an ERROR issue."""
        skeleton = TocAlignmentAuditor.parse_toc_markdown(self.sample_toc_md)
        ch1 = skeleton.chapters[0]

        # Missing "The Meaning of Work"
        incomplete_md = """# Chapter 1: Introduction to Career Counseling

## The Evolution of Career Development

History of career guidance.

## Ethical Standards in Practice

Codes of ethics.
"""
        issues, _, _ = TocAlignmentAuditor.align_chapter(
            markdown_text=incomplete_md,
            expected_sections=ch1.sections,
            auto_fix=False,
        )
        missing_issues = [i for i in issues if i.category == "TOC_MISSING_SECTION"]
        self.assertEqual(len(missing_issues), 1)
        self.assertEqual(missing_issues[0].severity, "ERROR")
        self.assertIn("The Meaning of Work", missing_issues[0].message)

    def test_detect_surplus_heading(self):
        """Verifies that an extra H2 heading not in TOC is flagged as WARNING."""
        skeleton = TocAlignmentAuditor.parse_toc_markdown(self.sample_toc_md)
        ch1 = skeleton.chapters[0]

        surplus_md = """# Chapter 1: Introduction to Career Counseling

## The Evolution of Career Development
Details...

## Unplanned Side Box Heading
This was actually a callout box that was incorrectly marked as H2.

## The Meaning of Work
Details...

## Ethical Standards in Practice
Details...
"""
        issues, _, _ = TocAlignmentAuditor.align_chapter(
            markdown_text=surplus_md,
            expected_sections=ch1.sections,
            auto_fix=False,
        )
        surplus_issues = [i for i in issues if i.category == "TOC_SURPLUS_HEADING"]
        self.assertEqual(len(surplus_issues), 1)
        self.assertEqual(surplus_issues[0].severity, "WARNING")
        self.assertIn("Unplanned Side Box Heading", surplus_issues[0].message)

    def test_auto_heal_demoted_heading(self):
        """Verifies that a heading in TOC rendered as H3 in text is healed to H2."""
        skeleton = TocAlignmentAuditor.parse_toc_markdown(self.sample_toc_md)
        ch1 = skeleton.chapters[0]

        demoted_md = """# Chapter 1: Introduction to Career Counseling

## The Evolution of Career Development
Details...

### The Meaning of Work
Details...

## Ethical Standards in Practice
Details...
"""
        issues, healed_md, repaired_count = TocAlignmentAuditor.align_chapter(
            markdown_text=demoted_md,
            expected_sections=ch1.sections,
            auto_fix=True,
        )
        self.assertIn("## The Meaning of Work", healed_md)
        self.assertNotIn("### The Meaning of Work", healed_md)
        self.assertGreaterEqual(repaired_count, 1)


if __name__ == "__main__":
    unittest.main()
