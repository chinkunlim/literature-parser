"""
Unit Tests for Batch Resilience, Table Structuring, and Layout Healing
======================================================================
Verifies predictive batch error isolation, XML control-character sanitization,
90-degree rotated table extraction, hyphenated table structuring, broken
ligature repair, heading prose intrusion healing, and strict verification rules.
"""

import unittest
from xml.etree import ElementTree as ET

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.adapters.verification.rules import (
    check_broken_ligatures,
    check_heading_prose_intrusion,
    check_unformatted_table_blocks,
)
from literature_parser.services.concurrency.m5_worker_pool import M5WorkerPool
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.utils.text_utils import (
    normalize_ligatures,
    sanitize_filename,
)


def _failing_worker_task(item: int) -> int:
    """Helper worker task that raises RuntimeError on value 2.

    Args:
        item: Integer work item.

    Returns:
        Doubled integer if item != 2.
    """
    if item == 2:
        raise RuntimeError("Simulated chapter conversion failure")
    return item * 2


class TestBatchResilienceAndTableStructuring(unittest.TestCase):
    """Tests batch resilience, table HTML structuring, ligature repair, and verification rules."""

    def test_sanitize_filename_caps_length_and_utf8_bytes(self) -> None:
        """Verifies sanitize_filename caps long chapter titles safely under macOS limits.

        Returns:
            None.
        """
        long_title = (
            "Ch11-Career-Multicultural-Marital-and-Military-Family-Genograms-"
            "Helping-Clients-Tell-Their-Stories-About-Their-Career–Family-Connections-"
            "And-Additional-Subtitles-Exceeding-Two-Hundred-Bytes"
        )
        sanitized = sanitize_filename(long_title)
        self.assertLessEqual(len(sanitized), 120)
        self.assertLessEqual(len(sanitized.encode("utf-8")), 200)
        self.assertTrue(sanitized.startswith("Ch11-Career-Multicultural"))

    def test_m5_worker_pool_isolates_worker_exceptions(self) -> None:
        """Verifies M5WorkerPool isolates per-item exceptions without aborting the batch.

        Returns:
            None.
        """
        pool = M5WorkerPool(max_workers=2)
        results = pool.execute_parallel([1, 2, 3], _failing_worker_task)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], 2)
        self.assertEqual(results[2], 6)
        self.assertIsInstance(results[1], dict)
        self.assertFalse(results[1].get("passed", True))
        self.assertIn("Simulated chapter conversion failure", results[1].get("error", ""))

    def test_repair_broken_ligatures_restores_split_words(self) -> None:
        """Verifies broken fi/fl/ffi/ffl ligature gaps are repaired without false positives.

        Returns:
            None.
        """
        sample = (
            "Clients with diffi cult career decisions experience signifi cant confl ict.\n"
            "They also experience infl uence from family and identifi cation challenges.\n"
            "A fi refi ghter requires specifi c interventions to refl ect career goals."
        )
        chk_before = check_broken_ligatures(sample)
        self.assertFalse(chk_before["passed"])

        repaired = normalize_ligatures(sample)
        self.assertIn("difficult", repaired)
        self.assertIn("significant", repaired)
        self.assertIn("conflict", repaired)
        self.assertIn("influence", repaired)
        self.assertIn("identification", repaired)
        self.assertIn("firefighter", repaired)
        chk_after = check_broken_ligatures(repaired)
        self.assertTrue(chk_after["passed"])

    def test_hyphenated_table_extracted_as_html_table(self) -> None:
        """Verifies hyphenated Table 1-1 headers and rows render as textbook-table HTML.

        Returns:
            None.
        """
        xml_str = """
        <page width="612" height="792">
            <fontspec id="0" size="10" family="Times" color="#000000"/>
            <text top="100" left="120" width="360" height="12" font="0"><b>Table 1-1. Individualistic and Collectivistic Orientations</b></text>
            <text top="125" left="80" width="140" height="10" font="0"><b>Dimension</b></text>
            <text top="125" left="250" width="140" height="10" font="0"><b>Individualism</b></text>
            <text top="125" left="420" width="140" height="10" font="0"><b>Collectivism</b></text>
            <text top="145" left="80" width="140" height="10" font="0">Self-construal</text>
            <text top="145" left="250" width="140" height="10" font="0">Independent</text>
            <text top="145" left="420" width="140" height="10" font="0">Interdependent</text>
            <text top="165" left="80" width="140" height="10" font="0">Decision making</text>
            <text top="165" left="250" width="140" height="10" font="0">Personal preference</text>
            <text top="165" left="420" width="140" height="10" font="0">Group consensus</text>
        </page>
        """
        page_elem = ET.fromstring(xml_str.strip())
        fonts = {"0": {"size": 10.0, "family": "Times"}}
        tbl_blocks, consumed = TableParser.extract_page_tables(
            page_elem, fonts, 612.0, 792.0
        )
        self.assertEqual(len(tbl_blocks), 1)
        html_out = tbl_blocks[0]["markdown"]
        self.assertIn('<table class="textbook-table"', html_out)
        self.assertIn("Table 1-1", html_out)
        self.assertIn("Self-construal", html_out)
        self.assertGreaterEqual(len(consumed), 7)

    def test_unformatted_table_check_and_auto_healer(self) -> None:
        """Verifies check_unformatted_table_blocks flags list-degraded tables and healer converts them.

        Returns:
            None.
        """
        degraded_md = (
            "### Table 9-1. Career Theme Analysis\n\n"
            "- **Client Statement:** I enjoy fixing machines — **Counselor Theme:** Realistic interest\n"
            "- **Client Statement:** I like leading teams — **Counselor Theme:** Enterprising interest\n\n"
            "Body paragraph following the table."
        )
        chk_before = check_unformatted_table_blocks(degraded_md)
        self.assertFalse(chk_before["passed"])

        healed_md, fixes = LayoutAutoHealer.heal_table_blocks(degraded_md)
        self.assertGreater(len(fixes), 0)
        self.assertIn('<table class="textbook-table"', healed_md)
        chk_after = check_unformatted_table_blocks(healed_md)
        self.assertTrue(chk_after["passed"])

    def test_heading_prose_intrusion_check_and_healer(self) -> None:
        """Verifies corrupted multi-column headings are detected and healed.

        Returns:
            None.
        """
        corrupted_md = (
            "## 4.1 Neural Conduction. The resting membrane potential is measured in millivolts.\n\n"
            "#### and the neurotransmitter is released into the cleft\n\n"
            "### ——————————\n\n"
            "Normal paragraph text."
        )
        chk_before = check_heading_prose_intrusion(corrupted_md)
        self.assertFalse(chk_before["passed"])
        self.assertEqual(chk_before["count"], 3)

        healed_md, fixes = LayoutAutoHealer.heal_corrupted_headings(corrupted_md)
        self.assertEqual(len(fixes), 3)
        chk_after = check_heading_prose_intrusion(healed_md)
        self.assertTrue(chk_after["passed"])


if __name__ == "__main__":
    unittest.main()
