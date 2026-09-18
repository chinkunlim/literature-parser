"""
Unit Tests: v29 SpecialBlockScanner & Enhanced Flashcard Deck
=============================================================
Tests the SpecialBlockScanner accumulated learning system and the
InlineGlossaryExtractor integration in DigitalPDFParser.
"""
import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure src package shadows the root-level book_processor.py shim
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from book_processor.profiler.special_block_scanner import (
    SpecialBlockScanner, _CALLOUT_SEED_PATTERNS, _LO_FORMAT_PATTERNS,
    _EOC_HEADING_SEEDS,
)
from book_processor.parsers.digital_pdf import DigitalPDFParser
from book_processor.profiler.model_advisor import (
    RECOMMENDED_MODELS, MINIMUM_RECOMMENDED, check_models_status,
)


# ---------------------------------------------------------------------------
# SpecialBlockScanner — unit tests
# ---------------------------------------------------------------------------

class TestSpecialBlockScanner(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.book_dir = Path(self.tmp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_scanner(self) -> SpecialBlockScanner:
        return SpecialBlockScanner(self.book_dir)

    def test_lo_format_detection_digit_dot_digit(self):
        """'1.1', '2.3' should map to digit_dot_digit format."""
        scanner = self._make_scanner()
        texts = [
            (100, 50, 30, 12, "1.1"),
            (120, 50, 30, 12, "1.2"),
            (140, 50, 30, 12, "1.3"),
        ]
        found = scanner._detect_lo_format(texts)
        self.assertTrue(all(f == "digit_dot_digit" for f in found))

    def test_lo_format_detection_LO_space(self):
        """'LO 1', 'LO 2' should map to LO_space_digit format."""
        scanner = self._make_scanner()
        texts = [
            (100, 50, 20, 12, "LO 1"),
            (120, 50, 20, 12, "LO 2"),
        ]
        found = scanner._detect_lo_format(texts)
        self.assertTrue(all(f == "LO_space_digit" for f in found))

    def test_eoc_heading_detection(self):
        """Should detect 'Summary', 'Key Terms and Concepts', 'Practice Test'."""
        scanner = self._make_scanner()
        texts = [
            (500, 50, 200, 18, "Summary"),
            (550, 50, 200, 18, "Key Terms and Concepts"),
            (600, 50, 200, 18, "Practice Test"),
            (650, 50, 200, 14, "Some regular paragraph text that should not match"),
        ]
        found = scanner._detect_eoc_headings(texts)
        self.assertIn("Summary", found)
        self.assertIn("Key Terms and Concepts", found)
        self.assertIn("Practice Test", found)
        self.assertNotIn("Some regular paragraph text that should not match", found)

    def test_has_margin_glossary_odd_page(self):
        """Narrow-width text cluster on right side of odd page → margin glossary detected."""
        scanner = self._make_scanner()
        pw, ph = 800.0, 1100.0
        # Odd page: right-side narrow texts at rel_left > 0.68
        texts = [
            (200, 560, 60, 10, "Independent variable"),
            (230, 560, 55, 10, "The presumed cause"),
            (260, 560, 60, 10, "Dependent variable"),
            (290, 560, 50, 10, "The effect measured"),
        ]
        result = scanner._has_margin_glossary(texts, pw, ph, page_num=3)  # odd page
        self.assertTrue(result)

    def test_has_margin_glossary_even_page(self):
        """Narrow-width text cluster on left side of even page → margin glossary detected."""
        scanner = self._make_scanner()
        pw, ph = 800.0, 1100.0
        # Even page: left-side narrow texts at rel_left < 0.30
        texts = [
            (200, 20, 60, 10, "Reliability"),
            (230, 20, 55, 10, "Consistency of measurement"),
            (260, 20, 60, 10, "Validity"),
            (290, 20, 50, 10, "Accuracy of measurement"),
        ]
        result = scanner._has_margin_glossary(texts, pw, ph, page_num=4)  # even page
        self.assertTrue(result)

    def test_scan_and_update_creates_profile(self):
        """scan_and_update() should create book_profile.json even with no real PDFs."""
        scanner = self._make_scanner()
        # Mock _extract_page_xml to return empty so no real PDF needed
        with patch.object(SpecialBlockScanner, '_extract_page_xml', return_value=""):
            result = scanner.scan_and_update([], force_rescan=True)

        profile_path = self.book_dir / "book_profile.json"
        self.assertTrue(profile_path.exists(), "book_profile.json should be created")
        loaded = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertIn("discovered_blocks", loaded)
        self.assertIn("column_roles", loaded)
        self.assertTrue(loaded.get("scan_complete"))

    def test_column_roles_majority_vote(self):
        """_finalise_column_roles should return majority-voted roles."""
        scanner = self._make_scanner()
        votes = [
            {"even_left": "margin_glossary", "even_right": "body"},
            {"even_left": "margin_glossary", "even_right": "body"},
            {"even_left": "body",            "even_right": "body"},  # outlier
        ]
        result = scanner._finalise_column_roles(votes)
        self.assertEqual(result.get("even_left"), "margin_glossary")
        self.assertEqual(result.get("even_right"), "body")

    def test_profile_not_rescanned_if_complete(self):
        """scan_and_update() should NOT rescan if scan_complete=True (unless force_rescan)."""
        scanner = self._make_scanner()
        # Write a pre-complete profile
        pre_profile = {"scan_complete": True, "discovered_blocks": [{"type": "sentinel"}]}
        profile_path = self.book_dir / "book_profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(pre_profile, f)

        with patch.object(SpecialBlockScanner, '_extract_page_xml', return_value="") as mock_xml:
            result = scanner.scan_and_update([], force_rescan=False)
            mock_xml.assert_not_called()   # Should NOT have called XML extraction

        # Sentinel should still be there
        self.assertAny = True
        self.assertTrue(any(b.get("type") == "sentinel" for b in result.get("discovered_blocks", [])))


# ---------------------------------------------------------------------------
# InlineGlossaryExtractor — unit tests
# ---------------------------------------------------------------------------

class TestInlineGlossaryExtractor(unittest.TestCase):

    def setUp(self):
        DigitalPDFParser.reset_chapter_state()

    def test_collect_inline_bold_finds_capitalized_term(self):
        """**Term** at start of sentence should be collected."""
        md = "The **Independent variable** is the presumed cause in an experiment."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=5)
        inline = DigitalPDFParser._chapter_inline_terms
        terms = [g['term'] for g in inline]
        self.assertIn("Independent variable", terms)

    def test_collect_inline_bold_skips_table_labels(self):
        """**Table 2.1** and **Figure 1.1** should NOT be collected."""
        md = "See **Table 2.1** and **Figure 1.2** for details."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=3)
        inline = DigitalPDFParser._chapter_inline_terms
        terms = [g['term'] for g in inline]
        self.assertNotIn("Table 2.1", terms)
        self.assertNotIn("Figure 1.2", terms)

    def test_collect_inline_bold_skips_all_caps(self):
        """ALL-CAPS acronyms like **IV** should NOT be collected."""
        md = "The **IV** is also known as the independent variable."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=2)
        inline = DigitalPDFParser._chapter_inline_terms
        terms = [g['term'] for g in inline]
        self.assertNotIn("IV", terms)

    def test_get_chapter_all_terms_deduplicates(self):
        """Terms in both margin glossary and inline bold should appear only once."""
        # Manually add a margin glossary term
        DigitalPDFParser._chapter_glossaries.append({
            'term': 'Validity',
            'definition': 'The accuracy of measurement',
            'page': 4,
        })
        # Now try to add same term as inline
        md = "**Validity** is important for research quality."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=4)
        combined = DigitalPDFParser.get_chapter_all_terms()
        validity_entries = [g for g in combined if g['term'].lower() == 'validity']
        self.assertEqual(len(validity_entries), 1, "Validity should appear only once (no duplicates)")

    def test_get_chapter_all_terms_ordering(self):
        """Margin terms should come before inline-only terms."""
        DigitalPDFParser._chapter_glossaries.append({
            'term': 'Reliability',
            'definition': 'Consistency of measurement',
            'page': 3,
        })
        md = "**Internal validity** refers to causal inference strength."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=4)
        combined = DigitalPDFParser.get_chapter_all_terms()
        self.assertGreater(len(combined), 1)
        # First entry should be the margin glossary term (no source='inline_bold')
        self.assertIsNone(combined[0].get('source'))
        # Second entry should be the inline term
        self.assertEqual(combined[1].get('source'), 'inline_bold')

    def test_inline_terms_have_none_definition(self):
        """Inline terms collected without margin definition should have definition=None."""
        md = "The **Dependent variable** is measured after the treatment."
        DigitalPDFParser.collect_inline_bold_terms(md, page_num=7)
        inline = DigitalPDFParser._chapter_inline_terms
        dv_entry = next((g for g in inline if 'Dependent' in g['term']), None)
        self.assertIsNotNone(dv_entry)
        self.assertIsNone(dv_entry['definition'])
        self.assertEqual(dv_entry['source'], 'inline_bold')


# ---------------------------------------------------------------------------
# ModelAdvisor — updated roster tests
# ---------------------------------------------------------------------------

class TestModelAdvisorUpdatedRoster(unittest.TestCase):

    def test_minimum_recommended_contains_moondream(self):
        """MINIMUM_RECOMMENDED should include moondream as entry-level vision model."""
        self.assertIn("moondream:latest", MINIMUM_RECOMMENDED)

    def test_minimum_recommended_contains_qwen(self):
        """MINIMUM_RECOMMENDED should include qwen2.5:7b for text structuring."""
        self.assertIn("qwen2.5:7b", MINIMUM_RECOMMENDED)

    def test_recommended_models_has_vision_quick(self):
        """RECOMMENDED_MODELS should have vision_quick role for moondream."""
        self.assertIn("vision_quick", RECOMMENDED_MODELS)
        self.assertIn("moondream", RECOMMENDED_MODELS["vision_quick"])

    def test_check_models_status_offline(self):
        """When Ollama is offline, missing_minimum should equal MINIMUM_RECOMMENDED."""
        with patch('book_processor.profiler.model_advisor.probe_ollama', return_value=False):
            status = check_models_status()
        self.assertFalse(status["ollama_online"])
        self.assertIn("missing_minimum", status)
        missing_names = [m if isinstance(m, str) else m[1] for m in status["missing_minimum"]]
        for req in MINIMUM_RECOMMENDED:
            self.assertIn(req, missing_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
