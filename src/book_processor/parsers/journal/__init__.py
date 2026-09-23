"""
Journal Specialized Parsers
===========================
Academic journal-specific structural parsers:
  - ReferenceParser: Hanging-indent academic citations parser
  - IMRADResolver: Universal IMRAD structure & emergent section resolver
"""

from book_processor.parsers.journal.reference_parser import ReferenceParser
from book_processor.parsers.journal.imrad_resolver import IMRADResolver

__all__ = ["ReferenceParser", "IMRADResolver"]
