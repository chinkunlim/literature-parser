"""Unit tests verifying strict determinism in quality scoring across Gate 1 and Gate 2.
"""

from __future__ import annotations

import unittest
from literature_parser.services.verification.quality_engine import QualityInspectionEngine
from literature_parser.services.verification.epub_visual_auditor import EpubVisualAuditor, PageAuditResult


class TestDeterministicScoring(unittest.TestCase):
    """Verifies that quality scores are strictly deterministic and reproducible."""

    def test_gate1_deterministic_repeated_evaluation(self):
        """Verifies that running Gate 1 inspection 5 times on same text yields identical scores."""
        engine = QualityInspectionEngine()
        sample_md = """# Chapter 1: Introduction

This is a well-formatted paragraph about career theories.

| Column A | Column B |
| --- | --- |
| Data 1 | Data 2 |

Here is a formula: $E = mc^2$ and an APA statistic: *t*(28) = 2.45, *p* < .05.
"""
        scores = []
        for _ in range(5):
            report = engine.inspect(sample_md, doc_name="test_doc")
            scores.append(report.scores.overall_score)

        # All 5 scores must be strictly identical
        self.assertEqual(len(set(scores)), 1)
        self.assertEqual(scores[0], scores[1])

    def test_gate2_defect_matrix_deterministic_score(self):
        """Verifies that Gate 2 calculates score strictly from the boolean defect matrix."""
        # 1. No defects -> 100.0 score
        score_clean = EpubVisualAuditor.calculate_page_score({
            "has_title_drop_shadow": False,
            "has_html_entity_leak": False,
            "has_torn_two_column": False,
            "has_stray_slice": False,
            "has_overlapping_text": False,
        })
        self.assertEqual(score_clean, 100.0)

        # 2. Drop shadow (-10) and HTML leak (-15) -> 75.0 score
        score_defective = EpubVisualAuditor.calculate_page_score({
            "has_title_drop_shadow": True,
            "has_html_entity_leak": True,
            "has_torn_two_column": False,
            "has_stray_slice": False,
            "has_overlapping_text": False,
        })
        self.assertEqual(score_defective, 75.0)


if __name__ == "__main__":
    unittest.main()
