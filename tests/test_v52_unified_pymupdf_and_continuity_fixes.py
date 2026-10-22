"""Unit tests for Unified PyMuPDF PDF Engine and Cross-Page Continuity Fixes (TASK-036).

Verifies:
1. ScannedPDFParser page rendering via native PyMuPDF without pdftoppm dependency.
2. rules.py <style> block exclusion in continuity and sentence completeness checks.
3. rules.py exemption for lettered study questions (e.g. 'b. How many...').
4. text_utils.py cross-page stitching for bold-starting paragraphs.
5. image_manager.py full-page background sheet filtering for non-cover chapters.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf

from literature_parser.adapters.verification.rules import (
    check_content_continuity,
    check_numeric_coordinate_noise,
    check_sentence_completeness,
)
from literature_parser.services.core.image_manager import ImageManager
from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser
from literature_parser.services.utils.text_utils import stitch_cross_page_continuity


class TestUnifiedPyMuPDFAndContinuityFixes(unittest.TestCase):
    """Test suite for verifying zero external Poppler dependencies and robust continuity rules."""

    def test_scanned_pdf_renders_page_with_pure_pymupdf(self):
        """Verifies ScannedPDFParser renders page directly using PyMuPDF without pdftoppm."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test_doc.pdf"
            doc = pymupdf.open()
            page = doc.new_page(width=400, height=600)
            page.insert_text((50, 50), "Scanned Page Sample Text")
            doc.save(str(pdf_path))
            doc.close()

            # Mock subprocess to ensure pdftoppm is NEVER called
            with patch("subprocess.run") as mock_subproc:
                mock_subproc.return_value = MagicMock(stdout="", returncode=0)
                work_dir = Path(tmpdir) / "work"
                # ScannedPDFParser.parse_page_to_markdown calls tesseract, mock tsv
                tsv_content = (
                    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                    "5\t1\t1\t1\t1\t1\t50\t50\t100\t20\t95\tSample\n"
                )
                mock_subproc.return_value.stdout = tsv_content

                res_md = ScannedPDFParser.parse_page_to_markdown(str(pdf_path), 1, str(work_dir))
                # Check that rendered PNG was created
                png_file = work_dir / "page_001.png"
                self.assertTrue(png_file.exists(), "page_001.png should be rendered by PyMuPDF")
                # pdftoppm should NOT be in any mock call args
                for call_args in mock_subproc.call_args_list:
                    cmd = call_args[0][0]
                    self.assertNotIn("pdftoppm", cmd, "pdftoppm must not be invoked")

    def test_rules_ignore_embedded_style_block(self):
        """Verifies rules.py strips <style> blocks and does not treat CSS rules as body sentences."""
        md_with_css = (
            "<style>\n"
            "  :root {\n"
            "    --color-text-main: #1f2937;\n"
            "  }\n\n"
            "  body {\n"
            "    font-family: sans-serif;\n"
            "    color: var(--color-text-main);\n"
            "  }\n"
            "</style>\n\n"
            "This is a genuine author paragraph starting with a proper capitalized sentence.\n"
        )
        cont_res = check_content_continuity(md_with_css)
        self.assertTrue(cont_res["passed"], f"Continuity should pass but got: {cont_res}")
        self.assertEqual(cont_res["abrupt_cuts"], 0)

        sent_res = check_sentence_completeness(md_with_css)
        self.assertTrue(sent_res["passed"], f"Sentence completeness should pass but got: {sent_res}")
        self.assertEqual(len(sent_res["incomplete_openings"]), 0)

    def test_rules_exempt_lettered_study_questions(self):
        """Verifies check_sentence_completeness permits lettered options (e.g. 'b. How many...')."""
        md_text = (
            "Review Questions:\n\n"
            "a. What was the hypothesis of the study?\n\n"
            "b. How many participants should you use in this experiment?\n\n"
            "(c) Which statistical test is most appropriate?\n"
        )
        sent_res = check_sentence_completeness(md_text)
        self.assertTrue(sent_res["passed"], f"Lettered questions must be exempted: {sent_res}")

    def test_rules_exempt_statistical_tables_from_numeric_noise(self):
        """Verifies check_numeric_coordinate_noise does not flag Table statistical rows."""
        table_md = (
            "Table 8.1 Number of Research Participants Needed for Effect Sizes\n"
            "Analysis of variance* 2 groups 586 95 38 3 groups 464 76 30\n"
            "Multiple regression** 2 predictors 698 97 45\n"
        )
        noise_res = check_numeric_coordinate_noise(table_md)
        self.assertTrue(noise_res["passed"], f"Statistical table rows must be exempted: {noise_res}")
        self.assertEqual(noise_res["count"], 0)

    def test_stitch_cross_page_continuity_with_bold_paragraph(self):
        """Verifies stitch_cross_page_continuity stitches paragraphs beginning with bold markdown."""
        md_input = (
            "**Power** is defined as the probability of rejecting a false null hypothesis. "
            "The null hypothesis states there is no relationship\n\n"
            "<!-- Page 6 -->\n"
            "between your independent and dependent variables, and you hope to reject it."
        )
        stitched = stitch_cross_page_continuity(md_input)
        self.assertIn("relationship <!-- Page 6 -->\nbetween your independent", stitched)

    def test_image_manager_filters_full_page_sheet_for_non_cover(self):
        """Verifies ImageManager discards full-page background sheets when is_cover is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "chapter.pdf"
            doc = pymupdf.open()
            page = doc.new_page(width=400, height=600)
            doc.save(str(pdf_path))
            doc.close()

            with patch("pymupdf.open") as mock_open:
                mock_doc = MagicMock()
                mock_open.return_value = mock_doc
                mock_page = MagicMock()
                mock_doc.__iter__.return_value = [mock_page]
                mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0)]
                # Return image with full-page dimensions (1146x1431)
                mock_doc.extract_image.return_value = {
                    "image": b"dummy_png_bytes" * 500,
                    "ext": "png",
                    "width": 1146,
                    "height": 1431,
                }
                # When is_cover is False: should be filtered out
                imgs_non_cover = ImageManager.extract_pdf_images(str(pdf_path), is_cover=False)
                self.assertEqual(len(imgs_non_cover), 0, "Full page scan must be discarded for non-cover")

                # When is_cover is True: cover image should be preserved
                imgs_cover = ImageManager.extract_pdf_images(str(pdf_path), is_cover=True)
                self.assertEqual(len(imgs_cover), 1, "Cover image must be preserved when is_cover is True")


if __name__ == "__main__":
    unittest.main()
