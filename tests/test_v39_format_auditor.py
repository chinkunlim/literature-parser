"""
Unit Tests for Dedicated Format & Quality Auditor (FormatAuditor)
================================================================
Verifies all 8 inspection dimensions:
1. Title integrity and completeness (missing, empty, watermark, truncated)
2. Abstract section detection and noise cleaning
3. Heading hierarchy and over-inflated TOC detection
4. Table/Figure placement, notes isolation, and raw OCR leakage
5. LaTeX math delimiters and statistical formula normalization
6. References section presence and inline ungluing
7. Page numbers and running header noise filtering
8. Auto-repair capabilities and markdown report generation
"""

import unittest
from pathlib import Path
from doc_processor.verification.format_auditor import FormatAuditor, AuditIssue, AuditReport


class TestFormatAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = FormatAuditor(is_literature=True)

    def test_title_detection(self):
        # 1. Missing title
        md_no_title = "## Abstract\nSome text here without any H1."
        rep = self.auditor.audit_text(md_no_title)
        self.assertFalse(rep.passed)
        self.assertTrue(any(i.category == "TITLE" and i.severity == "ERROR" for i in rep.issues))

        # 2. Empty title
        md_empty_title = "# \n\n## Abstract\nSome text."
        rep2 = self.auditor.audit_text(md_empty_title)
        self.assertTrue(any(i.category == "TITLE" and "空字串" in i.message for i in rep2.issues))

        # 3. Watermark title
        md_wm = "# NIH Public Access\n\n## Abstract\nSome text."
        rep3 = self.auditor.audit_text(md_wm)
        self.assertTrue(any(i.category == "TITLE" and "浮水印" in i.message for i in rep3.issues))

        # 4. Valid title
        md_valid = "# Dynamic Restructuring Model in Bilingual Brain\n\n## Abstract\nThis is the abstract."
        rep4 = self.auditor.audit_text(md_valid)
        self.assertFalse(any(i.category == "TITLE" for i in rep4.issues))

    def test_abstract_detection(self):
        # Missing abstract in literature
        md_no_abs = "# Valid Title\n\n## Introduction\nNo abstract provided."
        rep = self.auditor.audit_text(md_no_abs)
        self.assertTrue(any(i.category == "ABSTRACT" and i.severity == "ERROR" for i in rep.issues))

        # Valid abstract heading
        md_with_abs = "# Valid Title\n\n## Abstract\nThis study examines..."
        rep2 = self.auditor.audit_text(md_with_abs)
        self.assertFalse(any(i.category == "ABSTRACT" and i.severity == "ERROR" for i in rep2.issues))

        # Blockquote abstract
        md_bq = "# Valid Title\n\n> **Abstract**: This study examines cognitive reserve in aging."
        rep3 = self.auditor.audit_text(md_bq)
        self.assertFalse(any(i.category == "ABSTRACT" and i.severity == "ERROR" for i in rep3.issues))

    def test_heading_toc_inflation(self):
        # 25 numbered clinical recommendations erroneously made into ## headings
        fake_headings = [f"## {i}. Practitioners are encouraged to assess client readiness." for i in range(1, 26)]
        md_inflated = "# Guidelines\n\n## Abstract\nText.\n\n" + "\n\n".join(fake_headings)
        rep = self.auditor.audit_text(md_inflated)
        self.assertTrue(any(i.category == "HEADING" and "過多" in i.message for i in rep.issues))

    def test_table_and_figure_issues(self):
        # 1. Unisolated table note
        md_table_leak = (
            "# Title\n\n## Abstract\nAbs.\n\n"
            "<table><tr><td>Data</td></tr></table>\n\n"
            "*Note.* Blue indicates statistical significance at p < .05.\n\n"
            "Continuing body text paragraph."
        )
        rep = self.auditor.audit_text(md_table_leak)
        self.assertTrue(any(i.category == "TABLE" and "tfoot" in i.message for i in rep.issues))

        # 2. Raw OCR table numbers array
        md_raw_ocr = (
            "# Title\n\n## Abstract\nAbs.\n\n"
            "Table 1\n"
            "12.4 34.2 56.1\n"
            "78.9 90.1 23.4\n"
            "45.6 67.8 89.0\n"
            "11.2 22.3 33.4\n\n"
            "End of section."
        )
        rep2 = self.auditor.audit_text(md_raw_ocr)
        self.assertTrue(any(i.category == "TABLE" and "原始 OCR 數字" in i.message for i in rep2.issues))

    def test_latex_and_ocr_stats(self):
        # 1. Corrupted Elsevier stats: t ð 24 Þ
        md_stats = "# Title\n\n## Abstract\nAbs.\n\nThe effect was significant, *t* ð 24 Þ = 2: 06, p o 0: 01."
        rep = self.auditor.audit_text(md_stats)
        self.assertTrue(any(i.category == "LATEX" and "t ð 24 Þ" in i.message for i in rep.issues))

        # 2. Unbalanced dollar sign
        md_unbalanced = "# Title\n\n## Abstract\nAbs.\n\nFormula here: $x + y = z with no closing dollar."
        rep2 = self.auditor.audit_text(md_unbalanced)
        self.assertTrue(any(i.category == "LATEX" and "未成對閉合" in i.message for i in rep2.issues))

        # 3. Unescaped currency
        md_curr = "# Title\n\n## Abstract\nAbs.\n\nParticipants received $25 compensation for their time."
        rep3 = self.auditor.audit_text(md_curr)
        self.assertTrue(any(i.category == "LATEX" and "未轉義的貨幣符號" in i.message for i in rep3.issues))

    def test_references_detection(self):
        # 1. Missing references
        md_no_refs = "# Title\n\n## Abstract\nAbs.\n\n## Discussion\nConcluding remarks."
        rep = self.auditor.audit_text(md_no_refs)
        self.assertTrue(any(i.category == "REFERENCES" and i.severity == "ERROR" for i in rep.issues))

        # 2. Glued inline references
        md_glued = "# Title\n\n## Abstract\nAbs.\n\nFunded by award. **References** Abrahamsson N (2012)."
        rep2 = self.auditor.audit_text(md_glued)
        self.assertTrue(any(i.category == "REFERENCES" and "粘連" in i.message for i in rep2.issues))

    def test_noise_and_page_numbers(self):
        md_noise = (
            "# Title\n\n## Abstract\nAbs.\n\n"
            "First page paragraph.\n\n"
            "75\n\n"
            "Second page paragraph continuation.\n\n"
            "cambridge.org/bil\n\n"
            "More body prose."
        )
        rep = self.auditor.audit_text(md_noise)
        self.assertTrue(any(i.category == "NOISE" and "75" in i.snippet for i in rep.issues))
        self.assertTrue(any(i.category == "NOISE" and "cambridge.org/bil" in i.snippet for i in rep.issues))

    def test_auto_repair(self):
        flawed_md = (
            "# Title\n\n"
            "## Abstract\nAbs.\n\n"
            "Participants paid $50 to take BART.\n\n"
            "75\n\n"
            "Funded by grant. **References** FirstAuthor (2020)."
        )
        repaired, count = self.auditor.auto_repair(flawed_md)
        self.assertGreater(count, 0)
        self.assertNotIn("\n75\n", repaired)
        self.assertIn(r"\$50", repaired)
        self.assertIn("## References", repaired)

    def test_report_markdown_generation(self):
        perfect_md = (
            "# Understanding Structural Plasticity\n\n"
            "## Abstract\n"
            "This study investigates structural neuroplasticity in bilinguals.\n\n"
            "## Introduction\n"
            "Bilingualism introduces unique cognitive demands.\n\n"
            "## Methods\n"
            "MRI scans were collected.\n\n"
            "## Results\n"
            "Significant grey matter volume increases were observed, $p < .05$.\n\n"
            "## Discussion\n"
            "Findings support the Dynamic Restructuring Model.\n\n"
            "## References\n"
            "- Bialystok E (2007). Bilingualism in development.\n"
        )
        rep = self.auditor.audit_text(perfect_md, doc_name="TestDoc", file_path="/path/TestDoc.md")
        self.assertTrue(rep.passed)
        self.assertEqual(rep.error_count, 0)
        md_out = rep.to_markdown()
        self.assertIn("文獻排版與格式稽核報告", md_out)
        self.assertIn("PASSED", md_out)


if __name__ == "__main__":
    unittest.main()
