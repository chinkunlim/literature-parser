"""
Exporter Module
===============
Provides multi-format document conversion and packaging capabilities:
- EpubExporter: Generates standards-compliant EPUB 3 digital books from Markdown
"""

from literature_parser.services.exporter.epub_exporter import EpubExporter

__all__ = ["EpubExporter"]
