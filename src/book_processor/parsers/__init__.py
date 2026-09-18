"""
Parsers Module: Digital PDF, Scanned PDF, EPUB, and LaTeX Math
==============================================================
"""

from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.parsers.epub_parser import EPUBProcessor
from book_processor.parsers.digital_pdf import DigitalPDFParser
from book_processor.parsers.scanned_pdf import ScannedPDFParser

__all__ = [
    "MathLaTeXConverter",
    "EPUBProcessor",
    "DigitalPDFParser",
    "ScannedPDFParser"
]
