"""
Unit tests for layout submodules
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.parsers.layout.callout_parser import CalloutParser
from literature_parser.services.parsers.layout.list_parser import ListParser
from literature_parser.services.parsers.layout.margin_parser import MarginParser
from literature_parser.adapters.parsers.layout.table_llm_fixer import TableLLMFixer


class TestLayoutSubmodules(unittest.TestCase):

    def test_table_parser_detect_and_format(self):
        paragraphs = [
            "Col1   Col2   Col3\nVal1   Val2   Val3\nVal4   Val5   Val6"
        ]
        res = TableParser.detect_and_format_tables(paragraphs)
        self.assertEqual(len(res), 1)
        self.assertIn("| Col1 | Col2 | Col3 |", res[0])
        self.assertIn("| --- | --- | --- |", res[0])

    def test_callout_parser_alert(self):
        paras = ["Note: This is an important rule."]
        res = CalloutParser.format_callout_boxes(paras)
        self.assertEqual(len(res), 1)
        self.assertIn("> [!NOTE]", res[0])

    def test_callout_parser_caption(self):
        paras = ["Figure 1.2: Diagram of the neural network."]
        res = CalloutParser.format_figure_captions(paras)
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0].startswith("*Figure 1.2:"))

    def test_list_parser_normalize(self):
        text = "• Item one\n▪ Item two\n1.First item"
        res = ListParser.detect_and_format_lists(text)
        self.assertIn("- Item one", res)
        self.assertIn("- Item two", res)
        self.assertIn("1. First item", res)

    def test_table_llm_fixer_can_fix(self):
        table_text = "A   B   C   D   E\n1   2   3   4   5\n" * 5
        self.assertTrue(TableLLMFixer.can_fix(table_text, column_count=5))
        self.assertFalse(TableLLMFixer.can_fix("short", column_count=2))


if __name__ == "__main__":
    unittest.main()
