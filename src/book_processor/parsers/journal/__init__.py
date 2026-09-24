"""
Journal Parsers (Legacy Compatibility Shim)
===========================================
This module is kept for backward compatibility. New code should import from:
  book_processor.parsers.literature

Both paths resolve to the same implementations.
"""

# Re-export from the canonical location
from book_processor.parsers.literature.reference_parser import ReferenceParser
from book_processor.parsers.literature.imrad_resolver import IMRADResolver

__all__ = ["ReferenceParser", "IMRADResolver"]
