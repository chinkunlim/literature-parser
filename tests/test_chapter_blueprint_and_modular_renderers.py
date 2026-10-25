"""
Unit Tests for Two-Pass Chapter Blueprint Scanner, Docling Adapter, and Modular Renderers
=========================================================================================
Verifies `ChapterBlueprint` schema persistence, sub-chapter bookmark preservation in
`PDFSplitter`, `ChapterBlueprintScanner` vector geometry and table/heading extraction,
`DoclingBlueprintAdapter` availability, the five modular block renderers in
`BlockRendererRegistry`, and `check_blueprint_compliance` contract verification
(Refs: ADR-011).
"""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf

from literature_parser.adapters.parsers.docling_adapter import DoclingBlueprintAdapter
from literature_parser.adapters.verification.rules import check_blueprint_compliance
from literature_parser.domain.profiler.blueprint_schema import (
    BlueprintHeadingEntry,
    BlueprintTableEntry,
    ChapterBlueprint,
    PageLayoutBlueprint,
    PageZone,
)
from literature_parser.services.core.splitter import PDFSplitter
from literature_parser.services.parsers.renderers import (
    BlockRendererRegistry,
    CalloutAndExhibitRenderer,
    GlossaryAndEOCRenderer,
    HeadingBlockRenderer,
    ProseAndMathRenderer,
    TableZoneRenderer,
)
from literature_parser.services.profiler.chapter_blueprint_scanner import (
    ChapterBlueprintScanner,
)


class TestChapterBlueprintAndModularRenderers(unittest.TestCase):
    """Tests Two-Pass ChapterBlueprintScanner, DoclingAdapter, modular renderers, and compliance rules."""

    def test_docling_adapter_is_installed_and_available(self) -> None:
        """Verifies IBM Docling package is installed in the project environment.

        Returns:
            None.
        """
        self.assertTrue(DoclingBlueprintAdapter.is_available())

    def test_pdf_splitter_preserves_subchapter_toc_bookmarks(self) -> None:
        """Verifies PDFSplitter preserves and normalizes sub-chapter bookmarks on split.

        Returns:
            None.
        """
        with tempfile.TemporaryDirectory() as tmp:
            src_pdf = Path(tmp) / "book.pdf"
            ch_pdf = Path(tmp) / "Ch01.pdf"
            doc = pymupdf.open()
            for i in range(5):
                p = doc.new_page(width=612, height=792)
                p.insert_text((72, 100), f"Page {i + 1} content")
            doc.set_toc(
                [
                    [1, "Part I Foundations", 1],
                    [2, "Chapter 1 Overview", 2],
                    [3, "1.1 Historical Context", 3],
                    [3, "1.2 Modern Approaches", 4],
                    [2, "Chapter 2 Next Topic", 5],
                ]
            )
            doc.save(str(src_pdf))
            doc.close()

            PDFSplitter.split_chapter(str(src_pdf), 2, 4, str(ch_pdf))
            sub = pymupdf.open(str(ch_pdf))
            sub_toc = sub.get_toc(simple=True)
            sub.close()

            self.assertEqual(len(sub_toc), 3)
            self.assertEqual(sub_toc[0], [1, "Chapter 1 Overview", 1])
            self.assertEqual(sub_toc[1], [2, "1.1 Historical Context", 2])
            self.assertEqual(sub_toc[2], [2, "1.2 Modern Approaches", 3])

    def test_chapter_blueprint_scanner_extracts_zones_and_saves_json(self) -> None:
        """Verifies ChapterBlueprintScanner extracts outline headings, vector rules, and tables.

        Returns:
            None.
        """
        with tempfile.TemporaryDirectory() as tmp:
            ch_dir = Path(tmp)
            ch_pdf = ch_dir / "Ch01-Sample.pdf"
            doc = pymupdf.open()
            page = doc.new_page(width=612, height=792)
            page.insert_text((72, 80), "1.1 Research Foundations", fontsize=15)
            page.insert_text(
                (72, 120),
                "Body paragraph explaining scientific research methodologies in detail.",
                fontsize=10,
            )
            # Draw vector horizontal table rules and Table 1.1 header
            shape = page.new_shape()
            shape.draw_line((72, 195), (500, 195))
            shape.draw_line((72, 215), (500, 215))
            shape.finish(color=(0, 0, 0), width=1.0)
            shape.commit()
            page.insert_text((72, 185), "Table 1.1 Comparison of Research Designs", fontsize=11)
            doc.set_toc([[1, "Ch01 Sample", 1], [2, "1.1 Research Foundations", 1]])
            doc.save(str(ch_pdf))
            doc.close()

            bp = ChapterBlueprintScanner.scan_chapter(
                pdf_path=ch_pdf, chapter_name="Ch01-Sample", output_dir=ch_dir
            )
            bp_json_path = ch_dir / "chapter_blueprint.json"
            self.assertTrue(bp_json_path.exists())
            loaded = ChapterBlueprint.load_json(bp_json_path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.page_count, 1)
            self.assertEqual(len(loaded.expected_tables), 1)
            self.assertEqual(loaded.expected_tables[0].table_id, "1.1")
            self.assertTrue(loaded.expected_tables[0].has_grid_lines)
            self.assertGreaterEqual(len(loaded.expected_headings), 2)

    def test_five_modular_block_renderers(self) -> None:
        """Verifies Heading, TableZone, Callout, Glossary, and Prose modular renderers.

        Returns:
            None.
        """
        bp = ChapterBlueprint(
            chapter_name="Ch02",
            page_count=2,
            body_font_size=10.0,
            expected_headings=[
                BlueprintHeadingEntry(level=2, title="2.1 Theoretical Frameworks", page_num=1)
            ],
            pages={
                1: PageLayoutBlueprint(
                    page_num=1,
                    zones=[
                        PageZone(
                            zone_type="TABLE_ZONE",
                            page_num=1,
                            bbox=[60.0, 100.0, 500.0, 240.0],
                            identifier="Table 2.1",
                            caption="Summary of Theories",
                            pre_rendered_html='<table class="textbook-table"><tr><td>Cell</td></tr></table>',
                        )
                    ],
                )
            },
        )

        # 1. HeadingBlockRenderer
        lvl = HeadingBlockRenderer.resolve_heading_level(
            "2.1 Theoretical Frameworks", 13.5, 1, blueprint=bp
        )
        self.assertEqual(lvl, 2)
        self.assertEqual(
            HeadingBlockRenderer.render("2.1 Theoretical Frameworks", level=lvl or 2),
            "## 2.1 Theoretical Frameworks",
        )
        # Body font size should not be promoted to heading
        self.assertIsNone(
            HeadingBlockRenderer.resolve_heading_level("Normal sentence fragment", 10.0, 1, blueprint=bp)
        )

        # 2. TableZoneRenderer (using pre-rendered zone from blueprint)
        page_elem = ET.fromstring('<page width="612" height="792"></page>')
        tables, _ = TableZoneRenderer.render_page_tables(
            page_elem, {}, 612.0, 792.0, page_num=1, blueprint=bp
        )
        self.assertEqual(len(tables), 1)
        self.assertIn('<table class="textbook-table">', tables[0]["markdown"])

        # 3. CalloutAndExhibitRenderer
        callout_md = CalloutAndExhibitRenderer.render_semantic_callout(
            "learning_objectives", "Learning Objectives", ["1.1 Explain key concepts."]
        )
        self.assertIn("> [!IMPORTANT] **Learning Objectives**", callout_md)

        # 4. GlossaryAndEOCRenderer
        fc_md = GlossaryAndEOCRenderer.render_flashcards_section(
            [{"term": "Self-Efficacy", "definition": "Belief in one's capability.", "page": 12}]
        )
        self.assertIn("flashcard-self-efficacy", fc_md)

        # 5. ProseAndMathRenderer
        cleaned = ProseAndMathRenderer.clean_and_reflow_prose(
            "Clients face diffi cult choices and signifi cant confl ict.", stitch_pages=False
        )
        self.assertIn("difficult", cleaned)
        self.assertIn("significant", cleaned)
        self.assertIs(BlockRendererRegistry.heading, HeadingBlockRenderer)

    def test_check_blueprint_compliance_detects_missing_and_validates_complete(self) -> None:
        """Verifies check_blueprint_compliance flags unformatted tables or missing outline headings.

        Returns:
            None.
        """
        bp_dict = {
            "expected_tables": [{"table_id": "3.1", "page_num": 4, "source": "pymupdf_vector"}],
            "expected_headings": [
                {"level": 2, "title": "3.1 Ethical Decision Making", "page_num": 2, "source": "outline"}
            ],
        }
        bad_md = (
            "## 3.1 Ethical Decision Making\n\n"
            "### Table 3.1 Ethical Principles\n\n"
            "- Autonomy\n- Beneficence\n"
        )
        res_bad = check_blueprint_compliance(bad_md, bp_dict)
        self.assertFalse(res_bad["passed"])
        self.assertIn("Table 3.1", res_bad["missing_tables"])

        good_md = (
            "## 3.1 Ethical Decision Making\n\n"
            "### Table 3.1 Ethical Principles\n\n"
            '<table class="textbook-table"><thead><tr><th>Principle</th></tr></thead>'
            "<tbody><tr><td>Autonomy</td></tr></tbody></table>\n"
        )
        res_good = check_blueprint_compliance(good_md, bp_dict)
        self.assertTrue(res_good["passed"])


if __name__ == "__main__":
    unittest.main()
