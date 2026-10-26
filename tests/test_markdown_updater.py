"""Unit tests for MarkdownUpdater engine."""

import unittest
from pathlib import Path
import tempfile
import shutil

from literature_parser.services.core.markdown_updater import MarkdownUpdater


class TestMarkdownUpdater(unittest.TestCase):
    """Verifies syntax cleaning, comment normalization, and book markdown updates."""

    def test_clean_markdown_text(self):
        """Verifies typography, comment standardization, and token cleanup."""
        sample = (
            "<style>\n"
            "- import url('https://fonts.googleapis.com/...');\n"
            "</style>\n\n"
            "<!------ Page 10 ------>\n"
            "# Chapter 10\n\n"
            "** **Some empty bold tokens here: *** ***.\n"
            "**1.***First item.* And **2.***Second item.*\n\n"
            "| think that is correct.\n\n"
            "```mermaid\n"
            "graph TD\n"
            "  A —> B\n"
            "```\n\n"
            "<!-------- OBSIDIAN_NAV_START -------->\n"
            "<div align=\"center\">Navigation</div>\n"
            "<!-------- OBSIDIAN_NAV_END -------->\n"
        )
        cleaned = MarkdownUpdater.clean_markdown_text(sample)

        self.assertIn("@import url('https://fonts.googleapis.com/...');", cleaned)
        self.assertNotIn("- import url", cleaned)
        self.assertIn("<!-- Page 10 -->", cleaned)
        self.assertNotIn("<!------ Page 10 ------>", cleaned)
        self.assertIn("<!-- OBSIDIAN_NAV_START -->", cleaned)
        self.assertIn("<!-- OBSIDIAN_NAV_END -->", cleaned)
        self.assertNotIn("** **", cleaned)
        self.assertNotIn("*** ***", cleaned)
        self.assertIn("**1.** *First item.*", cleaned)
        self.assertIn("**2.** *Second item.*", cleaned)
        self.assertIn("I think that is correct.", cleaned)
        self.assertIn("A --> B", cleaned)
        self.assertNotIn("A —> B", cleaned)

    def test_update_book_markdown_files(self):
        """Verifies book-level updates, index generation, and status sync."""
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            chapters_root = tmp_dir / "chapters"
            ch1_dir = chapters_root / "01-ch01"
            ch2_dir = chapters_root / "02-ch02"
            ch1_dir.mkdir(parents=True)
            ch2_dir.mkdir(parents=True)

            ch1_file = ch1_dir / "01-ch01.md"
            ch1_file.write_text(
                "<!------ Page 1 ------>\n# Chapter 1\nProse text ** ** here.",
                encoding="utf-8",
            )
            ch2_file = ch2_dir / "02-ch02.md"
            ch2_file.write_text(
                "<!------ Page 2 ------>\n# Chapter 2\nSecond chapter text.",
                encoding="utf-8",
            )

            res = MarkdownUpdater.update_book_markdown_files(tmp_dir)

            self.assertEqual(res["total_chapters"], 2)
            self.assertTrue((tmp_dir / "index.md").exists())
            self.assertTrue((tmp_dir / "processing_status.md").exists())

            # Check that ch1 was cleaned and navigation was injected
            content1 = ch1_file.read_text(encoding="utf-8")
            self.assertIn("<!-- Page 1 -->", content1)
            self.assertNotIn("** **", content1)
            self.assertIn("<!-- OBSIDIAN_NAV_START -->", content1)
            self.assertIn("[[02-ch02|02-ch02]]", content1)
        finally:
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    unittest.main()
