"""
Converter Package (literature_parser.services.converter)
========================================================
High-fidelity domain conversion engine transforming PDF documents
into structured Markdown based on canonical DocumentProfile schemas.

Exports:
- MarkdownConversionService: Core transformation engine
- ConversionOptions: Tunable configuration for TOC, images, cropping, CSS
- ConversionResult: Standardized conversion output contract
- CroppedElement: Cropped figure and table metadata container
- ElementCropper: Utility cropping figures and tables with captions and equal margins
- PostProcessorStrategy: Abstract post-processing strategy interface
- BookPostProcessor: Post-processor for textbooks and front-matter sections
- LiteraturePostProcessor: Post-processor for academic literature
"""

from literature_parser.services.converter.element_cropper import ElementCropper
from literature_parser.services.converter.markdown_converter import MarkdownConversionService
from literature_parser.services.converter.models import (
    ConversionOptions,
    ConversionResult,
    CroppedElement,
)
from literature_parser.services.converter.strategies.base_strategy import PostProcessorStrategy
from literature_parser.services.converter.strategies.book_strategy import BookPostProcessor
from literature_parser.services.converter.strategies.literature_strategy import LiteraturePostProcessor

__all__ = [
    "MarkdownConversionService",
    "ConversionOptions",
    "ConversionResult",
    "CroppedElement",
    "ElementCropper",
    "PostProcessorStrategy",
    "BookPostProcessor",
    "LiteraturePostProcessor",
]
