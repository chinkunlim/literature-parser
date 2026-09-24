import unittest
from book_processor.pipelines.literature_pipeline import LiteraturePipeline


class TestLiteraturePipeline(unittest.TestCase):

    def test_detect_subtype(self):
        # 1. IEEE via publisher
        self.assertEqual(
            LiteraturePipeline.detect_subtype("Sample text", publisher="ieee"),
            LiteraturePipeline.SUBTYPE_IEEE,
        )

        # 2. IEEE via content
        self.assertEqual(
            LiteraturePipeline.detect_subtype("Published in IEEE Transactions on Neural Networks and Learning Systems"),
            LiteraturePipeline.SUBTYPE_IEEE,
        )

        # 3. Preprint via arXiv
        self.assertEqual(
            LiteraturePipeline.detect_subtype("arXiv:2301.00123v1 [cs.CV] 1 Jan 2023"),
            LiteraturePipeline.SUBTYPE_PREPRINT,
        )

        # 4. Preprint via submitted to
        self.assertEqual(
            LiteraturePipeline.detect_subtype("Preprint. Under review at Nature Machine Intelligence"),
            LiteraturePipeline.SUBTYPE_PREPRINT,
        )

        # 5. Dissertation
        dissertation_text = "# Chapter 1 Introduction\n\nBackground information...\n\n# Chapter 2 Literature Review"
        self.assertEqual(
            LiteraturePipeline.detect_subtype(dissertation_text, total_pages=120),
            LiteraturePipeline.SUBTYPE_DISSERTATION,
        )

        # 6. Default journal
        self.assertEqual(
            LiteraturePipeline.detect_subtype("Journal of Clinical Psychology, Vol 40", total_pages=15),
            LiteraturePipeline.SUBTYPE_JOURNAL,
        )

    def test_clean_ieee_boilerplate(self):
        dirty_md = (
            "# Introduction\n\nMain content here.\n\n"
            "Authorized licensed use limited to: MIT Libraries. Restrictions apply.\n\n"
            "## References\n\n[1] A. Smith, 2020.\n\n"
            "## Author Biography\n\n"
            "John Doe received the B.S. degree in 2010. He is currently an IEEE Fellow.\n\n"
            "Jane Doe is a researcher at Stanford University."
        )
        cleaned = LiteraturePipeline.clean_ieee_boilerplate(dirty_md)
        self.assertNotIn("Author Biography", cleaned)
        self.assertNotIn("John Doe received", cleaned)
        self.assertNotIn("Authorized licensed use limited to", cleaned)
        self.assertIn("## References", cleaned)
        self.assertIn("Main content here.", cleaned)

    def test_format_index_terms(self):
        sample_md = (
            "# Abstract\n\nThis is the abstract.\n\n"
            "Index Terms—Deep learning, natural language processing, transformer models.\n\n"
            "# Introduction\n\nIntroduction paragraph."
        )
        formatted = LiteraturePipeline.format_index_terms(sample_md)
        self.assertIn("> [!NOTE] **🏷️ 關鍵領域詞 (Index Terms)**", formatted)
        self.assertIn("`Deep learning`", formatted)
        self.assertIn("`natural language processing`", formatted)
        self.assertIn("`transformer models`", formatted)
        self.assertIn("# Introduction", formatted)


if __name__ == "__main__":
    unittest.main()
