"""
Unit Tests for Book Profile Adaptive Learning and Cross-Chapter Memory Evolution
================================================================================
Tests DocumentProfile anomalies, learned_fixes, chapter_history serialization,
and closed-loop recording of chapter verification and MiniCPM-V visual defects.
"""

import json
import tempfile
import unittest
from pathlib import Path

from literature_parser.domain.profiler.profile_schema import DocumentProfile, ProfileMetadata


class TestBookProfileAdaptiveLearning(unittest.TestCase):
    """Verifies that book profile captures chapter audits, visual defects, and learned fixes."""

    def test_document_profile_anomalies_and_chapter_history_serialization(self) -> None:
        """Verifies DocumentProfile to_dict and from_dict roundtrip with dynamic fields."""
        prof = DocumentProfile(
            meta=ProfileMetadata(title="Test Textbook"),
            anomalies=[
                {"chapter": "Ch01", "page": 3, "feature": "table", "defect": "Mismatched columns"}
            ],
            learned_fixes={"table_padding": "tight"},
            chapter_history={"Ch01": {"passed": True, "accuracy_percent": 95.0}},
        )

        data = prof.to_dict()
        self.assertIn("anomalies", data)
        self.assertIn("learned_fixes", data)
        self.assertIn("chapter_history", data)
        self.assertEqual(len(data["anomalies"]), 1)
        self.assertEqual(data["learned_fixes"]["table_padding"], "tight")

        restored = DocumentProfile.from_dict(data)
        self.assertEqual(restored.meta.title, "Test Textbook")
        self.assertEqual(len(restored.anomalies), 1)
        self.assertEqual(restored.anomalies[0]["defect"], "Mismatched columns")
        self.assertEqual(restored.learned_fixes["table_padding"], "tight")
        self.assertIn("Ch01", restored.chapter_history)

    def test_document_profile_record_chapter_audit_with_visual_defect(self) -> None:
        """Verifies record_chapter_audit extracts visual defects and records chapter history."""
        prof = DocumentProfile(meta=ProfileMetadata(title="Research Methods"))

        audit_res = {
            "chapter": "Ch15-Descriptive-Statistics",
            "passed": True,
            "accuracy_percent": 98.0,
            "checks": {
                "vocabulary": {"passed": True},
                "math_integrity": {"passed": True},
            },
        }

        visual_res = {
            "status": "PASSED",
            "quality_score": 9.0,
            "vision_model": "minicpm-v:latest",
            "audited_pages": [
                {
                    "page": 1,
                    "feature": "concept_map_and_lo",
                    "verified": True,
                    "vision_verified": True,
                    "vision_defect": None,
                },
                {
                    "page": 13,
                    "feature": "table",
                    "verified": False,
                    "vision_verified": False,
                    "vision_defect": "Table 15.4 data row missing sum value",
                    "confidence": 0.90,
                },
            ],
        }

        prof.record_chapter_audit(
            chapter_name="Ch15-Descriptive-Statistics",
            audit_data=audit_res,
            visual_data=visual_res,
        )

        # Check chapter history
        self.assertIn("Ch15-Descriptive-Statistics", prof.chapter_history)
        entry = prof.chapter_history["Ch15-Descriptive-Statistics"]
        self.assertTrue(entry["passed"])
        self.assertEqual(entry["accuracy_percent"], 98.0)
        self.assertEqual(entry["visual_audit"]["vision_model"], "minicpm-v:latest")
        self.assertEqual(entry["visual_audit"]["quality_score"], 9.0)

        # Check anomaly extraction
        self.assertEqual(len(prof.anomalies), 1)
        anomaly = prof.anomalies[0]
        self.assertEqual(anomaly["chapter"], "Ch15-Descriptive-Statistics")
        self.assertEqual(anomaly["page"], 13)
        self.assertEqual(anomaly["feature"], "table")
        self.assertIn("data row missing sum value", anomaly["defect"])

    def test_profile_persistence_in_book_dir(self) -> None:
        """Verifies book_profile.json persistence and updates across chapter runs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            book_dir = Path(tmp_dir)
            prof_file = book_dir / "book_profile.json"

            # Initial calibration state
            initial_prof = DocumentProfile(meta=ProfileMetadata(title="Sample Book"))
            with open(prof_file, "w", encoding="utf-8") as f:
                json.dump(initial_prof.to_dict(), f, indent=2)

            # Simulate chapter 1 completion
            with open(prof_file, "r", encoding="utf-8") as f:
                loaded = DocumentProfile.from_dict(json.load(f))

            loaded.record_chapter_audit(
                chapter_name="Ch01-Introduction",
                audit_data={"passed": True, "accuracy_percent": 99.0, "checks": {}},
                visual_data={"status": "PASSED", "quality_score": 10.0, "vision_model": "minicpm-v:latest", "audited_pages": []},
            )

            with open(prof_file, "w", encoding="utf-8") as f:
                json.dump(loaded.to_dict(), f, indent=2)

            # Read back from disk
            with open(prof_file, "r", encoding="utf-8") as f:
                updated_disk = json.load(f)

            self.assertIn("chapter_history", updated_disk)
            self.assertIn("Ch01-Introduction", updated_disk["chapter_history"])
            self.assertEqual(updated_disk["chapter_history"]["Ch01-Introduction"]["accuracy_percent"], 99.0)


if __name__ == "__main__":
    unittest.main()
