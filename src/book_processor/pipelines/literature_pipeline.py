"""
Academic Literature Pipeline (LiteraturePipeline)
=================================================
Dedicated, modular processing pipeline for academic literature (journal articles,
conference papers, preprints, dissertations). Standardized superset and alias of JournalPipeline.
"""

from book_processor.pipelines.journal_pipeline import JournalPipeline, ACADEMIC_JOURNAL_CSS


class LiteraturePipeline(JournalPipeline):
    """
    Pipeline for converting academic literature (journal articles, conference papers, preprints)
    into high-fidelity, dual-column parsed, IMRAD-structured Markdown.
    """
    pass


__all__ = ["LiteraturePipeline", "JournalPipeline", "ACADEMIC_JOURNAL_CSS"]
