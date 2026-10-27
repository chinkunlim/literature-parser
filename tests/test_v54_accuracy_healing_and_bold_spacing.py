"""Unit tests for TASK-061: Library accuracy healing and typography fixes.

Validates:
1. Bold spacing preservation (preventing word collision/merging).
2. Safe empty bold token cleanup.
3. Numbered item '#' prefix normalization.
4. Adjacent inline math delimiter spacing ($A$$B$ -> $A$ $B$).
5. Front matter and Part division blueprint compliance rules.
6. Cover chapter exemption from full-page scan detection.
"""

from __future__ import annotations

import unittest
from literature_parser.services.utils.text_utils import clean_typography_artifacts
from literature_parser.services.parsers.math_latex import MathLaTeXConverter
from literature_parser.adapters.verification.rules import (
    check_latex_and_symbol_integrity,
    check_blueprint_compliance,
)


class TestAccuracyHealing(unittest.TestCase):
    """Test suite for accuracy healing and typography integrity fixes."""

    def test_bold_word_merging_prevention(self) -> None:
        """Verifies that consecutive bold spans retain spaces between words.

        Args:
            None

        Returns:
            None
        """
        raw = "**THE** **VELOCITY** **OF** **AXONAL**"
        cleaned = clean_typography_artifacts(raw)
        self.assertEqual(cleaned, "**THE VELOCITY OF AXONAL**")

        raw_mixed = "Here is **LO 1.1** **Define** and **discuss**."
        cleaned_mixed = clean_typography_artifacts(raw_mixed)
        self.assertIn("LO 1.1 Define", cleaned_mixed)
        self.assertIn("and **discuss**", cleaned_mixed)

    def test_empty_bold_and_italic_cleanup(self) -> None:
        """Verifies that genuine empty bold and italic tokens are stripped.

        Args:
            None

        Returns:
            None
        """
        raw = "Header **** Middle ****** End **   ** Done"
        cleaned = clean_typography_artifacts(raw)
        self.assertNotIn("****", cleaned)
        self.assertNotIn("******", cleaned)
        self.assertNotIn("**   **", cleaned)

    def test_numbered_item_hash_normalization(self) -> None:
        """Verifies that items starting with '#1.' or '#2.' are normalized to avoid heading leaks.

        Args:
            None

        Returns:
            None
        """
        raw = "#1. Imagine three critical moments\n#2. Follow up discussion"
        cleaned = clean_typography_artifacts(raw)
        self.assertTrue(cleaned.startswith("1. Imagine"))
        self.assertIn("\n2. Follow up", cleaned)

    def test_adjacent_inline_math_delimiters(self) -> None:
        """Verifies that adjacent inline math tokens are separated with space and don't trigger $$ parity failure.

        Args:
            None

        Returns:
            None
        """
        raw = "scores $T T T Z Z Z$$Z_Y$ times"
        processed = MathLaTeXConverter.process_text(raw)
        self.assertIn("$T T T Z Z Z$ $Z_Y$", processed)

        check_res = check_latex_and_symbol_integrity(processed)
        self.assertTrue(check_res["passed"])
        self.assertEqual(check_res["count"], 0)

    def test_blueprint_front_matter_and_part_exemption(self) -> None:
        """Verifies that front matter and book-level Part divisions do not fail blueprint compliance.

        Args:
            None

        Returns:
            None
        """
        bp_front = {
            "expected_headings": [{"title": "Front Cover", "source": "outline"}],
            "expected_tables": [],
        }
        res_front = check_blueprint_compliance("# Research Methods", bp_front, is_front_matter=True)
        self.assertTrue(res_front["passed"])

        bp_body = {
            "expected_headings": [
                {"title": "Part One: What Is Biopsychology?", "source": "outline"},
                {"title": "Chapter 1. Biopsychology as a Neuroscience", "source": "outline"},
            ],
            "expected_tables": [],
        }
        res_body = check_blueprint_compliance(
            "# Chapter 1: Biopsychology as a Neuroscience\n\nContent here.",
            bp_body,
            is_front_matter=False,
        )
        self.assertTrue(res_body["passed"])
        self.assertEqual(res_body["missing_headings"], [])

    def test_running_header_preserves_punctuated_headings(self) -> None:
        """Verifies running header filter does not swallow uppercase section headings ending with punctuation.

        Args:
            None

        Returns:
            None
        """
        from literature_parser.services.parsers.digital_pdf import DigitalPDFParser

        ph = 792.0
        # Punctuated headings near top margin (top < 0.12 * ph) must NOT be filtered
        self.assertFalse(
            DigitalPDFParser._is_running_header(
                top=49.0, ph=ph, txt="TOPOGRAPHIC SENSORY CORTEX MAPS.", font_size=11.1
            )
        )
        self.assertFalse(
            DigitalPDFParser._is_running_header(
                top=49.0,
                ph=ph,
                txt="WHAT EFFECT DOES STRESS HAVE ON IMMUNE FUNCTION: DISRUPTIVE OR BENEFICIAL?",
                font_size=11.1,
            )
        )
        self.assertFalse(
            DigitalPDFParser._is_running_header(
                top=81.0, ph=ph, txt="APPETIZER EFFECT AND SATIETY.", font_size=11.1
            )
        )

        # Standard running headers in top 4% are caught
        self.assertTrue(
            DigitalPDFParser._is_running_header(top=22.0, ph=ph, txt="Chapter 17", font_size=8.3)
        )

    def test_heading_split_and_hanging_connector_stitching(self) -> None:
        """Verifies multi-line split headings with hanging prepositions are stitched cleanly.

        Args:
            None

        Returns:
            None
        """
        from literature_parser.services.utils.text_utils import heal_corrupted_headings

        raw = (
            "#### Comparison of the\n\n"
            "#### Hazards of Nicotine, Alcohol, Marijuana, Cocaine, and Heroin"
        )
        healed, fixes = heal_corrupted_headings(raw)
        self.assertIn(
            "#### Comparison of the Hazards of Nicotine, Alcohol, Marijuana, Cocaine, and Heroin",
            healed,
        )
        self.assertGreater(len(fixes), 0)


if __name__ == "__main__":
    unittest.main()
