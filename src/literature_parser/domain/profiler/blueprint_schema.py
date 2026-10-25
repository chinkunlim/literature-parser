"""
Chapter Structural Blueprint Domain Schema
==========================================
Defines strongly-typed domain data structures for pre-conversion chapter
structural blueprints (`chapter_blueprint.json`), capturing authoritative
sub-chapter PDF outline headings, typographic font-role signatures, and
per-page 2D spatial zones (tables, callouts, exhibits, figures, margin glossaries,
and body columns) before text conversion begins (Refs: ADR-011).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FontRoleSignature:
    """Typographic signature mapped to a semantic document role.

    Attributes:
        role: Semantic role ('h1', 'h2', 'h3', 'h4', 'body', 'caption', 'margin_term').
        font_family: Normalized font family name.
        font_size: Typical font size in points.
        is_bold: Whether the font style is bold.
        is_italic: Whether the font style is italic.
        sample_count: Number of text spans or lines matching this signature.
    """

    role: str
    font_family: str
    font_size: float
    is_bold: bool = False
    is_italic: bool = False
    sample_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the font role signature to a dictionary.

        Returns:
            Dictionary representation of the font role signature.
        """
        return {
            "role": self.role,
            "font_family": self.font_family,
            "font_size": round(self.font_size, 2),
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FontRoleSignature:
        """Deserializes a FontRoleSignature from a dictionary.

        Args:
            data: Raw dictionary containing font role attributes.

        Returns:
            Constructed FontRoleSignature instance.
        """
        return cls(
            role=str(data.get("role", "body")),
            font_family=str(data.get("font_family", "")),
            font_size=float(data.get("font_size", 10.0)),
            is_bold=bool(data.get("is_bold", False)),
            is_italic=bool(data.get("is_italic", False)),
            sample_count=int(data.get("sample_count", 0)),
        )


@dataclass
class BlueprintHeadingEntry:
    """Authoritative heading entry discovered during the pre-conversion scan.

    Attributes:
        level: Markdown heading level (1 for H1, 2 for H2, 3 for H3, 4 for H4).
        title: Clean heading text.
        page_num: 1-indexed chapter page number where the heading appears.
        top_y: Vertical Y coordinate on the page in points.
        source: Discovery source ('outline', 'typography', or 'docling').
    """

    level: int
    title: str
    page_num: int
    top_y: float = 0.0
    source: str = "outline"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the heading entry to a dictionary.

        Returns:
            Dictionary representation of the heading entry.
        """
        return {
            "level": self.level,
            "title": self.title,
            "page_num": self.page_num,
            "top_y": round(self.top_y, 2),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlueprintHeadingEntry:
        """Deserializes a BlueprintHeadingEntry from a dictionary.

        Args:
            data: Raw dictionary containing heading entry fields.

        Returns:
            Constructed BlueprintHeadingEntry instance.
        """
        return cls(
            level=int(data.get("level", 2)),
            title=str(data.get("title", "")),
            page_num=int(data.get("page_num", 1)),
            top_y=float(data.get("top_y", 0.0)),
            source=str(data.get("source", "outline")),
        )


@dataclass
class BlueprintTableEntry:
    """Authoritative table entry discovered during the pre-conversion scan.

    Attributes:
        table_id: Canonical table identifier (e.g. '1-1', '2.1', '15.5').
        title: Caption or title of the table.
        page_num: 1-indexed chapter page number where the table starts.
        bbox: Bounding box tuple `(x0, y0, x1, y1)` in page points.
        has_grid_lines: Whether PyMuPDF detected explicit vector grid/ruling lines.
        source: Discovery source ('pymupdf_vector', 'caption_anchor', or 'docling').
    """

    table_id: str
    title: str
    page_num: int
    bbox: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    has_grid_lines: bool = False
    source: str = "pymupdf_vector"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the table entry to a dictionary.

        Returns:
            Dictionary representation of the table entry.
        """
        return {
            "table_id": self.table_id,
            "title": self.title,
            "page_num": self.page_num,
            "bbox": [round(v, 2) for v in self.bbox],
            "has_grid_lines": self.has_grid_lines,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlueprintTableEntry:
        """Deserializes a BlueprintTableEntry from a dictionary.

        Args:
            data: Raw dictionary containing table entry fields.

        Returns:
            Constructed BlueprintTableEntry instance.
        """
        raw_bbox = data.get("bbox", [0.0, 0.0, 0.0, 0.0])
        return cls(
            table_id=str(data.get("table_id", "")),
            title=str(data.get("title", "")),
            page_num=int(data.get("page_num", 1)),
            bbox=[float(x) for x in raw_bbox[:4]],
            has_grid_lines=bool(data.get("has_grid_lines", False)),
            source=str(data.get("source", "pymupdf_vector")),
        )


@dataclass
class PageZone:
    """Represents a 2D spatial semantic zone on a single PDF page.

    Attributes:
        zone_type: Semantic category ('HEADER', 'FOOTER', 'MARGIN_GLOSSARY',
            'TABLE_ZONE', 'EXHIBIT_ZONE', 'CALLOUT_ZONE', 'FIGURE_ZONE',
            'BODY_COL_1', 'BODY_COL_2').
        page_num: 1-indexed page number.
        bbox: Bounding box `[x0, y0, x1, y1]` in PDF points.
        identifier: Optional semantic identifier (e.g. 'Table 2.1', 'Exhibit 3.1').
        caption: Optional caption or title string.
        has_border_lines: Whether vector border strokes enclose or rule this zone.
        has_shaded_fill: Whether a colored vector fill rectangle backs this zone.
        pre_rendered_html: Optional HTML/Markdown pre-rendered by a specialist engine (e.g. Docling).
    """

    zone_type: str
    page_num: int
    bbox: List[float]
    identifier: str = ""
    caption: str = ""
    has_border_lines: bool = False
    has_shaded_fill: bool = False
    pre_rendered_html: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the page zone to a dictionary.

        Returns:
            Dictionary representation of the page zone.
        """
        res: Dict[str, Any] = {
            "zone_type": self.zone_type,
            "page_num": self.page_num,
            "bbox": [round(v, 2) for v in self.bbox],
            "identifier": self.identifier,
            "caption": self.caption,
            "has_border_lines": self.has_border_lines,
            "has_shaded_fill": self.has_shaded_fill,
        }
        if self.pre_rendered_html:
            res["pre_rendered_html"] = self.pre_rendered_html
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageZone:
        """Deserializes a PageZone from a dictionary.

        Args:
            data: Raw dictionary containing zone fields.

        Returns:
            Constructed PageZone instance.
        """
        raw_bbox = data.get("bbox", [0.0, 0.0, 0.0, 0.0])
        return cls(
            zone_type=str(data.get("zone_type", "BODY_COL_1")),
            page_num=int(data.get("page_num", 1)),
            bbox=[float(x) for x in raw_bbox[:4]],
            identifier=str(data.get("identifier", "")),
            caption=str(data.get("caption", "")),
            has_border_lines=bool(data.get("has_border_lines", False)),
            has_shaded_fill=bool(data.get("has_shaded_fill", False)),
            pre_rendered_html=data.get("pre_rendered_html"),
        )


@dataclass
class PageLayoutBlueprint:
    """Layout blueprint for a single page within a chapter.

    Attributes:
        page_num: 1-indexed page number.
        width: Page width in points.
        height: Page height in points.
        layout_mode: Column layout classification ('single_column', 'two_column',
            'rotated_landscape', or 'blank').
        gutter_x: Horizontal X coordinate separating two body columns, if applicable.
        drawing_rects_count: Count of vector rectangles/lines detected on this page.
        zones: List of 2D semantic PageZone instances on this page.
    """

    page_num: int
    width: float = 612.0
    height: float = 792.0
    layout_mode: str = "single_column"
    gutter_x: Optional[float] = None
    drawing_rects_count: int = 0
    zones: List[PageZone] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the page layout blueprint to a dictionary.

        Returns:
            Dictionary representation of the page layout blueprint.
        """
        return {
            "page_num": self.page_num,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "layout_mode": self.layout_mode,
            "gutter_x": round(self.gutter_x, 2) if self.gutter_x is not None else None,
            "drawing_rects_count": self.drawing_rects_count,
            "zones": [z.to_dict() for z in self.zones],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageLayoutBlueprint:
        """Deserializes a PageLayoutBlueprint from a dictionary.

        Args:
            data: Raw dictionary containing page layout blueprint fields.

        Returns:
            Constructed PageLayoutBlueprint instance.
        """
        gx = data.get("gutter_x")
        return cls(
            page_num=int(data.get("page_num", 1)),
            width=float(data.get("width", 612.0)),
            height=float(data.get("height", 792.0)),
            layout_mode=str(data.get("layout_mode", "single_column")),
            gutter_x=float(gx) if gx is not None else None,
            drawing_rects_count=int(data.get("drawing_rects_count", 0)),
            zones=[PageZone.from_dict(z) for z in data.get("zones", [])],
        )


@dataclass
class ChapterBlueprint:
    """Root structural blueprint for a chapter (`chapter_blueprint.json`).

    Attributes:
        chapter_name: Canonical chapter stem name.
        page_count: Total number of pages in the chapter PDF.
        engine: Primary scanner engine used ('pymupdf_vector' or 'pymupdf+docling').
        body_font_size: Calibrated modal body font size in points.
        body_font_family: Calibrated modal body font family.
        font_roles: List of calibrated FontRoleSignature mappings.
        expected_headings: Authoritative list of sub-chapter headings.
        expected_tables: Authoritative list of tables detected in the chapter.
        pages: Mapping of 1-indexed page number to PageLayoutBlueprint.
    """

    chapter_name: str
    page_count: int
    engine: str = "pymupdf_vector"
    body_font_size: float = 10.0
    body_font_family: str = ""
    font_roles: List[FontRoleSignature] = field(default_factory=list)
    expected_headings: List[BlueprintHeadingEntry] = field(default_factory=list)
    expected_tables: List[BlueprintTableEntry] = field(default_factory=list)
    pages: Dict[int, PageLayoutBlueprint] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the complete ChapterBlueprint to a JSON-compatible dictionary.

        Returns:
            Dictionary representation of the ChapterBlueprint.
        """
        return {
            "chapter_name": self.chapter_name,
            "page_count": self.page_count,
            "engine": self.engine,
            "body_font_size": round(self.body_font_size, 2),
            "body_font_family": self.body_font_family,
            "font_roles": [fr.to_dict() for fr in self.font_roles],
            "expected_headings": [h.to_dict() for h in self.expected_headings],
            "expected_tables": [t.to_dict() for t in self.expected_tables],
            "pages": {str(k): v.to_dict() for k, v in sorted(self.pages.items())},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChapterBlueprint:
        """Deserializes a ChapterBlueprint from a dictionary.

        Args:
            data: Raw dictionary loaded from `chapter_blueprint.json`.

        Returns:
            Constructed ChapterBlueprint instance.
        """
        raw_pages = data.get("pages", {})
        pages_map: Dict[int, PageLayoutBlueprint] = {}
        for k, v in raw_pages.items():
            try:
                pages_map[int(k)] = PageLayoutBlueprint.from_dict(v)
            except (ValueError, TypeError):
                continue
        return cls(
            chapter_name=str(data.get("chapter_name", "untitled")),
            page_count=int(data.get("page_count", 0)),
            engine=str(data.get("engine", "pymupdf_vector")),
            body_font_size=float(data.get("body_font_size", 10.0)),
            body_font_family=str(data.get("body_font_family", "")),
            font_roles=[FontRoleSignature.from_dict(fr) for fr in data.get("font_roles", [])],
            expected_headings=[
                BlueprintHeadingEntry.from_dict(h) for h in data.get("expected_headings", [])
            ],
            expected_tables=[
                BlueprintTableEntry.from_dict(t) for t in data.get("expected_tables", [])
            ],
            pages=pages_map,
        )

    def save_json(self, path: str | Path) -> Path:
        """Writes the ChapterBlueprint to a JSON file on disk.

        Args:
            path: Target file path or chapter directory path.

        Returns:
            Path to the written `chapter_blueprint.json` file.
        """
        target = Path(path)
        if target.is_dir():
            target = target / "chapter_blueprint.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> Optional[ChapterBlueprint]:
        """Loads a ChapterBlueprint from a file or chapter directory if it exists.

        Args:
            path: File path to `chapter_blueprint.json` or chapter directory path.

        Returns:
            Loaded ChapterBlueprint instance, or None if not found or invalid.
        """
        target = Path(path)
        if target.is_dir():
            target = target / "chapter_blueprint.json"
        if not target.exists():
            return None
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return cls.from_dict(data)
        except Exception:
            return None
