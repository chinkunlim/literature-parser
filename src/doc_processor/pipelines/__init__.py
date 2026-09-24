"""
Document Archetype Pipelines
============================
Separated processing pipelines for different document types:
  - BasePipeline: Abstract base lifecycle
  - LiteraturePipeline: Academic literature (two-column flow, IMRAD, references)
  - TextbookPipeline: University textbooks (chapters, TOC, LOs, Anki, EOC)
"""

from doc_processor.pipelines.base_pipeline import BasePipeline
from doc_processor.pipelines.literature_pipeline import LiteraturePipeline
from doc_processor.pipelines.textbook_pipeline import TextbookPipeline

__all__ = ["BasePipeline", "LiteraturePipeline", "TextbookPipeline"]

