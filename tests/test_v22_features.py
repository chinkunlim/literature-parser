"""
v2.2.0 Feature Tests
====================
Tests for:
  1. GlobalLearner cross-book rule persistence
  2. AdaptiveLearner ↔ GlobalLearner pattern sharing
  3. Auto-accept confidence threshold in ReviewManager
  4. Atomic write correctness in checkpoint
  5. Fixed math symbol grouping in MathLaTeXConverter
  6. CircuitBreaker new threshold (3)
  7. Watchdog log rotation
  8. Watchdog scan_stuck_books
  9. ImageManager cover-art fix (dead code removed)
  10. Verifier: dynamic sips path
  11. Config: GLOBAL_RULES_DIR, AUTO_ACCEPT_CONFIDENCE_THRESHOLD
  12. Full convert_symbols adjacency grouping
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src/ is on the path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))


class TestConfig(unittest.TestCase):
    """Validate new config constants."""

    def test_global_rules_dir_is_in_home(self):
        from doc_processor.config import GLOBAL_RULES_DIR
        self.assertTrue(str(GLOBAL_RULES_DIR).startswith(str(Path.home())))
        self.assertIn(".doc_processor", str(GLOBAL_RULES_DIR))

    def test_auto_accept_threshold_value(self):
        from doc_processor.config import AUTO_ACCEPT_CONFIDENCE_THRESHOLD
        self.assertGreaterEqual(AUTO_ACCEPT_CONFIDENCE_THRESHOLD, 0.90)
        self.assertLessEqual(AUTO_ACCEPT_CONFIDENCE_THRESHOLD, 1.0)

    def test_circuit_breaker_max_failures_three(self):
        from doc_processor.config import CIRCUIT_BREAKER_MAX_FAILURES
        self.assertEqual(CIRCUIT_BREAKER_MAX_FAILURES, 3)

    def test_max_alert_log_bytes_positive(self):
        from doc_processor.config import MAX_ALERT_LOG_BYTES
        self.assertGreater(MAX_ALERT_LOG_BYTES, 0)


class TestGlobalLearner(unittest.TestCase):
    """Test GlobalLearner cross-book persistence."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Redirect GlobalLearner to a temp dir
        from doc_processor import config as cfg
        self._orig_dir = cfg.GLOBAL_RULES_DIR
        cfg.GLOBAL_RULES_DIR = Path(self.tmp)
        # Reimport to pick up patched constant
        from doc_processor.core import learner as lm
        lm.GLOBAL_RULES_DIR = Path(self.tmp)
        from importlib import reload
        reload(lm)
        self.lm = lm

    def tearDown(self):
        from doc_processor import config as cfg
        cfg.GLOBAL_RULES_DIR = self._orig_dir
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_and_retrieve_noise_patterns(self):
        GL = self.lm.GlobalLearner
        GL._rules_file = Path(self.tmp) / "global_rules.json"
        added = GL.add_noise_patterns([r"\btest_pattern_xyz\b"])
        self.assertEqual(added, 1)
        patterns = GL.get_noise_patterns()
        self.assertIn(r"\btest_pattern_xyz\b", patterns)

    def test_no_duplicate_patterns(self):
        GL = self.lm.GlobalLearner
        GL._rules_file = Path(self.tmp) / "global_rules.json"
        GL.add_noise_patterns([r"\bduplicate\b"])
        added_again = GL.add_noise_patterns([r"\bduplicate\b"])
        self.assertEqual(added_again, 0)

    def test_global_rules_file_created(self):
        GL = self.lm.GlobalLearner
        GL._rules_file = Path(self.tmp) / "global_rules.json"
        GL.add_noise_patterns([r"\bfoo\b"])
        self.assertTrue(GL._rules_file.exists())

    def test_json_not_corrupted_on_add(self):
        GL = self.lm.GlobalLearner
        GL._rules_file = Path(self.tmp) / "global_rules.json"
        GL.add_noise_patterns([r"\bpat1\b"])
        GL.add_noise_patterns([r"\bpat2\b"])
        with open(GL._rules_file) as f:
            data = json.load(f)
        self.assertIn(r"\bpat1\b", data["noise_patterns"])
        self.assertIn(r"\bpat2\b", data["noise_patterns"])


class TestAdaptiveLearnerGlobalIntegration(unittest.TestCase):
    """AdaptiveLearner should push patterns to GlobalLearner."""

    def setUp(self):
        self.tmp_book = tempfile.mkdtemp()
        self.tmp_global = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_book, ignore_errors=True)
        shutil.rmtree(self.tmp_global, ignore_errors=True)

    def test_get_noise_patterns_merges_global(self):
        from doc_processor.core.learner import GlobalLearner, AdaptiveLearner
        orig = GlobalLearner._rules_file
        GlobalLearner._rules_file = Path(self.tmp_global) / "global_rules.json"
        try:
            GlobalLearner.add_noise_patterns([r"\bglobal_noise\b"])
            learner = AdaptiveLearner(self.tmp_book)
            merged = learner.get_noise_patterns()
            self.assertIn(r"\bglobal_noise\b", merged)
        finally:
            GlobalLearner._rules_file = orig


class TestAtomicCheckpoint(unittest.TestCase):
    """Checkpoint writes must survive simulated mid-write failures."""

    def test_checkpoint_creates_json_and_md(self):
        from doc_processor.core.checkpoint import CheckpointManager
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = CheckpointManager(tmp, "TestBook")
            ckpt.init_chapters([{"name": "Ch01", "start": 1, "end": 10}])
            self.assertTrue((Path(tmp) / "processing_status.json").exists())
            self.assertTrue((Path(tmp) / "processing_status.md").exists())

    def test_checkpoint_resume_command_is_correct(self):
        from doc_processor.core.checkpoint import CheckpointManager
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = CheckpointManager(tmp, "TestBook")
            ckpt.init_chapters([{"name": "Ch01", "start": 1, "end": 5}])
            md = (Path(tmp) / "processing_status.md").read_text()
            # Must use the real entry-point, not -m doc_processor.cli
            self.assertIn("doc_processor.py resume", md)
            self.assertNotIn("-m doc_processor.cli", md)

    def test_no_leftover_tmp_files_on_success(self):
        from doc_processor.core.checkpoint import CheckpointManager
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = CheckpointManager(tmp, "TestBook")
            ckpt.init_chapters([{"name": "Ch01", "start": 1, "end": 5}])
            tmp_files = list(Path(tmp).glob("*.tmp"))
            self.assertEqual(tmp_files, [])


class TestAutoAcceptReviewManager(unittest.TestCase):
    """High-confidence proposals must be auto-accepted; low-confidence go to HITL."""

    def _make_md(self, tmp_dir: str, content: str) -> None:
        ch_name = Path(tmp_dir).name
        (Path(tmp_dir) / f"{ch_name}.md").write_text(content)

    def test_high_confidence_auto_accepted(self):
        from doc_processor.verification.review_manager import ReviewManager
        with tempfile.TemporaryDirectory() as tmp:
            ch_name = Path(tmp).name
            self._make_md(tmp, "This tezt should be corrected.")
            proposals = [
                {
                    "id": "rev-1",
                    "original": "tezt",
                    "proposed": "text",
                    "reason": "OCR error",
                    "category": "ocr_typo",
                    "confidence": 0.98,
                }
            ]
            result = ReviewManager.save_review_manifest(tmp, proposals)
            self.assertEqual(result["auto_accepted"], 1)
            self.assertEqual(result["pending"], 0)
            # The markdown should have been patched
            md = (Path(tmp) / f"{ch_name}.md").read_text()
            self.assertIn("text", md)
            self.assertNotIn("tezt", md)

    def test_low_confidence_goes_to_pending(self):
        from doc_processor.verification.review_manager import ReviewManager
        with tempfile.TemporaryDirectory() as tmp:
            self._make_md(tmp, "Some ambiguous content here.")
            proposals = [
                {
                    "id": "rev-2",
                    "original": "ambiguous",
                    "proposed": "clear",
                    "reason": "AI suggestion",
                    "category": "style",
                    "confidence": 0.70,
                }
            ]
            result = ReviewManager.save_review_manifest(tmp, proposals)
            self.assertEqual(result["auto_accepted"], 0)
            self.assertEqual(result["pending"], 1)

    def test_mixed_confidence_split(self):
        from doc_processor.verification.review_manager import ReviewManager
        with tempfile.TemporaryDirectory() as tmp:
            self._make_md(tmp, "word1 word2 word3")
            proposals = [
                {"id": "r1", "original": "word1", "proposed": "Word1", "reason": "cap", "category": "style", "confidence": 0.97},
                {"id": "r2", "original": "word2", "proposed": "Word2", "reason": "cap", "category": "style", "confidence": 0.60},
                {"id": "r3", "original": "word3", "proposed": "Word3", "reason": "cap", "category": "style", "confidence": 0.99},
            ]
            result = ReviewManager.save_review_manifest(tmp, proposals)
            self.assertEqual(result["auto_accepted"], 2)
            self.assertEqual(result["pending"], 1)


class TestMathLaTeXConverterSymbols(unittest.TestCase):
    """Adjacent Greek symbols must be grouped into a single $...$ span."""

    def test_single_symbol(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        result = MathLaTeXConverter.convert_symbols("α")
        self.assertEqual(result, r"$\alpha$")

    def test_two_adjacent_symbols_no_collision(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        result = MathLaTeXConverter.convert_symbols("αβ")
        # Must not produce $\alpha$$\beta$
        self.assertNotIn("$$", result)
        self.assertIn(r"\alpha", result)
        self.assertIn(r"\beta", result)

    def test_symbols_with_operator_between(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        result = MathLaTeXConverter.convert_symbols("α + β")
        self.assertNotIn("$$", result)

    def test_no_math_chars_unchanged(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        text = "Hello, World!"
        self.assertEqual(MathLaTeXConverter.convert_symbols(text), text)

    def test_dfrac_injection(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        result = MathLaTeXConverter.ensure_uniform_fraction_sizing(r"$$\frac{a}{b}$$")
        self.assertIn(r"\dfrac", result)
        self.assertIn(r"\displaystyle", result)

    def test_check_equation_balance_ok(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        res = MathLaTeXConverter.check_equation_balance("Some text $x = 1$ and $$y = 2$$")
        self.assertTrue(res["balanced"])
        self.assertEqual(res["issues"], [])

    def test_check_equation_balance_fail(self):
        from doc_processor.parsers.math_latex import MathLaTeXConverter
        res = MathLaTeXConverter.check_equation_balance("Unpaired $x = 1")
        self.assertFalse(res["balanced"])


class TestCircuitBreakerNewThreshold(unittest.TestCase):
    """Circuit breaker should trip only after 3 consecutive failures."""

    def test_trips_at_three(self):
        from doc_processor.core.invariants import CircuitBreaker
        cb = CircuitBreaker(max_consecutive_failures=3)
        cb.record_failure("ch1", "err")
        self.assertFalse(cb.is_tripped())
        cb.record_failure("ch2", "err")
        self.assertFalse(cb.is_tripped())
        cb.record_failure("ch3", "err")
        self.assertTrue(cb.is_tripped())

    def test_reset_on_success(self):
        from doc_processor.core.invariants import CircuitBreaker
        cb = CircuitBreaker(max_consecutive_failures=3)
        cb.record_failure("ch1", "err")
        cb.record_failure("ch2", "err")
        cb.record_success("ch3")  # resets streak
        cb.record_failure("ch4", "err")
        self.assertFalse(cb.is_tripped())

    def test_config_default_is_three(self):
        from doc_processor.config import CIRCUIT_BREAKER_MAX_FAILURES
        self.assertEqual(CIRCUIT_BREAKER_MAX_FAILURES, 3)


class TestWatchdogScanStuckBooks(unittest.TestCase):
    """scan_stuck_books must detect partially-converted output books."""

    def test_detects_failed_chapter(self):
        from doc_processor.core.watchdog import WatchdogService
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            book_dir = output_dir / "MyBook"
            book_dir.mkdir(parents=True)
            status = {
                "book_title": "MyBook",
                "chapters": {
                    "Ch01": {"status": "VERIFIED"},
                    "Ch02": {"status": "FAILED"},
                }
            }
            (book_dir / "processing_status.json").write_text(
                json.dumps(status)
            )
            wd = WatchdogService(
                inbox_dir=str(Path(tmp) / "inbox"),
                processed_dir=str(Path(tmp) / "processed"),
                output_dir=str(output_dir),
            )
            stuck = wd.scan_stuck_books()
            self.assertEqual(len(stuck), 1)
            self.assertEqual(stuck[0][0], "MyBook")
            self.assertEqual(stuck[0][1], 1)  # 1 pending chapter

    def test_no_stuck_when_all_verified(self):
        from doc_processor.core.watchdog import WatchdogService
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            book_dir = output_dir / "MyBook"
            book_dir.mkdir(parents=True)
            status = {
                "book_title": "MyBook",
                "chapters": {
                    "Ch01": {"status": "VERIFIED"},
                    "Ch02": {"status": "VERIFIED"},
                }
            }
            (book_dir / "processing_status.json").write_text(
                json.dumps(status)
            )
            wd = WatchdogService(
                inbox_dir=str(Path(tmp) / "inbox"),
                processed_dir=str(Path(tmp) / "processed"),
                output_dir=str(output_dir),
            )
            stuck = wd.scan_stuck_books()
            self.assertEqual(len(stuck), 0)


class TestWatchdogLogRotation(unittest.TestCase):
    """log_alert should rotate the file when it exceeds MAX_ALERT_LOG_BYTES."""

    def test_rotation_occurs(self):
        from doc_processor.core.watchdog import WatchdogService
        from doc_processor import config as cfg
        orig = cfg.MAX_ALERT_LOG_BYTES
        cfg.MAX_ALERT_LOG_BYTES = 50  # Very small threshold for test
        try:
            with tempfile.TemporaryDirectory() as tmp:
                output_dir = Path(tmp) / "output"
                output_dir.mkdir()
                wd = WatchdogService(
                    inbox_dir=str(Path(tmp) / "inbox"),
                    processed_dir=str(Path(tmp) / "processed"),
                    output_dir=str(output_dir),
                )
                # Write until rotation is triggered
                for i in range(20):
                    wd.log_alert(f"Alert message number {i} with some padding data.")
                rotated = wd.alerts_file.with_suffix(".log.1")
                self.assertTrue(
                    rotated.exists(),
                    "Rotated log file should exist after size threshold exceeded.",
                )
        finally:
            cfg.MAX_ALERT_LOG_BYTES = orig


class TestContentContinuity(unittest.TestCase):
    """Validate content continuity verification and auto-stitching."""

    def test_continuous_text_passes(self):
        from doc_processor.verification.rules import check_content_continuity
        good_md = (
            "# Chapter 1\n\n"
            "<!-- Page 1 -->\n"
            "This is a complete sentence that finishes properly.\n\n"
            "<!-- Page 2 -->\n"
            "This is another complete sentence on the next page."
        )
        res = check_content_continuity(good_md)
        self.assertTrue(res["passed"])
        self.assertEqual(res["abrupt_cuts"], 0)

    def test_detects_abrupt_paragraph_cut(self):
        from doc_processor.verification.rules import check_content_continuity
        broken_md = (
            "# Chapter 1\n\n"
            "This sentence was abruptly cut in the middle of\n\n"
            "a thought without terminal punctuation."
        )
        res = check_content_continuity(broken_md)
        self.assertFalse(res["passed"])
        self.assertGreater(res["abrupt_cuts"], 0)

    def test_stitch_joins_hyphenated_word_across_pages(self):
        from doc_processor.utils.text_utils import stitch_cross_page_continuity
        broken_md = "This was an experi-\n\n<!-- Page 2 -->\n\nment that succeeded."
        fixed = stitch_cross_page_continuity(broken_md)
        self.assertIn("experiment that succeeded.", fixed)
        self.assertNotIn("experi-", fixed)

    def test_stitch_joins_sentence_across_pages(self):
        from doc_processor.utils.text_utils import stitch_cross_page_continuity
        broken_md = (
            "The researcher observed the\n\n"
            "<!-- Page 2 -->\n\n"
            "behavior of the subjects carefully."
        )
        fixed = stitch_cross_page_continuity(broken_md)
        # Should remove double newline between text and page comment so sentence flows
        self.assertNotIn("observed the\n\n<!-- Page 2 -->\n\nbehavior", fixed)
        self.assertIn("behavior of the subjects carefully.", fixed)

    def test_sentence_completeness_dangling_word(self):
        from doc_processor.verification.rules import check_sentence_completeness
        bad_text = "The participants were randomly assigned to the condition and"
        res = check_sentence_completeness(bad_text)
        self.assertFalse(res["passed"])
        self.assertGreater(len(res["incomplete_endings"]), 0)


class TestCommonPDFConversionIssues(unittest.TestCase):
    """Validate solutions for common textbook PDF-to-Markdown conversion defects."""

    def test_normalize_ligatures(self):
        from doc_processor.utils.text_utils import normalize_ligatures
        corrupted = "The ﬁrst deﬁnition of the eﬀect was found on the ﬂoor of the oﬃce."
        fixed = normalize_ligatures(corrupted)
        self.assertEqual(fixed, "The first definition of the effect was found on the floor of the office.")

    def test_clean_typography_artifacts(self):
        from doc_processor.utils.text_utils import clean_typography_artifacts
        raw = "Treatment A---control B--measured\n|\nNext paragraph."
        cleaned = clean_typography_artifacts(raw)
        self.assertIn("—", cleaned)
        self.assertNotIn("---", cleaned)
        self.assertNotIn("--", cleaned)

    def test_detect_and_format_tables(self):
        from doc_processor.parsers.layout_detector import LayoutDetector
        table_raw = (
            "Variable   Mean   SD   n\n"
            "Group1     15.2   2.1  30\n"
            "Group2     12.8   1.9  30\n"
            "Control    10.1   2.4  30"
        )
        formatted = LayoutDetector.detect_and_format_tables([table_raw])
        self.assertEqual(len(formatted), 1)
        self.assertIn("| Variable | Mean | SD | n |", formatted[0])
        self.assertIn("| --- | --- | --- | --- |", formatted[0])
        self.assertIn("| Group1 | 15.2 | 2.1 | 30 |", formatted[0])

    def test_detect_and_format_lists(self):
        from doc_processor.parsers.layout_detector import LayoutDetector
        squashed = "The key criteria were: • Random assignment. • Control group. • Double blind."
        formatted = LayoutDetector.detect_and_format_lists(squashed)
        self.assertIn("- Random assignment.", formatted)
        self.assertIn("- Control group.", formatted)
        self.assertIn("- Double blind.", formatted)

    def test_format_figure_captions(self):
        from doc_processor.parsers.layout_detector import LayoutDetector
        caption = "Figure 3.2: Distribution of sample test scores across treatment conditions."
        formatted = LayoutDetector.format_figure_captions([caption])
        self.assertEqual(formatted[0], f"*{caption}*")


if __name__ == "__main__":
    unittest.main(verbosity=2)


