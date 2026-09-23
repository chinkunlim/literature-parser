"""
Document Classifier
===================
Determines whether an input document is an academic journal article, a full
multi-chapter textbook, lecture slides, or a standalone technical report.
"""

import re
from typing import Dict, Any


class DocumentClassifier:
    """Classifies documents into archetypes: 'journal_article', 'textbook', or 'standalone'."""

    @classmethod
    def classify(cls, total_pages: int, sample_text: str, toc_entries: list = None) -> Dict[str, Any]:
        """
        Analyzes page count, table of contents entries, and page 1 textual cues to classify the document.

        Returns:
            Dict containing:
                - doc_type: 'journal_article' | 'textbook' | 'monograph'
                - is_journal: bool
                - confidence: float (0.0 to 1.0)
                - reason: str
        """
        sample_text_lower = sample_text.lower() if sample_text else ""

        # Journal indicators
        has_doi = bool(re.search(r'\b10\.\d{4,5}/', sample_text or ""))
        has_abstract = bool(re.search(r'\babstract\b', sample_text_lower))
        has_keywords = bool(re.search(r'\bkeywords\b', sample_text_lower))
        has_volume = bool(re.search(r'\bvol(?:ume)?\.?\s*\d+', sample_text_lower))
        has_journal_name = bool(re.search(r'\bjournal of\b', sample_text_lower))

        # Textbook indicators
        has_chapters = bool(toc_entries and len(toc_entries) >= 3)
        has_large_page_count = total_pages > 45

        # Decision Logic:
        # If <= 40 pages and has DOI or Abstract or Journal naming -> High confidence journal article
        if total_pages <= 40 and (has_doi or has_abstract or (has_volume and has_journal_name)):
            confidence = 0.95 if (has_doi and has_abstract) else 0.85
            return {
                "doc_type": "journal_article",
                "is_journal": True,
                "confidence": confidence,
                "reason": f"Page count ({total_pages} <= 40) with academic indicators (DOI={has_doi}, Abstract={has_abstract})"
            }

        # If has many chapters or page count is large (> 60 pages) -> Textbook
        if has_large_page_count or has_chapters:
            return {
                "doc_type": "textbook",
                "is_journal": False,
                "confidence": 0.90 if has_chapters else 0.75,
                "reason": f"Page count ({total_pages} pages) or multi-chapter structure ({len(toc_entries or [])} chapters)"
            }

        # Borderline cases: short non-journal or single monograph
        if has_abstract or has_doi:
            return {
                "doc_type": "journal_article",
                "is_journal": True,
                "confidence": 0.70,
                "reason": "Borderline page count but contains academic article structure"
            }

        return {
            "doc_type": "standalone",
            "is_journal": False,
            "confidence": 0.60,
            "reason": "Standard single document"
        }

    @classmethod
    def is_journal_article(cls, pdf_path: str = None) -> bool:
        """Convenience method to check if a file is an academic journal article."""
        if not pdf_path:
            return False
        p_lower = str(pdf_path).lower()
        if re.search(r'\b(?:10\.\d{4,5}|[a-z]{2,8}-\d{4}-\d{4,6}|\d{4}-\d{5}-\d{3})\b', p_lower):
            return True
        return False
