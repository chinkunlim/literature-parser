"""
Unit Tests for Profile Schema, Inheritance & Closed-Loop Healing
================================================================
Validates:
- DocumentProfile strongly-typed domain schema and sub-dataclasses
- Serialization and deserialization roundtrip
- Backward compatibility parsing of legacy book_profile and document_profile dicts
- ConfigManager profile loading precedence (profile.json > document_profile.json > book_profile.json)
- ConfigManager mirror persistence for backward compatibility
- Closed-loop geometry healing (LEAKED_HEADER, LEAKED_FOOTER, GUTTER_OVERFLOW)
"""

import json
import tempfile
import unittest
from pathlib import Path

from literature_parser.domain.profiler.profile_schema import (
    DocumentProfile,
    ProfileGeometry,
    ProfileMetadata,
    ProfileSpecialBlocks,
    ProfileTypography,
)
from literature_parser.services.config_manager import ConfigManager
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator


class TestDocumentProfileSchema(unittest.TestCase):
    """Tests the DocumentProfile domain dataclass and validation rules."""

    def test_default_initialization_and_validation(self) -> None:
        """Verifies default values and schema validation behavior."""
        profile = DocumentProfile()
        self.assertEqual(profile.meta.doc_type, "book")
        self.assertEqual(profile.meta.mode, "digital")
        self.assertEqual(profile.geometry.header_cutoff_y, 45.0)
        self.assertEqual(profile.geometry.footer_cutoff_y, 740.0)

        # Default profile should produce no validation warnings
        warnings = profile.validate()
        self.assertEqual(len(warnings), 0)

        # Invalid geometry: header >= footer
        profile.geometry.header_cutoff_y = 800.0
        warnings = profile.validate()
        self.assertTrue(any("Header cutoff must be strictly less" in w for w in warnings))

        # Invalid two-column layout without split_x
        profile.geometry.header_cutoff_y = 45.0
        profile.geometry.layout = "two_column"
        profile.geometry.gutter_split_x = None
        warnings = profile.validate()
        self.assertTrue(any("gutter_split_x" in w for w in warnings))

    def test_serialization_and_deserialization(self) -> None:
        """Verifies to_dict and from_dict roundtrip fidelity."""
        profile = DocumentProfile(
            meta=ProfileMetadata(
                doc_type="literature",
                mode="digital",
                title="Cognitive Psychology Study",
                publisher="apa",
            ),
            geometry=ProfileGeometry(
                page_width=595.0,
                page_height=842.0,
                header_cutoff_y=50.0,
                footer_cutoff_y=790.0,
                layout="two_column",
                gutter_split_x=297.5,
            ),
            typography=ProfileTypography(
                h1_min_size=20.0,
                h2_min_size=16.0,
                h3_min_size=13.0,
                body_font_size=10.5,
                symbol_mappings={"beta": "\\beta"},
            ),
            special_blocks=ProfileSpecialBlocks(
                has_concept_map=False,
                has_margin_glossary=True,
                lo_pattern=r"^Learning Objective\b",
            ),
            publisher_rules={"clean_banner": True},
        )

        data = profile.to_dict()
        self.assertIn("meta", data)
        self.assertIn("geometry", data)
        self.assertIn("typography", data)
        self.assertIn("special_blocks", data)
        self.assertEqual(data["publisher"], "apa")
        self.assertTrue(data["is_journal"])

        restored = DocumentProfile.from_dict(data)
        self.assertEqual(restored.meta.doc_type, "literature")
        self.assertEqual(restored.meta.title, "Cognitive Psychology Study")
        self.assertEqual(restored.geometry.page_width, 595.0)
        self.assertEqual(restored.geometry.gutter_split_x, 297.5)
        self.assertEqual(restored.typography.h1_min_size, 20.0)
        self.assertEqual(restored.typography.symbol_mappings.get("beta"), "\\beta")
        self.assertTrue(restored.special_blocks.has_margin_glossary)
        self.assertEqual(restored.publisher_rules.get("clean_banner"), True)

    def test_backward_compatible_from_dict(self) -> None:
        """Verifies parsing of legacy flat book_profile and document_profile formats."""
        legacy_data = {
            "book_name": "Legacy Book",
            "is_scanned": True,
            "margins": {
                "header_cutoff_y": 55.0,
                "footer_cutoff_y": 720.0,
                "even_page_margin_bound": 0.28,
            },
            "gutters": {
                "split_x": 305.0,
            },
            "typography": {
                "h1_min_size": 22.0,
            },
            "has_concept_map": True,
        }

        profile = DocumentProfile.from_dict(legacy_data)
        self.assertEqual(profile.meta.title, "Legacy Book")
        self.assertEqual(profile.meta.mode, "scanned")
        self.assertEqual(profile.geometry.header_cutoff_y, 55.0)
        self.assertEqual(profile.geometry.footer_cutoff_y, 720.0)
        self.assertEqual(profile.geometry.gutter_split_x, 305.0)
        self.assertEqual(profile.geometry.even_margin_bound, 0.28)
        self.assertEqual(profile.typography.h1_min_size, 22.0)
        self.assertTrue(profile.special_blocks.has_concept_map)

    def test_apply_feedback_closed_loop(self) -> None:
        """Verifies closed-loop geometry adjustments for running headers and footers."""
        profile = DocumentProfile(
            geometry=ProfileGeometry(
                header_cutoff_y=45.0,
                footer_cutoff_y=740.0,
                gutter_split_x=300.0,
            )
        )

        # Test LEAKED_HEADER default (+5.0)
        adjusted = profile.apply_feedback("LEAKED_HEADER")
        self.assertTrue(adjusted)
        self.assertEqual(profile.geometry.header_cutoff_y, 50.0)

        # Test LEAKED_FOOTER custom delta (-10.0)
        adjusted = profile.apply_feedback("LEAKED_FOOTER", {"delta": 10.0})
        self.assertTrue(adjusted)
        self.assertEqual(profile.geometry.footer_cutoff_y, 730.0)

        # Test GUTTER_OVERFLOW split_x adjustment
        adjusted = profile.apply_feedback("GUTTER_OVERFLOW", {"split_x": 306.5})
        self.assertTrue(adjusted)
        self.assertEqual(profile.geometry.gutter_split_x, 306.5)


class TestConfigManagerProfileOperations(unittest.TestCase):
    """Tests ConfigManager hierarchical loading and saving with unified profile.json."""

    def setUp(self) -> None:
        """Sets up temporary directory for profile storage tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleans up temporary directory after testing."""
        self.temp_dir.cleanup()

    def test_load_instance_profile_precedence(self) -> None:
        """Verifies priority resolution: profile.json > document_profile.json > book_profile.json."""
        cm = ConfigManager()

        # 1. Fallback to book_profile.json when profile.json is absent
        book_file = self.work_dir / "book_profile.json"
        book_file.write_text(json.dumps({"meta": {"title": "Book From Legacy"}}), encoding="utf-8")
        loaded = cm.load_instance_profile(self.work_dir)
        self.assertEqual(loaded.get("meta", {}).get("title"), "Book From Legacy")

        # 2. Fallback to document_profile.json
        doc_file = self.work_dir / "document_profile.json"
        doc_file.write_text(json.dumps({"meta": {"title": "Doc From Legacy"}}), encoding="utf-8")
        loaded = cm.load_instance_profile(self.work_dir)
        self.assertEqual(loaded.get("meta", {}).get("title"), "Doc From Legacy")

        # 3. Canonical profile.json takes absolute priority
        canonical_file = self.work_dir / "profile.json"
        canonical_file.write_text(json.dumps({"meta": {"title": "Canonical Profile"}}), encoding="utf-8")
        loaded = cm.load_instance_profile(self.work_dir)
        self.assertEqual(loaded.get("meta", {}).get("title"), "Canonical Profile")

    def test_save_instance_profile_mirroring(self) -> None:
        """Verifies that saving instance profile writes canonical profile.json and legacy mirror."""
        cm = ConfigManager()
        data = {
            "meta": {"doc_type": "book", "title": "Mirror Test Book"},
            "geometry": {"header_cutoff_y": 48.0},
        }

        # Saving as book should create profile.json and book_profile.json
        saved_path = cm.save_instance_profile(self.work_dir, data, mirror_legacy=True)
        self.assertEqual(saved_path, self.work_dir / "profile.json")
        self.assertTrue((self.work_dir / "profile.json").exists())
        self.assertTrue((self.work_dir / "book_profile.json").exists())

        # Verify content matches
        with open(self.work_dir / "profile.json", "r", encoding="utf-8") as f:
            profile_content = json.load(f)
        self.assertEqual(profile_content["meta"]["title"], "Mirror Test Book")


class TestCoordinateCalibratorProfileOperations(unittest.TestCase):
    """Tests CoordinateCalibrator closed-loop profile adjustment."""

    def setUp(self) -> None:
        """Sets up temporary workspace for calibration tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleans up temporary directory after testing."""
        self.temp_dir.cleanup()

    def test_adjust_geometry_from_feedback_persists(self) -> None:
        """Verifies adjust_geometry_from_feedback updates both canonical and mirror files."""
        profile_data = {
            "meta": {"doc_type": "book", "title": "Feedback Book"},
            "geometry": {"header_cutoff_y": 45.0, "footer_cutoff_y": 740.0},
        }
        (self.work_dir / "profile.json").write_text(json.dumps(profile_data), encoding="utf-8")

        calibrator = CoordinateCalibrator()
        result = calibrator.adjust_geometry_from_feedback(
            book_dir=self.work_dir,
            anomaly_type="LEAKED_HEADER",
            details={"delta": 7.5},
        )
        self.assertTrue(result)

        # Check updated profile.json
        with open(self.work_dir / "profile.json", "r", encoding="utf-8") as f:
            updated = json.load(f)
        self.assertEqual(updated["geometry"]["header_cutoff_y"], 52.5)

        # Check legacy mirror file also updated
        self.assertTrue((self.work_dir / "book_profile.json").exists())
        with open(self.work_dir / "book_profile.json", "r", encoding="utf-8") as f:
            legacy = json.load(f)
        self.assertEqual(legacy["geometry"]["header_cutoff_y"], 52.5)


if __name__ == "__main__":
    unittest.main()
