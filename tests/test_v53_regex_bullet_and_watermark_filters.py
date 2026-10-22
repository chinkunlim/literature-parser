"""
test_v53_regex_bullet_and_watermark_filters.py - Unit tests for TASK-038 regex bullet fixes and watermark filters.

Verifies:
1. Bullet regex does not strip initial 'e' from words like 'encourage' or 'example'.
2. Table banner integrity check does not misidentify TOC links as collapsed banners.
3. Running footer filter drops Cengage copyright notices in lower margin.
4. Full page sheet-like background filter drops proportional sheet scans on non-cover pages.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import pymupdf

from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser
from literature_parser.adapters.verification.rules import check_table_banner_integrity
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.layout.margin_parser import MarginParser
from literature_parser.services.core.image_manager import ImageManager


class TestRegexBulletAndWatermarkFilters(unittest.TestCase):
    """
    Test suite for verifying bullet letter preservation, TOC banner integrity,
    and background watermark sheet filtering.
    """

    def test_scanned_pdf_preserves_initial_letter_e(self):
        """
        Verifies that words starting with 'e' (e.g., 'encourage', 'evaluate')
        are not truncated to '- ncourage' by ScannedPDFParser.
        """
        lines = [
            [{"text": "encourage", "height": 20, "x0": 50, "y0": 100}, {"text": "members", "height": 20, "x0": 120, "y0": 100}],
            [{"text": "•", "height": 20, "x0": 50, "y0": 130}, {"text": "real bullet item here", "height": 20, "x0": 70, "y0": 130}],
            [{"text": "e", "height": 20, "x0": 50, "y0": 160}, {"text": "bullet item with separate e", "height": 20, "x0": 70, "y0": 160}],
        ]
        page_md = "\n\n".join(ScannedPDFParser._lines_to_markdown(lines))
        self.assertIn("encourage members", page_md)
        self.assertNotIn("- ncourage", page_md)
        self.assertIn("- real bullet item here", page_md)
        self.assertIn("- bullet item with separate e", page_md)

    def test_table_banner_integrity_ignores_toc_links(self):
        """
        Verifies check_table_banner_integrity does not flag TOC navigation links
        such as '- [Advantages of Coleading](#advantages-of-coleading)'.
        """
        toc_content = (
            "# Table of Contents\n\n"
            "- [Overview of Groups](#overview-of-groups)\n"
            "- [Advantages of Coleading](#advantages-of-coleading)\n"
            "- [Disadvantages of Coleading](#disadvantages-of-coleading)\n"
        )
        res = check_table_banner_integrity(toc_content)
        self.assertTrue(res["passed"], f"TOC links should pass banner integrity: {res}")
        self.assertEqual(res["count"], 0)

        # Genuine collapsed banner should still fail
        collapsed_content = (
            "- Some discussion here Advantages of Coleading without proper formatting\n"
        )
        res_fail = check_table_banner_integrity(collapsed_content)
        self.assertFalse(res_fail["passed"])
        self.assertEqual(res_fail["count"], 1)

    def test_digital_pdf_drops_cengage_running_footer(self):
        """
        Verifies DigitalPDFParser._is_running_footer drops Cengage copyright notices
        near the bottom margin.
        """
        ph = 792.0  # Standard letter height
        footer_y = ph * 0.95  # in bottom 5%
        notice = "Copyright 2017 Cengage Learning. All Rights Reserved. May not be copied."
        is_hf = DigitalPDFParser._is_running_footer(footer_y, ph, notice, footer_ratio=0.1)
        self.assertTrue(is_hf, "Cengage copyright footer notice must be identified as header/footer")

    def test_margin_parser_drops_cengage_footer_text(self):
        """
        Verifies MarginParser skips bottom Cengage copyright notices in margins.
        """
        from xml.etree import ElementTree as ET
        xml_data = """
        <page id="1" width="500" height="700">
            <text top="670" left="20" width="400" height="12" font="1">
                Copyright 2017 Cengage Learning. All Rights Reserved.
            </text>
        </page>
        """
        page_elem = ET.fromstring(xml_data)
        glossaries, consumed = MarginParser.extract_margin_glossaries(
            page_elem=page_elem, fonts={}, pw=500.0, ph=700.0, page_num=1
        )
        self.assertEqual(len(glossaries), 0, "Cengage footer in margin must not create glossaries")
        self.assertEqual(len(consumed), 0, "Cengage footer in margin must not be consumed as glossaries")

    def test_image_manager_filters_sheet_like_background_watermark(self):
        """
        Verifies ImageManager drops full-page sheet-like bitmaps matching page ratio
        when is_cover is False.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test_watermark.pdf"
            doc = pymupdf.open()
            page = doc.new_page(width=458.4, height=572.8)  # Cengage loose-leaf page
            doc.save(str(pdf_path))
            doc.close()

            with patch("pymupdf.open") as mock_open:
                mock_doc = MagicMock()
                mock_open.return_value = mock_doc
                mock_page = MagicMock()
                mock_page.rect.width = 458.4
                mock_page.rect.height = 572.8
                mock_doc.__iter__.return_value = [mock_page]
                mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0)]
                # 573x716 watermark image (w/h = 0.8002 ~= 458.4/572.8 = 0.8002)
                mock_doc.extract_image.return_value = {
                    "image": b"fake_png_data" * 500,
                    "ext": "png",
                    "width": 573,
                    "height": 716,
                }
                # When is_cover is False: should be filtered
                non_cover_imgs = ImageManager.extract_pdf_images(str(pdf_path), is_cover=False)
                self.assertEqual(len(non_cover_imgs), 0, "573x716 sheet watermark must be discarded on non-cover")

    def test_numeric_noise_exempts_factorial_anova_matrices(self):
        """
        Verifies check_numeric_coordinate_noise does not flag ANOVA interaction
        matrices with repeated cell counts.
        """
        from literature_parser.adapters.verification.rules import check_numeric_coordinate_noise
        sample = (
            "B 1 30 40 50 40 B 2 50 40 30 40 40 40 40 (c) Interaction is significant; A and B are not significant\n"
        )
        res = check_numeric_coordinate_noise(sample)
        self.assertTrue(res["passed"], f"Factorial ANOVA interaction matrix should pass: {res}")

    def test_heading_intrusion_exempts_numbered_questions(self):
        """
        Verifies check_heading_prose_intrusion does not flag numbered questions like
        '## 7. How aware are you of your cultural background...'.
        """
        from literature_parser.adapters.verification.rules import check_heading_prose_intrusion
        heading_line = "## •~-------- 7. How aware are you of how your cultural background is likely to influence your abil-"
        res = check_heading_prose_intrusion(heading_line)
        self.assertTrue(res["passed"], f"Numbered heading question should pass: {res}")

    def test_clean_decorative_noise_filters_cengage_glyph_artifacts(self):
        """
        Verifies clean_decorative_noise strips Cengage font glyph noise lines.
        """
        from literature_parser.services.utils.text_utils import clean_decorative_noise
        content = (
            "## Section 1\n\n"
            "**11.e;,-4——**\n\n"
            "Normal text line here.\n\n"
            "u•~·!t—\n\n"
            "•~-------- 7. Question begins here\n"
        )
        cleaned = clean_decorative_noise(content)
        self.assertNotIn("**11.e;,-4——**", cleaned)
        self.assertNotIn("u•~·!t—", cleaned)
        self.assertIn("7. Question begins here", cleaned)
        self.assertIn("Normal text line here.", cleaned)

    def test_back_matter_heading_density_exemption(self):
        """
        Verifies check_heading_density exempts back matter reference sections like Glossary.
        """
        from literature_parser.adapters.verification.rules import check_heading_density
        glossary_md = "# Glossary\n\nDefinition 1: A very long glossary text..." * 100
        res = check_heading_density(glossary_md, word_count=8000, is_back_matter=True)
        self.assertTrue(res["passed"], f"Back matter Glossary should pass heading density: {res}")

    def test_running_footer_filters_wcn_and_permissions(self):
        """
        Verifies _is_running_footer catches WCN codes and permission lines in bottom margin.
        """
        ph = 687.0
        wcn_line = "be copied, scanned, or duplicated, in whole or in part. WCN 02-200-202"
        self.assertTrue(
            DigitalPDFParser._is_running_footer(top=ph * 0.95, ph=ph, txt=wcn_line),
            "WCN line in bottom margin must be detected as running footer"
        )
        perm_line = "*This material is reproduced with permission of John Wiley & Sons, Inc.*"
        self.assertTrue(
            DigitalPDFParser._is_running_footer(top=ph * 0.95, ph=ph, txt=perm_line),
            "Permission note in bottom margin must be detected as running footer"
        )


if __name__ == "__main__":
    unittest.main()
