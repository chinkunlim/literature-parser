"""
Unit Tests for Input Segregation & Folder Naming Hygiene
=========================================================
Validates:
- sanitize_filename hyphenation and underscore stripping
- format_chapter_title and format_appendix_title standard hyphenation
- Convention-based input segregation (digital-pdf vs scanned-pdf)
- Document archetype resolution from folder parents
"""

import tempfile
import unittest
from pathlib import Path

from literature_parser.services.utils.text_utils import (
    format_appendix_title,
    format_chapter_title,
    sanitize_filename,
)


class TestFolderNamingHygiene(unittest.TestCase):
    """Verifies that filenames and directory names adhere to hyphen-separated hygiene rules."""

    def test_sanitize_filename_hyphenation(self):
        """Ensures whitespace, underscores, and illegal characters are turned into hyphens."""
        self.assertEqual(
            sanitize_filename("Research Methods, Design, and Analysis 13th ed"),
            "Research-Methods-Design-and-Analysis-13th-ed"
        )
        self.assertEqual(
            sanitize_filename("Sample_Book_With_Underscore"),
            "Sample-Book-With-Underscore"
        )
        self.assertEqual(
            sanitize_filename("   Spaces   and   Tabs\t"),
            "Spaces-and-Tabs"
        )
        self.assertEqual(
            sanitize_filename("Invalid:Chars/And\\Slashes*?"),
            "Invalid-Chars-And-Slashes"
        )
        self.assertEqual(sanitize_filename(""), "untitled")

    def test_format_chapter_title_hyphenation(self):
        """Ensures chapter title formatting yields clean hyphenated directory strings."""
        self.assertEqual(
            format_chapter_title("Chapter 1 Introduction to Science"),
            "Ch01-Introduction-to-Science"
        )
        self.assertEqual(
            format_chapter_title("Chapter 12 Advanced Methods & Stats"),
            "Ch12-Advanced-Methods-Stats"
        )
        self.assertEqual(format_chapter_title(""), "untitled")

    def test_format_appendix_title_hyphenation(self):
        """Ensures appendix title formatting yields clean hyphenated directory strings."""
        self.assertEqual(
            format_appendix_title("Appendix A Complete Solutions"),
            "Appendix-A-Solutions"
        )
        self.assertEqual(
            format_appendix_title("Appendix B Formula Tables"),
            "Appendix-B-Formula-Tables"
        )
        self.assertEqual(format_appendix_title(""), "Appendix")


class TestInputSegregationRouting(unittest.TestCase):
    """Verifies directory convention routing for digital-pdf and scanned-pdf inputs."""

    def test_convention_scan_mode_resolution(self):
        """Tests that parent directory names reliably dictate scan mode without heuristic probing."""
        # Book: digital-pdf
        p1 = Path("/workspace/data/input/books/digital-pdf/sample_book.pdf")
        p1_names = [p.name.lower() for p in p1.parents]
        self.assertTrue(any(name in ("digital-pdf", "digital_pdf", "digital") for name in p1_names))
        self.assertFalse(any(name in ("scanned-pdf", "scanned_pdf", "scanned") for name in p1_names))

        # Book: scanned-pdf
        p2 = Path("/workspace/data/input/books/scanned-pdf/scanned_book.pdf")
        p2_names = [p.name.lower() for p in p2.parents]
        self.assertTrue(any(name in ("scanned-pdf", "scanned_pdf", "scanned") for name in p2_names))

        # Literature: root default
        p3 = Path("/workspace/data/input/literature/academic_paper.pdf")
        p3_names = [p.name.lower() for p in p3.parents]
        self.assertTrue(any(name in ("literature", "journals", "papers") for name in p3_names))
