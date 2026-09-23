import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from book_processor.fingerprinting.document_classifier import DocumentClassifier
from book_processor.parsers.math.apa_stats_normalizer import APAStatsNormalizer
from book_processor.parsers.layout.table_parser import TableParser


class TestJournalConversion(unittest.TestCase):
    def test_journal_classification_by_name_and_content(self):
        # 1. Filename cues
        self.assertTrue(DocumentClassifier.is_journal_article("inbox/2008-17521-013.pdf"))
        self.assertTrue(DocumentClassifier.is_journal_article("Journal of Adolescence - 2003 - Lejuez.pdf"))
        self.assertTrue(DocumentClassifier.is_journal_article("processed/2002-01194-001.pdf"))

        # 2. Textbooks must not be classified as journals
        self.assertFalse(DocumentClassifier.is_journal_article("Research-Methods-in-Psychology-1641401901.pdf"))
        self.assertFalse(DocumentClassifier.is_journal_article("Group Counseling Strategies.pdf"))

    def test_special_symbols_normalization(self):
        raw = "r ⫽ ⫹.77, p ⬍ .001, rank correlation ␳ ⫽ ⫹.71, average r ¼ 0.82, p ⱕ .005"
        res = APAStatsNormalizer.normalize_text(raw)
        self.assertIn("$r = +.77, p < .001$", res)
        self.assertIn("$\\rho = +.71$", res)
        self.assertIn("$r = 0.82$", res)
        self.assertNotIn("⫽", res)
        self.assertNotIn("⫹", res)
        self.assertNotIn("⬍", res)
        self.assertNotIn("␳", res)

    def test_t_test_with_tuple_df(self):
        raw = "mean did not change over time, t(1, 38) = 0.85, ns"
        res = APAStatsNormalizer.normalize_text(raw)
        self.assertIn("$t(1, 38) = 0.85$", res)


if __name__ == '__main__':
    unittest.main()
