"""Unit tests for PedagogicalEnclosureAuditor (Learning Objectives vs End-of-Chapter Summary).
"""

from __future__ import annotations

import unittest
from literature_parser.services.verification.pedagogical_enclosure_auditor import PedagogicalEnclosureAuditor


class TestPedagogicalEnclosureAuditor(unittest.TestCase):
    """Verifies enclosure audit between Chapter Learning Objectives and Summary."""

    def test_complete_enclosure_passes(self):
        """Verifies that when LO topics are covered in Chapter Summary, no error is flagged."""
        md = """# Chapter 3: Career Assessments

## Learning Objectives
- Understand qualitative assessment methods in career counseling.
- Examine reliability and validity standards of standardized tests.

### Section 1: Qualitative Methods
Details on qualitative assessment...

### Section 2: Standardized Tests
Details on reliability and validity...

## Chapter Summary
This chapter covered qualitative assessment methods and reviewed reliability and validity standards in counseling.
"""
        issues = PedagogicalEnclosureAuditor.audit(md)
        unclosed = [i for i in issues if i.category == "LO_EOC_UNCLOSED"]
        self.assertEqual(len(unclosed), 0)

    def test_detect_unclosed_objectives(self):
        """Verifies that when a chapter summary is completely missing or truncates topics, a warning is raised."""
        md = """# Chapter 3: Career Assessments

## Learning Objectives
- Understand qualitative assessment methods in career counseling.
- Examine reliability and validity standards of standardized tests.
- Evaluate multicultural fairness in psychological testing.
- Formulate ethical feedback protocols for clients.

### Section 1: Qualitative Methods
Details...

## Chapter Summary
In this brief summary we only mentioned qualitative methods.
"""
        issues = PedagogicalEnclosureAuditor.audit(md)
        unclosed = [i for i in issues if i.category == "LO_EOC_UNCLOSED"]
        self.assertEqual(len(unclosed), 1)
        self.assertEqual(unclosed[0].severity, "WARNING")


if __name__ == "__main__":
    unittest.main()
