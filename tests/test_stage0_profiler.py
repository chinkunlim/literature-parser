"""Unit tests for Stage0Profiler pre-flight layout probing."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from literature_parser.adapters.profiler.stage0_profiler import Stage0Profiler
from literature_parser.domain.profiler.profile_schema import DocumentProfile


class TestStage0Profiler(unittest.TestCase):
    """Verifies that Stage0Profiler induces canonical profile and persists correctly."""

    def test_probe_and_persist_profile(self):
        """Verifies profile synthesis and persistence in target directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "output" / "TestBook"
            fake_pdf = Path(tmp_dir) / "TestBook.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4 minimal dummy pdf content")

            with patch("literature_parser.services.profiler.coordinate_calibrator.CoordinateCalibrator.calibrate_book_geometry") as mock_calib:
                mock_calib.return_value = {
                    "page_dimensions": {"width": 800.0, "height": 1000.0},
                    "margins": {"header_cutoff_y": 50.0, "footer_cutoff_y": 950.0},
                    "columns": {"layout": "single_column", "column_count": 1},
                }

                prof = Stage0Profiler.probe_and_persist_profile(
                    pdf_path=fake_pdf,
                    book_output_dir=out_dir,
                    use_ollama=False,
                )

                self.assertIsInstance(prof, DocumentProfile)
                self.assertEqual(prof.meta.doc_type, "book")

                canon_file = out_dir / "profile.json"
                legacy_file = out_dir / "book_profile.json"
                self.assertTrue(canon_file.exists())
                self.assertTrue(legacy_file.exists())

                with open(canon_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assertEqual(data["geometry"]["columns"]["layout"], "single_column")


if __name__ == "__main__":
    unittest.main()
