"""
Academic Journal Article Pipeline (JournalPipeline)
===================================================
Legacy backward-compatibility shim. Automatically redirects to LiteraturePipeline.
"""

from book_processor.pipelines.literature_pipeline import LiteraturePipeline as JournalPipeline

__all__ = ["JournalPipeline"]
