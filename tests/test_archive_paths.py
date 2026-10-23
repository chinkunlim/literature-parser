"""Unit tests for archive path routing and input scanner exclusion."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from literature_parser.config.settings import AppConfig, load_config
from literature_parser.adapters.core.orchestrator import BookProcessorOrchestrator


class TestArchivePaths(unittest.TestCase):
    """Verifies that processed books and literature are routed to input/processed/ subdirectories."""

    def test_app_config_archive_paths(self):
        """Verifies AppConfig exposes processed-books and processed-literature under input/processed/."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = AppConfig(data_dir=Path(tmp_dir))
            self.assertEqual(cfg.processed_dir, Path(tmp_dir) / "input" / "processed")
            self.assertEqual(cfg.processed_books_dir, Path(tmp_dir) / "input" / "processed" / "processed-books")
            self.assertEqual(cfg.processed_literature_dir, Path(tmp_dir) / "input" / "processed" / "processed-literature")

    def test_orchestrator_archive_source_book_and_literature(self):
        """Verifies orchestrator moves books to processed-books and literature to processed-literature."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            cfg = AppConfig(data_dir=data_dir)

            book_file = data_dir / "input" / "books" / "sample_book.pdf"
            book_file.parent.mkdir(parents=True, exist_ok=True)
            book_file.write_bytes(b"%PDF-1.4 dummy book")

            lit_file = data_dir / "input" / "literature" / "sample_paper.pdf"
            lit_file.parent.mkdir(parents=True, exist_ok=True)
            lit_file.write_bytes(b"%PDF-1.4 dummy paper")

            with patch("literature_parser.config.settings.load_config", return_value=cfg):
                orch = BookProcessorOrchestrator(
                    input_dir=str(data_dir / "input" / "books"),
                    output_dir=str(data_dir / "output" / "books"),
                    processed_dir=str(cfg.processed_dir),
                )

                # Archive book
                orch.archive_source_file(str(book_file), doc_type="book")
                expected_book_dest = cfg.processed_books_dir / "sample_book.pdf"
                self.assertFalse(book_file.exists())
                self.assertTrue(expected_book_dest.exists())

                # Archive literature
                orch.archive_source_file(str(lit_file), doc_type="literature")
                expected_lit_dest = cfg.processed_literature_dir / "sample_paper.pdf"
                self.assertFalse(lit_file.exists())
                self.assertTrue(expected_lit_dest.exists())

    def test_discover_books_ignores_processed_directory(self):
        """Verifies discover_books excludes files inside input/processed/."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            cfg = AppConfig(data_dir=data_dir)

            raw_book = data_dir / "input" / "books" / "incoming_book.pdf"
            raw_book.parent.mkdir(parents=True, exist_ok=True)
            raw_book.write_bytes(b"%PDF-1.4 raw book")

            processed_book = data_dir / "input" / "processed" / "processed-books" / "archived_book.pdf"
            processed_book.parent.mkdir(parents=True, exist_ok=True)
            processed_book.write_bytes(b"%PDF-1.4 archived book")

            with patch("literature_parser.config.settings.load_config", return_value=cfg):
                orch = BookProcessorOrchestrator(
                    input_dir=str(data_dir / "input"),
                    output_dir=str(data_dir / "output"),
                )
                discovered = orch.discover_books()
                disc_paths = [p[0] for p in discovered]
                self.assertTrue(any("incoming_book.pdf" in p for p in disc_paths))
                self.assertFalse(any("archived_book.pdf" in p for p in disc_paths))


if __name__ == "__main__":
    unittest.main()
