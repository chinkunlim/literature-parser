"""
Unit Tests for MiniCPM-V Visual Auditing and Verification-Driven Surgical Healing
================================================================================
Tests PyMuPDF page rendering, page snippet extraction, multimodal visual
auditor sampling, Ollama vision model selection, and surgical table healing invariants.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf as fitz

from literature_parser.adapters.verification.ollama_healer import OllamaHealer
from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier
from literature_parser.adapters.verification.visual_auditor import VisualAuditor


class TestMiniCPMVisualAuditAndSurgicalHealing(unittest.TestCase):
    """Verifies multimodal visual auditing and surgical LLM healing."""

    def test_ollama_verifier_model_selection(self) -> None:
        """Verifies OllamaVerifier includes vision_model attribute and selects best candidate."""
        verifier = OllamaVerifier(auto_start=False)
        self.assertTrue(hasattr(verifier, "vision_model"))
        if verifier.is_available:
            self.assertIn("minicpm-v", verifier.vision_model)

    def test_visual_auditor_extract_page_snippet(self) -> None:
        """Verifies VisualAuditor cleanly extracts Markdown between page boundary markers."""
        sample_md = (
            "<!-- Page 1 -->\n"
            "# Chapter 1: Introduction\n\n"
            "This is page 1 content.\n\n"
            "<!-- Page 2 -->\n"
            "## Section 1.1\n\n"
            "This is page 2 content.\n"
        )
        p1 = VisualAuditor.extract_page_snippet(sample_md, 1)
        self.assertIn("Chapter 1: Introduction", p1)
        self.assertNotIn("Section 1.1", p1)

        p2 = VisualAuditor.extract_page_snippet(sample_md, 2)
        self.assertIn("Section 1.1", p2)
        self.assertNotIn("Chapter 1: Introduction", p2)

        p3 = VisualAuditor.extract_page_snippet(sample_md, 3)
        self.assertEqual(p3, "")

    def test_visual_auditor_render_pdf_page_image_pymupdf(self) -> None:
        """Verifies PyMuPDF renders PDF page to PNG with zero external binary dependency."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_path = tmp_path / "dummy.pdf"
            out_png = tmp_path / "dummy_p01.png"

            # Create dummy 1-page PDF
            doc = fitz.open()
            page = doc.new_page(width=300, height=300)
            page.insert_text((50, 50), "Hello PyMuPDF Visual Audit", fontsize=14)
            doc.save(str(pdf_path))
            doc.close()

            success = VisualAuditor.render_pdf_page_image(str(pdf_path), 1, out_png)
            self.assertTrue(success)
            self.assertTrue(out_png.exists())
            self.assertGreater(out_png.stat().st_size, 100)

    def test_visual_auditor_audit_chapter_sampling(self) -> None:
        """Verifies VisualAuditor identifies table and exhibit pages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_path = tmp_path / "test_ch.pdf"
            md_path = tmp_path / "test_ch.md"

            doc = fitz.open()
            for _ in range(5):
                p = doc.new_page(width=300, height=300)
                p.insert_text((50, 50), "Test content", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            md_content = (
                "<!-- Page 1 -->\n"
                "- 🎯 **1.1** Describe features\n\n"
                "```mermaid\ngraph TD\nRoot-->Child\n```\n\n"
                "<!-- Page 2 -->\n"
                "Prose on page 2.\n\n"
                "<!-- Page 3 -->\n"
                "### EXHIBIT 1.1 Sample Exhibit\n\n"
                "| Col1 | Col2 |\n| --- | --- |\n| A | B |\n\n"
                "<!-- Page 4 -->\n"
                "Table 1.2 on page 4\n<table class=\"textbook-table\"><tr><td>Data</td></tr></table>\n"
            )
            md_path.write_text(md_content, encoding="utf-8")

            report = VisualAuditor.audit_chapter(pdf_path, md_path, tmp_path, use_vision_model=False)
            self.assertEqual(report["chapter"], "test_ch")
            self.assertTrue(report["has_mindmap"])
            self.assertGreaterEqual(report["table_count"], 2)

            audited_pages = [ap["page"] for ap in report["audited_pages"]]
            self.assertIn(1, audited_pages)
            self.assertIn(3, audited_pages)

    def test_ollama_healer_numerical_invariance(self) -> None:
        """Verifies OllamaHealer rejects repairs that drop original numeric values."""
        healer = OllamaHealer(auto_start=False)
        healer.is_available = True

        raw_table = (
            "| Program | Applied | Admitted |\n"
            "| --- | --- |\n"
            "| Clinical | 60 | 9 |\n"
            "| Experimental | 120 | 90 |\n"
        )

        # Case 1: Mock LLM drops the number 120 -> Should be rejected
        with patch.object(healer, "_query_ollama_raw", return_value=(
            "```markdown\n"
            "| Program | Applied | Admitted |\n"
            "| --- | --- | --- |\n"
            "| Clinical | 60 | 9 |\n"
            "| Experimental | ? | 90 |\n"
            "```"
        )):
            repaired, modified = healer.heal_table_block_with_llm(raw_table, "Column mismatch")
            self.assertFalse(modified)
            self.assertEqual(repaired, raw_table)

        # Case 2: Mock LLM preserves all numbers 60, 9, 120, 90 -> Should be accepted
        with patch.object(healer, "_query_ollama_raw", return_value=(
            "```markdown\n"
            "| Program | Applied | Admitted |\n"
            "| --- | --- | --- |\n"
            "| Clinical | 60 | 9 |\n"
            "| Experimental | 120 | 90 |\n"
            "```"
        )):
            repaired, modified = healer.heal_table_block_with_llm(raw_table, "Column mismatch")
            self.assertTrue(modified)
            self.assertIn("| --- | --- | --- |", repaired)
            self.assertIn("120", repaired)


if __name__ == "__main__":
    unittest.main()
