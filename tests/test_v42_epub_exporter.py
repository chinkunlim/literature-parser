"""
Unit Tests for EPUB 3 Exporter Engine & Pipeline Integration
============================================================
Validates:
- LaTeX to MathML conversion & currency escaping
- Markdown to valid XHTML5 document generation
- Pure-Python EPUB 3 container packaging (mimetype, container, opf, nav, ncx, css, images)
- Single literature export and multi-chapter book unification
- CLI command dispatcher and error handling
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from literature_parser.services.exporter.epub_exporter import (
    EpubExporter,
    LaTeXToMathML,
    MarkdownToXHTML,
    PurePythonEpubBuilder,
)


class TestLaTeXToMathML(unittest.TestCase):
    """Verifies that mathematical expressions are converted into standard EPUB 3 MathML."""

    def test_inline_greek_and_subscript(self):
        latex = r"\alpha + \beta_1 = \gamma"
        res = LaTeXToMathML.convert_formula(latex)
        self.assertIn('<math xmlns="http://www.w3.org/1998/Math/MathML"', res)
        self.assertIn("α", res)
        self.assertIn("β", res)
        self.assertIn("<msub>", res)

    def test_fraction_and_superscript(self):
        latex = r"\frac{a^2}{b}"
        res = LaTeXToMathML.convert_formula(latex)
        self.assertIn("<mfrac>", res)
        self.assertIn("<msup>", res)

    def test_display_block(self):
        latex = r"E = mc^2"
        res = LaTeXToMathML.convert_formula(latex, display_block=True)
        self.assertIn('display="block"', res)

    def test_process_markdown_math_preserves_currency(self):
        md = "The test cost $15.50 and the result was $t(24) = 2.06$."
        res = LaTeXToMathML.process_markdown_math(md)
        # Currency should remain literal or entity-escaped
        self.assertIn("&#36;15.50", res)
        # Statistical formula should be converted to MathML
        self.assertIn('<math xmlns="http://www.w3.org/1998/Math/MathML"', res)


class TestMarkdownToXHTML(unittest.TestCase):
    """Verifies that Markdown content translates to standards-compliant XHTML5."""

    def test_clean_markdown_for_epub(self):
        md = "<style>body{color:red;}</style>\n# Document Title\nSome content"
        cleaned, title = MarkdownToXHTML.clean_markdown_for_epub(md)
        self.assertEqual(title, "Document Title")
        self.assertNotIn("<style>", cleaned)
        self.assertIn("Some content", cleaned)

    def test_xhtml_elements_and_void_tags(self):
        md = (
            "# Main Heading\n\n"
            "This is a paragraph with **bold**, *italic*, and `code`.\n\n"
            "> A blockquote observation\n\n"
            "- Item A\n- Item B\n\n"
            '<div class="author-block"><div class="author-name">Dr. Smith</div></div>\n'
            "<details open><summary>Summary</summary>Details content</details>\n"
            "Here is a break<br>and an image:\n"
            "![Chart](images/chart.png)"
        )
        xhtml = MarkdownToXHTML.to_xhtml_body(md)
        # Ensure XHTML compliance
        self.assertIn("<h1>Main Heading</h1>", xhtml)
        self.assertIn("<strong>bold</strong>", xhtml)
        self.assertIn("<em>italic</em>", xhtml)
        self.assertIn("<code>code</code>", xhtml)
        self.assertIn("<blockquote>", xhtml)
        self.assertIn("<ul>", xhtml)
        self.assertIn('open="open"', xhtml)
        self.assertIn("<br />", xhtml)
        self.assertIn("<img", xhtml)
        self.assertIn("/>", xhtml)

        # Full document XML parse test
        full_doc = f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Test</title></head><body>{xhtml}</body></html>'
        root = ET.fromstring(full_doc)
        self.assertIsNotNone(root)


class TestPurePythonEpubBuilder(unittest.TestCase):
    """Verifies that the pure-Python builder produces valid EPUB 3 zip containers."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.out_epub = Path(self.tmp_dir.name) / "test_book.epub"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_epub_packaging_and_xml_validity(self):
        builder = PurePythonEpubBuilder(book_title="Test Publication", author="Test Author", language="en")
        builder.add_chapter("Chapter 1", "chapter_01.xhtml", "<h1>Chapter 1</h1><p>Welcome to Chapter 1.</p>")
        builder.add_chapter("Chapter 2", "chapter_02.xhtml", "<h1>Chapter 2</h1><p>Mathematical proof: <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mrow>x</mrow></math></p>")

        # Add a dummy image
        img_path = Path(self.tmp_dir.name) / "figure.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
        builder.add_image("images/figure.png", img_path)

        res_path = builder.build(self.out_epub)
        self.assertTrue(res_path.exists())

        # Inspect zip archive
        with zipfile.ZipFile(res_path, "r") as zf:
            namelist = zf.namelist()
            # 1. mimetype must be exact first entry uncompressed
            self.assertEqual(namelist[0], "mimetype")
            self.assertEqual(zf.read("mimetype"), b"application/epub+zip")
            info = zf.getinfo("mimetype")
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

            # 2. Required EPUB files
            self.assertIn("META-INF/container.xml", namelist)
            self.assertIn("OEBPS/content.opf", namelist)
            self.assertIn("OEBPS/nav.xhtml", namelist)
            self.assertIn("OEBPS/toc.ncx", namelist)
            self.assertIn("OEBPS/styles/style.css", namelist)
            self.assertIn("OEBPS/text/chapter_01.xhtml", namelist)
            self.assertIn("OEBPS/text/chapter_02.xhtml", namelist)
            self.assertIn("OEBPS/images/figure.png", namelist)

            # 3. XML validation for all markup files
            for fname in ["META-INF/container.xml", "OEBPS/content.opf", "OEBPS/nav.xhtml", "OEBPS/toc.ncx", "OEBPS/text/chapter_01.xhtml", "OEBPS/text/chapter_02.xhtml"]:
                data = zf.read(fname).decode("utf-8")
                if "<!DOCTYPE" in data:
                    data = data.split(">", 1)[1]
                tree = ET.fromstring(data)
                self.assertIsNotNone(tree)

            # 4. MathML property in manifest
            content_opf = zf.read("OEBPS/content.opf").decode("utf-8")
            self.assertIn('properties="mathml"', content_opf)
            self.assertIn('<dc:title>Test Publication</dc:title>', content_opf)


class TestEpubExporterLiteratureAndBook(unittest.TestCase):
    """Verifies end-to-end export for both Literature and multi-chapter Book directories."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_export_literature_success(self):
        lit_dir = self.base_dir / "paper_01"
        lit_dir.mkdir(parents=True)
        img_dir = lit_dir / "images"
        img_dir.mkdir()
        (img_dir / "img1.png").write_bytes(b"dummy image data")

        md_content = (
            "<style>p{color:#333;}</style>\n"
            "# A Study on Cognitive Agility\n\n"
            '<div class="article-meta">Vol 1, Issue 2</div>\n'
            '<div class="author-block"><div class="author-name">Alice Walker</div></div>\n\n'
            "## Abstract\n\n"
            "This is the paper abstract.\n\n"
            "## Results\n\n"
            "Statistical formula: $p < .01$ and $F_{1, 20} = 4.5$.\n\n"
            '<figure><img src="images/img1.png" alt="Fig 1" /><figcaption>Figure 1</figcaption></figure>\n'
        )
        (lit_dir / "paper_01.md").write_text(md_content, encoding="utf-8")

        epub_path = EpubExporter.export_literature(lit_dir, engine="python")
        self.assertTrue(epub_path.exists())
        self.assertEqual(epub_path.suffix, ".epub")

        with zipfile.ZipFile(epub_path) as zf:
            self.assertIn("OEBPS/text/document.xhtml", zf.namelist())
            self.assertIn("OEBPS/images/img1.png", zf.namelist())

    def test_export_book_multi_chapter_unification(self):
        book_dir = self.base_dir / "Textbook_A"
        chapters_root = book_dir / "chapters"
        ch1 = chapters_root / "Chapter_01"
        ch2 = chapters_root / "Chapter_02"
        ch1.mkdir(parents=True)
        ch2.mkdir(parents=True)

        (ch1 / "Chapter_01.md").write_text("# Chapter 1: Introduction\n\nIntro content.", encoding="utf-8")
        (ch2 / "Chapter_02.md").write_text("# Chapter 2: Methods\n\nMethods content.", encoding="utf-8")

        epub_path = EpubExporter.export_book(book_dir, engine="python")
        self.assertTrue(epub_path.exists())
        self.assertEqual(epub_path.name, "Textbook_A.epub")

        with zipfile.ZipFile(epub_path) as zf:
            namelist = zf.namelist()
            self.assertIn("OEBPS/text/chapter_01.xhtml", namelist)
            self.assertIn("OEBPS/text/chapter_02.xhtml", namelist)
            nav_content = zf.read("OEBPS/nav.xhtml").decode("utf-8")
            self.assertIn("Chapter 1: Introduction", nav_content)
            self.assertIn("Chapter 2: Methods", nav_content)

    def test_export_book_single_chapter_filter(self):
        book_dir = self.base_dir / "Textbook_B"
        chapters_root = book_dir / "chapters"
        ch1 = chapters_root / "Chapter_01"
        ch2 = chapters_root / "Chapter_02"
        ch1.mkdir(parents=True)
        ch2.mkdir(parents=True)

        (ch1 / "Chapter_01.md").write_text("# Chapter 1: Foundations\n\nFoundations.", encoding="utf-8")
        (ch2 / "Chapter_02.md").write_text("# Chapter 2: Advanced\n\nAdvanced.", encoding="utf-8")

        epub_path = EpubExporter.export_book(book_dir, chapter="Chapter_01", engine="python")
        self.assertTrue(epub_path.exists())
        self.assertEqual(epub_path.name, "Chapter_01.epub")

        with zipfile.ZipFile(epub_path) as zf:
            self.assertIn("OEBPS/text/chapter_01.xhtml", zf.namelist())
            self.assertNotIn("OEBPS/text/chapter_02.xhtml", zf.namelist())


class TestEpubCLIDispatch(unittest.TestCase):
    """Verifies CLI argument parsing and dispatching for the 'epub' command."""

    @patch("literature_parser.services.exporter.epub_exporter.EpubExporter.export_literature")
    def test_cmd_epub_literature_dispatch(self, mock_export):
        from literature_parser.entrypoints.project_cli.cli_process import cmd_epub

        mock_export.return_value = Path("dummy.epub")
        args = MagicMock()
        args.path = "data/output/literature/2002-01194-001/2002-01194-001.md"
        args.output = None
        args.engine = "auto"
        args.chapter = None

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                cmd_epub(args)
                mock_export.assert_called_once()


if __name__ == "__main__":
    unittest.main()
