"""
Unit tests for v2.3 Layout Reconstruction Features
- 2D Concept Map / Mindmap reconstruction (Mermaid + Outline)
- Two-column Learning Objectives extraction
- Odd and Even page Margin Glossary Callout extraction
- Indented paragraph detection
- Table 1.1 bullet list table formatting
- Section & Subsection heading recognition
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from book_processor.parsers.layout_detector import LayoutDetector
from book_processor.parsers.digital_pdf import DigitalPDFParser


class TestV23LayoutFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ch01_pdf = "output/Research Methods, Design, and Analysis 13th ed/chapters/Ch01 Introduction to Scientific Research/Ch01 Introduction to Scientific Research.pdf"
        cls.pdf_exists = Path(cls.ch01_pdf).exists()
        from book_processor.style_loader import load_style
        cls.orig_style = load_style()
        test_style = dict(cls.orig_style)
        test_style["gloss_placement"] = "inline"
        DigitalPDFParser.set_active_style(test_style)

    @classmethod
    def tearDownClass(cls):
        DigitalPDFParser.set_active_style(cls.orig_style)

    def test_extract_learning_objectives(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")
            
        xml_p1 = DigitalPDFParser.extract_page_xml(self.ch01_pdf, 1)
        root_p1 = ET.fromstring(xml_p1[xml_p1.find('<page'):xml_p1.rfind('</page>')+7])
        fonts_p1 = {f.attrib['id']: f.attrib for f in root_p1.findall('fontspec')}

        lo_md, consumed = LayoutDetector.extract_learning_objectives(root_p1, fonts_p1)
        self.assertIn("### Learning Objectives", lo_md)
        self.assertIn("**1.1**", lo_md)
        self.assertIn("**1.7**", lo_md)
        self.assertNotIn("- **1.1**", lo_md)
        self.assertGreater(len(consumed), 10)
        # Verify chronological ordering of objectives
        self.assertTrue(lo_md.find("**1.1**") < lo_md.find("**1.4**") < lo_md.find("**1.7**"))

    def test_reconstruct_concept_map(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")
            
        xml_p1 = DigitalPDFParser.extract_page_xml(self.ch01_pdf, 1)
        root_p1 = ET.fromstring(xml_p1[xml_p1.find('<page'):xml_p1.rfind('</page>')+7])
        fonts_p1 = {f.attrib['id']: f.attrib for f in root_p1.findall('fontspec')}

        map_md, consumed = LayoutDetector.reconstruct_concept_map(root_p1, fonts_p1, 338, 848)
        self.assertIn("```mermaid", map_md)
        self.assertIn("graph LR", map_md)
        self.assertIn("Introduction to Scientific Research", map_md)
        self.assertIn("Traditional Methods of Acquiring Knowledge", map_md)
        self.assertIn("Science", map_md)
        self.assertIn("Pseudoscience", map_md)
        self.assertGreater(len(consumed), 20)

    def test_extract_margin_glossaries_odd_page(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")
            
        xml_p3 = DigitalPDFParser.extract_page_xml(self.ch01_pdf, 3)
        root_p3 = ET.fromstring(xml_p3[xml_p3.find('<page'):xml_p3.rfind('</page>')+7])
        fonts_p3 = {f.attrib['id']: f.attrib for f in root_p3.findall('fontspec')}

        glossaries, consumed = LayoutDetector.extract_margin_glossaries(root_p3, fonts_p3, 918, 1174, 3)
        terms = [g['term'] for g in glossaries]
        self.assertIn("Authority", terms)
        self.assertIn("Rationalism", terms)
        self.assertIn("Empiricism", terms)
        for g in glossaries:
            self.assertIn("**" + g['term'] + "**", g['callout'])
            self.assertNotIn("Key Term:", g['callout'])
        self.assertGreater(len(consumed), 5)

    def test_extract_margin_glossaries_even_page(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")
            
        xml_p4 = DigitalPDFParser.extract_page_xml(self.ch01_pdf, 4)
        root_p4 = ET.fromstring(xml_p4[xml_p4.find('<page'):xml_p4.rfind('</page>')+7])
        fonts_p4 = {f.attrib['id']: f.attrib for f in root_p4.findall('fontspec')}

        glossaries, consumed = LayoutDetector.extract_margin_glossaries(root_p4, fonts_p4, 918, 1174, 4)
        terms = [g['term'] for g in glossaries]
        self.assertIn("Science", terms)
        self.assertIn("Induction", terms)
        self.assertGreater(len(consumed), 4)

    def test_table_bullet_formatting(self):
        sample_table_block = (
            "**Table 1.1** *Reasons for Taking a Research Methods Course*\n"
            "- Learn how to conduct psychological research.\n"
            "- Provides a foundation for topic-specific courses.\n"
            "- Can be a more informed consumer."
        )
        formatted = LayoutDetector.detect_and_format_tables([sample_table_block])
        self.assertEqual(len(formatted), 1)
        # Bold-label style should be preserved as-is (already formatted correctly)
        self.assertIn("**Table 1.1**", formatted[0])
        self.assertIn("- Learn how to conduct psychological research.", formatted[0])


    def test_end_to_end_pages_1_to_3(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        # Page 1
        p1 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 1, [])
        self.assertIn("```mermaid", p1)
        self.assertIn("### Learning Objectives", p1)
        self.assertNotIn("Regularity Induction Authority", p1)  # No horizontal salad

        # Page 2
        p2 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 2, [])
        self.assertIn("In our daily lives", p2)
        self.assertIn("In an attempt to gain information", p2)
        self.assertIn("The course in which you are now enrolled", p2)
        self.assertIn("- Learn how to conduct psychological research.", p2)
        self.assertIn("## Traditional Methods of Acquiring Knowledge", p2)
        self.assertTrue("🎯 **1.1**" in p2, "Should detect LO 1.1")
        self.assertIn("accumulating this knowledge over time.", p2)  # No footer cut


        # Page 3
        p3 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 3, [])
        self.assertIn("### Authority", p3)
        self.assertIn("### Rationalism", p3)
        self.assertIn("### Empiricism", p3)
        self.assertIn("**Authority**", p3)
        self.assertIn("**Rationalism**", p3)
        self.assertIn("**Empiricism**", p3)
        self.assertNotIn("Key Term:", p3)

    def test_page_4_study_question_and_footnote(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p4 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 4, [])
        self.assertIn("> [!TIP] **Study Question 1.1**", p4)
        self.assertIn("Explain each of the approaches to acquiring knowledge", p4)
        self.assertIn("## The Scientific Approach to Knowledge Generation", p4)
        self.assertIn("### Induction and Deduction", p4)
        self.assertIn("[^1]", p4)
        self.assertIn("[^1]: In the philosophy of logic", p4)
        self.assertIn("**Science**", p4)
        self.assertNotIn("Key Term:", p4)

    def test_page_9_multiline_term_unhyphenation(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p9 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 9, [])
        self.assertIn("**Operationalizing a construct**", p9)
        self.assertIn("Identifying an instrument (or set of instruments)", p9)
        self.assertNotIn("Operationalizing a con-", p9)
        self.assertNotIn("**struct **", p9)
        self.assertIn("**Randomized controlled trial (RCTs)**", p9)
        self.assertNotIn("Key Term:", p9)

    def test_page_10_vector_figure_and_clean_text(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p10 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 10, [])
        self.assertIn("![Figure 1.1 Example of an operationalization of a good car salesperson.](images/figure_1_1.png)", p10)
        self.assertIn("*Figure 1.1 Example of an operationalization of a good car salesperson.*", p10)
        self.assertNotIn("8GTDCNUVCVGOGPV", p10)
        self.assertNotIn("5JGKUCIQQF", p10)
        self.assertNotIn("UGNNUOCP[ECTU", p10)
        self.assertIn("### Replication", p10)
        self.assertIn("**Replication**", p10)
        self.assertIn("**Meta-analysis**", p10)
        self.assertNotIn("Key Term:", p10)


    def test_page_1_concept_map_mermaid_only(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p1 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 1, [])
        self.assertIn("```mermaid", p1)
        self.assertIn("graph LR", p1)
        # Verify no redundant pure text outline
        self.assertNotIn("- **Introduction to Scientific Research**", p1)
        self.assertNotIn("- **Traditional Methods of Acquiring Knowledge**", p1)

    def test_page_8_characteristics_heading(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p8 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 8, [])
        self.assertIn("## Characteristics of Scientific Research", p8)
        self.assertNotIn("Characteristics of Scientific Research" in p8 and "## Characteristics" not in p8, [True])

    def test_page_11_blockquotes(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p11 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 11, [])
        self.assertIn("> The interpretation of research data culminates in conditional probabilistic", p11)
        self.assertIn("> Science is a process for producing knowledge. The process depends on making", p11)

    def test_page_12_figure_1_2_and_table_1_2(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p12 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 12, [])
        # Figure 1.2 verification
        self.assertIn("![Figure 1.2 Illustration of the relationship between theory and research.](images/figure_1_2.png)", p12)
        self.assertNotIn("1DUGTXCVKQPU", p12)
        self.assertNotIn("8GTDCN", p12)

        # Table 1.2 verification
        self.assertIn("**Table 1.2**", p12)
        self.assertIn("1. Does the theory/explanation fit the empirical data?", p12)
        self.assertIn("8. Can practitioners use the theory to produce desired outcomes in the world?", p12)
        # Should not be converted to fake footnotes
        self.assertNotIn("[^8]:", p12)
        self.assertNotIn("[^2]:", p12)


    def test_page_16_and_17_end_of_chapter_sections(self):
        if not self.pdf_exists:
            self.skipTest("Chapter 1 PDF not found")

        p16 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 16, [])
        self.assertIn("### Key Terms and Concepts", p16)
        self.assertIn('<a id="key-terms-and-concepts"></a>', p16)
        self.assertIn("[Authority *p. 3*](#term-authority)", p16)
        self.assertIn("[Falsificationism *p. 6*](#term-falsificationism)", p16)
        self.assertIn("### Related Internet Sites", p16)
        # Dynamic extraction: URLs appear as <url> Markdown format
        self.assertIn("http://www.pbs.org/wgbh/aso/databank/humbeh.html", p16)

        # URL should not be a margin glossary
        self.assertNotIn("Key Term: http://", p16)
        self.assertIn("### Practice Test", p16)
        # Dynamic extraction reads actual PDF; question numbers are bold
        self.assertIn("Empiricism is a vital element in scientific studies", p16)

        p17 = DigitalPDFParser.parse_page_to_markdown(self.ch01_pdf, 17, [])
        self.assertIn("### Challenge Exercises", p17)
        # Dynamic extraction reads actual PDF content (long lines may be split)
        self.assertIn("Psychology makes use of many concepts", p17)
        self.assertIn("medical community", p17)
        self.assertIn("science of psychology", p17)




if __name__ == '__main__':
    unittest.main()

