"""Unit tests for LayoutFeedbackLoop and closed-loop profile auto-tuning."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from literature_parser.adapters.verification.feedback_loop import LayoutFeedbackLoop


class TestLayoutFeedbackLoop(unittest.TestCase):
    """Verifies that LayoutFeedbackLoop detects anomalies, applies adjustments, and updates profile.json."""

    def test_detect_density_anomalies(self):
        """Verifies low-density anomaly detection on abnormal page content."""
        sample_md = (
            "<!-- Page 1 -->\n# Chapter 1\n" + ("This is full content. " * 30) + "\n\n"
            "<!-- Page 2 -->\nSuspicious drop.\n\n"  # < 100 characters
            "<!-- Page 3 -->\n" + ("Another normal page with extensive body text. " * 20)
        )
        anomalies = LayoutFeedbackLoop._detect_density_anomalies(sample_md)
        self.assertIn(2, anomalies)
        self.assertNotIn(1, anomalies)
        self.assertNotIn(3, anomalies)

    def test_audit_and_tune_persists_feedback(self):
        """Verifies adjustments are persisted into profile.json."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            book_dir = Path(tmp_dir) / "TestBook"
            book_dir.mkdir(parents=True, exist_ok=True)
            canon_profile = book_dir / "profile.json"

            initial_data = {
                "book_name": "TestBook",
                "geometry": {
                    "margins": {"header_cutoff_y": 50.0, "footer_cutoff_y": 950.0},
                    "columns": {"layout": "two_column"},
                },
            }
            canon_profile.write_text(json.dumps(initial_data), encoding="utf-8")

            fake_pdf = book_dir / "ch01.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4 dummy")

            sample_md = "<!-- Page 1 -->\nShort.\n\n"

            with patch.object(LayoutFeedbackLoop, "_diagnose_with_vision") as mock_diag:
                mock_diag.return_value = [{
                    "page": 1,
                    "parameter": "margin_cutoff",
                    "defect": "column_cutoff",
                    "adjustment": "expand_margin_boundary",
                }]

                healed_md, adjustments = LayoutFeedbackLoop.audit_and_tune(
                    markdown_text=sample_md,
                    ch_pdf=fake_pdf,
                    book_output_dir=book_dir,
                    use_vision=True,
                )

                self.assertEqual(len(adjustments), 1)
                self.assertTrue(canon_profile.exists())
                with open(canon_profile, "r", encoding="utf-8") as f:
                    updated = json.load(f)
                    self.assertIn("feedback_history", updated)
                    self.assertEqual(len(updated["feedback_history"]), 1)


if __name__ == "__main__":
    unittest.main()
