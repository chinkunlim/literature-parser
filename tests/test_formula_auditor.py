"""Unit tests for FormulaAuditor.

Tests mathematical formula delimiter balance, MathML compatibility, APA statistical
notation standardization, and currency dollar-sign escape safety.
"""

import unittest

from literature_parser.services.verification.formula_auditor import FormulaAuditor


class TestFormulaAuditor(unittest.TestCase):
    """Test suite for FormulaAuditor."""

    def test_unescaped_currency_escaped(self):
        """Verifies unescaped currency amounts ($100, $25.50) are safely escaped to avoid LaTeX math mode."""
        md = "The fee was $100 and the book cost $25.50 in 2024."
        issues, cleaned, repaired = FormulaAuditor.audit(md, auto_fix=True)
        self.assertEqual(repaired, 2)
        self.assertIn(r"\$100", cleaned)
        self.assertIn(r"\$25.50", cleaned)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].category, "FORMULA_CURRENCY_UNESCAPED")

    def test_unbalanced_block_equation(self):
        """Verifies odd count of '$$' delimiters triggers an ERROR issue."""
        md = "$$\nE = mc^2\n"
        issues, _, _ = FormulaAuditor.audit(md, auto_fix=False)
        error_issues = [i for i in issues if i.category == "FORMULA_BLOCK_DELIMITER_UNBALANCED"]
        self.assertEqual(len(error_issues), 1)
        self.assertEqual(error_issues[0].severity, "ERROR")

    def test_unbalanced_inline_equation(self):
        """Verifies odd count of unescaped single '$' triggers an ERROR issue."""
        md = "This formula $x + y = z has no closing delimiter."
        issues, _, _ = FormulaAuditor.audit(md, auto_fix=False)
        error_issues = [i for i in issues if i.category == "FORMULA_INLINE_DELIMITER_UNBALANCED"]
        self.assertEqual(len(error_issues), 1)
        self.assertEqual(error_issues[0].severity, "ERROR")

    def test_apa_statistics_standardization(self):
        """Verifies plain statistical tests (t, F, p, R2) are standardized with italics."""
        md = "Results indicated t(24) = 2.15, p < .05, F(1, 48) = 4.20, and R2 = .35."
        issues, cleaned, repaired = FormulaAuditor.audit(md, auto_fix=True)
        self.assertIn("*t*(24) = 2.15", cleaned)
        self.assertIn("*p* < .05", cleaned)
        self.assertIn("*F*(1, 48) = 4.20", cleaned)
        self.assertIn("*R*² = .35", cleaned)
        self.assertGreater(repaired, 0)


if __name__ == "__main__":
    unittest.main()
