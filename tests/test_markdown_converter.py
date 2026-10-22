"""
Unit Tests for MarkdownConversionService & Strategies
=====================================================
Tests service life-cycle, model contracts, strategies, and CSS dual outputs.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from literature_parser.domain.profiler.profile_schema import DocumentProfile, ProfileGeometry, ProfileMetadata
from literature_parser.services.converter.markdown_converter import MarkdownConversionService
from literature_parser.services.converter.models import (
    ConversionOptions,
    ConversionResult,
    CroppedElement,
)
from literature_parser.services.converter.strategies.book_strategy import BookPostProcessor
from literature_parser.services.converter.strategies.literature_strategy import LiteraturePostProcessor


class TestMarkdownConversionService(unittest.TestCase):
    """Test suite for MarkdownConversionService and PostProcessor strategies."""

    def setUp(self):
        self.service = MarkdownConversionService()
        self.book_profile = DocumentProfile(
            meta=ProfileMetadata(doc_type="book", mode="digital", title="Sample Psychology Book"),
            geometry=ProfileGeometry(uniform_crop_margin_pt=16.0),
        )
        self.lit_profile = DocumentProfile(
            meta=ProfileMetadata(doc_type="literature", mode="digital", title="Sample Neuroscience Paper"),
            geometry=ProfileGeometry(uniform_crop_margin_pt=16.0),
        )

    def test_book_post_processor_title_and_toc(self):
        """Tests that BookPostProcessor prepends title, generates TOC, and inserts table dual link."""
        processor = BookPostProcessor()
        raw_md = (
            "## Section 1: Introduction\n\nSome introductory text.\n\n"
            "### Table 1 Demographics\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |\n\n"
            "## Section 2: Methodology\n\nMethodology content."
        )
        table_crop = CroppedElement(
            element_type="table",
            identifier="table_1",
            filename="table_1.png",
            filepath=Path("/tmp/images/table_1.png"),
            page_num=1,
            bbox=(50.0, 100.0, 200.0, 300.0),
            padded_bbox=(34.0, 84.0, 216.0, 316.0),
            caption="Table 1 Demographics",
        )
        opts = ConversionOptions(
            generate_toc=True,
            toc_mode="open",
            prepend_title_if_missing=True,
            custom_title="Chapter 1: Foundations",
            dual_table_presentation=True,
        )
        processed = processor.process(
            raw_markdown=raw_md,
            profile=self.book_profile,
            options=opts,
            cropped_elements=[table_crop],
            context={"chapter_name": "Chapter 1: Foundations"},
        )

        # Verifies title prepended
        self.assertTrue(processed.startswith("# Chapter 1: Foundations"))
        # Verifies TOC inserted
        self.assertIn("<summary>📑 <b>Table of Contents</b>", processed)
        self.assertIn("- [Section 1: Introduction](#section-1-introduction)", processed)
        # Verifies table dual image link inserted
        self.assertIn('src="images/table_1.png"', processed)

    def test_book_post_processor_front_matter_no_toc(self):
        """Tests that 00-* front matter sections do not prepend chapter titles or generate TOC."""
        processor = BookPostProcessor()
        raw_md = "## Table of Contents\n\nFront matter text."
        opts = ConversionOptions(is_front_matter=True)
        processed = processor.process(
            raw_markdown=raw_md,
            profile=self.book_profile,
            options=opts,
            cropped_elements=[],
            context={"chapter_name": "00-01-Cover"},
        )
        self.assertFalse(processed.startswith("# 00-01-Cover"))
        self.assertNotIn("<summary>📑 <b>Table of Contents</b>", processed)

    def test_literature_post_processor_title_and_imrad(self):
        """Tests that LiteraturePostProcessor promotes main title and inserts table dual link."""
        processor = LiteraturePostProcessor()
        raw_md = (
            "### Novel Neural Architecture for Sequence Modeling\n\n"
            "### Abstract\n\nThis paper proposes a transformer variant.\n\n"
            "### Introduction\n\nRecent advances have transformed NLP.\n\n"
            "### Table 1 BLEU Scores\n\n| Model | BLEU |\n| --- | --- |\n| Ours | 42.1 |"
        )
        table_crop = CroppedElement(
            element_type="table",
            identifier="table_1",
            filename="table_1.png",
            filepath=Path("/tmp/images/table_1.png"),
            page_num=2,
            bbox=(50.0, 100.0, 200.0, 300.0),
            padded_bbox=(34.0, 84.0, 216.0, 316.0),
            caption="Table 1 BLEU Scores",
        )
        opts = ConversionOptions()
        processed = processor.process(
            raw_markdown=raw_md,
            profile=self.lit_profile,
            options=opts,
            cropped_elements=[table_crop],
            context={"publisher": "IEEE"},
        )
        # Verifies title promoted to H1
        self.assertIn("# Novel Neural Architecture for Sequence Modeling", processed)
        # Verifies table dual image link
        self.assertIn('src="images/table_1.png"', processed)

    @patch("literature_parser.services.converter.markdown_converter.DigitalPDFParser.parse_page_to_markdown")
    @patch("literature_parser.services.converter.markdown_converter.PDFAnalyzer.get_page_count")
    @patch("literature_parser.services.converter.markdown_converter.ImageManager.extract_pdf_images")
    def test_convert_lifecycle_and_css_outputs(self, mock_extract_images, mock_page_count, mock_parse_page):
        """Tests full convert() lifecycle, standalone style.css generation, and embedded <style>."""
        mock_page_count.return_value = 2
        mock_extract_images.return_value = []
        mock_parse_page.side_effect = [
            "## Section 1\nPage 1 body content.",
            "## Section 2\nPage 2 body content.",
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fake_pdf = tmp_path / "chapter_01.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4 Mock PDF Content")

            opts = ConversionOptions(
                embed_css=True,
                output_standalone_css=True,
                crop_figures_and_tables=False,
                custom_title="Chapter 1: Overview",
            )

            result = self.service.convert(
                pdf_path=fake_pdf,
                profile=self.book_profile,
                output_dir=tmp_path,
                options=opts,
                context={"chapter_name": "Chapter 1: Overview"},
            )

            self.assertIsInstance(result, ConversionResult)
            self.assertEqual(result.page_count, 2)
            self.assertTrue(result.markdown.startswith("<style>"))
            self.assertIn("# Chapter 1: Overview", result.markdown)

            # Verifies standalone style.css exists
            standalone_css = tmp_path / "style.css"
            self.assertTrue(standalone_css.exists())
            css_text = standalone_css.read_text(encoding="utf-8")
            self.assertNotIn("<style>", css_text)
            self.assertNotIn("</style>", css_text)


if __name__ == "__main__":
    unittest.main()
