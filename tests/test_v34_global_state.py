import os
import shutil
import tempfile
import unittest
from pathlib import Path

from book_processor.core.global_state import GlobalStateManager


class TestGlobalStateManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "state"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_update_book_and_progress_calculation(self):
        gsm = GlobalStateManager(self.state_dir)
        chapters = {
            "ch01": {"status": "VERIFIED"},
            "ch02": {"status": "VERIFIED"},
            "ch03": {"status": "PENDING"},
            "ch04": {"status": "FAILED"},
        }
        res = gsm.update_book("Test Textbook", chapters, doc_type="book")
        self.assertEqual(res["total_chapters"], 4)
        self.assertEqual(res["verified"], 2)
        self.assertEqual(res["failed"], 1)
        self.assertEqual(res["progress_pct"], 50)
        self.assertEqual(res["status"], "HAS_FAILURES")

        # Test reload from disk
        all_data = gsm.get_all()
        self.assertIn("Test Textbook", all_data["books"])
        self.assertIsNotNone(all_data["last_updated"])

    def test_complete_status(self):
        gsm = GlobalStateManager(self.state_dir)
        chapters = {
            "ch01": {"status": "VERIFIED"},
            "ch02": {"status": "VERIFIED"},
        }
        res = gsm.update_book("Finished Book", chapters)
        self.assertEqual(res["status"], "COMPLETE")
        self.assertEqual(res["progress_pct"], 100)


if __name__ == "__main__":
    unittest.main()
