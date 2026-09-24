"""
Literature Specialized Parsers
==============================
Academic literature-specific structural parsers:
  - ReferenceParser: Hanging-indent academic citations parser
  - IMRADResolver: Universal IMRAD structure & emergent section resolver
"""

from book_processor.parsers.literature.reference_parser import ReferenceParser
from book_processor.parsers.literature.imrad_resolver import IMRADResolver

__all__ = ["ReferenceParser", "IMRADResolver"]
