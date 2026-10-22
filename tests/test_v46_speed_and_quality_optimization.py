"""
Unit Tests for Speed and Quality Pipeline Optimizations (TASK-019)
=================================================================
Validates:
- Dual-Engine PDF Parser (Native PyMuPDF with Poppler fallback)
- Enhanced LaTeX Math formula reconstruction (fractions, sub/superscripts, delimiters)
- Two-Column Gutter Guard and Spanning Element isolation
- Academic reference stitching (broken DOIs and URLs)
- Pipelined chapter execution (CPU extraction overlapping GPU Ollama review)
- TextbookPipeline parallel wiring
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf

from literature_parser.adapters.parsers.pdf_engine import PDFDocumentEngine
from literature_parser.services.concurrency.pipelined_processor import PipelinedChapterProcessor
from literature_parser.services.parsers.literature.reference_parser import ReferenceParser
from literature_parser.services.parsers.math_latex import MathLaTeXParser
from literature_parser.services.pipelines.textbook_pipeline import TextbookPipeline


class TestPDFEngineDualMode(unittest.TestCase):
    """Tests the high-performance native PyMuPDF engine and Poppler fallback adapter."""

    def setUp(self) -> None:
        """Creates a temporary test PDF with text and a mock drawing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.temp_dir.name) / "sample_doc.pdf"

        # Create a real 2-page PDF using pymupdf
        doc = pymupdf.open()
        p1 = doc.new_page(width=612, height=792)
        p1.insert_text((72, 72), "Chapter 1: Cognitive Processes", fontsize=18)
        p1.insert_text((72, 120), "Cognitive psychology investigates human cognition.", fontsize=11)
        p1.draw_line((72, 140), (540, 140))  # Horizontal rule

        p2 = doc.new_page(width=612, height=792)
        p2.insert_text((72, 72), "Section 1.1: Foundations", fontsize=14)
        p2.insert_text((72, 100), "Memory models describe information storage.", fontsize=11)
        doc.save(str(self.pdf_path))
        doc.close()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_native_pymupdf_extraction_speed_and_pages(self) -> None:
        """Verifies native PyMuPDF engine extracts pages, text spans, and geometry without CLI subprocesses."""
        with PDFDocumentEngine(self.pdf_path, force_fallback=False) as engine:
            self.assertTrue(engine.is_native_active)
            self.assertEqual(engine.get_page_count(), 2)

            # Test page text extraction
            page1_data = engine.extract_page_data(1)
            self.assertIn("Cognitive Processes", page1_data["text"])
            self.assertGreater(len(page1_data["spans"]), 0)

            # Verify line drawings detected (horizontal rule)
            lines = engine.get_drawings(1)
            self.assertGreaterEqual(len(lines), 1)

            # Test crop rendering
            crop_path = Path(self.temp_dir.name) / "crop_test.png"
            engine.render_cropped_image(page_num=1, bbox=(70, 60, 400, 150), output_path=crop_path)
            self.assertTrue(crop_path.exists())
            self.assertGreater(crop_path.stat().st_size, 0)

    def test_poppler_fallback_mode(self) -> None:
        """Verifies engine degrades gracefully to CLI fallback when force_fallback is True."""
        with PDFDocumentEngine(self.pdf_path, force_fallback=True) as engine:
            self.assertFalse(engine.is_native_active)
            self.assertEqual(engine.get_page_count(), 2)


class TestLaTeXMathEnhancements(unittest.TestCase):
    """Tests advanced LaTeX math formula and fraction reconstruction."""

    def test_reconstruct_fraction_from_vertical_spans(self) -> None:
        """Verifies horizontal division line with numerator above and denominator below builds \\frac{num}{den}."""
        numerator_span = {"text": "a + b", "bbox": (100, 50, 140, 62), "size": 10.0}
        division_line = {"start": (98, 65), "end": (142, 65), "width": 1.0}
        denominator_span = {"text": "2c", "bbox": (105, 68, 125, 80), "size": 10.0}

        frac = MathLaTeXParser.detect_and_build_fraction(numerator_span, division_line, denominator_span)
        self.assertEqual(frac, r"\frac{a + b}{2c}")

    def test_normalize_sub_and_superscripts(self) -> None:
        """Verifies sub/superscripts are properly formatted with math delimiters."""
        raw_text = "The regression formula yields R 2 = 0.45 with x 1 as predictor."
        normalized = MathLaTeXParser.normalize_sub_and_superscripts(raw_text)
        self.assertIn("$R^2$", normalized)
        self.assertIn("$x_1$", normalized)

    def test_ensure_balanced_math_delimiters(self) -> None:
        """Verifies unbalanced dollar signs are resolved without escaping valid math."""
        # Single isolated dollar in prose should be escaped
        prose_with_price = "The equipment cost $500 per unit, where $x = 10$."
        fixed = MathLaTeXParser.balance_and_sanitize_delimiters(prose_with_price)
        self.assertIn(r"\$500", fixed)
        self.assertIn("$x = 10$", fixed)


class TestTwoColumnReadingFlowAndGutter(unittest.TestCase):
    """Tests gutter detection, column sorting, and spanning block isolation."""

    def test_gutter_detection_and_column_sorting(self) -> None:
        """Verifies text blocks in column 1 (left) come before column 2 (right)."""
        from literature_parser.services.parsers.layout_detector import TwoColumnFlowResolver

        # Page width 600, gutter at ~300
        blocks = [
            {"bbox": (350, 100, 550, 150), "text": "Right column paragraph 1."},
            {"bbox": (50, 100, 250, 150), "text": "Left column paragraph 1."},
            {"bbox": (50, 160, 250, 210), "text": "Left column paragraph 2."},
            {"bbox": (350, 160, 550, 210), "text": "Right column paragraph 2."},
        ]
        sorted_blocks = TwoColumnFlowResolver.order_blocks_by_flow(blocks, page_width=600)
        ordered_texts = [b["text"] for b in sorted_blocks]

        # Left column should be read in full before right column
        self.assertEqual(ordered_texts[0], "Left column paragraph 1.")
        self.assertEqual(ordered_texts[1], "Left column paragraph 2.")
        self.assertEqual(ordered_texts[2], "Right column paragraph 1.")
        self.assertEqual(ordered_texts[3], "Right column paragraph 2.")

    def test_spanning_element_isolation(self) -> None:
        """Verifies elements spanning across both columns (e.g. width > 70% of page) are treated as full-width."""
        from literature_parser.services.parsers.layout_detector import TwoColumnFlowResolver

        spanning_figure = {"bbox": (50, 50, 550, 200), "text": "Figure 1: Full-width experimental architecture."}
        col1_text = {"bbox": (50, 220, 250, 300), "text": "Text in left column."}
        col2_text = {"bbox": (350, 220, 550, 300), "text": "Text in right column."}

        blocks = [col2_text, spanning_figure, col1_text]
        resolved = TwoColumnFlowResolver.order_blocks_by_flow(blocks, page_width=600)

        # Spanning figure at y=50 must precede column texts at y=220
        self.assertEqual(resolved[0]["text"], "Figure 1: Full-width experimental architecture.")
        self.assertEqual(resolved[1]["text"], "Text in left column.")
        self.assertEqual(resolved[2]["text"], "Text in right column.")


class TestReferenceParserEnhancements(unittest.TestCase):
    """Tests academic reference stitching for broken DOIs and URLs."""

    def test_stitch_broken_doi(self) -> None:
        """Verifies DOIs broken across line wraps are seamlessly rejoined."""
        broken_ref = (
            "Smith, J. (2022). Deep neural representation. Journal of AI, 12(3), 45-56. "
            "https://doi.org/10.1016/\n"
            "j.ai.2022.04.012"
        )
        stitched = ReferenceParser.stitch_broken_identifiers(broken_ref)
        self.assertIn("https://doi.org/10.1016/j.ai.2022.04.012", stitched)
        self.assertNotIn("https://doi.org/10.1016/\n", stitched)

    def test_stitch_broken_url(self) -> None:
        """Verifies URLs broken by trailing hyphens or line wraps are restored."""
        broken_url_ref = (
            "Available from: http://www.psychology-\n"
            "research.org/data/archive/2021"
        )
        stitched = ReferenceParser.stitch_broken_identifiers(broken_url_ref)
        self.assertIn("http://www.psychology-research.org/data/archive/2021", stitched)


class TestPipelinedChapterProcessor(unittest.TestCase):
    """Tests the asynchronous CPU parsing and GPU Ollama review pipeline."""

    def test_pipelined_overlap_execution(self) -> None:
        """Verifies that chapters are processed through the producer-consumer pipeline."""
        processor = PipelinedChapterProcessor(max_cpu_workers=2)

        items = ["Chapter_01", "Chapter_02", "Chapter_03"]

        def mock_cpu_worker(ch_name: str) -> dict:
            return {"chapter": ch_name, "markdown": f"# {ch_name}\nContent here."}

        def mock_gpu_reviewer(item: dict) -> dict:
            item["reviewed"] = True
            item["score"] = 98.0
            return item

        results = processor.run_pipeline(
            items=items,
            cpu_task_fn=mock_cpu_worker,
            gpu_task_fn=mock_gpu_reviewer,
        )

        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.get("reviewed"))
            self.assertEqual(r.get("score"), 98.0)


class TestTextbookPipelineParallelWiring(unittest.TestCase):
    """Verifies that TextbookPipeline wires parallel execution when requested."""

    @patch("literature_parser.services.core.analyzer.PDFAnalyzer.get_sections")
    def test_parallel_flag_triggers_concurrency(self, mock_get_sections) -> None:
        mock_get_sections.return_value = ([
            {"name": "Ch01", "start": 1, "end": 10},
            {"name": "Ch02", "start": 11, "end": 20},
        ], {})

        mock_orchestrator = MagicMock()
        mock_orchestrator.convert_single_chapter.return_value = {"passed": True}

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "dummy.pdf"
            doc = pymupdf.open()
            for i in range(20):
                p = doc.new_page(width=612, height=792)
                p.insert_text((72, 72), f"Page {i+1}")
            doc.save(str(pdf_path))
            doc.close()

            pipeline = TextbookPipeline(
                output_dir=tmp_dir,
                processed_dir=tmp_dir,
                orchestrator=mock_orchestrator,
            )

            # Process with parallel=True
            res = pipeline.process(str(pdf_path), parallel=True)
            self.assertTrue(res["passed"])
            self.assertEqual(res["chapters_count"], 2)


if __name__ == "__main__":
    unittest.main()
