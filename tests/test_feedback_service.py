"""Unit tests for CorrectionService, diff tracking, and regression suite generation."""

import json
import tempfile
import unittest
from pathlib import Path

from literature_parser.domain.correction import CorrectionRecord
from literature_parser.services.core.correction_service import CorrectionService


class TestCorrectionService(unittest.TestCase):
    """Verifies that user corrections are recorded, queried, and converted to unit tests."""

    def setUp(self):
        """Prepares a temporary directory and an isolated CorrectionService instance."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "db" / "corrections.json"
        self.service = CorrectionService(db_path=self.db_path)

    def tearDown(self):
        """Cleans up the temporary directory."""
        self.temp_dir.cleanup()

    def test_record_correction_creates_diff_and_persists(self):
        """Verifies recording a correction computes unified diff and saves to JSON."""
        orig = "# Chapter 1\nThis is a typoo in the text.\n"
        corr = "# Chapter 1\nThis is a typo in the text.\n"

        record = self.service.record_correction(
            book_id="TestBook",
            chapter_id="Ch01",
            original_text=orig,
            corrected_text=corr,
            issue_type="ocr_typo",
            user_notes="Fixed extra 'o' in typo",
        )

        self.assertIsInstance(record, CorrectionRecord)
        self.assertEqual(record.book_id, "TestBook")
        self.assertEqual(record.chapter_id, "Ch01")
        self.assertEqual(record.issue_type, "ocr_typo")
        self.assertIn("typoo", record.diff_snippet)
        self.assertIn("typo", record.diff_snippet)
        self.assertTrue(self.db_path.exists())

        # Verify disk persistence
        records = self.service.list_corrections()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, record.id)
        self.assertEqual(records[0].user_notes, "Fixed extra 'o' in typo")

    def test_list_corrections_with_filters(self):
        """Verifies filtering by book_id and issue_type."""
        self.service.record_correction("BookA", "Ch01", "a", "b", issue_type="ocr_typo")
        self.service.record_correction("BookB", "Ch02", "c", "d", issue_type="table_layout")
        self.service.record_correction("BookA", "Ch03", "e", "f", issue_type="heading_level")

        all_recs = self.service.list_corrections()
        self.assertEqual(len(all_recs), 3)

        book_a_recs = self.service.list_corrections(book_id="BookA")
        self.assertEqual(len(book_a_recs), 2)

        table_recs = self.service.list_corrections(issue_type="table_layout")
        self.assertEqual(len(table_recs), 1)
        self.assertEqual(table_recs[0].book_id, "BookB")

    def test_delete_correction(self):
        """Verifies deletion of a record by ID."""
        rec = self.service.record_correction("BookA", "Ch01", "a", "b")
        self.assertEqual(len(self.service.list_corrections()), 1)

        success = self.service.delete_correction(rec.id)
        self.assertTrue(success)
        self.assertEqual(len(self.service.list_corrections()), 0)

        # Deleting non-existent returns False
        self.assertFalse(self.service.delete_correction("non-existent-id"))

    def test_generate_regression_tests(self):
        """Verifies that recorded corrections are compiled into an executable test script."""
        self.service.record_correction(
            book_id="BookA",
            chapter_id="Ch01",
            original_text="Old Corrupt Header",
            corrected_text="Clean Proper Header",
            issue_type="heading_level",
            user_notes="Should be H1",
        )

        test_file = Path(self.temp_dir.name) / "test_generated_regression.py"
        res = self.service.generate_regression_tests(target_file=test_file)

        self.assertTrue(res["success"])
        self.assertEqual(res["total_records"], 1)
        self.assertTrue(test_file.exists())

        code = test_file.read_text(encoding="utf-8")
        self.assertIn("class TestUserCorrectionsRegression(unittest.TestCase):", code)
        self.assertIn("Clean Proper Header", code)
        self.assertIn("test_correction_1_heading_level", code)


if __name__ == "__main__":
    unittest.main()
