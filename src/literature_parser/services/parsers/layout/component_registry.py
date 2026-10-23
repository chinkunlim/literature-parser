"""
Layout Component Registry & Modular Micro-Handlers
=================================================
Implements the Component Registry and micro-handler dispatch architecture:
- Standardizes independent, pure Python parsers for each layout component
  (Tables, Figures, Callouts, Margin Glossaries, End-of-Chapter, and Math).
- Dispatches zoned page elements to dedicated micro-handlers.
- Wraps each component extraction in an isolated resilience boundary.
- Emits standardized ComponentResult instances for downstream semantic stitching.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Set

logger = logging.getLogger(__name__)


@dataclass
class ComponentResult:
    """Encapsulates the structured output from a single layout component parser."""
    element_type: str
    identifier: str
    content: str
    page_num: int
    consumed_elements: Set[Any] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComponentHandler(Protocol):
    """Protocol defining the interface for layout component micro-handlers."""

    def can_handle(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determines whether this handler can extract its element from the page.

        Args:
            page_elem: XML root or subtree for the page.
            fonts: Font dictionary mapping font IDs to metadata.
            context: Context dictionary (pw, ph, page_num, pdf_path, style).

        Returns:
            True if element type is present and extractable, False otherwise.
        """
        ...

    def extract(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> List[ComponentResult]:
        """Extracts component results from page elements.

        Args:
            page_elem: XML root or subtree for the page.
            fonts: Font dictionary mapping font IDs to metadata.
            context: Context dictionary (pw, ph, page_num, pdf_path, style).

        Returns:
            List of ComponentResult instances.
        """
        ...


class TableComponentHandler:
    """Micro-handler for extracting page tables and exhibits."""

    def can_handle(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Checks for presence of table or exhibit markers.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary.

        Returns:
            True if tables or exhibits are likely present.
        """
        for t in page_elem.findall("text"):
            txt = "".join(t.itertext()).strip()
            if txt.startswith("Table ") or txt.startswith("Exhibit "):
                return True
        return False

    def extract(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> List[ComponentResult]:
        """Extracts tables and exhibits as ComponentResult instances.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary containing pw, ph, page_num.

        Returns:
            List of extracted table ComponentResults.
        """
        from literature_parser.services.parsers.layout_detector import LayoutDetector

        pw = context.get("pw", 918.0)
        ph = context.get("ph", 1174.0)
        p_num = context.get("page_num", 1)
        results: List[ComponentResult] = []

        try:
            tables, tbl_consumed = LayoutDetector.extract_page_tables(page_elem, fonts, pw, ph)
            for tbl in tables:
                results.append(ComponentResult(
                    element_type="table",
                    identifier=tbl.get("identifier", f"table_{p_num}"),
                    content=tbl.get("markdown", ""),
                    page_num=p_num,
                    consumed_elements=tbl_consumed,
                    metadata={"caption": tbl.get("caption", "")},
                ))
        except Exception as exc:
            logger.warning("TableComponentHandler exception on page %d: %s", p_num, exc)

        return results


class MarginGlossaryHandler:
    """Micro-handler for extracting margin glossaries and sidebar definitions."""

    def can_handle(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determines if margin glossaries are enabled for this document.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary.

        Returns:
            True if margin glossary feature is active.
        """
        style = context.get("style", {})
        return style.get("features", {}).get("margin_glossary", True)

    def extract(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> List[ComponentResult]:
        """Extracts margin glossary terms from the page.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary containing pw, ph, page_num, already_consumed.

        Returns:
            List of extracted glossary ComponentResults.
        """
        from literature_parser.services.parsers.layout_detector import LayoutDetector

        pw = context.get("pw", 918.0)
        ph = context.get("ph", 1174.0)
        p_num = context.get("page_num", 1)
        consumed = context.get("already_consumed", set())
        results: List[ComponentResult] = []

        try:
            glossaries, g_consumed = LayoutDetector.extract_margin_glossaries(
                page_elem, fonts, pw, ph, p_num, already_consumed=consumed
            )
            for g in glossaries:
                term = g.get("term", "")
                defn = g.get("definition", "")
                md_block = f"> 📖 **{term}**: {defn}\n" if defn else f"> 📖 **{term}**\n"
                results.append(ComponentResult(
                    element_type="glossary",
                    identifier=f"glossary_{term}",
                    content=md_block,
                    page_num=p_num,
                    consumed_elements=g_consumed,
                    metadata=g,
                ))
        except Exception as exc:
            logger.warning("MarginGlossaryHandler exception on page %d: %s", p_num, exc)

        return results


class CalloutComponentHandler:
    """Micro-handler for extracting pedagogical callout boxes and alert panels."""

    def can_handle(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Checks for callout box presence.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary.

        Returns:
            True if callouts might be present.
        """
        for t in page_elem.findall("text"):
            txt = "".join(t.itertext()).strip().lower()
            if any(k in txt for k in ["tip", "note", "caution", "case study", "important", "in practice"]):
                return True
        return False

    def extract(self, page_elem: Any, fonts: Dict[str, Any], context: Dict[str, Any]) -> List[ComponentResult]:
        """Extracts callout blocks.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Context dictionary.

        Returns:
            List of extracted callout ComponentResults.
        """
        from literature_parser.services.parsers.layout.callout_parser import (
            extract_callout_boxes,
        )

        p_num = context.get("page_num", 1)
        results: List[ComponentResult] = []

        try:
            callouts, c_consumed = extract_callout_boxes(page_elem, fonts)
            for idx, c in enumerate(callouts, 1):
                results.append(ComponentResult(
                    element_type="callout",
                    identifier=f"callout_{p_num}_{idx}",
                    content=c.get("markdown", ""),
                    page_num=p_num,
                    consumed_elements=c_consumed,
                    metadata=c,
                ))
        except Exception as exc:
            logger.warning("CalloutComponentHandler exception on page %d: %s", p_num, exc)

        return results


class ComponentRegistry:
    """Registry coordinating all layout component micro-handlers."""

    def __init__(self):
        """Initializes default handlers in priority order."""
        self.handlers: List[ComponentHandler] = [
            TableComponentHandler(),
            CalloutComponentHandler(),
            MarginGlossaryHandler(),
        ]

    def register_handler(self, handler: ComponentHandler) -> None:
        """Registers a custom or specialized component micro-handler.

        Args:
            handler: ComponentHandler instance.

        Returns:
            None.
        """
        self.handlers.append(handler)

    def dispatch_page_components(
        self,
        page_elem: Any,
        fonts: Dict[str, Any],
        context: Dict[str, Any],
    ) -> tuple[List[ComponentResult], Set[Any]]:
        """Dispatches page to registered handlers and collects components safely.

        Args:
            page_elem: XML root for the page.
            fonts: Font dictionary.
            context: Execution context dictionary.

        Returns:
            Tuple of (list_of_ComponentResult, all_consumed_elements_set).
        """
        all_results: List[ComponentResult] = []
        all_consumed: Set[Any] = set()
        active_context = dict(context)

        for handler in self.handlers:
            try:
                active_context["already_consumed"] = all_consumed
                if handler.can_handle(page_elem, fonts, active_context):
                    results = handler.extract(page_elem, fonts, active_context)
                    for r in results:
                        all_results.append(r)
                        all_consumed.update(r.consumed_elements)
            except Exception as exc:
                logger.warning("Component dispatch error in %s: %s", type(handler).__name__, exc)

        return all_results, all_consumed
