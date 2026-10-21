"""
Parsers Module: Digital PDF, Scanned PDF, EPUB, and LaTeX Math
==============================================================
"""

from doc_processor.parsers.digital_pdf import DigitalPDFParser
from doc_processor.parsers.epub_parser import EPUBProcessor
from doc_processor.parsers.math_latex import MathLaTeXConverter
from doc_processor.parsers.scanned_pdf import ScannedPDFParser

__all__ = [
    "DigitalPDFParser",
    "EPUBProcessor",
    "MathLaTeXConverter",
    "ScannedPDFParser"
]
