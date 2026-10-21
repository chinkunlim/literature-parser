import sys
import re
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from literature_parser.services.parsers.layout_detector import LayoutDetector
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser

CH04_PDF = ROOT / "./data/output/books/Research Methods, Design, and Analysis 13th ed/chapters/Ch04 Ethics/Ch04 Ethics.pdf"


class TestV26ExhibitsAndColumns(unittest.TestCase):

    def setUp(self):
        if not CH04_PDF.exists():
            self.skipTest("Chapter 4 PDF not found")

    def test_exhibit_4_3_two_column_uncurling(self):
        """Verify Exhibit 4.3 on Page 8 is extracted with columns uncurled, not interleaved."""
        xml_p8 = DigitalPDFParser.extract_page_xml(str(CH04_PDF), 8)
        root_p8 = ET.fromstring(xml_p8[xml_p8.find('<page'):xml_p8.rfind('</page>') + 7])
        fonts_p8 = {}
        for fs in root_p8.findall('fontspec'):
            fonts_p8[fs.attrib['id']] = {'family': fs.attrib['family'].lower(), 'size': float(fs.attrib.get('size', 12))}
        pw = float(root_p8.attrib.get('width', '918'))
        ph = float(root_p8.attrib.get('height', '1174'))

        exhibits, consumed = LayoutDetector.extract_exhibits(root_p8, fonts_p8, pw, ph, 8)
        self.assertEqual(len(exhibits), 1, "Should detect 1 exhibit on page 8")
        ex_md = exhibits[0]['markdown']
        self.assertIn("### EXHIBIT 4.3 The Tuskegee Syphilis Experiment", ex_md)
        self.assertIn("In July 1972, the Associated Press released a story that", ex_md)
        self.assertIn("to and from the clinic, hot meals, free treatment for other", ex_md)
        idx_c1 = ex_md.find("In July 1972")
        idx_c2 = ex_md.find("to and from the clinic")
        self.assertLess(idx_c1, idx_c2, "Column 1 text must appear before Column 2 text")
        self.assertNotIn("story that to and from", ex_md, "Must not interweave columns horizontally")

    def test_table_4_1_multiline_title(self):
        """Verify Table 4.1 consumes its wrapped title line 'Presented to the IRB'."""
        xml_p4 = DigitalPDFParser.extract_page_xml(str(CH04_PDF), 4)
        root_p4 = ET.fromstring(xml_p4[xml_p4.find('<page'):xml_p4.rfind('</page>') + 7])
        fonts_p4 = {}
        for fs in root_p4.findall('fontspec'):
            fonts_p4[fs.attrib['id']] = {'family': fs.attrib['family'].lower(), 'size': float(fs.attrib.get('size', 12))}
        pw = float(root_p4.attrib.get('width', '918'))
        ph = float(root_p4.attrib.get('height', '1174'))

        tables, consumed = LayoutDetector.extract_page_tables(root_p4, fonts_p4, pw, ph)
        self.assertEqual(len(tables), 1, "Should detect Table 4.1 on page 4")
        tbl_md = tables[0]['markdown']
        self.assertIn("Presented to the IRB", tbl_md, "Table 4.1 title must include wrapped line 'Presented to the IRB'")
        consumed_texts = [re.sub(r'[\s\u00a0]+', ' ', ''.join(c.itertext()).strip()) for c in consumed]
        self.assertTrue(any("Presented to the IRB" in t for t in consumed_texts), "Title element must be in consumed set")

    def test_no_false_diagram_crop_on_p8_and_p26(self):
        """Verify uncaptioned diagram detection does not falsely crop colons on page 8 or page 26."""
        xml_p8 = DigitalPDFParser.extract_page_xml(str(CH04_PDF), 8)
        root_p8 = ET.fromstring(xml_p8[xml_p8.find('<page'):xml_p8.rfind('</page>') + 7])
        fonts_p8 = {}
        for fs in root_p8.findall('fontspec'):
            fonts_p8[fs.attrib['id']] = {'family': fs.attrib['family'].lower(), 'size': float(fs.attrib.get('size', 12))}
        pw = float(root_p8.attrib.get('width', '918'))
        ph = float(root_p8.attrib.get('height', '1174'))

        images, consumed = LayoutDetector.extract_vector_figures(root_p8, fonts_p8, str(CH04_PDF), 8, pw, ph)
        self.assertEqual(len(images), 0, "Page 8 has no figures or diagrams, must extract 0 images")

    def test_eoc_two_column_uncurling_p26(self):
        """Verify Practice Test and Challenge Exercises on Page 26 are read column-by-column."""
        xml_p26 = DigitalPDFParser.extract_page_xml(str(CH04_PDF), 26)
        root_p26 = ET.fromstring(xml_p26[xml_p26.find('<page'):xml_p26.rfind('</page>') + 7])
        fonts_p26 = {}
        for fs in root_p26.findall('fontspec'):
            fonts_p26[fs.attrib['id']] = {'family': fs.attrib['family'].lower(), 'size': float(fs.attrib.get('size', 12))}
        pw = float(root_p26.attrib.get('width', '918'))
        ph = float(root_p26.attrib.get('height', '1174'))

        sections, consumed = LayoutDetector.extract_end_of_chapter_sections(root_p26, fonts_p26, pw, ph, 26)
        self.assertGreaterEqual(len(sections), 1, "Should detect EOC sections on page 26")
        all_eoc_md = "\n\n".join(s['markdown'] for s in sections)
        idx_q1 = all_eoc_md.find("Dr. Doom")
        idx_q4 = all_eoc_md.find("13-year-olds")
        self.assertNotEqual(idx_q1, -1)
        self.assertNotEqual(idx_q4, -1)
        self.assertLess(idx_q1, idx_q4, "Column 1 Question 1 must appear before Column 2 Question 4")

    def test_margin_glossary_does_not_swallow_exhibit_p3(self):
        """Verify Research misconduct glossary definition ends properly and does not swallow Exhibit 4.1."""
        from literature_parser.services.style_loader import load_style
        orig = load_style()
        try:
            test_style = dict(orig)
            test_style["gloss_placement"] = "inline"
            DigitalPDFParser.set_style(test_style)
            md_p3 = DigitalPDFParser.parse_page_to_markdown(str(CH04_PDF), 3, [])
            self.assertIn("**Research misconduct**", md_p3)
            self.assertIn("EXHIBIT 4.1", md_p3)
            # Verify glossary callout itself does not contain Exhibit text
            for line in md_p3.splitlines():
                if line.startswith("> 📖") and "Research misconduct" in line:
                    self.assertNotIn("Two Cases of Reportedly Fraudulent Research", line)
                    self.assertNotIn("Cyril Burt", line)
        finally:
            DigitalPDFParser.set_style(orig)

    def test_bleed_removal_p5(self):
        """Verify Page 5 does not interleave out-of-bounds text from Page 6 (left=1013)."""
        md_p5 = DigitalPDFParser.parse_page_to_markdown(str(CH04_PDF), 5, [])
        # 'from the research study outweighs the cost' is from Page 6 bleed, must not appear on Page 5
        self.assertNotIn("from the research study outweighs the cost to the research participant", md_p5)
        self.assertIn("Treatment of Research Participants", md_p5)


if __name__ == '__main__':
    unittest.main()
