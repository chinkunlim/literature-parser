"""Document Archetype Pipelines.

Separated processing pipelines for different document types:
  - BasePipeline: Abstract base lifecycle
  - TextbookPipeline: University textbooks (chapters, TOC, LOs, Anki, EOC)
"""

from literature_parser.services.pipelines.base_pipeline import BasePipeline
from literature_parser.services.pipelines.textbook_pipeline import TextbookPipeline

__all__ = ["BasePipeline", "TextbookPipeline"]

