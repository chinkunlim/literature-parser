"""Unit tests for SemanticStitcher and artifact anchoring."""

import unittest
from literature_parser.services.converter.semantic_stitcher import SemanticStitcher
from literature_parser.services.parsers.layout.component_registry import ComponentResult


class TestSemanticStitcher(unittest.TestCase):
    """Verifies that prose paragraphs and decoupled components are stitched cleanly."""

    def test_semantic_stitcher_anchors_table_at_citation(self):
        """Verifies table is mounted strictly after the paragraph that cites it."""
        prose = (
            "This is the introductory paragraph.\n\n"
            "As we can observe in Table 1.1, the scores increased dramatically.\n\n"
            "This is the subsequent discussion section."
        )
        table_comp = ComponentResult(
            element_type="table",
            identifier="table_1.1",
            content="| Column A | Column B |\n|---|---|\n| 10 | 20 |",
            page_num=1,
        )

        stitched = SemanticStitcher.stitch(prose, [table_comp])

        # Table should be placed after paragraph 2 and before paragraph 3
        self.assertIn("Table 1.1", stitched)
        self.assertIn("| Column A | Column B |", stitched)
        idx_p2 = stitched.find("As we can observe in Table 1.1")
        idx_tbl = stitched.find("| Column A | Column B |")
        idx_p3 = stitched.find("This is the subsequent discussion section")

        self.assertLess(idx_p2, idx_tbl)
        self.assertLess(idx_tbl, idx_p3)

    def test_semantic_stitcher_flushes_unmounted_artifacts(self):
        """Verifies uncited orphan components are flushed at section headers or document end."""
        prose = (
            "# Chapter 1: Introduction\n\n"
            "Some narrative text without any citations.\n\n"
            "## Section 2: Results\n\n"
            "More narrative text."
        )
        orphan_fig = ComponentResult(
            element_type="figure",
            identifier="figure_99",
            content="![Figure 99](images/fig99.png)\n*Figure 99: Overview*",
            page_num=1,
        )

        stitched = SemanticStitcher.stitch(prose, [orphan_fig])
        self.assertIn("![Figure 99]", stitched)


if __name__ == "__main__":
    unittest.main()
