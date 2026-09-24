"""
Academic Literature Parsers
===========================
Sub-parsers tailored for academic literature (journals, conference papers,
preprints, and dissertations).
"""

from book_processor.parsers.literature.reference_parser import ReferenceParser
from book_processor.parsers.literature.imrad_resolver import IMRADResolver
from book_processor.parsers.literature.metadata_extractor import LiteratureMetadataExtractor
from book_processor.parsers.literature.figure_formatter import FigureFormatter

__all__ = [
    "ReferenceParser",
    "IMRADResolver",
    "LiteratureMetadataExtractor",
    "FigureFormatter",
]
