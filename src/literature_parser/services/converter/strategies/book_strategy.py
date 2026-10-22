"""
Book & Textbook Post-Processing Strategy
========================================
Specialized post-processor for multi-chapter textbooks and front-matter sections:
- Normalizes top-level chapter and section headings.
- Generates clickable, collapsible Table of Contents (<summary>📑 Table of Contents</summary>).
- Injects dual-presentation links for cropped Table images above structured tables.
- Preserves pedagogical blocks (Learning Objectives, Margin Glossaries, Worked Examples).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.converter.models import ConversionOptions, CroppedElement
from literature_parser.services.converter.strategies.base_strategy import PostProcessorStrategy
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.layout_detector import generate_markdown_toc
from literature_parser.services.utils.text_utils import stitch_cross_page_continuity

logger = logging.getLogger(__name__)


class BookPostProcessor(PostProcessorStrategy):
    """Encapsulates textbook and front matter domain post-processing rules."""

    def process(
        self,
        raw_markdown: str,
        profile: DocumentProfile,
        options: ConversionOptions,
        cropped_elements: list[CroppedElement],
        context: Dict[str, Any],
    ) -> str:
        """Processes raw textbook markdown and injects structure and tables.

        Args:
            raw_markdown: Combined raw page Markdown text.
            profile: DocumentProfile with typographic settings.
            options: ConversionOptions controlling TOC, titles, and layout.
            cropped_elements: List of CroppedElement instances (figures and tables).
            context: Contextual dictionary with chapter_name, etc.

        Returns:
            Refined and semantically enriched textbook Markdown.
        """
        md = raw_markdown.strip()
        chapter_name = context.get("chapter_name") or options.custom_title or profile.meta.title
        is_front_matter = options.is_front_matter or (chapter_name and chapter_name.startswith("00-"))

        # 1. Heading Normalization & Title Prepending
        if options.prepend_title_if_missing and not is_front_matter:
            has_h1 = bool(re.search(r'^\s*#\s+[^\n]+', md, re.MULTILINE))
            if not has_h1 and chapter_name:
                md = f"# {chapter_name}\n\n{md}"

        # 2. Table Dual Presentation (Insert image reference alongside text table)
        for elem in cropped_elements:
            if elem.element_type == "table":
                # Look for table header e.g. "Table 1" or "Table 1.1" or "### Table 1"
                t_id_clean = elem.identifier.replace("table_", "").replace("_", ".")
                pattern = rf'(?m)(^\s*(?:###\s*Table\s+{re.escape(t_id_clean)}\b|\*\*Table\s+{re.escape(t_id_clean)}\*\*|<table\b))'
                match = re.search(pattern, md)
                img_tag = f'\n\n<p align="center"><img src="images/{elem.filename}" alt="{elem.caption or elem.identifier}" style="max-width: 95%; border: 1px solid #e1e4e8; border-radius: 4px;" /></p>\n'
                if match and elem.filename not in md:
                    # Place image right above the matched table
                    idx = match.start()
                    md = md[:idx] + img_tag + "\n" + md[idx:]

        # 3. Insert clickable Table of Contents (TOC)
        if options.generate_toc and not is_front_matter and options.toc_mode != "none":
            toc_block = generate_markdown_toc(md, toc_mode=options.toc_mode)
            if toc_block and "<summary>📑 <b>Table of Contents</b>" not in md:
                m_h1 = re.search(r'^(#[^\n]+\n+)', md)
                if m_h1:
                    md = md[:m_h1.end()] + toc_block + "\n\n" + md[m_h1.end():]
                else:
                    md = f"{toc_block}\n\n{md}"

        # 4. Stitch Cross-Page Sentence Continuity
        try:
            md = stitch_cross_page_continuity(md)
        except Exception as e:
            logger.debug("stitch_cross_page_continuity skipped: %s", e)

        # 4.5. Semantic Anchoring for Figures & Tables (Marker-Style Paragraph Boundary Placement)
        try:
            from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter
            md = FigureFormatter.reposition_figures_and_tables(md)
        except Exception as e:
            logger.debug("Figure/Table repositioning skipped in textbook: %s", e)

        # 5. Append Chapter-End Key Terms / Flashcards if present
        is_scanned = (profile.meta.mode == "scanned")
        if not is_scanned and not is_front_matter:
            try:
                ch_gloss = DigitalPDFParser.get_chapter_all_terms()
                if ch_gloss and "## 🗂️ Chapter Key Terms" not in md and "## 📖 Chapter Key Terms" not in md:
                    fc_lines = [
                        "## 🗂️ Chapter Key Terms & Active Recall",
                        "",
                        "> 💡 **Learning tip:** Try to recall the definition of each term *before* clicking to reveal it.",
                        "> This active retrieval practice strengthens long-term memory far more than re-reading.",
                        "",
                    ]
                    for g in ch_gloss:
                        t = g.get('term', '')
                        d = (g.get('definition') or '').strip()
                        pg = g.get('page')
                        pg_str = f" *(p. {pg})*" if pg else ""
                        slug = re.sub(r'[^a-zA-Z0-9]+', '-', t.lower()).strip('-')
                        fc_lines.append(f'<details id="flashcard-{slug}">')
                        fc_lines.append(f"<summary>📇 <b>{t}</b>{pg_str}</summary>")
                        fc_lines.append("")
                        if d:
                            fc_lines.append(f"> **Definition:** {d}")
                        else:
                            loc = f"on p. {pg}" if pg else "in the chapter"
                            fc_lines.append(f"> *This term appears in bold {loc}.*")
                            fc_lines.append("> *Write your own definition from context, then re-read that passage to check.*")
                        fc_lines.append("")
                        fc_lines.append("</details>")
                        fc_lines.append("")

                    fc_text = '\n'.join(fc_lines)
                    m_eoc = re.search(
                        r'(?:<a id="key-terms-and-concepts"></a>|###\s*Key Terms and Concepts)',
                        md
                    )
                    if m_eoc:
                        pos = m_eoc.start()
                        md = md[:pos] + fc_text + "\n\n" + md[pos:]
                    else:
                        md = md + "\n\n" + fc_text
            except Exception as e:
                logger.debug("Flashcards extraction skipped: %s", e)

        return md.strip()
