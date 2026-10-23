"""Unit tests for ZoneTagger and layout framing."""

import unittest
from xml.etree import ElementTree as ET
from literature_parser.services.converter.layout_frame import (
    PageZone,
    ZoneTagger,
)


class TestZoneTagger(unittest.TestCase):
    """Verifies that page elements are accurately categorized into layout zones."""

    def test_zone_tagger_partitions_page_correctly(self):
        """Verifies header, footer, margin, and main body partitioning."""
        pw, ph = 600.0, 800.0
        # Create sample XML elements
        hdr_el = ET.Element("text", attrib={"top": "20.0", "left": "50.0", "width": "200.0"})
        ftr_el = ET.Element("text", attrib={"top": "780.0", "left": "50.0", "width": "200.0"})
        body_el = ET.Element("text", attrib={"top": "150.0", "left": "80.0", "width": "300.0"})
        margin_odd_el = ET.Element("text", attrib={"top": "200.0", "left": "480.0", "width": "100.0"})

        elements = [hdr_el, ftr_el, body_el, margin_odd_el]
        geometry = {
            "margins": {"header_cutoff_y": 40.0, "footer_cutoff_y": 750.0},
            "has_margin_column": True,
        }

        # Odd page test (margin is on the right >= 72% pw = 432.0)
        zones = ZoneTagger.tag_elements(elements, pw, ph, page_num=1, geometry=geometry)

        self.assertIn(hdr_el, zones[PageZone.HEADER_FOOTER])
        self.assertIn(ftr_el, zones[PageZone.HEADER_FOOTER])
        self.assertIn(body_el, zones[PageZone.MAIN_BODY])
        self.assertIn(margin_odd_el, zones[PageZone.MARGIN])

    def test_zone_tagger_even_page_facing_margin(self):
        """Verifies even page facing margin is on the left side."""
        pw, ph = 600.0, 800.0
        margin_even_el = ET.Element("text", attrib={"top": "200.0", "left": "30.0", "width": "100.0"})
        body_el = ET.Element("text", attrib={"top": "200.0", "left": "200.0", "width": "350.0"})

        elements = [margin_even_el, body_el]
        geometry = {
            "margins": {"header_cutoff_y": 40.0, "footer_cutoff_y": 750.0},
            "has_margin_column": True,
        }

        # Even page test (margin is on the left <= 28% pw = 168.0)
        zones = ZoneTagger.tag_elements(elements, pw, ph, page_num=2, geometry=geometry)

        self.assertIn(margin_even_el, zones[PageZone.MARGIN])
        self.assertIn(body_el, zones[PageZone.MAIN_BODY])


if __name__ == "__main__":
    unittest.main()
