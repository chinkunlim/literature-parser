"""
Test Suite v28: Advanced Features Verification
===============================================
Tests for:
1. Model Advisor: status checking and recommendation structure.
2. Coordinate Calibrator: geometry calibration on sample textbook.
3. Visual Auditor: automated page sampling and scoring.
4. Checkpoint Manager: manifest state tracking and dashboard rendering.
"""

import os
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from literature_parser.domain.profiler.model_advisor import check_models_status
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.adapters.verification.visual_auditor import VisualAuditor
from literature_parser.services.core.checkpoint import CheckpointManager
from literature_parser.config.settings import load_config
import tempfile

BOOK_DIR = load_config().output_dir / "books/Research Methods, Design, and Analysis 13th ed"
CH02_PDF = BOOK_DIR / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.pdf"
CH02_MD = BOOK_DIR / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.md"


class TestV28AdvancedFeatures(unittest.TestCase):

    def test_model_advisor_structure(self):
        """Verify model advisor checks and returns proper recommendation dict."""
        status = check_models_status()
        self.assertIn("ollama_online", status)
        self.assertIn("recommended", status)
        self.assertIn("text_structuring", status["recommended"])
        self.assertIn("vision_audit", status["recommended"])

    def test_coordinate_calibrator(self):
        """Verify coordinate calibrator extracts valid margins from sample textbook."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        geom = CoordinateCalibrator.calibrate_book_geometry(str(CH02_PDF))
        self.assertIn("page_width", geom)
        self.assertIn("page_height", geom)
        self.assertIn("odd_page_margin_x", geom)
        self.assertIn("even_page_margin_x", geom)
        self.assertGreater(geom["page_width"], 500)
        self.assertGreater(geom["page_height"], 700)
        self.assertLess(geom["even_page_margin_x"][1], 0.40)
        self.assertGreater(geom["odd_page_margin_x"][0], 0.60)

    def test_visual_auditor_scoring(self):
        """Verify visual auditor calculates valid quality score and finds key features."""
        import shutil
        if not CH02_PDF.exists() or not CH02_MD.exists() or not shutil.which("pdftohtml"):
            self.skipTest("Ch02 PDF or MD or pdftohtml not found")
        res = VisualAuditor.audit_chapter(CH02_PDF, CH02_MD, CH02_PDF.parent)
        self.assertIn("quality_score", res)
        self.assertGreaterEqual(res["quality_score"], 8.0)
        self.assertTrue(res["has_mindmap"])
        self.assertGreaterEqual(res["flashcard_count"], 0)

    def test_checkpoint_manager_state(self):
        """Verify CheckpointManager loads and updates chapter statuses atomically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir, "Research Methods, Design, and Analysis 13th ed")
            cm.update_status("TestChapter", status="CONVERTED", total_pages=10)
            self.assertIn("TestChapter", cm.data["chapters"])
            self.assertEqual(cm.data["chapters"]["TestChapter"]["status"], "CONVERTED")
            md_text = cm._render_markdown()
            self.assertIn("# Processing Status", md_text)
            # Clean up test entry
            del cm.data["chapters"]["TestChapter"]
            cm.save()


if __name__ == '__main__':
    unittest.main()
