"""
Unit tests for PublisherDetector and DocumentClassifier
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from literature_parser.services.fingerprinting.publisher_detector import PublisherDetector
from literature_parser.services.fingerprinting.document_classifier import DocumentClassifier


class TestFingerprinting(unittest.TestCase):

    def test_detect_apa_from_doi(self):
        text = "Journal of Experimental Psychology. DOI: 10.1037//1076-898X.8.2.75"
        pub = PublisherDetector.detect_from_text(text)
        self.assertEqual(pub, "apa")
        profile = PublisherDetector.get_profile_name(pub, is_journal=True)
        self.assertEqual(profile, "literature_apa.json")

    def test_detect_elsevier_from_doi_and_text(self):
        text = "Cognition 102 (2007) 1–25. doi:10.1016/j.cognition.2005.12.008. Elsevier B.V."
        pub = PublisherDetector.detect_from_text(text)
        self.assertEqual(pub, "elsevier")
        profile = PublisherDetector.get_profile_name(pub, is_journal=True)
        self.assertEqual(profile, "literature_elsevier.json")

    def test_detect_wiley(self):
        text = "British Journal of Psychology. doi: 10.1111/bjop.12345. John Wiley & Sons Ltd."
        pub = PublisherDetector.detect_from_text(text)
        self.assertEqual(pub, "wiley")

    def test_detect_pearson_textbook(self):
        text = "Research Methods, Design, and Analysis. Copyright 2019 Pearson Education, Inc."
        pub = PublisherDetector.detect_from_text(text)
        self.assertEqual(pub, "pearson")
        profile = PublisherDetector.get_profile_name(pub, is_journal=False)
        self.assertEqual(profile, "publisher_pearson.json")

    def test_classify_journal_article(self):
        sample = "Abstract: This study investigated the BART task. DOI: 10.1037/001."
        res = DocumentClassifier.classify(total_pages=10, sample_text=sample)
        self.assertTrue(res["is_journal"])
        self.assertEqual(res["doc_type"], "journal_article")

    def test_classify_textbook(self):
        sample = "Table of Contents. Chapter 1: Introduction. Chapter 2: Methods."
        toc = [("Chapter 1", 1), ("Chapter 2", 20), ("Chapter 3", 40), ("Chapter 4", 65)]
        res = DocumentClassifier.classify(total_pages=350, sample_text=sample, toc_entries=toc)
        self.assertFalse(res["is_journal"])
        self.assertEqual(res["doc_type"], "textbook")


if __name__ == "__main__":
    unittest.main()
