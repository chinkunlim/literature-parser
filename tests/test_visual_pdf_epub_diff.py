"""
Unit tests for EPUB vs Source PDF visual side-by-side comparison.
"""

import tempfile
import unittest
from pathlib import Path
from PIL import Image
from literature_parser.adapters.verification.epub_visual_auditor import EpubVisualAuditor


class TestVisualPdfEpubDiff(unittest.TestCase):
    """Verifies side-by-side image stitching and visual comparison report generation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name)
        self.epub_pages_dir = self.book_dir / "epub_pages"
        self.epub_pages_dir.mkdir(parents=True)
        self.diff_samples_dir = self.book_dir / "visual_diff_samples"

        # Create dummy EPUB rendered page
        img_epub = Image.new("RGB", (600, 800), color=(240, 240, 240))
        img_epub.save(self.epub_pages_dir / "page_0001.png")

        # Create dummy PDF page image
        self.dummy_pdf_img = self.book_dir / "dummy_pdf_page.png"
        img_pdf = Image.new("RGB", (600, 800), color=(255, 255, 255))
        img_pdf.save(self.dummy_pdf_img)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_stitch_side_by_side_comparison(self):
        """Verifies creating a side-by-side comparison image with header banner."""
        out_path = self.diff_samples_dir / "diff_test.png"
        res_path = EpubVisualAuditor.stitch_side_by_side(
            left_img_path=self.dummy_pdf_img,
            right_img_path=self.epub_pages_dir / "page_0001.png",
            output_path=out_path,
            left_title="Original Book PDF (Page 1)",
            right_title="EPUB 3 Rendered Page",
        )
        self.assertTrue(res_path.exists())
        with Image.open(res_path) as im:
            self.assertGreaterEqual(im.width, 1000)
            self.assertGreaterEqual(im.height, 800)


if __name__ == "__main__":
    unittest.main()
