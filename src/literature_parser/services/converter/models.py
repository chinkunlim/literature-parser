"""
Models and Data Contracts for Markdown Conversion
=================================================
Defines strongly-typed data structures for the Markdown conversion engine:
- ConversionOptions: Tunable configuration for TOC, images, cropping, and CSS.
- CroppedElement: Represents an extracted Figure or Table with bounding box,
  caption, notes, and equal margin padding.
- ConversionResult: Immutable-like output contract carrying Markdown body,
  CSS styling, image references, and extracted metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature_parser.domain.profiler.profile_schema import DocumentProfile


@dataclass(frozen=True)
class ConversionOptions:
    """Tunable options controlling document conversion behavior.

    Attributes:
        extract_images: Whether to extract embedded raster images from the PDF.
        crop_figures_and_tables: Whether to crop standalone figures and tables to image files.
        uniform_crop_margin_pt: Margin in PDF points added equally to top, bottom, left, and right.
        generate_toc: Whether to generate a clickable Table of Contents.
        toc_mode: Mode for TOC rendering ('open', 'close', or 'none').
        prepend_title_if_missing: Whether to prepend an H1 title if not detected.
        custom_title: Optional override title for the section or chapter.
        embed_css: Whether to embed a <style> block in the output Markdown.
        output_standalone_css: Whether to generate a standalone style.css file in the output root.
        is_front_matter: Whether the current document is a 00-* front matter section.
    """

    extract_images: bool = True
    crop_figures_and_tables: bool = True
    uniform_crop_margin_pt: float = 16.0
    generate_toc: bool = True
    toc_mode: str = "open"
    prepend_title_if_missing: bool = True
    custom_title: Optional[str] = None
    embed_css: bool = True
    output_standalone_css: bool = True
    is_front_matter: bool = False
    dual_table_presentation: bool = False


@dataclass
class CroppedElement:
    """Represents a cropped figure or table image extracted from a page.

    Attributes:
        element_type: Classification string ('figure' or 'table').
        identifier: Semantic identifier (e.g. 'figure_1', 'table_2_1').
        filename: Destination filename (e.g. 'figure_1.png', 'table_2_1.png').
        filepath: Full path on disk to the cropped image.
        page_num: 1-indexed page number in the PDF where the element appeared.
        bbox: Original unpadded bounding box (left, top, right, bottom) in points.
        padded_bbox: Padded bounding box with equal margin (left, top, right, bottom) in points.
        caption: Caption text associated with the element.
        notes: Explanatory notes or legends associated with the element.
    """

    element_type: str
    identifier: str
    filename: str
    filepath: Path
    page_num: int
    bbox: tuple[float, float, float, float]
    padded_bbox: tuple[float, float, float, float]
    caption: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts element metadata to dictionary representation.

        Returns:
            Dictionary containing element metadata.
        """
        return {
            "element_type": self.element_type,
            "identifier": self.identifier,
            "filename": self.filename,
            "filepath": str(self.filepath),
            "page_num": self.page_num,
            "bbox": list(self.bbox),
            "padded_bbox": list(self.padded_bbox),
            "caption": self.caption,
            "notes": self.notes,
        }


@dataclass
class ConversionResult:
    """Standardized output result returned by MarkdownConversionService.

    Attributes:
        markdown: Processed structured Markdown content.
        css_content: CSS stylesheet content matching the document typography.
        images: List of extracted figure image metadata dictionaries.
        cropped_elements: List of CroppedElement instances (figures and tables).
        page_count: Total number of pages processed.
        metadata: Extracted document metadata (titles, authors, sections).
        stats: Execution performance and parsing statistics.
        profile: Canonical DocumentProfile instance utilized for conversion.
    """

    markdown: str
    css_content: str = ""
    images: List[Dict[str, Any]] = field(default_factory=list)
    cropped_elements: List[CroppedElement] = field(default_factory=list)
    page_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    profile: Optional[DocumentProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts result summary to dictionary representation.

        Returns:
            Dictionary summary of the conversion result.
        """
        return {
            "page_count": self.page_count,
            "images_count": len(self.images),
            "cropped_elements_count": len(self.cropped_elements),
            "metadata": self.metadata,
            "stats": self.stats,
            "has_css": bool(self.css_content),
        }
