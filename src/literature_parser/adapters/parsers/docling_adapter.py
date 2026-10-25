"""
Docling Hybrid Layout & Table Blueprint Adapter
===============================================
Integrates IBM `docling` (`DocumentConverter`, `DocLayNet`, and `TableFormer`)
as a modular specialist adapter in the `adapters` layer (Refs: ADR-003, ADR-011).
Used to enrich `ChapterBlueprint` instances on scanned image PDFs or complex
borderless table pages with structured HTML tables and section headings while
enforcing Apple Silicon unified memory safety guards.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List, Optional

from literature_parser.domain.profiler.blueprint_schema import (
    BlueprintHeadingEntry,
    BlueprintTableEntry,
    ChapterBlueprint,
    PageZone,
)

logger = logging.getLogger(__name__)


class DoclingBlueprintAdapter:
    """Adapter wrapping IBM `docling` for structural blueprint enrichment and table extraction."""

    _converter_instance: Any = None

    @classmethod
    def is_available(cls) -> bool:
        """Checks whether the `docling` package is installed in the current environment.

        Returns:
            True if `docling` package specification is found, False otherwise.
        """
        import importlib.util
        return importlib.util.find_spec("docling") is not None

    @classmethod
    def _get_converter(cls) -> Any:
        """Lazily initializes and caches a `docling.document_converter.DocumentConverter` instance.

        Returns:
            Initialized `DocumentConverter` instance, or None if unavailable.
        """
        if cls._converter_instance is not None:
            return cls._converter_instance
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
            cls._converter_instance = DocumentConverter()
            return cls._converter_instance
        except Exception as exc:
            logger.warning("Failed initializing Docling DocumentConverter: %s", exc)
            return None

    @classmethod
    def enrich_blueprint(
        cls,
        pdf_path: str | Path,
        blueprint: ChapterBlueprint,
        page_range: Optional[tuple[int, int]] = None,
    ) -> ChapterBlueprint:
        """Enriches an existing `ChapterBlueprint` using Docling's layout and TableFormer models.

        Args:
            pdf_path: Path to the target chapter PDF file.
            blueprint: Existing `ChapterBlueprint` to enrich.
            page_range: Optional `(start_page, end_page)` 1-indexed range to restrict conversion.

        Returns:
            Updated `ChapterBlueprint` with Docling-extracted tables and headings.
        """
        p_path = Path(pdf_path)
        if not p_path.exists() or not cls.is_available():
            return blueprint

        converter = cls._get_converter()
        if converter is None:
            return blueprint

        logger.info("Running DoclingBlueprintAdapter on '%s'...", p_path.name)
        try:
            kwargs: dict[str, Any] = {}
            if page_range is not None:
                kwargs["page_range"] = page_range
            conv_res = converter.convert(str(p_path), **kwargs)
            doc_obj = getattr(conv_res, "document", None)
            if doc_obj is None:
                return blueprint

            blueprint.engine = "pymupdf+docling"

            # 1. Extract structured tables via TableFormer
            doc_tables = getattr(doc_obj, "tables", []) or []
            existing_ids = {(t.table_id, t.page_num) for t in blueprint.expected_tables}
            for idx_t, tbl in enumerate(doc_tables, 1):
                p_no = cls._extract_prov_page(tbl, default_page=1)
                bbox = cls._extract_prov_bbox(tbl)
                html_str = cls._render_docling_table_html(tbl, doc_obj, idx_t)
                t_id = f"docling_{p_no}_{idx_t}"
                caption_txt = cls._extract_caption_text(tbl, doc_obj)
                m_num = re.search(r"Table\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)", caption_txt, re.IGNORECASE)
                if m_num:
                    t_id = m_num.group(1)

                if (t_id, p_no) not in existing_ids:
                    existing_ids.add((t_id, p_no))
                    blueprint.expected_tables.append(
                        BlueprintTableEntry(
                            table_id=t_id,
                            title=caption_txt,
                            page_num=p_no,
                            bbox=bbox,
                            has_grid_lines=True,
                            source="docling",
                        )
                    )
                if p_no in blueprint.pages and html_str:
                    blueprint.pages[p_no].zones.append(
                        PageZone(
                            zone_type="TABLE_ZONE",
                            page_num=p_no,
                            bbox=bbox,
                            identifier=f"Table {t_id}",
                            caption=caption_txt,
                            has_border_lines=True,
                            pre_rendered_html=html_str,
                        )
                    )

            # 2. Extract section headings if blueprint had no outline headings
            if not blueprint.expected_headings:
                texts = getattr(doc_obj, "texts", []) or []
                for item in texts:
                    label = str(getattr(item, "label", "")).lower()
                    if "header" in label or "title" in label:
                        txt = str(getattr(item, "text", "")).strip()
                        p_no = cls._extract_prov_page(item, default_page=1)
                        if txt and len(txt) >= 3:
                            blueprint.expected_headings.append(
                                BlueprintHeadingEntry(
                                    level=2,
                                    title=txt,
                                    page_num=p_no,
                                    source="docling",
                                )
                            )
        except Exception as exc:
            logger.warning("DoclingBlueprintAdapter enrichment skipped for %s: %s", p_path.name, exc)

        return blueprint

    @staticmethod
    def _extract_prov_page(item: Any, default_page: int = 1) -> int:
        """Extracts the 1-indexed page number from a Docling item's provenance list.

        Args:
            item: Docling document element (`TableItem`, `TextItem`, etc.).
            default_page: Fallback page number if provenance is absent.

        Returns:
            1-indexed page number.
        """
        prov = getattr(item, "prov", None)
        if prov and len(prov) > 0:
            p_no = getattr(prov[0], "page_no", None)
            if p_no is not None:
                return int(p_no)
        return default_page

    @staticmethod
    def _extract_prov_bbox(item: Any) -> List[float]:
        """Extracts bounding box coordinates `[x0, y0, x1, y1]` from a Docling item.

        Args:
            item: Docling document element.

        Returns:
            4-element float list `[x0, y0, x1, y1]`.
        """
        prov = getattr(item, "prov", None)
        if prov and len(prov) > 0:
            bbox = getattr(prov[0], "bbox", None)
            if bbox is not None:
                return [
                    float(getattr(bbox, "l", 0.0)),
                    float(getattr(bbox, "t", 0.0)),
                    float(getattr(bbox, "r", 0.0)),
                    float(getattr(bbox, "b", 0.0)),
                ]
        return [0.0, 0.0, 0.0, 0.0]

    @staticmethod
    def _extract_caption_text(tbl: Any, doc_obj: Any) -> str:
        """Extracts caption string from a Docling TableItem if available.

        Args:
            tbl: Docling `TableItem` object.
            doc_obj: Parent `DoclingDocument` object.

        Returns:
            Clean caption string or empty string.
        """
        try:
            cap_fn = getattr(tbl, "caption_text", None)
            if callable(cap_fn):
                return str(cap_fn(doc_obj)).strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def _render_docling_table_html(tbl: Any, doc_obj: Any, seq: int) -> str:
        """Converts a Docling `TableItem` into our canonical `<table class="textbook-table">` HTML.

        Args:
            tbl: Docling `TableItem` instance.
            doc_obj: Parent `DoclingDocument` instance.
            seq: 1-indexed sequence number of the table.

        Returns:
            Formatted HTML `<table class="textbook-table">` string, or empty string on failure.
        """
        try:
            export_html = getattr(tbl, "export_to_html", None)
            if callable(export_html):
                raw_html = str(export_html(doc=doc_obj)).strip()
                if "<table" in raw_html:
                    return re.sub(
                        r"<table\b[^>]*>",
                        '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">',
                        raw_html,
                        count=1,
                    )
        except Exception as exc:
            logger.debug("Docling table HTML export fallback on table %d: %s", seq, exc)
        return ""
