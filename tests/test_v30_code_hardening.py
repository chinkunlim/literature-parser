import unittest
from unittest.mock import patch
import subprocess

from book_processor.utils.text_utils import (
    sanitize_filename,
    repair_hyphens,
    stitch_cross_page_continuity,
    normalize_ligatures,
    clean_typography_artifacts,
    clean_punctuation_spacing,
    clean_page_text_artifacts,
    format_chapter_title,
    format_appendix_title,
)
from book_processor.parsers.digital_pdf import DigitalPDFParser
from book_processor.core.orchestrator import BookProcessorOrchestrator


class TestCodeHardening(unittest.TestCase):
    """Verifies defensive coding and boundary guards hardened via Qwen code review."""

    def test_text_utils_empty_guards(self):
        """Ensures all text processing utilities gracefully handle empty/null inputs."""
        self.assertEqual(sanitize_filename(""), "untitled")
        self.assertEqual(repair_hyphens(""), "")
        self.assertEqual(stitch_cross_page_continuity(""), "")
        self.assertEqual(normalize_ligatures(""), "")
        self.assertEqual(clean_typography_artifacts(""), "")
        self.assertEqual(clean_punctuation_spacing(""), "")
        self.assertEqual(clean_page_text_artifacts(""), "")
        self.assertEqual(format_chapter_title(""), "untitled")
        self.assertEqual(format_appendix_title(""), "Appendix")

    def test_running_header_footer_helpers(self):
        """Verifies running header and footer classification helper methods."""
        ph = 1000.0
        # Header (top 4%)
        self.assertTrue(DigitalPDFParser._is_running_header(30.0, ph))
        self.assertFalse(DigitalPDFParser._is_running_header(50.0, ph))

        # Footer (bottom 6% with digit or copyright)
        self.assertTrue(DigitalPDFParser._is_running_footer(950.0, ph, "42", footer_ratio=0.06))
        self.assertTrue(DigitalPDFParser._is_running_footer(960.0, ph, "Copyright 2024", footer_ratio=0.06))
        # Not footer if normal text
        self.assertFalse(DigitalPDFParser._is_running_footer(950.0, ph, "Important body sentence.", footer_ratio=0.06))
        # Not footer if in middle of page
        self.assertFalse(DigitalPDFParser._is_running_footer(500.0, ph, "42", footer_ratio=0.06))

    @patch("subprocess.check_output")
    def test_orchestrator_subprocess_timeouts(self, mock_subp):
        """Verifies orchestrator handles subprocess TimeoutExpired and CalledProcessError without raising unhandled exceptions."""
        mock_subp.side_effect = subprocess.TimeoutExpired(cmd="pdfinfo", timeout=15)
        page_count = BookProcessorOrchestrator.get_pdf_page_count("non_existent.pdf")
        self.assertEqual(page_count, 0)

        mock_subp.side_effect = subprocess.CalledProcessError(returncode=1, cmd="pdfimages")
        is_scanned = BookProcessorOrchestrator.is_scanned_pdf("non_existent.pdf")
        self.assertFalse(is_scanned)


if __name__ == "__main__":
    unittest.main()
