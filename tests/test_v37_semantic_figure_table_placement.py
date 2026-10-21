"""
Tests for Semantic Placement of Figures and Tables (v37)
=========================================================
Verifies:
1. All figures are placed strictly after the paragraph that first mentions them.
2. Bisected prose sentences at figure extraction sites are 100% healed.
3. Uncited figures fall back gracefully to the end of the section without breaking prose.
"""

import unittest
from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter


class TestSemanticFigureTablePlacement(unittest.TestCase):

    def test_reposition_figures_after_first_mention(self):
        raw_md = (
            "## Method\n\n"
            "This is introduction to the task. Participants were shown a screen (see Figure 1). "
            "Next sentence explains the controls.\n\n"
            "Here is the second paragraph.\n\n"
            "<!-- Page 2 -->\n"
            "Here is text at the bottom of page two that ends abruptly with all money in\n\n"
            "<figure>\n"
            '  <img src="images/001.png" alt="Figure 1" style="max-width: 650px; width: 100%;">\n'
            "  <figcaption><strong>Figure 1.</strong> Task overview.</figcaption>\n"
            "</figure>\n\n"
            "your temporary bank is lost. Exploded balloons do not count.\n"
        )

        repositioned = FigureFormatter.reposition_figures(raw_md)

        # 1. Figure 1 should appear after the paragraph mentioning Figure 1
        pos_fig1 = repositioned.find("<figure>")
        pos_mention = repositioned.find("(see Figure 1).")
        self.assertNotEqual(pos_fig1, -1)
        self.assertNotEqual(pos_mention, -1)
        self.assertGreater(pos_fig1, pos_mention)

        # 2. The bisected sentence should be healed
        self.assertIn("all money in your temporary bank is lost", repositioned)
        self.assertNotIn("all money in\n\n<figure>", repositioned)

    def test_figure2_placement_and_healing(self):
        raw_md = (
            "### Task Design\n\n"
            "Figure 2 shows the expected amount of money earned across 30 trials as a function of pumps. "
            "These plots indicate maximum earnings at 64 pumps.\n\n"
            "Subsequent paragraph explains colors.\n\n"
            "If the balloon explodes before you click Collect, then you move on to the next balloon and all money in\n\n"
            "<figure>\n"
            '  <img src="images/004_002.png" alt="Figure 2" style="max-width: 650px; width: 100%;">\n'
            "  <figcaption><strong>Figure 2.</strong> Expected earnings plot.</figcaption>\n"
            "</figure>\n\n"
            "<!-- Page 5 -->\n"
            "your temporary bank is lost. Exploded balloons do not affect the money accumulated.\n"
        )

        repositioned = FigureFormatter.reposition_figures(raw_md)

        # Verify Figure 2 is placed immediately after the Figure 2 paragraph
        f2_idx = repositioned.find("<strong>Figure 2.</strong>")
        mention_idx = repositioned.find("Figure 2 shows the expected amount")
        self.assertGreater(f2_idx, mention_idx)

        # Verify sentence is healed across page comment
        self.assertIn("all money in your temporary bank is lost", repositioned)

    def test_uncited_figure_fallback(self):
        raw_md = (
            "## Results\n\n"
            "This is paragraph one.\n\n"
            "<figure>\n"
            '  <img src="images/uncited.png" alt="Figure 99" style="max-width: 650px; width: 100%;">\n'
            "  <figcaption><strong>Figure 99.</strong> An uncited plot.</figcaption>\n"
            "</figure>\n\n"
            "This is paragraph two.\n\n"
            "## Discussion\n\n"
            "Here is discussion."
        )

        repositioned = FigureFormatter.reposition_figures(raw_md)

        # Figure 99 was uncited, should fall back before next heading (## Discussion)
        fig_idx = repositioned.find("Figure 99")
        disc_idx = repositioned.find("## Discussion")
        self.assertNotEqual(fig_idx, -1)
        self.assertLess(fig_idx, disc_idx)


if __name__ == "__main__":
    unittest.main()
