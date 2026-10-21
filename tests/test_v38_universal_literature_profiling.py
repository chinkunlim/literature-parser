import unittest
from pathlib import Path
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.services.fingerprinting.publisher_detector import PublisherDetector
from literature_parser.services.parsers.literature.imrad_resolver import IMRADResolver
from literature_parser.adapters.parsers.literature.metadata_extractor import LiteratureMetadataExtractor


class TestV38UniversalLiteratureProfiling(unittest.TestCase):
    def test_publisher_detector_expanded(self):
        # DOI prefixes
        self.assertEqual(PublisherDetector.detect_from_text("10.1063/5.0290984"), "aip")
        self.assertEqual(PublisherDetector.detect_from_text("10.1146/annurev-linguist-030514-124937"), "annual_reviews")
        self.assertEqual(PublisherDetector.detect_from_text("10.1017/S136672892000045X"), "cup")

        # Profiles
        self.assertEqual(PublisherDetector.get_profile_name("aip", is_literature=True), "literature_aip.json")
        self.assertEqual(PublisherDetector.get_profile_name("cup", is_literature=True), "literature_cup.json")
        self.assertEqual(PublisherDetector.get_profile_name("annual_reviews", is_literature=True), "literature_annual_reviews.json")

    def test_clean_nih_watermarks(self):
        text = (
            "NIH-PA Author Manuscript\n"
            "This is genuine academic content.\n"
            "HHS Public Access\n"
            "Author manuscript; available in PMC 2019 August 01.\n"
            "Next paragraph continues cleanly."
        )
        cleaned = IMRADResolver._clean_nih_watermarks(text)
        self.assertNotIn("NIH-PA Author Manuscript", cleaned)
        self.assertNotIn("HHS Public Access", cleaned)
        self.assertNotIn("available in PMC", cleaned)
        self.assertIn("This is genuine academic content.", cleaned)
        self.assertIn("Next paragraph continues cleanly.", cleaned)

    def test_relocate_auxiliary_sections(self):
        md = (
            "# Title\n\n"
            "## Introduction\n\nIntro text.\n\n"
            "## References\n\n- Ref 1\n- Ref 2\n\n"
            "## Conflict of Interest\n\nThe authors declare no conflict of interest.\n\n"
            "## Data Availability Statement\n\nData available on OSF.\n"
        )
        relocated = IMRADResolver._relocate_auxiliary_sections(md)
        # Conflict of Interest and Data Availability should appear BEFORE ## References
        pos_coi = relocated.find("## Conflict of Interest")
        pos_da = relocated.find("## Data Availability Statement")
        pos_ref = relocated.find("## References")
        self.assertTrue(pos_coi != -1)
        self.assertTrue(pos_da != -1)
        self.assertTrue(pos_ref != -1)
        self.assertTrue(pos_coi < pos_ref)
        self.assertTrue(pos_da < pos_ref)

    def test_nih_metadata_rule_extraction(self):
        sample = (
            "Published in final edited form as:\n"
            "Trends Cogn Sci. 2012 April ; 16(4): 240–250. doi:10.1016/j.tics.2012.03.001.\n"
            "# Reshaping the Mind: The Benefits of Bilingualism\n\n"
            "## Abstract\n\nAbstract text here."
        )
        meta = LiteratureMetadataExtractor.extract_with_rules(sample)
        self.assertIn("Trends Cogn Sci", meta["journal"])
        self.assertEqual(meta["doi"], "10.1016/j.tics.2012.03.001")


if __name__ == '__main__':
    unittest.main()
