"""
Semantic Stitcher & Contextual Artifact Anchoring
=================================================
Stitches parsed prose paragraphs and component results into cohesive Markdown:
- Registers tables and figures into an ArtifactRegistry.
- Anchors floating artifacts strictly after complete paragraphs or upon citation.
- Prevents sentence fragmentation caused by floating blocks.
- Flushes uncited orphan elements at section breaks (Zero-Drop Guarantee).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from literature_parser.services.converter.layout_frame import (
    ArtifactRegistry,
    DocumentLayoutFrame,
    SemanticAnchorEmitter,
)
from literature_parser.services.parsers.layout.component_registry import ComponentResult

logger = logging.getLogger(__name__)


class SemanticStitcher:
    """Coordinates prose flow and layout components into clean, structured Markdown."""

    @classmethod
    def stitch(
        cls,
        prose_markdown: str,
        components: List[ComponentResult],
        gloss_placement: str = "inline",
    ) -> str:
        """Stitches prose and component blocks into cohesive Markdown.

        Args:
            prose_markdown: Primary linear Markdown text from body paragraphs and headings.
            components: List of ComponentResult instances (tables, figures, callouts, glossaries).
            gloss_placement: Where to place margin glossaries ('inline' vs 'chapter_end').

        Returns:
            Integrated, semantically anchored Markdown string.
        """
        registry = ArtifactRegistry()
        inline_callouts: List[ComponentResult] = []
        glossary_items: List[ComponentResult] = []

        for comp in components:
            if comp.element_type == "table":
                clean_id = re.sub(r"^(?:table_?)", "", comp.identifier, flags=re.IGNORECASE).replace("_", ".")
                registry.register_table(clean_id, comp.content)
            elif comp.element_type == "figure":
                clean_id = re.sub(r"^(?:figure_?|fig_?)", "", comp.identifier, flags=re.IGNORECASE).replace("_", ".")
                registry.register_figure(clean_id, comp.content)
            elif comp.element_type == "callout":
                inline_callouts.append(comp)
            elif comp.element_type == "glossary":
                glossary_items.append(comp)

        emitter = SemanticAnchorEmitter(registry=registry)
        anchored_md = emitter.process_text(prose_markdown, flush_orphans=True)

        # Inject inline callouts at paragraph boundaries if present
        if inline_callouts:
            blocks = re.split(r"\n\n+", anchored_md)
            new_blocks = []
            for b in blocks:
                new_blocks.append(b)
                # If block is a heading or end of section, mount one callout if pending
                if inline_callouts and b.startswith("#"):
                    callout = inline_callouts.pop(0)
                    new_blocks.append(callout.content.strip())
            # Append any remaining callouts
            for callout in inline_callouts:
                new_blocks.append(callout.content.strip())
            anchored_md = "\n\n".join(new_blocks).strip()

        # Inject inline glossaries if enabled
        if gloss_placement == "inline" and glossary_items:
            gloss_blocks = [g.content.strip() for g in glossary_items if g.content.strip()]
            if gloss_blocks:
                anchored_md = f"{anchored_md}\n\n" + "\n\n".join(gloss_blocks)

        return anchored_md
