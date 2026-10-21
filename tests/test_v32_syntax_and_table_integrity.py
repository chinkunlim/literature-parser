"""
Unit Tests for Syntax, Symbol, and Table Column Integrity Rules (v32)
====================================================================
Tests automated detection of:
- Unescaped currency and multi-dollar sequences ($3, $$$)
- KaTeX math delimiter parity and curly brace balance
- Table column count matching between header and body rows
- Phantom empty table columns
- Raw angle brackets and fake # heading numbers
"""

import unittest
from doc_processor.verification.rules import (
    check_latex_and_symbol_integrity,
    check_table_column_integrity,
    check_unescaped_special_chars,
)


class TestSyntaxAndTableIntegrity(unittest.TestCase):

    def test_latex_integrity_valid(self):
        text = (
            "The model yielded $F(1, 84) = 8.4$, $p < .01$. "
            "Gift card was \\$5 and participants saw button ‘Collect \\$\\$\\$.’ "
            "Formula $1/128$ and display $$\\displaystyle X = \\dfrac{A}{B}$$ are valid."
        )
        res = check_latex_and_symbol_integrity(text)
        self.assertTrue(res['passed'], f"Expected pass, got issues: {res['issues']}")

    def test_latex_integrity_detects_unescaped_currency(self):
        text = "The participant was awarded $3 for completing the task."
        res = check_latex_and_symbol_integrity(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("stray or unescaped dollar" in iss for iss in res['issues']))

    def test_latex_integrity_detects_unescaped_triple_dollars(self):
        text = "Click the button labeled ‘Collect $$$’ to withdraw."
        res = check_latex_and_symbol_integrity(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("multi-dollar sequence" in iss for iss in res['issues']))

    def test_latex_integrity_detects_unescaped_percent_in_math(self):
        text = "Accounted for $39.1%$ of the total variance."
        res = check_latex_and_symbol_integrity(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("Unescaped percent sign % inside LaTeX math" in iss for iss in res['issues']))

    def test_latex_integrity_detects_mismatched_braces(self):
        text = "Formula $$\\dfrac{X}{Y$$ is missing a brace."
        res = check_latex_and_symbol_integrity(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("Mismatched curly braces" in iss for iss in res['issues']))

    def test_table_column_integrity_valid(self):
        table = """
        <table>
          <thead>
            <tr>
              <th rowspan="2">Measure</th>
              <th colspan="2">Total</th>
            </tr>
            <tr>
              <th>M</th><th>SD</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="3">Section</td></tr>
            <tr><td>Blue</td><td>12.5</td><td>3.2</td></tr>
          </tbody>
        </table>
        """
        res = check_table_column_integrity(table)
        self.assertTrue(res['passed'], f"Expected pass, got issues: {res['issues']}")

    def test_table_column_integrity_detects_mismatch(self):
        table = """
        <table>
          <thead>
            <tr><th>Col1</th><th>Col2</th><th>Col3</th></tr>
          </thead>
          <tbody>
            <tr><td>A</td><td>B</td><td>C</td><td>D</td></tr>
          </tbody>
        </table>
        """
        res = check_table_column_integrity(table)
        self.assertFalse(res['passed'])
        self.assertTrue(any("column count mismatch" in iss for iss in res['issues']))

    def test_table_column_integrity_detects_phantom_header(self):
        table = """
        <table>
          <thead>
            <tr><th>Measure</th><th colspan="2">Total</th><th></th><th></th></tr>
          </thead>
          <tbody>
            <tr><td>A</td><td>B</td><td>C</td><td>D</td><td>E</td></tr>
          </tbody>
        </table>
        """
        res = check_table_column_integrity(table)
        self.assertFalse(res['passed'])
        self.assertTrue(any("phantom empty header columns" in iss for iss in res['issues']))

    def test_unescaped_special_chars_detects_raw_angle_brackets(self):
        text = "The effect was significant with p < .05 on the measure."
        res = check_unescaped_special_chars(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("raw statistical angle bracket" in iss for iss in res['issues']))

    def test_unescaped_special_chars_detects_item_number_header(self):
        text = "Here is the list:\n# 15. Drug usage in sample\nNext paragraph."
        res = check_unescaped_special_chars(text)
        self.assertFalse(res['passed'])
        self.assertTrue(any("starting with '#' as item numbers" in iss for iss in res['issues']))


if __name__ == "__main__":
    unittest.main()
