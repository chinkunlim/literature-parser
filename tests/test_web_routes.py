"""Integration tests for FastAPI web routes and static SPA hosting."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from literature_parser.entrypoints.web_app import app
from literature_parser.services.core.web_data_service import WebDataService


class TestWebRoutes(unittest.TestCase):
    """Verifies all REST API endpoints exposed by web_app.py."""

    def setUp(self):
        """Creates the TestClient."""
        self.client = TestClient(app)

    def test_get_dashboard(self):
        """Verifies GET /api/dashboard returns HTTP 200 with required schema keys."""
        resp = self.client.get("/api/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_docs", data)
        self.assertIn("completed_docs", data)
        self.assertIn("overall_pct", data)
        self.assertIn("books", data)

    def test_list_books(self):
        """Verifies GET /api/books returns HTTP 200 with book list."""
        resp = self.client.get("/api/books")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("books", data)
        self.assertIsInstance(data["books"], list)

    def test_save_chapter_markdown_and_record_correction(self):
        """Verifies POST /api/books/{book_id}/chapters/{chapter_id}/markdown saves and records issue."""
        with patch.object(WebDataService, "save_chapter_markdown") as mock_save:
            mock_save.return_value = {
                "success": True,
                "correction_id": "mock-uuid-1234",
                "issue_type": "ocr_typo",
                "epub_status": "rebuilt",
            }

            payload = {
                "markdown": "# Chapter 1\nCorrected body text.",
                "issue_type": "ocr_typo",
                "user_notes": "Fixed character error",
                "rebuild_epub": True,
            }
            resp = self.client.post("/api/books/SampleBook/chapters/Ch01/markdown", json=payload)
            self.assertEqual(resp.status_code, 200)
            res_data = resp.json()
            self.assertTrue(res_data["success"])
            self.assertEqual(res_data["correction_id"], "mock-uuid-1234")

    def test_corrections_endpoints(self):
        """Verifies GET /api/corrections, POST /api/corrections, and test generation."""
        # Record direct correction
        record_payload = {
            "book_id": "TestBook",
            "chapter_id": "Ch02",
            "original_text": "bad text",
            "corrected_text": "good text",
            "issue_type": "heading_level",
            "user_notes": "Level was wrong",
        }
        create_resp = self.client.post("/api/corrections", json=record_payload)
        self.assertEqual(create_resp.status_code, 200)
        rec_data = create_resp.json()
        self.assertTrue(rec_data["success"])
        rec_id = rec_data["correction"]["id"]

        # List corrections
        list_resp = self.client.get("/api/corrections")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()["corrections"]
        self.assertTrue(any(r["id"] == rec_id for r in items))

        # Generate regression tests
        gen_resp = self.client.post("/api/corrections/generate-tests")
        self.assertEqual(gen_resp.status_code, 200)
        self.assertTrue(gen_resp.json()["success"])

        # Delete correction
        del_resp = self.client.delete(f"/api/corrections/{rec_id}")
        self.assertEqual(del_resp.status_code, 200)

    def test_serve_index_html(self):
        """Verifies GET / serves the SPA index HTML page."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["content-type"])
        self.assertIn("Literature Parser Studio", resp.text)


if __name__ == "__main__":
    unittest.main()
