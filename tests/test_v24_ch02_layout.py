import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
import re
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.layout_detector import LayoutDetector
from literature_parser.services.style_loader import load_style

CH02_PDF = ROOT / 'output/Research Methods, Design, and Analysis 13th ed/chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.pdf'


@unittest.skipIf(not CH02_PDF.exists(), "Ch02 PDF not yet generated; run batch_convert or split first.")
class TestV24Ch02LayoutFixes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.style = load_style()

    def test_ch02_concept_map_multi_level(self):

        """Issue 1: Mindmap hierarchy must preserve multi-level structure (Root -> Quantitative -> Experimental...)."""
        xml1 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 1)
        root1 = ET.fromstring(xml1[xml1.find('<page'):xml1.rfind('</page>')+7])
        fonts1 = {f.attrib['id']: f.attrib for f in root1.findall('fontspec')}

        map_md, consumed = LayoutDetector.reconstruct_concept_map(root1, fonts1, 309.0, 815.0)
        self.assertTrue(map_md.startswith('```mermaid'), "Must output mermaid block")
        # Check all 4 levels exist
        self.assertIn('Research Approaches and Methods of Data Collection', map_md)
        self.assertIn('Quantitative', map_md)
        self.assertIn('Experimental', map_md)
        self.assertIn('Causation', map_md)
        self.assertIn('Characteristics', map_md)
        self.assertIn('Settings', map_md)
        self.assertIn('Manipulation', map_md)
        self.assertIn('Control', map_md)
        self.assertIn('Variables', map_md)
        self.assertIn('Independent Variable', map_md)
        self.assertIn('Data Collection', map_md)
        self.assertIn('Tests', map_md)
        self.assertIn('Questionnaires', map_md)

    def test_ch02_margin_glossaries_right_side(self):
        """Issue 2: Right-hand margin glossaries on Page 2 must be extracted, not merged into body."""
        xml2 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 2)
        root2 = ET.fromstring(xml2[xml2.find('<page'):xml2.rfind('</page>')+7])
        fonts2 = {f.attrib['id']: f.attrib for f in root2.findall('fontspec')}
        pw = float(root2.attrib.get('width', '918'))
        ph = float(root2.attrib.get('height', '1174'))

        # Detect margin side
        side = LayoutDetector.detect_page_margin_side(root2, pw, ph)
        self.assertEqual(side, 'right', "Page 2 (printed page 19) must have margin on right")

        glossaries, consumed = LayoutDetector.extract_margin_glossaries(root2, fonts2, pw, ph, 2)
        extracted_terms = [g['term'] for g in glossaries]
        self.assertIn('Experimental research', extracted_terms)
        self.assertIn('Manipulation', extracted_terms)
        self.assertIn('Nonexperimental research', extracted_terms)
        self.assertIn('Quantitative research', extracted_terms)
        self.assertIn('Numerical data', extracted_terms)
        self.assertNotIn('2.1', extracted_terms, "Section number 2.1 must not be a glossary term")

    def test_ch02_study_question_clean_boundary(self):
        """Issue 3 (Part A): Study Question 2.1 must not swallow subsequent sections or objectives."""
        md2 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 2, [])
        # Study question tip callout should contain only question text, not Section 2.1 or Variables
        self.assertIn('> [!TIP] **Study Question 2.1**', md2)
        sq_match = re.search(r'> \[!TIP\] \*\*Study Question 2.1\*\*\n(.*?)(?=\n\n|\Z)', md2, re.DOTALL)
        self.assertTrue(sq_match)
        sq_content = sq_match.group(1)
        self.assertNotIn('Variables in Quantitative Research', sq_content)
        self.assertNotIn('The basic building blocks of quantitative research', sq_content)

    def test_ch02_table_2_1_markdown_grid(self):
        """Issue 3 (Part B): Table 2.1 must be extracted as a GitHub Flavored Markdown table."""
        xml3 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 3)
        root3 = ET.fromstring(xml3[xml3.find('<page'):xml3.rfind('</page>')+7])
        fonts3 = {f.attrib['id']: f.attrib for f in root3.findall('fontspec')}
        pw = float(root3.attrib.get('width', '918'))
        ph = float(root3.attrib.get('height', '1174'))

        tables, consumed = LayoutDetector.extract_page_tables(root3, fonts3, pw, ph)
        self.assertEqual(len(tables), 1, "Must extract Table 2.1")
        tbl_md = tables[0]['markdown']
        self.assertTrue('<th>Variable Type</th>' in tbl_md or '| Variable Type |' in tbl_md)
        self.assertTrue('Categorical variable' in tbl_md)
        self.assertTrue('Quantitative variable' in tbl_md)
        self.assertTrue('Independent variable (IV)' in tbl_md)
        self.assertTrue('Dependent variable (DV)' in tbl_md)

    def test_ch02_no_accidental_blockquote_causation(self):
        """Issue 4: Body text under Causation on Page 5 must not be turned into blockquotes."""
        md5 = DigitalPDFParser.parse_page_to_markdown(str(CH02_PDF), 5, [])
        # 'Causation is one of those terms...' should be a standard paragraph, NOT blockquoted
        self.assertIn('Causation is one of those terms that people frequently use', md5)
        self.assertNotIn('> Causation is one of those terms', md5)
        self.assertNotIn('> When individuals discuss causation', md5)

    def test_ch02_uncaptioned_diagram_crop(self):
        """Issue 5: Uncaptioned diagram on Page 7 should be extracted as an image and not fragmented text."""
        xml7 = DigitalPDFParser.extract_page_xml(str(CH02_PDF), 7)
        root7 = ET.fromstring(xml7[xml7.find('<page'):xml7.rfind('</page>')+7])
        fonts7 = {f.attrib['id']: f.attrib for f in root7.findall('fontspec')}
        pw = float(root7.attrib.get('width', '918'))
        ph = float(root7.attrib.get('height', '1174'))

        images, consumed = LayoutDetector.extract_vector_figures(root7, fonts7, str(CH02_PDF), 7, pw, ph)
        self.assertTrue(any('diagram' in img['filename'] for img in images), "Must extract cropped diagram image")


if __name__ == '__main__':
    unittest.main()
