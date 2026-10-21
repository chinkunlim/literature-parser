"""
Parsers Module: Digital PDF, Scanned PDF, EPUB, and LaTeX Math
==============================================================
"""

from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.epub_parser import EPUBProcessor
from literature_parser.services.parsers.math_latex import MathLaTeXConverter
from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser

__all__ = [
    "DigitalPDFParser",
    "EPUBProcessor",
    "MathLaTeXConverter",
    "ScannedPDFParser"
]
