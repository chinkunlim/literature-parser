"""
Unit Tests for Three-Tier Quality Inspection Engine
===================================================
Tests LayoutAuditor, LexicalAuditor, SemanticAuditor, and QualityInspectionEngine.
"""

import tempfile
import unittest
from pathlib import Path

from literature_parser.services.verification import (
    AuditReport,
    LayoutAuditor,
    LexicalAuditor,
    QualityInspectionEngine,
    SemanticAuditor,
    VerificationConfig,
)


class TestQualityInspectionEngine(unittest.TestCase):
    """Test suite for quality verification system."""

    def setUp(self):
        self.engine = QualityInspectionEngine(config=VerificationConfig(enable_safe_autofix=True))

    def test_layout_auditor_tag_repair_and_prose_demotion(self):
        """Tests that LayoutAuditor auto-closes unclosed tags and demotes H3 prose."""
        raw_md = (
            "# Document Title\n\n"
            "### This is an excessively long heading that is actually a regular sentence explaining something in great detail and should not be a heading at all.\n\n"
            "<table><tr><td>Cell</td></tr>\n"
            "Printed in the United States\n"
            "Regular paragraph."
        )
        issues, repaired_md, repairs = LayoutAuditor.audit(raw_md, auto_fix=True)

        # Verifies prose demoted to bold
        self.assertNotIn("### This is an excessively long", repaired_md)
        self.assertIn("**This is an excessively long", repaired_md)

        # Verifies unclosed table tag closed
        self.assertIn("</table>", repaired_md)

        # Verifies running noise filtered
        self.assertNotIn("Printed in the United States", repaired_md)
        self.assertGreaterEqual(repairs, 2)

    def test_lexical_auditor_hyphen_and_math_syntax(self):
        """Tests that LexicalAuditor repairs broken hyphens and detects unmatched LaTeX."""
        auditor = LexicalAuditor()
        raw_md = (
            "This is an important devel-\nopment in science.\n\n"
            "Here is broken math: $$ x = 1\n\n"
            "And statistics: F ( 2 , 4 0 ) = 3.5\n"
        )
        issues, repaired_md, repairs, coverage = auditor.audit(raw_md, auto_fix=True)

        # Verifies hyphen joined
        self.assertIn("development", repaired_md)

        # Verifies shattered F-test normalized
        self.assertIn("F(2, 40) = 3.5", repaired_md)

        # Verifies unmatched $$ error recorded
        unmatched_errors = [i for i in issues if i.category == "LEXICAL_LATEX_UNMATCHED_BLOCK"]
        self.assertTrue(len(unmatched_errors) > 0)

    def test_semantic_auditor_cross_page_stitch_and_citations(self):
        """Tests SemanticAuditor cross-page continuity and citation cross-referencing."""
        raw_md = (
            "# Cognitive Science\n\n"
            "The experiment demonstrated significant results in the primary\n"
            "<!-- Page 2 -->\n"
            "conditions tested by researchers (Smith, 2020).\n\n"
            "## References\n\n"
            "- Jones, A. (2018). Other studies.\n"
        )
        issues, repaired_md, repairs = SemanticAuditor.audit(raw_md, auto_fix=True)

        # Verifies missing citation warning
        missing_cites = [i for i in issues if i.category == "SEMANTIC_UNMATCHED_CITATION"]
        self.assertTrue(len(missing_cites) > 0)

    def test_quality_engine_composite_score_and_report_export(self):
        """Tests full engine inspection, composite scoring, and report file generation."""
        sample_md = (
            "# High Quality Chapter Title\n\n"
            "This chapter introduces the fundamental concepts of neuroscience.\n\n"
            "## Section 1: Overview\n\n"
            "Cognitive processes are mediated by neural networks.\n"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            report = self.engine.inspect(sample_md, doc_name="Chapter 1", base_dir=tmp_path)

            self.assertIsInstance(report, AuditReport)
            self.assertTrue(report.passed)
            self.assertGreaterEqual(report.scores.overall_score, 85.0)

            # Export report files
            md_path, json_path = QualityInspectionEngine.export_report_files(report, tmp_path)
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())

            report_text = md_path.read_text(encoding="utf-8")
            self.assertIn("Quality Inspection Report: Chapter 1", report_text)
            self.assertIn("Score Breakdown", report_text)


if __name__ == "__main__":
    unittest.main()
