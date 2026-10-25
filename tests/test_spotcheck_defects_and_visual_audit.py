"""
Unit and Regression Tests for Spot-Checked Defects & Visual Audit (TASK-047 / ISSUE-016)
=======================================================================================
Verifies fixes for the 6 concrete defects discovered during user spot-checks:
1. Mermaid `-->` arrows and Markdown `| --- |` table dividers must never be turned into `—>` or `| — |` by `clean_typography_artifacts`.
2. `DocumentProfile` and `load_style` must preserve textbook EOC patterns (`Key Terms and Concepts`, `Related Internet Sites`, `Practice Test`, `Challenge Exercises`).
3. `FigureFormatter.reposition_figures_and_tables` must support hyphenated table numbers (`Table 1-1`, `Table 1-2`, `Table 16-1 (Continued)`) without overwriting `Table 1-1` or slicing `**Table 1-2**`.
4. `VectorFigureParser.extract_vector_figures` must not crop bogus uncaptioned `diagram_p*.png` images from ordinary colon-terminated prose lines.
5. `TableParser.extract_page_tables` must preserve the first column (`Realistic`) when the table title is centered (`h_left - col1_left > 115pt`) and group multi-line cell text cleanly.
6. `LayoutAutoHealer` and `rules.py` must heal and verify Mermaid syntax, broken table dividers, split multi-line headings, and table callout completeness.
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.adapters.verification.rules import (
    check_mermaid_syntax_integrity,
    check_table_callout_completeness,
)
from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.parsers.layout.vector_figure_parser import VectorFigureParser
from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter
from literature_parser.services.style_loader import load_style
from literature_parser.services.utils.text_utils import clean_typography_artifacts


class TestSpotcheckDefectsAndVisualAudit(unittest.TestCase):
    """Tests for the 6 spot-checked defects in TASK-047 (Refs: ISSUE-016)."""

    def test_clean_typography_preserves_mermaid_arrows_and_table_dividers(self) -> None:
        """Verifies clean_typography_artifacts does not corrupt Mermaid --> or Markdown | --- |."""
        sample = (
            "Here is prose with a double--dash and triple---dash.\n\n"
            "```mermaid\n"
            "graph LR\n"
            '    Root["Introduction to Scientific Research"]\n'
            '    N5["Characteristics"] --> N13["Empirical"]\n'
            "```\n\n"
            "| Term | Term | Term |\n"
            "| --- | --- | --- |\n"
            "| Authority *p. 3* | Falsificationism *p. 6* | Science *p. 4* |\n"
        )
        cleaned = clean_typography_artifacts(sample)
        self.assertIn("double—dash", cleaned)
        self.assertIn('N5["Characteristics"] --> N13["Empirical"]', cleaned)
        self.assertNotIn("—>", cleaned)
        self.assertIn("| --- | --- | --- |", cleaned)
        self.assertNotIn("| — |", cleaned)

    def test_document_profile_preserves_textbook_eoc_patterns(self) -> None:
        """Verifies DocumentProfile and load_style retain Key Terms and Related Internet Sites."""
        prof = DocumentProfile.from_dict({"title": "Research Methods"})
        prof_dict = prof.to_dict()
        with tempfile.TemporaryDirectory() as tmp:
            p_file = Path(tmp) / "profile.json"
            import json
            p_file.write_text(json.dumps(prof_dict), encoding="utf-8")
            style = load_style(tmp)
            pats = " ".join(style.get("eoc_heading_patterns", []))
            self.assertIn("Key Terms and Concepts", pats)
            self.assertIn("Related Internet Sites", pats)
            self.assertIn("Practice Test", pats)
            self.assertIn("Challenge Exercises", pats)

    def test_figure_formatter_preserves_hyphenated_tables_without_collision(self) -> None:
        """Verifies Table 1-1 and Table 1-2 both survive reposition_figures_and_tables intact."""
        md = (
            "An outline of these phases appears in Table 1-1.\n\n"
            "**Table 1-1** *The Structure of Career Counseling*\n\n"
            '<table class="textbook-table"><thead><tr><th>Phases</th><th>Alliance</th></tr></thead>'
            "<tbody><tr><td>Opening</td><td>Forming</td></tr></tbody></table>\n\n"
            "Later we discuss competencies in Table 1-2.\n\n"
            "**Table 1-2** *Career Counseling Self-Efficacy Scale*\n\n"
            '<table class="textbook-table"><thead><tr><th>0</th><th>1</th></tr></thead>'
            "<tbody><tr><td>Low</td><td>High</td></tr></tbody></table>"
        )
        res = FigureFormatter.reposition_figures_and_tables(md)
        self.assertIn("**Table 1-1** *The Structure of Career Counseling*", res)
        self.assertIn("**Table 1-2** *Career Counseling Self-Efficacy Scale*", res)
        self.assertIn("<th>Phases</th>", res)
        self.assertIn("<th>0</th>", res)
        self.assertNotRegex(res, r"(?m)^\*\*\s*$")
        self.assertNotRegex(res, r"(?m)^Table 1-[12]\*\*")

    def test_vector_figure_parser_does_not_crop_uncaptioned_colon_lines(self) -> None:
        """Verifies VectorFigureParser does not generate bogus diagram_p* images from colon lines."""
        xml_str = """
        <page number="1" width="612" height="792">
            <fontspec id="1" size="10" family="Palatino" color="#000000"/>
            <text top="200" left="72" width="300" height="12" font="1">Consider the following four options:</text>
            <text top="220" left="200" width="20" height="12" font="1">RA</text>
            <text top="240" left="200" width="20" height="12" font="1">X1</text>
            <text top="260" left="200" width="20" height="12" font="1">O1</text>
            <text top="280" left="200" width="20" height="12" font="1">O2</text>
        </page>
        """
        page_elem = ET.fromstring(xml_str.strip())
        fonts = {"1": {"size": 10.0, "family": "palatino", "is_bold": False}}
        imgs, consumed = VectorFigureParser.extract_vector_figures(
            page_elem, fonts, pdf_path="", page_num=1, pw=612.0, ph=792.0
        )
        self.assertEqual(len(imgs), 0)
        self.assertEqual(len(consumed), 0)

    def test_table_parser_includes_leftmost_column_under_centered_title(self) -> None:
        """Verifies Table 2-1 with centered header at x=180 still captures col 1 at x=60."""
        xml_str = """
        <page number="10" width="504" height="702">
            <fontspec id="1" size="10" family="Helvetica-Bold" color="#000000"/>
            <fontspec id="2" size="8.5" family="Palatino" color="#000000"/>
            <text top="60" left="180" width="160" height="11" font="1">Table 2-1 Personality Types</text>
            <text top="85" left="60" width="50" height="10" font="1">Realistic</text>
            <text top="85" left="140" width="65" height="10" font="1">Investigative</text>
            <text top="85" left="230" width="50" height="10" font="1">Artistic</text>
            <text top="105" left="60" width="55" height="9" font="2">Conforming</text>
            <text top="105" left="140" width="55" height="9" font="2">Intellectual</text>
            <text top="105" left="230" width="55" height="9" font="2">Imaginative</text>
            <text top="115" left="60" height="9" width="50" font="2">Practical</text>
            <text top="115" left="140" height="9" width="50" font="2">Curious</text>
            <text top="115" left="230" height="9" width="50" font="2">Intuitive</text>
        </page>
        """
        page_elem = ET.fromstring(xml_str.strip())
        fonts = {
            "1": {"size": 10.0, "family": "helvetica-bold", "is_bold": True},
            "2": {"size": 8.5, "family": "palatino", "is_bold": False},
        }
        tables, _ = TableParser.extract_page_tables(page_elem, fonts, pw=504.0, ph=702.0)
        self.assertEqual(len(tables), 1)
        md = tables[0]["markdown"]
        self.assertIn("<th>Realistic</th>", md)
        self.assertIn("Conforming", md)
        self.assertIn("Practical", md)

    def test_healer_and_verifier_detect_and_repair_mermaid_and_split_headings(self) -> None:
        """Verifies LayoutAutoHealer fixes —> in mermaid, | — | in tables, and split headings."""
        corrupted = (
            "## CAREER\n\n"
            "## COUNSELING\n\n"
            "#### 3 Identifying Research Questions and\n\n"
            "Forming Hypotheses\n\n"
            "```mermaid\n"
            "graph LR\n"
            '    N5["Characteristics"] —> N13["Empirical"]\n'
            "```\n\n"
            "| Term | Term |\n"
            "| — | — |\n"
            "| A | B |\n"
        )
        m_check_before = check_mermaid_syntax_integrity(corrupted)
        self.assertFalse(m_check_before["passed"])

        healed, _ = LayoutAutoHealer.audit_and_heal_chapter(corrupted, "", "")
        self.assertIn('N5["Characteristics"] --> N13["Empirical"]', healed)
        self.assertIn("| --- | --- |", healed)
        self.assertIn("## CAREER COUNSELING", healed)
        self.assertIn("#### 3 Identifying Research Questions and Forming Hypotheses", healed)

        m_check_after = check_mermaid_syntax_integrity(healed)
        self.assertTrue(m_check_after["passed"])

    def test_check_table_callout_completeness(self) -> None:
        """Verifies check_table_callout_completeness catches missing referenced tables."""
        missing_md = "As shown in Table 1-1 and Table 1-2, we see two phases.\n\n**Table 1-2** *Scale*\n\n<table><tr><td>1</td></tr></table>"
        res_missing = check_table_callout_completeness(missing_md)
        self.assertFalse(res_missing["passed"])
        self.assertIn("1-1", str(res_missing["missing_tables"]))

        complete_md = (
            "As shown in Table 1-1 and Table 1-2, we see two phases.\n\n"
            "**Table 1-1** *Structure*\n\n<table><tr><td>A</td></tr></table>\n\n"
            "**Table 1-2** *Scale*\n\n<table><tr><td>1</td></tr></table>"
        )
        res_ok = check_table_callout_completeness(complete_md)
        self.assertTrue(res_ok["passed"])


if __name__ == "__main__":
    unittest.main()
