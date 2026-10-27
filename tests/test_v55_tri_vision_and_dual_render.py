"""Unit tests for TASK-062: Tri-Vision (Apple Vision + MiniCPM-V + Llama Vision) Dual-Render Cross-Auditing.

Validates:
1. AppleVisionAuditor availability and Swift bridge presence.
2. AppleVisionAuditor OCR extraction and keyword coverage calculation.
3. DualRenderComparator PDF and EPUB page rendering to high-res PNG.
4. Cross-audit aggregation and defect reporting logic.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf  # type: ignore
from literature_parser.services.verification.apple_vision_auditor import AppleVisionAuditor
from literature_parser.services.verification.dual_render_comparator import DualRenderComparator
from literature_parser.services.verification.epub_visual_auditor import PageAuditResult


class TestTriVisionAndDualRender(unittest.TestCase):
    """Test suite for Tri-Vision cross-auditing and dual-render comparison."""

    def test_apple_vision_auditor_availability(self) -> None:
        """Verifies AppleVisionAuditor identifies macOS Swift binary and bridge script.

        Args:
            None

        Returns:
            None
        """
        auditor = AppleVisionAuditor()
        self.assertTrue(auditor.is_available())

    def test_compare_rendered_pages_coverage_calculation(self) -> None:
        """Verifies AppleVisionAuditor calculates word recall and flags low coverage.

        Args:
            None

        Returns:
            None
        """
        auditor = AppleVisionAuditor()
        # Mock extract_page_ocr responses
        pdf_ocr = {
            "success": True,
            "line_count": 5,
            "full_text": "Sensory systems perception and attention how you know the world in detail.",
        }
        epub_ocr_good = {
            "success": True,
            "line_count": 5,
            "full_text": "Sensory systems perception and attention how you know the world in detail.",
        }
        epub_ocr_poor = {
            "success": True,
            "line_count": 2,
            "full_text": "Random unrelated sentences without key terms.",
        }

        with patch.object(auditor, "extract_page_ocr", side_effect=[pdf_ocr, epub_ocr_good]):
            res_good = auditor.compare_rendered_pages("mock_pdf.png", "mock_epub.png")
            self.assertTrue(res_good["passed"])
            self.assertGreaterEqual(res_good["coverage_rate"], 80.0)

        with patch.object(auditor, "extract_page_ocr", side_effect=[pdf_ocr, epub_ocr_poor]):
            res_poor = auditor.compare_rendered_pages("mock_pdf.png", "mock_epub.png")
            self.assertFalse(res_poor["passed"])
            self.assertLess(res_poor["coverage_rate"], 80.0)
            self.assertGreater(len(res_poor["missing_keywords"]), 0)

    def test_dual_render_comparator_renders_pdf_and_runs_audit(self) -> None:
        """Verifies DualRenderComparator renders PDF pages to PNG and conducts cross-audit.

        Args:
            None

        Returns:
            None
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_d = Path(tmp)
            pdf_path = tmp_d / "sample_ch.pdf"

            # Create synthetic 2-page PDF
            doc = pymupdf.open()
            p1 = doc.new_page(width=612, height=792)
            p1.insert_text((72, 100), "Chapter 1: Sensory Systems and Perception", fontsize=16)
            p1.insert_text((72, 140), "Detailed body text discussing sensory receptor structures.", fontsize=10)
            p2 = doc.new_page(width=612, height=792)
            p2.insert_text((72, 100), "Page 2 continued discussion on neural pathways.", fontsize=10)
            doc.save(str(pdf_path))
            doc.close()

            comparator = DualRenderComparator(dpi=72)
            pdf_imgs = comparator.render_pdf_pages(pdf_path, tmp_d / "pdf_imgs")
            self.assertEqual(len(pdf_imgs), 2)
            self.assertTrue(pdf_imgs[0].exists())
            self.assertTrue(pdf_imgs[1].exists())

            # Test cross-audit with mock auditors
            mock_av = MagicMock()
            mock_av.extract_page_ocr.return_value = {
                "success": True,
                "line_count": 2,
                "full_text": "Sensory systems and perception neural pathways",
            }
            mock_av.compare_rendered_pages.return_value = {
                "passed": True,
                "coverage_rate": 95.0,
                "missing_keywords": [],
            }
            mock_mini = MagicMock()
            mock_mini.audit_page_with_ollama.return_value = PageAuditResult(
                page_index=1,
                image_path=str(pdf_imgs[0]),
                has_defects=False,
                defect_description=None,
                rating=10,
                model_used="minicpm-v:latest",
            )
            mock_llama = MagicMock()
            mock_llama.audit_page_with_ollama.return_value = PageAuditResult(
                page_index=1,
                image_path=str(pdf_imgs[0]),
                has_defects=False,
                defect_description=None,
                rating=10,
                model_used="llama3.2-vision:11b",
            )

            test_comparator = DualRenderComparator(
                apple_vision=mock_av,
                minicpm_auditor=mock_mini,
                llama_auditor=mock_llama,
                dpi=72,
            )

            with patch.object(test_comparator, "render_epub_chapter_pages", return_value=pdf_imgs):
                report = test_comparator.cross_audit_chapter(
                    chapter_name="Ch01-Test",
                    pdf_path=pdf_path,
                    epub_path=pdf_path,
                    eval_dir=tmp_d / "evals",
                    sample_stride=1,
                )
                self.assertTrue(report["passed"])
                self.assertEqual(report["defect_count"], 0)
                self.assertEqual(report["inspected_pages"], 2)
                self.assertEqual(report["average_content_coverage"], 100.0)


if __name__ == "__main__":
    unittest.main()
