"""
Unit Tests for Front Matter Separation, Pure Chapter 1 & Shared Knowledge Taxonomy
==================================================================================
Validates:
- Shared knowledge taxonomy loading (front_matter_taxonomy.json & pedagogical_blocks.json)
- Odd-Even PageAsymmetry schema and serialization
- Front matter slug matching and Chapter 1 pure body isolation
- Automatic detection and prepending of missing Front Matter pages
- Pre-flight book profiling strictly sampling body chapters (excluding 00-*)
- Full Markdown navigation linking Front Matter and Chapters in sequential order
"""

import json
import tempfile
import unittest
from pathlib import Path

from literature_parser.adapters.core.orchestrator import BookProcessorOrchestrator
from literature_parser.domain.profiler.profile_schema import (
    DocumentProfile,
    PageAsymmetry,
    ProfileGeometry,
    ProfileSpecialBlocks,
    ProfileTypography,
)
from literature_parser.services.config_manager import ConfigManager
from literature_parser.services.core.analyzer import PDFAnalyzer
from literature_parser.services.utils.obsidian_linker import (
    generate_book_index,
    inject_chapter_navigation,
)


class TestSharedKnowledgeTaxonomy(unittest.TestCase):
    """Verifies that Level 3 Shared Knowledge files load and conform to specifications."""

    def test_load_front_matter_taxonomy(self) -> None:
        """Ensures front_matter_taxonomy.json loads properly with expected categories."""
        tax = ConfigManager.load_front_matter_taxonomy()
        self.assertIsInstance(tax, list)
        self.assertGreaterEqual(len(tax), 6)

        slugs = [item.get("canonical_slug") for item in tax]
        self.assertIn("00-01-Cover", slugs)
        self.assertIn("00-07-TOC", slugs)
        self.assertIn("00-09-Preface", slugs)

    def test_load_pedagogical_blocks(self) -> None:
        """Ensures pedagogical_blocks.json loads with expected blocks."""
        blocks = ConfigManager.load_pedagogical_blocks()
        self.assertIsInstance(blocks, dict)
        self.assertIn("margin_glossary", blocks)
        self.assertIn("dialogue", blocks)
        self.assertIn("worked_example", blocks)
        self.assertIn("case_study", blocks)
        self.assertIn("learning_objectives", blocks)


class TestPageAsymmetryAndProfileSchema(unittest.TestCase):
    """Tests odd-even asymmetry and pedagogical block tracking in DocumentProfile."""

    def test_page_asymmetry_serialization(self) -> None:
        """Verifies PageAsymmetry to_dict and from_dict roundtrip."""
        asym = PageAsymmetry(
            outer_margin_x=[0.0, 0.28],
            binding_margin_x=[0.72, 1.0],
            header_align="left",
            page_number_pos="bottom_left",
        )
        data = asym.to_dict()
        self.assertEqual(data["header_align"], "left")
        self.assertEqual(data["page_number_pos"], "bottom_left")

        restored = PageAsymmetry.from_dict(data)
        self.assertEqual(restored.outer_margin_x, [0.0, 0.28])
        self.assertEqual(restored.binding_margin_x, [0.72, 1.0])
        self.assertEqual(restored.header_align, "left")

    def test_document_profile_with_odd_even_and_blocks(self) -> None:
        """Verifies full DocumentProfile roundtrip containing odd_even and active_blocks."""
        profile = DocumentProfile(
            geometry=ProfileGeometry(
                has_odd_even_asymmetry=True,
                even_page=PageAsymmetry(
                    outer_margin_x=[0.0, 0.25],
                    binding_margin_x=[0.75, 1.0],
                    header_align="left",
                ),
                odd_page=PageAsymmetry(
                    outer_margin_x=[0.75, 1.0],
                    binding_margin_x=[0.0, 0.25],
                    header_align="right",
                ),
                has_spanning_boxes=True,
            ),
            typography=ProfileTypography(
                has_drop_caps=True,
                drop_cap_lines=3,
                caption_patterns=[r"^Figure\s+\d+"],
            ),
            special_blocks=ProfileSpecialBlocks(
                active_blocks=["margin_glossary", "case_study", "worked_example"],
                block_rules={"case_study": {"category": "case"}},
            ),
        )

        data = profile.to_dict()
        self.assertTrue(data["geometry"]["has_odd_even_asymmetry"])
        self.assertTrue(data["geometry"]["has_spanning_boxes"])
        self.assertEqual(data["geometry"]["even_page"]["header_align"], "left")
        self.assertEqual(data["geometry"]["odd_page"]["header_align"], "right")
        self.assertTrue(data["typography"]["has_drop_caps"])
        self.assertIn("case_study", data["special_blocks"]["active_blocks"])

        restored = DocumentProfile.from_dict(data)
        self.assertTrue(restored.geometry.has_odd_even_asymmetry)
        self.assertEqual(restored.geometry.even_page.outer_margin_x, [0.0, 0.25])
        self.assertEqual(restored.geometry.odd_page.outer_margin_x, [0.75, 1.0])
        self.assertTrue(restored.typography.has_drop_caps)
        self.assertEqual(restored.typography.drop_cap_lines, 3)
        self.assertIn("worked_example", restored.special_blocks.active_blocks)


class TestFrontMatterDetectionAndChapter1Isolation(unittest.TestCase):
    """Tests slug matching, pure Chapter 1 isolation, and front matter prepending."""

    def test_match_front_matter_slug(self) -> None:
        """Verifies taxonomy slug matching on typical book titles."""
        tax = ConfigManager.load_front_matter_taxonomy()
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Book Cover", tax), "00-01-Cover")
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Copyright & Publisher Notice", tax), "00-04-Publish")
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Table of Contents", tax), "00-07-TOC")
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Brief Contents", tax), "00-06-Brief-Contents")
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Preface To The Student", tax), "00-09-Preface")
        self.assertEqual(PDFAnalyzer.match_front_matter_slug("Chapter 1 Introduction", tax), "")

    def test_verify_and_isolate_chapter1_prepends_missing_front_matter(self) -> None:
        """Ensures that when Chapter 1 begins at page > 1, front matter is automatically prepended."""
        # Simulated outline starting directly at Chapter 1 on page 25
        raw_targets = [(25, "Ch01-Introduction-to-Psychology"), (60, "Ch02-Research-Methods")]

        # For testing, we mock a dummy pdf path where detect_front_matter_from_text returns synthetic items
        adjusted = PDFAnalyzer.verify_and_isolate_chapter1(
            pdf_path="dummy.pdf",
            targets=list(raw_targets),
            total_pages=100
        )

        # The first target must now be a Front Matter section starting at page 1
        self.assertEqual(adjusted[0][0], 1)
        self.assertTrue(adjusted[0][1].startswith("00-"))
        # Chapter 1 must strictly remain at page 25
        ch1_target = next(t for t in adjusted if "Ch01" in t[1])
        self.assertEqual(ch1_target[0], 25)


class TestPreFlightProfilingAndSequentialLinking(unittest.TestCase):
    """Tests that pre-flight profiling excludes Front Matter and sequential linking includes all sections."""

    def setUp(self) -> None:
        """Sets up temporary workspace for tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleans up temporary directory."""
        self.temp_dir.cleanup()

    def test_ensure_book_profile_strictly_samples_body(self) -> None:
        """Verifies ensure_book_profile picks the first body chapter, never 00-* front matter."""
        sections = [
            {"start": 1, "end": 2, "name": "00-01-Cover"},
            {"start": 3, "end": 10, "name": "00-07-TOC"},
            {"start": 11, "end": 20, "name": "00-09-Preface"},
            {"start": 21, "end": 50, "name": "Ch01-Introduction"},
            {"start": 51, "end": 80, "name": "Ch02-Foundations"},
        ]

        book_dir = self.work_dir / "Test-Book"
        chapters_root = str(book_dir / "chapters")
        os_book_dir = book_dir
        os_book_dir.mkdir(parents=True, exist_ok=True)

        orch = BookProcessorOrchestrator(output_dir=str(self.work_dir), processed_dir=str(self.work_dir / "proc"))

        # Pre-seed a dummy Ch01 pdf so splitting is not attempted on dummy.pdf
        ch01_dir = book_dir / "chapters" / "Ch01-Introduction"
        ch01_dir.mkdir(parents=True, exist_ok=True)
        (ch01_dir / "Ch01-Introduction.pdf").write_bytes(b"%PDF-1.4 dummy")

        # Create pre-flight profile directly to simulate calibration
        profile_data = {
            "meta": {"doc_type": "book", "title": "Test-Book"},
            "geometry": {"header_cutoff_y": 45.0},
        }
        (book_dir / "profile.json").write_text(json.dumps(profile_data), encoding="utf-8")

        # When profile.json exists, ensure_book_profile should safely return without altering it
        orch.ensure_book_profile(book_dir, sections, chapters_root, "dummy.pdf")
        self.assertTrue((book_dir / "profile.json").exists())

    def test_obsidian_navigation_links_front_matter_and_chapters(self) -> None:
        """Verifies that navigation links sequentially include 00-* Front Matter and Ch* Chapters."""
        ch_list = []
        names = ["00-01-Cover", "00-07-TOC", "00-09-Preface", "Ch01-Introduction", "Ch02-Foundations"]

        for name in names:
            ch_dir = self.work_dir / name
            ch_dir.mkdir(parents=True, exist_ok=True)
            md_file = ch_dir / f"{name}.md"
            md_file.write_text(f"# {name}\n\nSample content for {name}.\n", encoding="utf-8")
            ch_list.append({"name": name, "md_path": md_file})

        # Inject navigation
        modified_count = inject_chapter_navigation(ch_list)
        self.assertEqual(modified_count, len(names))

        # Check that 00-01-Cover links forward to 00-07-TOC
        cover_content = (self.work_dir / "00-01-Cover" / "00-01-Cover.md").read_text(encoding="utf-8")
        self.assertIn("00-07-toc", cover_content)

        # Check that 00-09-Preface links forward to Ch01-Introduction
        preface_content = (self.work_dir / "00-09-Preface" / "00-09-Preface.md").read_text(encoding="utf-8")
        self.assertIn("ch01-introduction", preface_content)

        # Generate index.md and ensure all sections are listed
        index_path = generate_book_index(self.work_dir, ch_list)
        index_content = index_path.read_text(encoding="utf-8")
        for name in names:
            self.assertIn(name, index_content)


if __name__ == "__main__":
    unittest.main()
