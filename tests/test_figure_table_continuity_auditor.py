"""Unit tests for FigureTableContinuityAuditor (detecting sequence gaps and layout interruptions).
"""

from __future__ import annotations

import unittest
from literature_parser.services.verification.figure_table_continuity_auditor import FigureTableContinuityAuditor


class TestFigureTableContinuityAuditor(unittest.TestCase):
    """Verifies sequence continuity check for Figures/Tables and prose boundary adherence."""

    def test_continuous_sequence_passes(self):
        """Verifies that an unbroken sequence of figures and tables produces no errors."""
        md = """# Chapter 2

As illustrated in Figure 2.1 below:

![Figure 2.1 Career Tree](images/fig2_1.png)

Furthermore, data in Table 2.1 and Table 2.2 show correlations.

| Column 1 | Column 2 |
| --- | --- |
| Val A | Val B |

Next, Figure 2.2 shows outcomes.

![Figure 2.2 Outcomes](images/fig2_2.png)
"""
        issues = FigureTableContinuityAuditor.audit(md, chapter_num=2)
        gap_issues = [i for i in issues if "GAP" in i.category]
        self.assertEqual(len(gap_issues), 0)

    def test_detect_figure_sequence_gap(self):
        """Verifies that skipping a figure (e.g. 2.1 -> 2.3) raises FIGURE_SEQUENCE_GAP."""
        md = """# Chapter 2

Here is Figure 2.1:

![Figure 2.1 First](images/fig2_1.png)

Then we jump directly to Figure 2.3:

![Figure 2.3 Third](images/fig2_3.png)
"""
        issues = FigureTableContinuityAuditor.audit(md, chapter_num=2)
        gap_issues = [i for i in issues if i.category == "FIGURE_SEQUENCE_GAP"]
        self.assertEqual(len(gap_issues), 1)
        self.assertEqual(gap_issues[0].severity, "ERROR")
        self.assertIn("Figure 2.2", gap_issues[0].message)

    def test_detect_table_sequence_gap(self):
        """Verifies that skipping a table (e.g. Table 1.1 -> Table 1.3) raises TABLE_SEQUENCE_GAP."""
        md = """# Chapter 1

Table 1.1 summary:

| A | B |
|---|---|
| 1 | 2 |

Later in Table 1.3:

| C | D |
|---|---|
| 3 | 4 |
"""
        issues = FigureTableContinuityAuditor.audit(md, chapter_num=1)
        gap_issues = [i for i in issues if i.category == "TABLE_SEQUENCE_GAP"]
        self.assertEqual(len(gap_issues), 1)
        self.assertEqual(gap_issues[0].severity, "ERROR")
        self.assertIn("Table 1.2", gap_issues[0].message)


if __name__ == "__main__":
    unittest.main()
