"""Unit tests for WebDataService, document queries, PDF rendering, and markdown updates."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz

from literature_parser.services.core.web_data_service import WebDataService


class TestWebDataService(unittest.TestCase):
    """Verifies that WebDataService provides book summaries, chapter markdown, and PDF rendering."""

    def setUp(self):
        """Creates a mock data directory with sample book, chapter markdown, and chapter PDF."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.output_dir = self.data_dir / "output"
        self.books_dir = self.output_dir / "books"
        self.book_dir = self.books_dir / "Sample-Book"
        self.chapters_dir = self.book_dir / "chapters"
        self.ch1_dir = self.chapters_dir / "Ch01-Introduction"
        self.ch1_dir.mkdir(parents=True)

        # Create sample markdown
        self.md_file = self.ch1_dir / "Ch01-Introduction.md"
        self.md_file.write_text("# Chapter 1\nHello world body text.", encoding="utf-8")

        # Create dummy 1-page PDF using PyMuPDF
        self.pdf_file = self.ch1_dir / "Ch01-Introduction.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), "Sample PDF Text", fontsize=14)
        doc.save(str(self.pdf_file))
        doc.close()

        self.service = WebDataService(data_dir=self.data_dir)

    def tearDown(self):
        """Cleans up temporary directory."""
        self.temp_dir.cleanup()

    def test_list_books_and_get_chapters(self):
        """Verifies listing books and discovering chapter descriptors."""
        books = self.service.list_books()
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["id"], "Sample-Book")
        self.assertEqual(books[0]["chapters_count"], 1)

        chapters = self.service.get_book_chapters("Sample-Book")
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["id"], "Ch01-Introduction")
        self.assertTrue(chapters[0]["has_markdown"])
        self.assertTrue(chapters[0]["has_pdf"])

    def test_get_and_save_chapter_markdown(self):
        """Verifies reading chapter markdown and saving corrections with diff tracking."""
        data = self.service.get_chapter_markdown("Sample-Book", "Ch01-Introduction")
        self.assertIn("Hello world body text", data["markdown"])

        # Update chapter markdown
        with patch.object(WebDataService, "rebuild_book_epub") as mock_rebuild:
            mock_rebuild.return_value = self.book_dir / "Sample-Book.epub"
            res = self.service.save_chapter_markdown(
                book_id="Sample-Book",
                chapter_id="Ch01-Introduction",
                new_content="# Chapter 1\nHello world updated text.",
                issue_type="ocr_typo",
                user_notes="Fixed typo in body",
                rebuild_epub=True,
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["issue_type"], "ocr_typo")
            mock_rebuild.assert_called_once_with("Sample-Book")

        # Verify disk update
        updated_data = self.service.get_chapter_markdown("Sample-Book", "Ch01-Introduction")
        self.assertIn("Hello world updated text", updated_data["markdown"])

    def test_render_pdf_page(self):
        """Verifies rendering a chapter PDF page to PNG bytes via PyMuPDF."""
        png_bytes, total_pages = self.service.render_pdf_page(
            book_id="Sample-Book",
            chapter_id="Ch01-Introduction",
            page_index=0,
            dpi=72,
        )
        self.assertEqual(total_pages, 1)
        self.assertTrue(len(png_bytes) > 0)
        self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")

    def test_get_chapter_pdf_meta(self):
        """Verifies querying PDF metadata."""
        meta = self.service.get_chapter_pdf_meta("Sample-Book", "Ch01-Introduction")
        self.assertTrue(meta["has_pdf"])
        self.assertEqual(meta["total_pages"], 1)
        self.assertEqual(meta["file_name"], "Ch01-Introduction.pdf")


if __name__ == "__main__":
    unittest.main()
