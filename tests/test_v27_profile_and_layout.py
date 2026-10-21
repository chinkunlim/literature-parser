"""
Test Suite v27: Profile Architecture & Layout Fixes
===================================================
Tests for:
1. Appendix skips concept map reconstruction (no false mindmap).
2. Learning objectives format without blockquote gray boxes (- 🎯 **{num}**).
3. Table 2.1 category rows use HTML colspan and table footnote is isolated.
4. Table 2.2 criteria format as 2-column table.
5. Vector arrows ($\rightarrow$) inserted for spatial flow gaps.
6. Table caption in prose (Table 2.1 because...) is not falsely recognized as heading.
7. Study questions do not contain nested double-blockquotes (> >).
"""

import os
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.layout_detector import LayoutDetector

BOOK_DIR = Path(__file__).parent.parent / "./data/output/books/Research Methods, Design, and Analysis 13th ed"
CH01_PDF = BOOK_DIR / "chapters/Ch01 Introduction to Scientific Research/Ch01 Introduction to Scientific Research.pdf"
CH02_PDF = BOOK_DIR / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.pdf"
APP_PDF = BOOK_DIR / "chapters/Appendix/Appendix.pdf"


class TestV27ProfileAndLayout(unittest.TestCase):

    def test_appendix_skips_concept_map(self):
        """Verify Appendix page 1 does not reconstruct concept map mindmap."""
        if not APP_PDF.exists():
            self.skipTest("Appendix PDF not found")
        md_app = DigitalPDFParser.parse_page_to_markdown(str(APP_PDF), 1, [])
        self.assertNotIn("```mermaid", md_app)
        self.assertNotIn("mindmap", md_app)

    def test_learning_objective_list_format(self):
        """Verify learning objectives format as bullet list, not blockquotes."""
        if not CH01_PDF.exists():
            self.skipTest("Ch01 PDF not found")
        xml_p1 = DigitalPDFParser.extract_page_xml(str(CH01_PDF), 1)
        root = ET.fromstring(xml_p1[xml_p1.find('<page'):xml_p1.rfind('</page>') + 7])
        fonts = {}
        for fs in root.findall('fontspec'):
            fonts[fs.attrib['id']] = {'family': fs.attrib['family'].lower(), 'size': float(fs.attrib.get('size', 12))}
        lo_md, _ = LayoutDetector.extract_learning_objectives(root, fonts)
        self.assertIn("🎯 **1.1**", lo_md)
        self.assertNotIn("- 🎯", lo_md)
        self.assertNotIn("> 🎯", lo_md)

    def test_table_2_1_category_colspan_and_footnote(self):
        """Verify Table 2.1 contains colspan category rows and footnote is isolated."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        xml_p3 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 3)
        root = ET.fromstring(xml_p3[xml_p3.find('<page'):xml_p3.rfind('</page>') + 7])
        tbls, consumed = LayoutDetector.extract_page_tables(root, {}, 800, 1100)
        self.assertEqual(len(tbls), 1)
        t_md = tbls[0]['markdown']
        self.assertIn('<td colspan="3"><strong>Level of Measurement</strong></td>', t_md)
        self.assertIn('<td colspan="3"><strong>Role Taken by the Variable</strong></td>', t_md)
        self.assertIn("<em>* A four-level measurement system is provided in Chapter 5.</em>", t_md)

    def test_table_2_2_criterion_table(self):
        """Verify Table 2.2 extracts as a 2-column Criterion table."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        xml_p6 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 6)
        root = ET.fromstring(xml_p6[xml_p6.find('<page'):xml_p6.rfind('</page>') + 7])
        tbls, consumed = LayoutDetector.extract_page_tables(root, {}, 800, 1100)
        self.assertEqual(len(tbls), 1)
        t_md = tbls[0]['markdown']
        self.assertIn("| Criterion | Description |", t_md)
        self.assertIn("| **Criterion 1:** |", t_md)
        self.assertIn("| **Criterion 2:** |", t_md)
        self.assertIn("| **Criterion 3:** |", t_md)

    def test_vector_arrow_insertion(self):
        """Verify LaTeX vector arrow ($\rightarrow$) is inserted in causal diagrams."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        md_p4 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 4, [])
        self.assertIn(r"smoking $\rightarrow$ tissue damage $\rightarrow$ lung cancer.", md_p4)

    def test_no_false_table_heading_in_prose(self):
        """Verify 'Table 2.1 because the language...' is kept in prose and not treated as table heading."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        md_p4 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 4, [])
        self.assertNotIn("**Table 2.1** *because", md_p4)
        self.assertNotIn("### Table 2.1 because", md_p4)
        self.assertIn("because the language of variables", md_p4)

    def test_study_questions_no_nested_blockquotes(self):
        """Verify Study Questions do not contain nested gray callout blocks (> >)."""
        if not CH02_PDF.exists():
            self.skipTest("Ch02 PDF not found")
        md_p4 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 4, [])
        self.assertNotIn("> >", md_p4)
        md_p6 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 6, [])
        self.assertNotIn("> >", md_p6)


if __name__ == '__main__':
    unittest.main()
