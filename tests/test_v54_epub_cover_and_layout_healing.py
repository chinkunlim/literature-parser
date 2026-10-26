"""
Unit tests for EPUB cover thumbnail metadata, front-matter decorative image filtering,
shadow text deduplication, two-column false positive prevention, and TOC chapter backlinks.
"""

import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from literature_parser.services.exporter.epub_exporter import (
    PurePythonEpubBuilder,
    MarkdownToXHTML,
)
from literature_parser.services.utils.text_utils import clean_shadow_duplicates


class TestEPUBThumbnailAndLayoutHealing(unittest.TestCase):
    """Verifies EPUB cover metadata, front-matter filtering, shadow text dedup, and TOC backlinks."""

    def test_epub_cover_image_metadata(self):
        """Verifies that content.opf contains EPUB 3 properties='cover-image', meta cover, and guide."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_epub = Path(tmp_dir) / "test_book.epub"
            builder = PurePythonEpubBuilder(
                book_id="urn:uuid:test-1234",
                book_title="Career Counseling",
                author="Norman C. Gysbers",
                language="en",
            )
            # Create a dummy cover image file
            cover_img = Path(tmp_dir) / "cover.jpeg"
            cover_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200)

            builder.add_chapter(
                "Cover",
                "chapter_01.xhtml",
                '<figure><img src="../images/01_cover.jpeg" alt="Cover" /></figure>',
            )
            builder.add_chapter(
                "Chapter 1",
                "chapter_02.xhtml",
                '<h1>Chapter 1</h1><p>Body text</p>',
            )
            builder.add_image("images/01_cover.jpeg", cover_img, is_cover=True)

            res = builder.build(str(out_epub))
            self.assertTrue(Path(res).exists())

            with zipfile.ZipFile(res, "r") as zf:
                opf_text = zf.read("OEBPS/content.opf").decode("utf-8")

                # EPUB 2 / Apple Books fallback meta
                self.assertIn('<meta name="cover" content="cover-image"/>', opf_text)
                # EPUB 3 cover-image property on manifest item
                self.assertIn('id="cover-image"', opf_text)
                self.assertIn('properties="cover-image"', opf_text)
                # Guide reference
                self.assertIn('<reference type="cover"', opf_text)

    def test_duplicate_shadow_text_deduplication(self):
        """Verifies deduplication of duplicated shadow text lines from PDF graphic drop-shadows."""
        input_text = "CAREER CAREER COUNSELING COUNSELING"
        cleaned = clean_shadow_duplicates(input_text)
        self.assertEqual(cleaned, "CAREER COUNSELING")

        multi_line = "CAREER\nCAREER\nCOUNSELING\nCOUNSELING"
        cleaned_multi = clean_shadow_duplicates(multi_line)
        self.assertEqual(cleaned_multi, "CAREER\nCOUNSELING")

    def test_chapter_title_toc_backlink(self):
        """Verifies that chapter <h1> headings in XHTML link back to the TOC chapter."""
        md_text = "# Chapter 1: Introduction\n\nThis is chapter 1 body."
        xhtml = MarkdownToXHTML.markdown_to_xhtml(
            md_text,
            title="Chapter 1: Introduction",
            toc_href="chapter_03.xhtml",
        )
        self.assertIn('class="toc-backlink"', xhtml)
        self.assertIn('href="chapter_03.xhtml"', xhtml)
        self.assertIn('Chapter 1: Introduction</a></h1>', xhtml)

        # On the TOC chapter itself, toc_href is None or empty, so no backlink is inserted
        toc_xhtml = MarkdownToXHTML.markdown_to_xhtml(
            "# Table of Contents\n\n- [Ch1](ch1.xhtml)",
            title="Table of Contents",
            toc_href=None,
        )
        self.assertNotIn('class="toc-backlink"', toc_xhtml)

    def test_references_hanging_indent_formatting(self):
        """Verifies that paragraphs under References heading receive hanging-indent class."""
        md_text = "### References\n\nAncis, J. R., & Davidson, M. M. (2012). Gender and mental health.\n\nBandura, A. (1982). Chance encounters."
        xhtml = MarkdownToXHTML.markdown_to_xhtml(md_text, title="References")
        self.assertIn('<p class="hanging-indent">Ancis, J. R.', xhtml)
        self.assertIn('<p class="hanging-indent">Bandura, A.', xhtml)

    def test_front_matter_image_filtering(self):
        """Verifies that ImageManager discards all images in non-cover front-matter."""
        from literature_parser.services.core.image_manager import ImageManager
        # When is_front_matter=True and is_cover=False, returns empty list without parsing
        imgs = ImageManager.extract_pdf_images("dummy.pdf", is_front_matter=True, is_cover=False)
        self.assertEqual(imgs, [])
