"""
Modular Semantic Block Renderers (`BlockRendererRegistry`)
==========================================================
Implements the five specialized block renderers for Pass 2 of the
Two-Pass Chapter Blueprint architecture (Refs: ADR-011):
1. HeadingBlockRenderer — Blueprint-validated heading level resolution and formatting
2. TableZoneRenderer — Vector/grid and Docling-assisted HTML `<table class="textbook-table">` rendering
3. CalloutAndExhibitRenderer — Pedagogical callouts, Learning Objectives, Case Studies, Exhibits
4. GlossaryAndEOCRenderer — Margin glossaries, End-of-Chapter questions, and Active Recall Flashcards
5. ProseAndMathRenderer — Multi-column prose reflow, ligature repair, and LaTeX math normalization
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from literature_parser.domain.profiler.blueprint_schema import ChapterBlueprint
from literature_parser.services.parsers.layout.callout_parser import CalloutParser
from literature_parser.services.parsers.layout.eoc_parser import EndOfChapterParser
from literature_parser.services.parsers.layout.margin_parser import MarginParser
from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.utils.text_utils import (
    normalize_ligatures,
    repair_drop_caps,
    stitch_cross_page_continuity,
)


class HeadingBlockRenderer:
    """Renders and validates section headings against the chapter's structural blueprint."""

    @staticmethod
    def is_valid_heading_candidate(text: str) -> bool:
        """Checks whether a candidate line is syntactically valid as a section heading.

        Args:
            text: Raw candidate heading text.

        Returns:
            True if valid as a heading, False if it exhibits prose intrusion or noise.
        """
        clean = re.sub(r"^[\*_`#\s]+|[\*_`\s]+$", "", text or "").strip()
        if not clean:
            return False
        if clean[0].islower():
            return False
        if not re.search(r"[A-Za-z0-9]", clean):
            return False
        if re.match(r"^(?:https?://|www\.)", clean, re.IGNORECASE):
            return False
        if len(clean) < 3 and not re.fullmatch(r"[A-Z]", clean):
            return False
        scrubbed = re.sub(
            r"\b(?:e\.g|i\.e|vs|et al|Dr|Mr|Mrs|Ms|Prof|St|Jr|Sr|Inc|Ltd|Co|No|Vol|Ch|Fig|pp|Ed|U\.S|U\.K|Ph\.D|M\.A|B\.A)\.\s+",
            " ",
            clean,
            flags=re.IGNORECASE,
        )
        if re.search(r"[a-z]{2,}\.\s+[A-Z][a-z]", scrubbed):
            return False
        return True

    @classmethod
    def resolve_heading_level(
        cls,
        text: str,
        font_size: float,
        page_num: int,
        blueprint: Optional[ChapterBlueprint] = None,
    ) -> Optional[int]:
        """Determines the Markdown heading level (1..4) for `text` using the `ChapterBlueprint`.

        Args:
            text: Candidate heading text.
            font_size: Font size in points.
            page_num: 1-indexed page number.
            blueprint: Optional `ChapterBlueprint` containing outline headings and font roles.

        Returns:
            Integer heading level (1..4), or None if `text` should remain body prose.
        """
        if not cls.is_valid_heading_candidate(text):
            return None
        clean = re.sub(r"[\s\*_`#]+", " ", text).strip().lower()

        if blueprint is not None:
            for entry in blueprint.expected_headings:
                entry_clean = re.sub(r"[\s\*_`#]+", " ", entry.title).strip().lower()
                if entry.page_num == page_num and (
                    clean == entry_clean or clean.startswith(entry_clean[:25]) or entry_clean.startswith(clean[:25])
                ):
                    return max(1, min(4, entry.level))
            body_sz = blueprint.body_font_size or 10.0
            if font_size <= body_sz + 0.8:
                return None

        if font_size >= 18.0:
            return 1
        if font_size >= 14.0:
            return 2
        if font_size >= 12.0:
            return 3
        return None

    @classmethod
    def render(cls, text: str, level: int = 2) -> str:
        """Formats a validated heading string into Markdown `#` syntax.

        Args:
            text: Heading text content.
            level: Heading level between 1 and 4.

        Returns:
            Formatted Markdown heading line, or plain text if invalid.
        """
        clean = re.sub(r"^[\*_`#\s]+|[\*_`\s]+$", "", text or "").strip()
        clean = re.sub(r"^[•~\-—]{2,}\s*", "", clean).strip()
        if not cls.is_valid_heading_candidate(clean):
            return clean
        clamped = max(1, min(4, int(level)))
        return f"{'#' * clamped} {clean}"


class TableZoneRenderer:
    """Renders page tables using PyMuPDF vector zones, `TableParser`, and `Docling` fallbacks."""

    @classmethod
    def render_page_tables(
        cls,
        page_elem: Any,
        fonts: Dict[str, Any],
        pw: float,
        ph: float,
        page_num: int = 1,
        blueprint: Optional[ChapterBlueprint] = None,
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Set[Any]]:
        """Extracts and renders all tables on `page_num` as `<table class="textbook-table">`.

        Args:
            page_elem: XML `<page>` ElementTree object.
            fonts: Font id mapping dictionary.
            pw: Page width in points.
            ph: Page height in points.
            page_num: 1-indexed page number.
            blueprint: Optional `ChapterBlueprint` providing pre-scanned `TABLE_ZONE` metadata.
            style_config: Optional style configuration dictionary.

        Returns:
            Tuple of `(list_of_table_dicts, set_of_consumed_xml_elements)`.
        """
        tables, consumed = TableParser.extract_page_tables(
            page_elem, fonts, pw, ph, style_config=style_config
        )
        if blueprint is not None and page_num in blueprint.pages:
            existing_md = "\n".join(t.get("markdown", "") for t in tables)
            for zone in blueprint.pages[page_num].zones:
                if zone.zone_type == "TABLE_ZONE" and zone.pre_rendered_html:
                    if zone.identifier and zone.identifier not in existing_md:
                        header_str = f"### {zone.identifier} {zone.caption}".strip()
                        tables.append(
                            {
                                "top": zone.bbox[1] if len(zone.bbox) >= 2 else 100.0,
                                "markdown": f"{header_str}\n\n{zone.pre_rendered_html}",
                            }
                        )
        return tables, consumed


class CalloutAndExhibitRenderer:
    """Renders pedagogical callouts, Exhibits, Case Studies, and Worked Examples."""

    @staticmethod
    def render_semantic_callout(box_type: str, title: str, body_lines: List[str]) -> str:
        """Formats a pedagogical box into a structured GitHub alert or HTML callout block.

        Args:
            box_type: Semantic category ('learning_objectives', 'case_study', 'worked_example', 'exhibit').
            title: Header title of the callout box.
            body_lines: List of body text lines inside the callout.

        Returns:
            Formatted Markdown callout block.
        """
        b_type = (box_type or "exhibit").lower()
        tag = "[!NOTE]"
        if "learning" in b_type or "objective" in b_type:
            tag = "[!IMPORTANT]"
        elif "example" in b_type or "tip" in b_type:
            tag = "[!TIP]"
        header = f"> {tag} **{title.strip()}**" if title.strip() else f"> {tag}"
        quoted_body = [f"> {line}" if line.strip() else ">" for line in body_lines]
        return "\n".join([header] + quoted_body)

    @staticmethod
    def format_callout_paragraphs(paragraphs: List[str]) -> List[str]:
        """Formats sidebar and callout paragraphs into structured blockquote alerts.

        Args:
            paragraphs: List of raw Markdown paragraph blocks.

        Returns:
            List of formatted paragraph blocks.
        """
        return CalloutParser.format_callout_boxes(paragraphs)


class GlossaryAndEOCRenderer:
    """Renders Margin Glossaries, End-of-Chapter questions, and Active Recall Flashcards."""

    @staticmethod
    def extract_margin_glossaries(
        page_elem: Any,
        fonts: Dict[str, Any],
        pw: float,
        ph: float,
        page_num: int,
        already_consumed: Set[Any],
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Set[Any]]:
        """Extracts margin glossary terms and definitions from the outer margin zone.

        Args:
            page_elem: XML `<page>` ElementTree object.
            fonts: Font id mapping dictionary.
            pw: Page width in points.
            ph: Page height in points.
            page_num: 1-indexed page number.
            already_consumed: Set of XML elements already claimed by tables or exhibits.
            style_config: Optional style configuration dictionary.

        Returns:
            Tuple of `(list_of_glossary_dicts, set_of_consumed_elements)`.
        """
        return MarginParser.extract_margin_glossaries(
            page_elem, fonts, pw, ph, page_num, already_consumed=already_consumed, style=style_config
        )

    @staticmethod
    def extract_eoc_sections(
        page_elem: Any,
        fonts: Dict[str, Any],
        pw: float,
        ph: float,
        page_num: int,
        style_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Set[Any]]:
        """Extracts End-of-Chapter summary and review question blocks.

        Args:
            page_elem: XML `<page>` ElementTree object.
            fonts: Font id mapping dictionary.
            pw: Page width in points.
            ph: Page height in points.
            page_num: 1-indexed page number.
            style_config: Optional style configuration dictionary.

        Returns:
            Tuple of `(list_of_eoc_dicts, set_of_consumed_elements)`.
        """
        return EndOfChapterParser.extract_end_of_chapter_sections(
            page_elem, fonts, pw, ph, page_num, style=style_config
        )

    @staticmethod
    def render_flashcards_section(terms: List[Dict[str, Any]]) -> str:
        """Renders interactive HTML `<details>` Active Recall Flashcards for chapter key terms.

        Args:
            terms: List of glossary dictionaries with `'term'`, `'definition'`, and `'page'`.

        Returns:
            Formatted Markdown string containing interactive flashcards.
        """
        if not terms:
            return ""
        lines = [
            "## 🗂️ Chapter Key Terms & Active Recall",
            "",
            "> 💡 **Learning tip:** Try to recall the definition of each term *before* clicking to reveal it.",
            "",
        ]
        for item in terms:
            term = str(item.get("term", "")).strip()
            if not term:
                continue
            defn = str(item.get("definition") or "").strip()
            pg = item.get("page")
            pg_str = f" *(p. {pg})*" if pg else ""
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", term.lower()).strip("-")
            lines.append(f'<details id="flashcard-{slug}">')
            lines.append(f"<summary>📇 <b>{term}</b>{pg_str}</summary>")
            lines.append("")
            if defn:
                lines.append(f"> **Definition:** {defn}")
            else:
                lines.append("> *Review this key term in context within the chapter.*")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        return "\n".join(lines).strip()


class ProseAndMathRenderer:
    """Reflows multi-column body prose, repairs broken ligatures/drop-caps, and normalizes math."""

    @staticmethod
    def clean_and_reflow_prose(md_text: str, stitch_pages: bool = True) -> str:
        """Applies ligature normalization, drop-cap repair, and cross-page sentence stitching.

        Args:
            md_text: Raw or partially assembled Markdown text.
            stitch_pages: Whether to stitch sentences broken across `<!-- Page N -->` boundaries.

        Returns:
            Cleaned and reflowed Markdown prose.
        """
        if not md_text:
            return ""
        cleaned = normalize_ligatures(md_text)
        cleaned = repair_drop_caps(cleaned)
        if stitch_pages:
            cleaned = stitch_cross_page_continuity(cleaned)
        return cleaned


class BlockRendererRegistry:
    """Facade registry providing unified access to all five modular block renderers."""

    heading = HeadingBlockRenderer
    table = TableZoneRenderer
    callout = CalloutAndExhibitRenderer
    glossary = GlossaryAndEOCRenderer
    prose = ProseAndMathRenderer
