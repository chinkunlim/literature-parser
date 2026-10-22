"""
Unit Tests for Marker-Style Layout Framing, Paragraph Boundary Anchoring & Typography Colors (TASK-020)
======================================================================================================
Validates:
- TOC defaults to collapsed/hidden (<details> without open).
- Strict paragraph boundary anchoring: Figures/tables placed strictly after complete paragraph ends.
- Multiple mentions in the same paragraph emitted in order after the paragraph.
- List block protection: figures/tables placed after the entire list block completes.
- Sub-figure normalization (Figure 1A -> Figure 1 without duplicate mounting).
- Strict keyword matching: non-figure occurrences like 'sales figure' never trigger insertion.
- Complex table HTML+CSS adaptive mode (colspan/rowspan handling).
- Typography & color styles (Google Fonts dual-mode and 60-30-10 publishing palette).
"""

import unittest

from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.converter.layout_frame import (
    ArtifactRegistry,
    DocumentLayoutFrame,
    SemanticAnchorEmitter,
)
from literature_parser.services.literature_style import build_literature_css
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.parsers.layout_detector import generate_markdown_toc
from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter


class TestTOCDefaultHidden(unittest.TestCase):
    """Verifies that the generated Table of Contents defaults to hidden/collapsed."""

    def test_toc_mode_defaults_to_collapsed(self) -> None:
        """Ensures generate_markdown_toc produces <details> without 'open' attribute by default."""
        md_sample = (
            "## Section 1\n\nContent\n\n"
            "## Section 2\n\nContent\n\n"
        )
        toc = generate_markdown_toc(md_sample)
        self.assertIn("<details>", toc)
        self.assertNotIn("<details open>", toc)
        self.assertIn("<summary>📑 <b>Table of Contents</b></summary>", toc)


class TestParagraphBoundaryAnchoring(unittest.TestCase):
    """Tests that figures and tables are anchored strictly after paragraphs conclude."""

    def test_figure_inserted_only_after_full_paragraph(self) -> None:
        """Verifies that an in-text figure citation does not split the paragraph."""
        raw_md = (
            "Sentence one introduces task (see Figure 1). Sentence two explains controls. "
            "Sentence three concludes this logical paragraph.\n\n"
            "Here is the second paragraph.\n\n"
            "<figure>\n"
            '  <img src="images/fig1.png" alt="Figure 1">\n'
            "  <figcaption><strong>Figure 1.</strong> Task overview.</figcaption>\n"
            "</figure>\n"
        )
        repositioned = FigureFormatter.reposition_figures_and_tables(raw_md)

        # 1. Figure 1 must be placed AFTER the entire first paragraph
        fig_idx = repositioned.find("<figure>")
        p1_end_idx = repositioned.find("Sentence three concludes this logical paragraph.")
        p2_idx = repositioned.find("Here is the second paragraph.")

        self.assertNotEqual(fig_idx, -1)
        self.assertNotEqual(p1_end_idx, -1)
        self.assertGreater(fig_idx, p1_end_idx)
        self.assertLess(fig_idx, p2_idx)

        # 2. Sentences in paragraph 1 must remain contiguous without figure splitting them
        self.assertIn(
            "Sentence one introduces task (see Figure 1). Sentence two explains controls. "
            "Sentence three concludes this logical paragraph.",
            repositioned,
        )

    def test_multiple_mentions_in_same_paragraph(self) -> None:
        """Verifies that multiple mentions in one paragraph are queued and emitted in order after the paragraph."""
        raw_md = (
            "As depicted in Figure 1 and detailed in Table 2, experimental outcomes were consistent.\n\n"
            "Following paragraph continues narrative.\n\n"
            "<figure>\n"
            '  <img src="images/fig1.png" alt="Figure 1">\n'
            "  <figcaption><strong>Figure 1.</strong> Outcome plot.</figcaption>\n"
            "</figure>\n\n"
            '<table class="book-table">\n'
            "  <caption><strong>Table 2.</strong> Statistical metrics.</caption>\n"
            "  <tr><td>Row 1</td></tr>\n"
            "</table>\n"
        )
        repositioned = FigureFormatter.reposition_figures_and_tables(raw_md)

        fig1_pos = repositioned.find("<strong>Figure 1.</strong>")
        table2_pos = repositioned.find("<strong>Table 2.</strong>")
        p2_pos = repositioned.find("Following paragraph continues narrative.")

        self.assertNotEqual(fig1_pos, -1)
        self.assertNotEqual(table2_pos, -1)
        self.assertLess(fig1_pos, table2_pos)
        self.assertLess(table2_pos, p2_pos)

    def test_list_block_protection(self) -> None:
        """Verifies that figure mentions inside list items do not split list blocks."""
        raw_md = (
            "Key experimental conditions are as follows:\n\n"
            "- Condition A: Baseline measurement (see Figure 1).\n"
            "- Condition B: Secondary treatment.\n"
            "- Condition C: Final evaluation.\n\n"
            "Subsequent section discussion.\n\n"
            "<figure>\n"
            '  <img src="images/fig1.png" alt="Figure 1">\n'
            "  <figcaption><strong>Figure 1.</strong> Baseline diagram.</figcaption>\n"
            "</figure>\n"
        )
        repositioned = FigureFormatter.reposition_figures_and_tables(raw_md)

        fig_pos = repositioned.find("<figure>")
        list_end_pos = repositioned.find("- Condition C: Final evaluation.")
        next_p_pos = repositioned.find("Subsequent section discussion.")

        self.assertGreater(fig_pos, list_end_pos)
        self.assertLess(fig_pos, next_p_pos)


class TestArtifactRegistryAndSafeguards(unittest.TestCase):
    """Tests sub-figure normalization, keyword filtering, and orphan flushing."""

    def test_strict_keyword_matching_ignores_sales_figure(self) -> None:
        """Verifies lowercase 'sales figure' or 'table tennis' does not trigger artifact mounting."""
        registry = ArtifactRegistry()
        registry.register_figure("1", "<figure>Figure 1</figure>")

        text = "In 2021, the annual sales figure reached peak performance, but table tennis was canceled."
        emitter = SemanticAnchorEmitter(registry)
        output = emitter.process_paragraph(text)

        # Figure 1 should NOT be mounted in this paragraph
        self.assertNotIn("<figure>Figure 1</figure>", output)

    def test_sub_figure_normalization(self) -> None:
        """Verifies Figure 1A and Figure 1B mount master Figure 1 exactly once on first mention."""
        registry = ArtifactRegistry()
        registry.register_figure("1", "<figure>Figure 1 Master</figure>")

        p1 = "The visual stimulus is depicted in Figure 1A."
        p2 = "Response latencies are shown in Figure 1B."

        emitter = SemanticAnchorEmitter(registry)
        out1 = emitter.process_paragraph(p1)
        out2 = emitter.process_paragraph(p2)

        # Figure 1 should be mounted after p1
        self.assertIn("<figure>Figure 1 Master</figure>", out1)
        # Figure 1 should NOT be re-mounted after p2
        self.assertNotIn("<figure>Figure 1 Master</figure>", out2)

    def test_orphan_flush_before_next_heading(self) -> None:
        """Verifies uncited figures are safely flushed at section end before the next heading."""
        registry = ArtifactRegistry()
        registry.register_figure("99", "<figure>Uncited Diagram</figure>")

        raw_md = (
            "## Method\n\n"
            "This is paragraph one without any figure mentions.\n\n"
            "## Results\n\n"
            "Here is the results section."
        )
        emitter = SemanticAnchorEmitter(registry)
        output = emitter.process_text(raw_md)

        fig_pos = output.find("<figure>Uncited Diagram</figure>")
        results_pos = output.find("## Results")

        self.assertNotEqual(fig_pos, -1)
        self.assertLess(fig_pos, results_pos)


class TestComplexTableHTMLAdaptive(unittest.TestCase):
    """Tests adaptive switching between Markdown pipe tables and HTML+CSS for merged cells."""

    def test_simple_table_produces_markdown_pipe_table(self) -> None:
        """Verifies simple 1x1 cell table outputs standard Markdown table."""
        matrix = [
            ["Item", "Quantity", "Price"],
            ["Apple", "10", "$5.00"],
            ["Orange", "20", "$8.00"],
        ]
        res = TableParser.format_matrix_to_table(matrix)
        self.assertIn("| Item | Quantity | Price |", res)
        self.assertIn("| --- |", res)
        self.assertNotIn("<table", res)

    def test_merged_cells_produce_semantic_html_table(self) -> None:
        """Verifies merged header or spanned cells output semantic HTML <table> with colspan/rowspan."""
        cell_spans = {
            (0, 0): {"text": "Merged Header", "colspan": 2, "rowspan": 1},
            (1, 0): {"text": "Data A", "colspan": 1, "rowspan": 1},
            (1, 1): {"text": "Data B", "colspan": 1, "rowspan": 1},
        }
        res = TableParser.format_spanned_matrix_to_html(cell_spans, num_rows=2, num_cols=2)
        self.assertIn('<table class="book-table">', res)
        self.assertIn('colspan="2"', res)
        self.assertIn("Merged Header", res)


class TestTypographyAndColorStyles(unittest.TestCase):
    """Tests Google Fonts dual-mode typography and 60-30-10 publishing palette injection."""

    def test_css_contains_fonts_and_color_palette(self) -> None:
        """Verifies dual fonts and utility color classes are present in textbook and literature CSS."""
        css_textbook = build_textbook_css({})
        css_literature = build_literature_css({})

        for css in [css_textbook, css_literature]:
            # Fonts
            self.assertIn("--font-sans", css)
            self.assertIn("--font-serif", css)
            self.assertIn("--font-mono", css)
            self.assertIn("Inter", css)
            self.assertIn("Merriweather", css)

            # 60-30-10 Color Classes
            self.assertIn(".text-blue", css)
            self.assertIn(".text-emerald", css)
            self.assertIn(".text-amber", css)
            self.assertIn(".text-rose", css)
            self.assertIn(".book-table", css)


if __name__ == "__main__":
    unittest.main()
