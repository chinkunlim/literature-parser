"""
Strategies Subpackage for Conversion Post-Processing
===================================================
Exports base and domain-specific post-processing strategies:
- PostProcessorStrategy: Abstract base interface
- BookPostProcessor: Strategy for textbooks and front-matter sections
- LiteraturePostProcessor: Strategy for academic papers and journals
"""

from literature_parser.services.converter.strategies.base_strategy import PostProcessorStrategy
from literature_parser.services.converter.strategies.book_strategy import BookPostProcessor
from literature_parser.services.converter.strategies.literature_strategy import LiteraturePostProcessor

__all__ = [
    "PostProcessorStrategy",
    "BookPostProcessor",
    "LiteraturePostProcessor",
]
