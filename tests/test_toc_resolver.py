"""
Unit tests for TOCResolver (TOC hierarchical parsing, hybrid alignment, and hyperlinking).
"""

import tempfile
import unittest
from pathlib import Path
from literature_parser.services.core.toc_resolver import TOCResolver, TOCNode


class TestTOCResolver(unittest.TestCase):
    """Verifies TOC hierarchical scanning, alignment, in-book Markdown rendering, and EPUB nav rendering."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.temp_dir.name)
        self.chapters_dir = self.book_dir / "chapters"
        self.chapters_dir.mkdir(parents=True)

        # Create mock chapters
        (self.chapters_dir / "00-07-TOC").mkdir()
        (self.chapters_dir / "00-07-TOC" / "00-07-TOC.md").write_text(
            "# Contents\n\n**PART I** Introduction\n\nChapter 1 Introduction 1\nChapter 2 Methods 20\n",
            encoding="utf-8",
        )

        (self.chapters_dir / "Ch01-Introduction").mkdir()
        (self.chapters_dir / "Ch01-Introduction" / "Ch01-Introduction.md").write_text(
            "# Chapter 1: Introduction to Research\n\n"
            "<!----- Page 1 ----->\n"
            "Overview text.\n\n"
            "## Traditional Methods of Knowing\n\n"
            "<!----- Page 2 ----->\n"
            "Authority and rationalism.\n\n"
            "## The Scientific Approach\n\n"
            "Hypothesis testing.\n",
            encoding="utf-8",
        )

        (self.chapters_dir / "Ch02-Methods").mkdir()
        (self.chapters_dir / "Ch02-Methods" / "Ch02-Methods.md").write_text(
            "# Chapter 2: Research Methods\n\n"
            "<!----- Page 20 ----->\n"
            "Methods content.\n\n"
            "## Experimental Design\n\n"
            "Controls and variables.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_book_hierarchy(self):
        """Verifies scanning chapters extracts H1 and H2 nodes with anchor IDs."""
        nodes = TOCResolver.scan_book_hierarchy(self.book_dir)
        # 1 top-level Part node containing the chapters
        self.assertGreaterEqual(len(nodes), 1)
        part_node = nodes[0]
        self.assertEqual(part_node.level, "part")
        self.assertEqual(len(part_node.children), 2)

        ch1_node = part_node.children[0]
        self.assertEqual(ch1_node.level, "chapter")
        self.assertIn("Ch01-Introduction.md", ch1_node.target_file)
        self.assertGreaterEqual(len(ch1_node.children), 2)
        self.assertEqual(ch1_node.children[0].level, "section")
        self.assertIn("Traditional Methods", ch1_node.children[0].title)

    def test_render_in_book_toc_markdown(self):
        """Verifies rendering in-book TOC produces structured HTML with hyperlinks."""
        nodes = TOCResolver.scan_book_hierarchy(self.book_dir)
        rendered_html = TOCResolver.render_in_book_toc_html(nodes, for_epub=False)

        self.assertIn('class="textbook-toc"', rendered_html)
        self.assertIn('href="../Ch01-Introduction/Ch01-Introduction.md', rendered_html)
        self.assertIn("Chapter 1: Introduction to Research", rendered_html)
        self.assertIn("Traditional Methods of Knowing", rendered_html)

    def test_render_epub_nav_xhtml(self):
        """Verifies rendering EPUB nav.xhtml produces nested <ol><li> with xhtml hyperlinks."""
        nodes = TOCResolver.scan_book_hierarchy(self.book_dir)
        nav_xhtml = TOCResolver.render_epub_nav_xhtml(nodes, "Test Book")

        self.assertIn('<nav epub:type="toc" id="toc">', nav_xhtml)
        self.assertIn('<a href="text/', nav_xhtml)
        self.assertIn("<ol>", nav_xhtml)
        self.assertIn("Traditional Methods of Knowing", nav_xhtml)


if __name__ == "__main__":
    unittest.main()
