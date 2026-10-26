"""Unit tests for EpubVisualAuditor.

Tests EPUB page rendering via PyMuPDF and Ollama VLM multimodal verification.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from literature_parser.services.verification.epub_visual_auditor import EpubVisualAuditor, PageAuditResult


class TestEpubVisualAuditor(unittest.TestCase):
    """Test suite for EpubVisualAuditor."""

    def setUp(self):
        self.auditor = EpubVisualAuditor()

    def test_audit_page_with_ollama_mocked_success(self):
        """Verifies parsing a clean Ollama VLM response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_img = Path(tmpdir) / "page_001.png"
            fake_img.write_bytes(b"fake_png_data")

            mock_response = json.dumps({
                "response": json.dumps({
                    "has_defects": False,
                    "defect_description": None,
                    "rating": 10,
                })
            }).encode("utf-8")

            mock_resp_obj = MagicMock()
            mock_resp_obj.read.return_value = mock_response
            mock_resp_obj.__enter__.return_value = mock_resp_obj

            with patch("urllib.request.urlopen", return_value=mock_resp_obj):
                res = self.auditor.audit_page_with_ollama(fake_img, page_index=1)
                self.assertFalse(res.has_defects)
                self.assertEqual(res.rating, 10)
                self.assertIsNone(res.defect_description)

    def test_audit_page_with_ollama_mocked_defects(self):
        """Verifies parsing an Ollama VLM response that flags visual defects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_img = Path(tmpdir) / "page_002.png"
            fake_img.write_bytes(b"fake_png_data")

            mock_response = json.dumps({
                "response": json.dumps({
                    "has_defects": True,
                    "defect_description": "Overlapping drop shadow text detected",
                    "rating": 4,
                })
            }).encode("utf-8")

            mock_resp_obj = MagicMock()
            mock_resp_obj.read.return_value = mock_response
            mock_resp_obj.__enter__.return_value = mock_resp_obj

            with patch("urllib.request.urlopen", return_value=mock_resp_obj):
                res = self.auditor.audit_page_with_ollama(fake_img, page_index=2)
                self.assertTrue(res.has_defects)
                self.assertEqual(res.rating, 4)
                self.assertIn("Overlapping", res.defect_description)


if __name__ == "__main__":
    unittest.main()
