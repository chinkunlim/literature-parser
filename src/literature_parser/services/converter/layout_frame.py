"""
Marker-Style Layout Framing & Semantic Anchoring
================================================
Implements block-level document layout framing, prose continuity healing,
and paragraph-boundary semantic anchoring:
- Decouples floating figures and tables into an ArtifactRegistry.
- Heals broken sentences caused by physical page cuts or floating elements.
- Anchors figures and tables strictly after complete paragraphs or list blocks.
- Employs strict keyword matching to prevent false positives (e.g. 'sales figure').
- Normalizes sub-figure references (e.g. 'Figure 1A' maps to master 'Figure 1').
- Flushes uncited orphan artifacts at section boundaries (zero-drop guarantee).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Enumeration of semantic document block types."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_BLOCK = "list_block"
    FIGURE = "figure"
    TABLE = "table"
    CALLOUT = "callout"


class PageZone(Enum):
    """Enumeration of page physical geometric layout zones."""
    HEADER_FOOTER = "header_footer"
    MARGIN = "margin"
    FLOATING = "floating"
    MAIN_BODY = "main_body"


@dataclass
class ZoneClassification:
    """Carries categorized elements belonging to a specific page zone."""
    zone: PageZone
    elements: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ZoneTagger:
    """Partitions page elements into distinct geometric zones."""

    @classmethod
    def tag_elements(
        cls,
        elements: List[Any],
        pw: float,
        ph: float,
        page_num: int,
        geometry: Optional[Dict[str, Any]] = None,
    ) -> Dict[PageZone, List[Any]]:
        """Classifies raw page XML or bounding elements into layout zones.

        Args:
            elements: List of XML text or box elements.
            pw: Physical page width in points.
            ph: Physical page height in points.
            page_num: 1-indexed page number (used for facing margins).
            geometry: Optional calibrated geometry parameters.

        Returns:
            Dictionary mapping PageZone to the list of elements within that zone.
        """
        geom = geometry or {}
        hdr_cut = geom.get("margins", {}).get("header_cutoff_y", ph * 0.05)
        ftr_cut = geom.get("margins", {}).get("footer_cutoff_y", ph * 0.94)

        has_margin_col = geom.get("has_margin_column", True)
        is_odd = (page_num % 2 != 0)

        # Default margin cutoffs
        margin_left = pw * 0.72 if is_odd else 0.0
        margin_right = pw if is_odd else pw * 0.28

        zones: Dict[PageZone, List[Any]] = {
            PageZone.HEADER_FOOTER: [],
            PageZone.MARGIN: [],
            PageZone.FLOATING: [],
            PageZone.MAIN_BODY: [],
        }

        for el in elements:
            try:
                top = float(el.attrib.get("top", 0.0))
                left = float(el.attrib.get("left", 0.0))
                w = float(el.attrib.get("width", 0.0))
            except AttributeError:
                # If element is a dict or tuple
                top = float(getattr(el, "top", 0.0) if hasattr(el, "top") else el[0] if isinstance(el, (list, tuple)) else 0.0)
                left = float(getattr(el, "left", 0.0) if hasattr(el, "left") else el[1] if isinstance(el, (list, tuple)) else 0.0)
                w = float(getattr(el, "width", 0.0) if hasattr(el, "width") else el[2] if isinstance(el, (list, tuple)) else 0.0)

            # 1. Header / Footer Zone
            if top <= hdr_cut or top >= ftr_cut:
                zones[PageZone.HEADER_FOOTER].append(el)
                continue

            # 2. Margin Zone (glossaries, side callouts)
            if has_margin_col:
                if is_odd and left >= margin_left:
                    zones[PageZone.MARGIN].append(el)
                    continue
                if not is_odd and (left + w) <= margin_right:
                    zones[PageZone.MARGIN].append(el)
                    continue

            # 3. Main Body Zone
            zones[PageZone.MAIN_BODY].append(el)

        return zones


@dataclass
class FrameBlock:
    """Represents a discrete semantic block in a document layout frame."""
    block_type: BlockType
    text: str
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    page_num: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArtifactRegistry:
    """Registry maintaining decoupled figures and tables for semantic anchoring."""

    def __init__(self):
        """Initializes empty artifact registry."""
        self._figures: Dict[str, str] = {}
        self._tables: Dict[str, str] = {}
        self._mounted_figures: Set[str] = set()
        self._mounted_tables: Set[str] = set()

    def register_figure(self, fig_id: str, content: str) -> None:
        """Registers a figure under its normalized identifier (e.g. '1', '2.1').

        Args:
            fig_id: Normalized figure identifier.
            content: Complete HTML/Markdown content for the figure block.
        """
        clean_id = fig_id.strip()
        self._figures[clean_id] = content

    def register_table(self, table_id: str, content: str) -> None:
        """Registers a table under its normalized identifier (e.g. '1', '2.1').

        Args:
            table_id: Normalized table identifier.
            content: Complete HTML/Markdown content for the table block.
        """
        clean_id = table_id.strip()
        self._tables[clean_id] = content

    @staticmethod
    def normalize_id(raw_id: str) -> str:
        """Normalizes sub-figure identifiers like '1A', '1.2b' to master ID '1', '1.2'.

        Args:
            raw_id: Raw string identifier.

        Returns:
            Normalized base identifier without sub-index letter.
        """
        clean = raw_id.strip()
        m = re.match(r"^([0-9IVXLCDM]+(?:\.[0-9]+)*)[a-zA-Z]?$", clean)
        if m:
            return m.group(1)
        return clean

    def match_and_mount_figure(self, raw_id: str) -> Optional[str]:
        """Matches figure by exact or normalized ID and marks it as mounted.

        Args:
            raw_id: Mentioned figure ID.

        Returns:
            Figure block content if found and not yet mounted, None otherwise.
        """
        norm_id = self.normalize_id(raw_id)
        target_id = raw_id if raw_id in self._figures else (norm_id if norm_id in self._figures else None)

        if target_id and target_id not in self._mounted_figures:
            self._mounted_figures.add(target_id)
            return self._figures[target_id]
        return None

    def match_and_mount_table(self, raw_id: str) -> Optional[str]:
        """Matches table by exact or normalized ID and marks it as mounted.

        Args:
            raw_id: Mentioned table ID.

        Returns:
            Table block content if found and not yet mounted, None otherwise.
        """
        norm_id = self.normalize_id(raw_id)
        target_id = raw_id if raw_id in self._tables else (norm_id if norm_id in self._tables else None)

        if target_id and target_id not in self._mounted_tables:
            self._mounted_tables.add(target_id)
            return self._tables[target_id]
        return None

    def get_unmounted_figures(self) -> List[Tuple[str, str]]:
        """Returns list of all registered figures that have not yet been mounted.

        Returns:
            List of (fig_id, content) tuples.
        """
        return [(k, v) for k, v in self._figures.items() if k not in self._mounted_figures]

    def get_unmounted_tables(self) -> List[Tuple[str, str]]:
        """Returns list of all registered tables that have not yet been mounted.

        Returns:
            List of (table_id, content) tuples.
        """
        return [(k, v) for k, v in self._tables.items() if k not in self._mounted_tables]

    def mark_figure_mounted(self, fig_id: str) -> None:
        """Marks figure ID as mounted."""
        self._mounted_figures.add(fig_id)

    def mark_table_mounted(self, table_id: str) -> None:
        """Marks table ID as mounted."""
        self._mounted_tables.add(table_id)


class SemanticAnchorEmitter:
    """Emits narrative text with paragraph-boundary semantic anchoring of figures and tables."""

    # Strict citation patterns requiring capitalized Figure/Fig./Table followed by number
    FIGURE_MENTION_PATTERN = re.compile(
        r"\b(?:Figure|Fig\.)\s+([0-9IVXLCDM]+(?:\.[0-9]+)*[a-zA-Z]?)\b"
    )
    TABLE_MENTION_PATTERN = re.compile(
        r"\bTable\s+([0-9IVXLCDM]+(?:\.[0-9]+)*[a-zA-Z]?)\b"
    )

    def __init__(self, registry: Optional[ArtifactRegistry] = None):
        """Initializes SemanticAnchorEmitter with an ArtifactRegistry.

        Args:
            registry: Optional ArtifactRegistry containing figures and tables.
        """
        self.registry = registry or ArtifactRegistry()

    def process_paragraph(self, paragraph_text: str) -> str:
        """Processes a single logical paragraph, appending any newly cited figures/tables after it.

        Args:
            paragraph_text: Complete text of the paragraph.

        Returns:
            Paragraph text followed by any cited figures/tables.
        """
        clean_p = paragraph_text.strip()
        if not clean_p:
            return ""

        # Find all mentions in order
        to_mount: List[str] = []

        # Find figures
        for m in self.FIGURE_MENTION_PATTERN.finditer(clean_p):
            fig_id = m.group(1)
            content = self.registry.match_and_mount_figure(fig_id)
            if content:
                to_mount.append(content)

        # Find tables
        for m in self.TABLE_MENTION_PATTERN.finditer(clean_p):
            table_id = m.group(1)
            content = self.registry.match_and_mount_table(table_id)
            if content:
                to_mount.append(content)

        if to_mount:
            return clean_p + "\n\n" + "\n\n".join(to_mount)
        return clean_p

    def process_text(self, full_md: str, flush_orphans: bool = True) -> str:
        """Processes entire Markdown text, emitting blocks and flushing uncited orphans at section breaks.

        Args:
            full_md: Full markdown document string.
            flush_orphans: If True, appends unmounted orphan artifacts at section boundaries and document end.

        Returns:
            Markdown string with all figures and tables anchored cleanly at paragraph boundaries.
        """
        if not full_md:
            return ""

        # Split into blocks by double newlines or headers
        paragraphs = re.split(r"\n\n+", full_md.strip())
        output_blocks: List[str] = []

        for p in paragraphs:
            # If paragraph is a heading, flush any unmounted artifacts before it if requested
            if p.startswith("#") and flush_orphans:
                unmounted_figs = self.registry.get_unmounted_figures()
                unmounted_tbls = self.registry.get_unmounted_tables()
                for f_id, f_content in unmounted_figs:
                    output_blocks.append(f_content)
                    self.registry.mark_figure_mounted(f_id)
                for t_id, t_content in unmounted_tbls:
                    output_blocks.append(t_content)
                    self.registry.mark_table_mounted(t_id)

                output_blocks.append(p)
            else:
                processed_p = self.process_paragraph(p)
                output_blocks.append(processed_p)

        # Flush any remaining unmounted artifacts at end of document
        if flush_orphans:
            final_unmounted_figs = self.registry.get_unmounted_figures()
            final_unmounted_tbls = self.registry.get_unmounted_tables()
            for f_id, f_content in final_unmounted_figs:
                output_blocks.append(f_content)
                self.registry.mark_figure_mounted(f_id)
            for t_id, t_content in final_unmounted_tbls:
                output_blocks.append(t_content)
                self.registry.mark_table_mounted(t_id)

        return "\n\n".join(output_blocks).strip()


class DocumentLayoutFrame:
    """Manages document layout frame blocks and prose healing across boundaries."""

    @classmethod
    def heal_continuous_prose(cls, pre_text: str, post_text: str) -> Tuple[str, bool]:
        """Heals broken sentences split across extraction boundaries or page cuts.

        Args:
            pre_text: Text preceding the break.
            post_text: Text succeeding the break.

        Returns:
            Tuple of (combined_text, was_healed_bool).
        """
        pre_clean = pre_text.rstrip()
        post_clean = post_text.lstrip()

        if not pre_clean or not post_clean:
            return pre_clean + ("\n\n" if pre_clean and post_clean else "") + post_clean, False

        last_char = pre_clean[-1]
        first_char = post_clean[0]

        # Sentence is severed if pre doesn't end with sentence terminator and post starts with lowercase/paren
        if last_char not in {".", "?", "!", ":", ";", ")", "”", '"'} and (first_char.islower() or first_char in {"(", "["}):
            return pre_clean + " " + post_clean, True

        return pre_clean + "\n\n" + post_clean, False
