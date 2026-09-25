"""
Layout Parsers Subpackage
=========================
Modular layout and structure parsers for textbooks and academic papers.
"""

from doc_processor.parsers.layout.callout_parser import CalloutParser
from doc_processor.parsers.layout.concept_map_parser import ConceptMapParser
from doc_processor.parsers.layout.eoc_parser import EndOfChapterParser
from doc_processor.parsers.layout.list_parser import ListParser
from doc_processor.parsers.layout.margin_parser import MarginParser
from doc_processor.parsers.layout.table_llm_fixer import TableLLMFixer
from doc_processor.parsers.layout.table_parser import TableParser
from doc_processor.parsers.layout.vector_figure_parser import VectorFigureParser

__all__ = [
    "CalloutParser",
    "ConceptMapParser",
    "EndOfChapterParser",
    "ListParser",
    "MarginParser",
    "TableLLMFixer",
    "TableParser",
    "VectorFigureParser",
]
