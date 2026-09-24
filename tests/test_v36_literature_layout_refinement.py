"""
Unit Tests for V36: Academic Literature Layout Refinement & Journal Consolidation
=================================================================================
Tests:
  - LiteratureMetadataExtractor: Fast-path rule extraction, HTML rendering, TOC generation
  - FigureFormatter: Image deduplication per page & semantic <figure> HTML generation
  - IMRADResolver: APA tertiary headings, Author Note relocation, Table header suppression
  - ReferenceParser: HTML entity unescaping, en-dash page ranges, trailing OCR noise removal
  - LiteraturePipeline.sync_verified_tables: TOC isolation (never pollutes Table of Contents)
"""

import tempfile
import unittest
from pathlib import Path

from book_processor.parsers.literature.metadata_extractor import LiteratureMetadataExtractor, generate_markdown_toc
from book_processor.parsers.literature.figure_formatter import FigureFormatter
from book_processor.parsers.literature.imrad_resolver import IMRADResolver
from book_processor.parsers.literature.reference_parser import ReferenceParser
from book_processor.pipelines.literature_pipeline import LiteraturePipeline


class TestLiteratureLayoutRefinement(unittest.TestCase):

    def test_metadata_extractor_fast_path(self):
        sample = (
            "Journal of Experimental Psychology: Applied\n"
            "2002, Vol. 8, No. 2, 75- 84\n"
            "Copyright 2002 by the American Psychological Association, Inc.\n"
            "10.1037//1076-898X.8.2.75\n\n"
            "# Evaluation of a Behavioral Measure of Risk Taking: The BART\n\n"
            "## Abstract\n\n"
            "A novel behavioral measure of risk taking was evaluated.\n\n"
            "---\n\n"
            "## Method\n"
        )
        meta = LiteratureMetadataExtractor.extract_with_rules(sample)
        self.assertEqual(meta["journal"], "Journal of Experimental Psychology: Applied")
        self.assertEqual(meta["volume_info"], "2002, Vol. 8, No. 2, 75–84")
        self.assertEqual(meta["copyright"], "Copyright 2002 by the American Psychological Association, Inc.")
        self.assertEqual(meta["doi"], "10.1037//1076-898X.8.2.75")
        self.assertEqual(meta["title"], "Evaluation of a Behavioral Measure of Risk Taking: The BART")
        self.assertIn("novel behavioral measure", meta["abstract"])

    def test_metadata_extractor_render_header(self):
        meta = {
            "journal": "Journal of Testing",
            "volume_info": "2024, Vol. 1, No. 1, 1–10",
            "copyright": "Copyright 2024",
            "doi": "10.1000/182",
            "title": "A Great Study",
            "authors": [{"name": "Jane Doe", "affiliation": "MIT"}],
            "abstract": "This is an abstract text.",
        }
        rendered = LiteratureMetadataExtractor.render_header(meta, "A Great Study", "body text")
        self.assertIn('<div class="article-meta">', rendered)
        self.assertIn('<strong>Journal of Testing</strong>', rendered)
        self.assertIn('DOI: <a href="https://doi.org/10.1000/182">10.1000/182</a>', rendered)
        self.assertIn('# A Great Study', rendered)
        self.assertIn('<div class="author-name">Jane Doe</div>', rendered)
        self.assertIn('<div class="author-affiliation">MIT</div>', rendered)
        self.assertIn('<summary>📑 <b>Table of Contents</b></summary>', rendered)
        self.assertIn('> This is an abstract text.', rendered)

    def test_figure_formatter_deduplication(self):
        images = [
            {"page": 3, "filename": "003_001.png", "width": 800},
            {"page": 3, "filename": "figure_1_.png", "width": 800},
            {"page": 4, "filename": "004_002.png", "width": 800},
        ]
        deduped = FigureFormatter.deduplicate_page_images(images)
        self.assertEqual(len(deduped), 2)
        filenames = [img["filename"] for img in deduped]
        self.assertIn("003_001.png", filenames)
        self.assertNotIn("figure_1_.png", filenames)
        self.assertIn("004_002.png", filenames)

    def test_figure_formatter_render_html(self):
        html = FigureFormatter.render_figure_html("images/003_001.png", "Figure 1. Diagram of the task.", max_width=650)
        self.assertIn("<figure>", html)
        self.assertIn('<img src="images/003_001.png"', html)
        self.assertIn("<strong>Figure 1.</strong> Diagram of the task.", html)
        self.assertIn("</figure>", html)

    def test_imrad_resolver_apa_subheadings_and_author_note_relocation(self):
        doc = (
            "# Main Paper\n\n"
            "## Abstract\n\n"
            "> Abstract content\n\n"
            "---\n\n"
            "## Author Note & Acknowledgments\n\n"
            "Author notes on page 1.\n\n"
            "Risk-taking behavior in laboratory settings has been widely studied across diverse psychological paradigms. "
            "Here we present an empirical evaluation of risk preferences across diverse cohorts.\n\n"
            "## Method\n\n"
            "Participants\n\n"
            "86 participants were recruited.\n\n"
            "*Materials and Apparatus*\n\n"
            "*The BART*\n\n"
            "The BART was designed...\n\n"
            "## Results\n\n"
            "*Experimental Properties of the BART*\n\n"
            "Results text.\n\n"
            "### Table 4\n\n"
            "Raw table text\n\n"
            "## References\n\n"
            "- Author A (2000). Paper A.\n"
        )
        resolved = IMRADResolver.resolve_structure(doc)
        # Check Introduction inserted
        self.assertIn("## Introduction", resolved)
        # Check APA headings promoted
        self.assertIn("### Materials and Apparatus", resolved)
        self.assertIn("#### The BART", resolved)
        self.assertIn("### Experimental Properties of the BART", resolved)
        # Check Table 4 heading suppressed
        self.assertNotIn("### Table 4", resolved)
        # Check Author note moved to before references
        an_pos = resolved.find("Author Note & Acknowledgments")
        ref_pos = resolved.find("## References")
        self.assertTrue(an_pos != -1 and ref_pos != -1)
        self.assertTrue(an_pos < ref_pos)
        method_pos = resolved.find("## Method")
        self.assertTrue(an_pos > method_pos)

    def test_reference_parser_clean_entities_and_noise(self):
        raw_ref = (
            "## References\n\n"
            "Eysenck, S., Pearson, P., &amp; Easting, G. (1985). Age norms. *Pers Indiv Diff, 6,*613- 619. 䡲\n"
        )
        cleaned = ReferenceParser.clean_document_references(raw_ref)
        self.assertIn("& Easting, G.", cleaned)
        self.assertNotIn("&amp;", cleaned)
        self.assertIn("613–619", cleaned)
        self.assertNotIn("䡲", cleaned)

    def test_sync_verified_tables_does_not_pollute_toc(self):
        toc_md = (
            "<details open>\n"
            "<summary>📑 <b>Table of Contents</b></summary>\n\n"
            "- [Abstract](#abstract)\n"
            "- [Method](#method)\n"
            "- [Results](#results)\n"
            "  - [Table 4](#table-4)\n\n"
            "</details>\n\n---\n\n"
            "## Results\n\n"
            "### Table 4\n\n"
            "Old raw table contents\n\n"
            "## Discussion\n"
        )
        with tempfile.NamedTemporaryFile("w+", suffix="_Verified.md", delete=False) as f:
            f.write(
                '<div class="table-caption">Table 4</div>\n'
                '<div class="table-subtitle">Factor Loadings</div>\n'
                '<table><tr><th>Col</th></tr></table>\n'
                '<div class="table-notes"><em>Note.</em> Table note.</div>'
            )
            v_path = Path(f.name)

        try:
            synced = LiteraturePipeline.sync_verified_tables(toc_md, v_path)
            # TOC should NOT contain table HTML
            toc_section = synced[:synced.find("</details>")]
            self.assertNotIn("<table>", toc_section)
            self.assertNotIn('<div class="table-caption">', toc_section)
            self.assertIn("- [Table 4](#table-4)", toc_section)

            # Body section SHOULD contain table HTML
            body_section = synced[synced.find("</details>"):]
            self.assertIn('<div class="table-caption">Table 4</div>', body_section)
            self.assertIn("<table>", body_section)
        finally:
            v_path.unlink()


if __name__ == "__main__":
    unittest.main()
