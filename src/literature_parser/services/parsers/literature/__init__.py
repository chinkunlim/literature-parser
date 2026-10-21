"""Academic Literature Parsers."""

from literature_parser.services.parsers.literature.figure_formatter import FigureFormatter
from literature_parser.services.parsers.literature.imrad_resolver import IMRADResolver
from literature_parser.services.parsers.literature.reference_parser import ReferenceParser

__all__ = [
    "FigureFormatter",
    "IMRADResolver",
    "ReferenceParser",
]
