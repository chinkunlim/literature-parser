"""
Unit tests for full-pipeline precision enhancements and EPUB visual closed-loop healing (ISSUE-017).
Covers GFM pipe tables in EPUB XHTML, Mermaid-to-SVG conversion in EPUB, soft-hyphen (U+00AD)
healing, unbalanced bold & multi-line heading healing, and EpubVisualAuditor full-page PNG
screenshot rendering & closed-loop self-healing.
"""

import tempfile
import unittest
from pathlib import Path

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.services.exporter.epub_exporter import (
    EpubExporter,
    MarkdownToXHTML,
)
from literature_parser.services.utils.text_utils import (
    clean_typography_artifacts,
    repair_hyphens,
)


class TestEpubVisualClosedLoop(unittest.TestCase):
    """Tests for ISSUE-017 pipeline formatting fixes and EPUB page screenshot closed-loop healing."""

    def test_gfm_pipe_table_converted_to_xhtml_table(self) -> None:
        """Verifies that MarkdownToXHTML converts GFM pipe tables into semantic XHTML <table> blocks."""
        md = (
            "### Key Terms and Concepts\n\n"
            "| Term | Term | Term |\n"
            "| --- | --- | --- |\n"
            "| [Authority *p. 3*](#term-authority) | **Control** *p. 14* | Deduction *p. 5* |\n"
        )
        xhtml = MarkdownToXHTML.to_xhtml_body(md)
        self.assertIn("<table", xhtml)
        self.assertIn("<thead>", xhtml)
        self.assertIn("<tbody>", xhtml)
        self.assertIn('<a href="#term-authority">Authority <em>p. 3</em></a>', xhtml)
        self.assertNotIn("<p>| Term |", xhtml)
        self.assertNotIn("| --- |", xhtml)

    def test_mermaid_converted_to_embedded_svg_in_epub(self) -> None:
        """Verifies that ```mermaid blocks are rendered as embedded <svg> diagrams in EPUB XHTML."""
        md = (
            "```mermaid\n"
            "graph LR\n"
            '    Root["Introduction to Scientific Research"]\n'
            '    N5["Characteristics"] --> N13["Empirical"]\n'
            '    N5["Characteristics"] --> N18["Control"]\n'
            "```\n"
        )
        xhtml = MarkdownToXHTML.to_xhtml_body(md)
        self.assertIn("<svg", xhtml)
        self.assertIn("Introduction to Scientific Research", xhtml)
        self.assertIn("Empirical", xhtml)
        self.assertNotIn("<pre><code>graph LR", xhtml)

    def test_soft_hyphen_repair_and_removal(self) -> None:
        """Verifies that U+00AD (\\xad) soft hyphens are repaired across line wraps and stripped."""
        raw = "contains more than 950 \xadcitations and \xaddictated changes to brain-\xad\nimaging techniques."
        repaired = clean_typography_artifacts(repair_hyphens(raw))
        self.assertNotIn("\xad", repaired)
        self.assertIn("950 citations", repaired)
        self.assertIn("dictated", repaired)
        self.assertIn("brain-imaging", repaired)

    def test_heal_unbalanced_bold_and_split_headings(self) -> None:
        """Verifies that LayoutAutoHealer fixes dangling ** markers, HTML td **, and split headings."""
        raw_md = (
            "#### 14 Sleep, Dreaming, and Circadian\n\n"
            "Rhythms 371\n\n"
            "### Chapter 2 Ways of Understanding Career Behavior and Development:\n\n"
            "Selected Theories 21\n\n"
            "**Lisa Y. Flores, PhD,** ** is an associate professor.\n\n"
            "**Box 9-1.** ** Realistic\n\n"
            "<table><tr><td>Simple correlation ( r )**</td></tr></table>\n"
        )
        healed, fixes = LayoutAutoHealer.audit_and_heal_chapter(
            raw_md, pdf_path="", chapter_dir=""
        )
        self.assertIn("#### 14 Sleep, Dreaming, and Circadian Rhythms 371", healed)
        self.assertIn(
            "### Chapter 2 Ways of Understanding Career Behavior and Development: Selected Theories 21",
            healed,
        )
        self.assertNotIn("** ** is", healed)
        self.assertNotIn("( r )**", healed)
        for line in healed.splitlines():
            self.assertEqual(
                line.count("**") % 2,
                0,
                f"Line still has unbalanced **: {line}",
            )
        self.assertTrue(len(fixes) >= 3)

    def test_epub_visual_auditor_renders_all_pages_and_heals_closed_loop(self) -> None:
        """Verifies that EpubVisualAuditor screenshots every EPUB page to PNG and heals defects."""
        from literature_parser.adapters.verification.epub_visual_auditor import (
            EpubVisualAuditor,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            book_dir = Path(tmp_dir) / "Sample-Book"
            ch_dir = book_dir / "chapters" / "Ch01-Intro"
            ch_dir.mkdir(parents=True, exist_ok=True)
            ch_md = ch_dir / "Ch01-Intro.md"

            # Write a chapter with soft hyphen, unbalanced bold, GFM table, and Mermaid diagram
            ch_md.write_text(
                "# Chapter 1 Introduction\n\n"
                "```mermaid\n"
                "graph LR\n"
                '    Root["Chapter 1"] --> N1["Methods"]\n'
                "```\n\n"
                "**Author Name, PhD,** ** wrote 950 \xadcitations.\n\n"
                "| Group | Count |\n"
                "| --- | --- |\n"
                "| Control | 25 |\n",
                encoding="utf-8",
            )

            epub_path = EpubExporter.export_book(book_dir, engine="python")
            self.assertTrue(epub_path.exists())

            report = EpubVisualAuditor.closed_loop_heal_book_epub(
                book_dir=book_dir, dpi=96
            )
            self.assertEqual(report["remaining_defects"], 0)
            self.assertGreaterEqual(report["total_pages_rendered"], 1)

            pages_dir = book_dir / "epub_pages"
            png_files = list(pages_dir.glob("page_*.png"))
            self.assertEqual(len(png_files), report["total_pages_rendered"])

            healed_md = ch_md.read_text(encoding="utf-8")
            self.assertNotIn("\xad", healed_md)
            self.assertNotIn("** **", healed_md)


if __name__ == "__main__":
    unittest.main()
