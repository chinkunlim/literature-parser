r"""
Unit test suite for Book Processor v2.1 capabilities.
Tests:
- Uniform LaTeX math sizing and fraction consistency (\dfrac, \displaystyle)
- Equation delimiter parity and invariant checks
- Circuit breaker behavior on consecutive failures
- Multi-domain layout detection (callouts, footnotes, code blocks)
- Review manager diff parsing and programmatic/interactive acceptance/rejection
- Adaptive learner rule persistence
- Watchdog health status checks
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.core.invariants import QualityInvariantGuard, CircuitBreaker
from book_processor.parsers.layout_detector import LayoutDetector
from book_processor.verification.review_manager import ReviewManager
from book_processor.core.learner import AdaptiveLearner
from book_processor.core.watchdog import WatchdogService


class TestMathLaTeXUniformSizing(unittest.TestCase):
    """Test uniform LaTeX math font sizing and fraction consistency."""

    def setUp(self):
        self.converter = MathLaTeXConverter()

    def test_display_fractions_use_dfrac_and_displaystyle(self):
        r"""Ensure all fractions use \dfrac and display math gets \displaystyle."""
        raw_text = r"$$\frac{\sum X}{n} = \frac{6}{3} = 2$$"
        latex_eq = self.converter.ensure_uniform_fraction_sizing(raw_text)
        self.assertIn(r"\dfrac", latex_eq)
        self.assertNotIn(r"\frac{", latex_eq)
        self.assertIn(r"\displaystyle", latex_eq)

    def test_textbook_equations_use_dfrac(self):
        r"""Ensure predefined statistical formulas use \dfrac and \displaystyle."""
        text = "z score = raw score - mean standard deviation = X X SD"
        converted = self.converter.format_textbook_equations(text)
        self.assertIn(r"\dfrac", converted)
        self.assertIn(r"\displaystyle", converted)

    def test_check_equation_balance(self):
        """Ensure equation delimiter balance is verified."""
        balanced_text = r"Here is $d = .8$ and display $$\displaystyle \text{Mean} = \dfrac{\sum X}{n}$$ in text."
        res = self.converter.check_equation_balance(balanced_text)
        self.assertTrue(res['balanced'], res['issues'])

        unbalanced_text = "Here is an unclosed inline math $p < .05 without closing dollar."
        res = self.converter.check_equation_balance(unbalanced_text)
        self.assertFalse(res['balanced'])
        self.assertTrue(any("inline math" in issue.lower() for issue in res['issues']))


class TestQualityInvariantsAndCircuitBreaker(unittest.TestCase):
    """Test runtime invariants and fail-fast circuit breaker."""

    def setUp(self):
        self.guard = QualityInvariantGuard()

    def test_page_density_check(self):
        """Assert empty pages or non-dense pages are caught."""
        # Non-empty page
        res = self.guard.check_page_density("This is a rich academic paragraph with multiple sentences.", [], 1)
        self.assertFalse(res['anomaly'])

        # Completely blank page with no images
        res = self.guard.check_page_density("   \n\n  ", [], 2)
        self.assertTrue(res['anomaly'])
        self.assertIn("warning", res)

        # Blank text but has images (valid diagram plate)
        res = self.guard.check_page_density("   ", ["image_1.png"], 3)
        self.assertFalse(res['anomaly'])

    def test_circuit_breaker_tripping(self):
        """Assert circuit breaker trips after max consecutive failures."""
        breaker = CircuitBreaker(max_consecutive_failures=2)
        self.assertFalse(breaker.is_tripped())

        # Failure 1
        breaker.record_failure("Ch01", "Vocabulary accuracy failed")
        self.assertFalse(breaker.is_tripped())

        # Failure 2 -> Should trip
        breaker.record_failure("Ch02", "Noise check failed")
        self.assertTrue(breaker.is_tripped())

        # Success resets breaker
        breaker.record_success("Ch03")
        self.assertFalse(breaker.is_tripped())


class TestLayoutDetector(unittest.TestCase):
    """Test multi-domain layout detection (callouts, footnotes, code blocks)."""

    def setUp(self):
        self.detector = LayoutDetector()

    def test_callout_box_formatting(self):
        """Ensure exhibits and case studies are formatted as GitHub alerts."""
        paragraphs = [
            "Normal paragraph text.",
            "Exhibit 15.1 Key Statistical Guidelines\nAlways report effect sizes alongside p values."
        ]
        formatted = self.detector.format_callout_boxes(paragraphs)
        self.assertEqual(len(formatted), 2)
        self.assertTrue(formatted[1].startswith("> [!NOTE]"))
        self.assertIn("Exhibit 15.1", formatted[1])

    def test_code_block_formatting(self):
        """Ensure source code is enclosed in fenced code blocks."""
        raw_code = "def calculate_mean(data):\n    return sum(data) / len(data)"
        formatted = self.detector.detect_and_format_code_blocks(raw_code)
        self.assertTrue(formatted.startswith("```python"))
        self.assertTrue(formatted.endswith("```"))

    def test_footnote_separation(self):
        """Ensure bottom-of-page footnotes are extracted to markdown footnotes."""
        page_lines = [
            (100.0, 50.0, 12.0, "This empirical study was corroborated by contemporary findings."),
            (900.0, 50.0, 9.0, "1. Department of Psychology, Annual Review of Research, 2024.")
        ]
        body, footnotes = self.detector.separate_footnotes(page_lines, page_height=1000.0)
        self.assertEqual(len(footnotes), 1)
        self.assertIn("[^1]:", footnotes[0])
        self.assertEqual(len(body), 1)


class TestReviewManager(unittest.TestCase):
    """Test human-in-the-loop review diff resolution."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.review_manager = ReviewManager()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_accept_ai_review_fixes(self):
        """Test accepting all AI review fixes updates the markdown cleanly."""
        ch_dir = os.path.join(self.tmp_dir, "Ch01")
        os.makedirs(ch_dir, exist_ok=True)
        md_file = os.path.join(ch_dir, "Ch01.md")

        content = (
            "Here is the text.\n"
            "<!-- AI-REVIEW-START id=\"rev-1\" category=\"ocr_typo\" -->\n"
            "<!-- ORIGINAL:\n"
            "coun- seling theclienf with anxiety\n"
            "-->\n"
            "counseling the client with anxiety\n"
            "<!-- AI-REVIEW-END -->\n"
            "End of section."
        )
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(content)

        audit_data = [
            {
                "id": "rev-1",
                "category": "ocr_typo",
                "original": "coun- seling theclienf with anxiety",
                "proposed": "counseling the client with anxiety",
                "reason": "Fix hyphenation and OCR typo"
            }
        ]
        self.review_manager.save_review_manifest(ch_dir, audit_data)

        # Apply accepting all
        res = self.review_manager.apply_review_decisions(ch_dir, accept_all=True)
        self.assertTrue(res['success'])
        self.assertEqual(res['applied_count'], 1)

        # Read back markdown
        with open(md_file, "r", encoding="utf-8") as f:
            updated_md = f.read()

        self.assertIn("counseling the client with anxiety", updated_md)
        self.assertNotIn("<!-- AI-REVIEW-START", updated_md)
        self.assertNotIn("theclienf", updated_md)


class TestAdaptiveLearner(unittest.TestCase):
    """Test adaptive learner diagnosis and rule persistence."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.book_output = os.path.join(self.tmp_dir, "test_book")
        os.makedirs(self.book_output, exist_ok=True)
        self.learner = AdaptiveLearner(self.book_output)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_learn_and_persist_noise_rule(self):
        """Test learning a novel noise regex and saving to learned_rules.json."""
        ch_dir = os.path.join(self.book_output, "chapters", "Ch01")
        os.makedirs(ch_dir, exist_ok=True)
        ch_md = os.path.join(ch_dir, "Ch01.md")
        with open(ch_md, "w", encoding="utf-8") as f:
            f.write("Some chapter text with CONFIDENTIAL DRAFT.")

        verification_report = {
            'passed': False,
            'checks': {
                'noise_filter': {
                    'passed': False,
                    'found_strings': ["CONFIDENTIAL DRAFT"]
                }
            }
        }

        diagnosis = self.learner.diagnose_and_learn(verification_report, ch_dir)
        self.assertTrue(diagnosis['should_retry'])

        rules_path = os.path.join(self.book_output, "learned_rules.json")
        self.assertTrue(os.path.exists(rules_path))

        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("noise_patterns", data)
        self.assertTrue(any("CONFIDENTIAL" in p for p in data["noise_patterns"]))


class TestWatchdogService(unittest.TestCase):
    """Test watchdog system health checks."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.inbox = os.path.join(self.tmp_dir, "inbox")
        self.output = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.inbox, exist_ok=True)
        os.makedirs(self.output, exist_ok=True)
        self.watchdog = WatchdogService(inbox_dir=self.inbox, output_dir=self.output)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_system_health_check(self):
        """Assert system health check runs and returns valid disk and cpu info."""
        health = self.watchdog.check_system_health()
        self.assertIn("free_disk_gb", health)
        self.assertIn("cpu_load_pct", health)
        self.assertGreater(health["free_disk_gb"], 0)

    def test_inbox_scan_detects_new_books(self):
        """Assert newly dropped PDF in inbox is detected."""
        dummy_pdf = os.path.join(self.inbox, "NewBook.pdf")
        with open(dummy_pdf, "wb") as f:
            f.write(b"%PDF-1.4 dummy content")

        new_books = self.watchdog.scan_inbox()
        self.assertEqual(len(new_books), 1)
        self.assertEqual(new_books[0].name, "NewBook.pdf")


if __name__ == "__main__":
    unittest.main()
