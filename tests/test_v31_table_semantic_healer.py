"""
Unit Tests for V3.1 Table Archetypes, Plain-Text Heading Detection,
Math Formula Healing, and Semantic Quality Rules
"""

import unittest
from book_processor.utils.text_utils import (
    reflow_wrapped_lines, repair_drop_caps, clean_decorative_noise,
    detect_plain_text_headings, format_dialogue_lines, stitch_cross_page_continuity
)
from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.parsers.layout_detector import generate_markdown_toc
from book_processor.book_style import build_textbook_css
from book_processor.verification.rules import (
    check_numeric_coordinate_noise, check_shattered_math,
    check_infix_math_in_words, check_heading_prose_intrusion,
    check_table_banner_integrity, check_heading_density,
    check_excessive_hard_wraps
)


class TestTableSemanticHealer(unittest.TestCase):

    def test_reflow_wrapped_lines(self):
        wrapped = (
            "If you are a new group leader or a student studying group leadership, you may be\n"
            "thinking that you know very little about groups, especially if you believe you have\n"
            "never been in one.\n\n"
            "- What are the advantages of leading groups?\n"
            "- What kinds of groups are there?\n\n"
            "## Section Heading\n\n"
            "Another paragraph with hyphen-\n"
            "ated word continuation."
        )
        reflowed = reflow_wrapped_lines(wrapped)
        self.assertIn("leadership, you may be thinking that you know", reflowed)
        self.assertIn("hyphenated word continuation", reflowed)
        self.assertIn("- What are the advantages of leading groups?", reflowed)
        self.assertIn("## Section Heading", reflowed)

    def test_repair_drop_caps(self):
        text1 = "Y\n\nou are about to enter a new field."
        self.assertEqual(repair_drop_caps(text1), "You are about to enter a new field.")

        text2 = "ou are about to enter a new field of study."
        self.assertEqual(repair_drop_caps(text2), "You are about to enter a new field of study.")

        text3 = "\n\nhe first experiment was conducted in 1898."
        self.assertEqual(repair_drop_caps(text3), "\n\nThe first experiment was conducted in 1898.")

    def test_clean_decorative_noise(self):
        text = (
            "@ EXAMPLES\n\n"
            "Here is an example.\n\n"
            "m@ EXAMPLES\n\n"
            "Table 2.3 Continued\n\n"
            "Some text here."
        )
        cleaned = clean_decorative_noise(text)
        self.assertIn("### Examples", cleaned)
        self.assertNotIn("@ EXAMPLES", cleaned)
        self.assertNotIn("Table 2.3 Continued", cleaned)

    def test_detect_plain_text_headings(self):
        raw_layout = (
            "                    Who Should Lead Groups?\n"
            "Knowing how to lead groups is beneficial to anyone in a helping role.\n\n"
            "                  Reasons for Leading Groups\n"
            "Corey (2012) opens his text on group counseling by saying..."
        )
        res = detect_plain_text_headings(raw_layout)
        self.assertIn("## Who Should Lead Groups?", res)
        self.assertIn("## Reasons for Leading Groups", res)

    def test_format_dialogue_lines(self):
        dialogue = (
            "LEADER: Okay, let's talk about the different ways of studying.\n"
            "JERRY: Well, I just read the chapter and underline."
        )
        res = format_dialogue_lines(dialogue)
        self.assertIn("**LEADER:** Okay, let's talk", res)
        self.assertIn("**JERRY:** Well, I just read", res)

    def test_math_formula_healing(self):
        # Infix Greek symbols
        text = "The popula$\\mu$tion mean was estimated."
        fixed = MathLaTeXConverter.repair_symbol_artifacts(text)
        self.assertEqual(fixed, "The population $\\mu$ mean was estimated.")

        # Detached superscripts
        text2 = "Using $\\chi$ 2 tests and $R$ 2 regressions."
        fixed2 = MathLaTeXConverter.repair_symbol_artifacts(text2)
        self.assertIn("$\\chi^{2}$", fixed2)
        self.assertIn("$R^{2}$", fixed2)

        # Shattered Pearson r
        shattered = (
            "sum of the cross products of the\n\n"
            "z\n\n"
            "scores\n\n"
            "X\n\n"
            "Y\n\n"
            "number of cases\n\n"
            "n\n\n"
            "where"
        )
        healed = MathLaTeXConverter.heal_shattered_math(shattered)
        self.assertIn(r"\dfrac{\sum(Z_X Z_Y)}{n}", healed)

    def test_generate_markdown_toc_modes(self):
        md = "# Chapter 1\n\n## Section One\n\n### Sub Section A\n\nContent here."
        # Open mode
        toc_open = generate_markdown_toc(md, toc_mode="open")
        self.assertTrue(toc_open.startswith("<details open>"))
        self.assertIn("- [Section One](#section-one)", toc_open)
        self.assertIn("  - [Sub Section A](#sub-section-a)", toc_open)

        # Close mode (standard HTML5 <details>)
        toc_close = generate_markdown_toc(md, toc_mode="close")
        self.assertTrue(toc_close.startswith("<details>"))
        self.assertFalse(toc_close.startswith("<details open>"))
        self.assertNotIn("<details close>", toc_close)

        # None mode
        toc_none = generate_markdown_toc(md, toc_mode="none")
        self.assertEqual(toc_none, "")

    def test_stitch_cross_page_heading_protection(self):
        # Heading must NOT be swallowed across page tag
        heading_text = (
            "### Advantages of Experimental Research\n\n"
            "<!-- Page 10 -->\n\n"
            "explanation, but also help explain why much scientific research is directed."
        )
        res_h = stitch_cross_page_continuity(heading_text)
        self.assertIn("### Advantages of Experimental Research", res_h)
        self.assertNotIn("### Advantages of Experimental Research <!-- Page 10 -->", res_h)
        self.assertNotIn("### Advantages of Experimental Research explanation", res_h)

        # Regular prose sentence SHOULD be stitched
        prose_text = (
            "The investigator conducted a rigorous experimental study\n\n"
            "<!-- Page 10 -->\n\n"
            "and obtained statistically significant outcomes."
        )
        res_p = stitch_cross_page_continuity(prose_text)
        self.assertIn("study <!-- Page 10 -->\nand obtained", res_p)

    def test_semantic_verification_rules(self):
        # 1. Numeric coordinate noise
        bad_num = "Some text.\n5 2 5 2 5 2\nMore text."
        res_num = check_numeric_coordinate_noise(bad_num)
        self.assertFalse(res_num['passed'])
        self.assertEqual(res_num['count'], 1)

        # 2. Shattered math
        bad_math = "Z\nX\nY\n=\n1"
        res_math = check_shattered_math(bad_math)
        self.assertFalse(res_math['passed'])

        # 3. Infix math
        bad_infix = "The popula$\\mu$tion distribution."
        res_infix = check_infix_math_in_words(bad_infix)
        self.assertFalse(res_infix['passed'])

        # 4. Heading prose intrusion
        bad_heading = "### Heading Title with a whole sentence attached here that explains why something happened. Another sentence follows."
        res_head = check_heading_prose_intrusion(bad_heading)
        self.assertFalse(res_head['passed'])

        # 5. Table banner integrity
        bad_banner = "- Some bullet point text Weaknesses of tests can be expensive."
        res_ban = check_table_banner_integrity(bad_banner)
        self.assertFalse(res_ban['passed'])

        # 6. Heading density
        res_density = check_heading_density("Text without headings", 1500, is_front_matter=False)
        self.assertFalse(res_density['passed'])

        # 7. CSS Theme builder
        css = build_textbook_css({})
        self.assertIn(".textbook-table", css)
        self.assertIn(".comparison-card", css)
        self.assertIn(".framed-card", css)
        self.assertIn(".dialogue-block", css)


if __name__ == '__main__':
    unittest.main()
