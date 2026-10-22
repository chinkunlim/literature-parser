"""
Academic Literature Post-Processing Strategy
============================================
Specialized post-processor for academic literature (peer-reviewed articles,
conference papers, preprints, dissertations):
- Promotes main article title to H1 (#).
- Resolves IMRAD headings (Introduction, Methods, Results, Discussion).
- Formats hanging-indent bibliographic references (APA, IEEE).
- Synchronizes dual-presentation for cropped Tables and semantic <figure> tags.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.converter.models import ConversionOptions, CroppedElement
from literature_parser.services.converter.strategies.base_strategy import PostProcessorStrategy
from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter
from literature_parser.services.parsers.literature.imrad_resolver import IMRADResolver
from literature_parser.services.parsers.literature.reference_parser import ReferenceParser

logger = logging.getLogger(__name__)


class LiteraturePostProcessor(PostProcessorStrategy):
    """Encapsulates academic paper and journal literature post-processing rules."""

    def process(
        self,
        raw_markdown: str,
        profile: DocumentProfile,
        options: ConversionOptions,
        cropped_elements: list[CroppedElement],
        context: Dict[str, Any],
    ) -> str:
        """Processes raw literature markdown and injects academic structure.

        Args:
            raw_markdown: Combined raw page Markdown text.
            profile: DocumentProfile with academic typographic settings.
            options: ConversionOptions controlling generation parameters.
            cropped_elements: List of CroppedElement instances (figures and tables).
            context: Contextual dictionary with publisher, subtype, etc.

        Returns:
            Refined and semantically enriched academic Markdown.
        """
        md = raw_markdown.strip()

        # 1. Promote Main Article Title to H1 if missing
        if not re.search(r'^\s*#\s+[^\n]+', md):
            m_first_h = re.search(r'###\s+([^\n]+)(?:\n+###\s+([^\n]+))?', md)
            if m_first_h:
                t1 = m_first_h.group(1).strip()
                t2 = m_first_h.group(2).strip() if m_first_h.group(2) else ""
                combined = f"{t1} {t2}".strip()
                md = md[:m_first_h.start()] + f"# {combined}" + md[m_first_h.end():]

        # 2. Resolve IMRAD Section Headings
        try:
            md = IMRADResolver.resolve(md)
        except Exception as e:
            logger.debug("IMRADResolver skipped: %s", e)

        # 3. Format References with Hanging Indent
        try:
            md = ReferenceParser.parse_and_format(md)
        except Exception as e:
            logger.debug("ReferenceParser skipped: %s", e)

        # 4. Table Dual Presentation (Insert cropped image alongside text table)
        for elem in cropped_elements:
            if elem.element_type == "table":
                t_id_clean = elem.identifier.replace("table_", "").replace("_", ".")
                pattern = rf'(?m)(^\s*(?:###\s*Table\s+{re.escape(t_id_clean)}\b|\*\*Table\s+{re.escape(t_id_clean)}\*\*|<div class="table-caption"[^>]*>Table\s+{re.escape(t_id_clean)}</div>|<table\b))'
                match = re.search(pattern, md)
                img_tag = f'\n\n<p align="center"><img src="images/{elem.filename}" alt="{elem.caption or elem.identifier}" style="max-width: 95%; border: 1px solid #e1e4e8; border-radius: 4px;" /></p>\n'
                if match and elem.filename not in md:
                    idx = match.start()
                    md = md[:idx] + img_tag + "\n" + md[idx:]

        # 5. Semantic Anchoring for Figures & Tables (Marker-Style Paragraph Boundary Placement)
        try:
            from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter
            md = FigureFormatter.reposition_figures_and_tables(md)
        except Exception as e:
            logger.debug("FigureFormatter repositioning skipped: %s", e)

        return md.strip()
