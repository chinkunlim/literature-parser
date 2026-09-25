"""
Academic Literature Parsers
===========================
Sub-parsers tailored for academic literature (journals, conference papers,
preprints, and dissertations).
"""

from doc_processor.parsers.literature.figure_formatter import FigureFormatter
from doc_processor.parsers.literature.imrad_resolver import IMRADResolver
from doc_processor.parsers.literature.metadata_extractor import (
    LiteratureMetadataExtractor,
)
from doc_processor.parsers.literature.reference_parser import ReferenceParser

__all__ = [
    "FigureFormatter",
    "IMRADResolver",
    "LiteratureMetadataExtractor",
    "ReferenceParser",
]
