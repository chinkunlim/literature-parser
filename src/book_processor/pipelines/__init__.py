"""
Document Archetype Pipelines
============================
Separated processing pipelines for different document types:
  - BasePipeline: Abstract base lifecycle
  - JournalPipeline: Academic journal articles (two-column flow, IMRAD, references)
  - TextbookPipeline: University textbooks (chapters, TOC, LOs, Anki, EOC)
"""

from book_processor.pipelines.base_pipeline import BasePipeline
from book_processor.pipelines.journal_pipeline import JournalPipeline
from book_processor.pipelines.textbook_pipeline import TextbookPipeline

__all__ = ["BasePipeline", "JournalPipeline", "TextbookPipeline"]
