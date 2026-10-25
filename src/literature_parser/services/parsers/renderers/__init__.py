"""
Modular Semantic Block Renderers Package
========================================
Provides five specialized, single-responsibility block renderers driven by
`ChapterBlueprint` (Refs: ADR-011):
- HeadingBlockRenderer
- TableZoneRenderer
- CalloutAndExhibitRenderer
- GlossaryAndEOCRenderer
- ProseAndMathRenderer
- BlockRendererRegistry
"""

from literature_parser.services.parsers.renderers.block_renderers import (
    BlockRendererRegistry,
    CalloutAndExhibitRenderer,
    GlossaryAndEOCRenderer,
    HeadingBlockRenderer,
    ProseAndMathRenderer,
    TableZoneRenderer,
)

__all__ = [
    "HeadingBlockRenderer",
    "TableZoneRenderer",
    "CalloutAndExhibitRenderer",
    "GlossaryAndEOCRenderer",
    "ProseAndMathRenderer",
    "BlockRendererRegistry",
]
