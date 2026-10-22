"""
Unit Tests for ElementCropper
=============================
Tests bounding box padding, equal margin computation, and crop dimension math.
"""

import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from literature_parser.services.converter.element_cropper import ElementCropper
from literature_parser.services.converter.models import CroppedElement


class TestElementCropper(unittest.TestCase):
    """Test suite for ElementCropper calculations."""

    def test_compute_padded_bbox_interior(self):
        """Tests that interior bounding box expands symmetrically by margin_pt."""
        raw_bbox = (100.0, 150.0, 300.0, 400.0)
        margin = 16.0
        padded = ElementCropper.compute_padded_bbox(raw_bbox, page_width=612.0, page_height=792.0, margin_pt=margin)
        self.assertEqual(padded, (84.0, 134.0, 316.0, 416.0))

    def test_compute_padded_bbox_boundary_clamp(self):
        """Tests that bounding box clamping respects 0 and page dimensions."""
        raw_bbox = (5.0, 10.0, 605.0, 788.0)
        margin = 16.0
        padded = ElementCropper.compute_padded_bbox(raw_bbox, page_width=612.0, page_height=792.0, margin_pt=margin)
        self.assertEqual(padded, (0.0, 0.0, 612.0, 792.0))

    def test_cropped_element_serialization(self):
        """Tests CroppedElement to_dict conversion."""
        elem = CroppedElement(
            element_type="table",
            identifier="table_1_1",
            filename="table_1_1.png",
            filepath=Path("/tmp/images/table_1_1.png"),
            page_num=3,
            bbox=(50.0, 100.0, 250.0, 300.0),
            padded_bbox=(34.0, 84.0, 266.0, 316.0),
            caption="Table 1.1 Summary of Demographics",
            notes="Note. p < 0.05",
        )
        d = elem.to_dict()
        self.assertEqual(d["element_type"], "table")
        self.assertEqual(d["identifier"], "table_1_1")
        self.assertEqual(d["filename"], "table_1_1.png")
        self.assertEqual(d["page_num"], 3)
        self.assertEqual(d["caption"], "Table 1.1 Summary of Demographics")
        self.assertEqual(d["notes"], "Note. p < 0.05")
        self.assertEqual(d["bbox"], [50.0, 100.0, 250.0, 300.0])
        self.assertEqual(d["padded_bbox"], [34.0, 84.0, 266.0, 316.0])


if __name__ == "__main__":
    unittest.main()
