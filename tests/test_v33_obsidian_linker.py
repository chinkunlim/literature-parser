import os
import shutil
import tempfile
import unittest
from pathlib import Path

from literature_parser.services.utils.obsidian_linker import (
    sanitize_obsidian_slug,
    generate_book_index,
    inject_chapter_navigation,
)


class TestObsidianLinker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.book_dir = Path(self.temp_dir) / "Test Book"
        self.book_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_obsidian_slug(self):
        self.assertEqual(
            sanitize_obsidian_slug("Ch01 Introduction to Research!"),
            "ch01_introduction_to_research"
        )
        self.assertEqual(
            sanitize_obsidian_slug("Part I: Fundamentals & Basics"),
            "part_i_fundamentals_basics"
        )

    def test_generate_book_index(self):
        ch_list = [
            {"name": "Ch01 Intro", "md_path": self.book_dir / "ch01.md"},
            {"name": "Ch02 Methods", "md_path": self.book_dir / "ch02.md"},
        ]
        index_path = generate_book_index(self.book_dir, ch_list)
        self.assertTrue(index_path.exists())
        content = index_path.read_text(encoding="utf-8")
        self.assertIn("# 📚 Test Book", content)
        self.assertIn("[[ch01_intro|Ch01 Intro]]", content)
        self.assertIn("[[ch02_methods|Ch02 Methods]]", content)

    def test_inject_chapter_navigation_and_idempotency(self):
        f1 = self.book_dir / "ch01.md"
        f2 = self.book_dir / "ch02.md"
        f3 = self.book_dir / "ch03.md"
        f1.write_text("# Chapter 1 Content\n", encoding="utf-8")
        f2.write_text("# Chapter 2 Content\n", encoding="utf-8")
        f3.write_text("# Chapter 3 Content\n", encoding="utf-8")

        ch_list = [
            {"name": "Chapter 1", "md_path": f1},
            {"name": "Chapter 2", "md_path": f2},
            {"name": "Chapter 3", "md_path": f3},
        ]

        count = inject_chapter_navigation(ch_list)
        self.assertEqual(count, 3)

        c1 = f1.read_text(encoding="utf-8")
        c2 = f2.read_text(encoding="utf-8")
        c3 = f3.read_text(encoding="utf-8")

        # Chapter 1 only has next
        self.assertIn("[[chapter_2|Chapter 2]] →", c1)
        self.assertNotIn("←", c1)

        # Chapter 2 has both prev and next
        self.assertIn("← [[chapter_1|Chapter 1]]", c2)
        self.assertIn("[[chapter_3|Chapter 3]] →", c2)

        # Chapter 3 only has prev
        self.assertIn("← [[chapter_2|Chapter 2]]", c3)
        self.assertNotIn("→", c3)

        # Test idempotency (repeated call does not duplicate footers)
        count_repeat = inject_chapter_navigation(ch_list)
        self.assertEqual(count_repeat, 0)
        c2_repeat = f2.read_text(encoding="utf-8")
        self.assertEqual(c2_repeat.count("OBSIDIAN_NAV_START"), 1)


if __name__ == "__main__":
    unittest.main()
