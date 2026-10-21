"""
Document Classifier
===================
Determines whether an input document is an academic journal article, a full
multi-chapter textbook, lecture slides, or a standalone technical report.
"""

import logging
from pathlib import Path
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Classifies documents into archetypes: 'journal_article', 'textbook', or 'standalone'."""

    @classmethod
    def classify(
        cls,
        total_pages: int,
        sample_text: str,
        toc_entries: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Analyzes page count, table of contents entries, and page 1 textual cues to classify the document.

        Args:
            total_pages: Total number of pages in the document.
            sample_text: Sample text extracted from the first pages of the document.
            toc_entries: Optional list of table-of-contents entries.

        Returns:
            Dict containing:
                - doc_type: 'journal_article' | 'textbook' | 'standalone'
                - is_journal: bool
                - confidence: float (0.0 to 1.0)
                - reason: str
        """
        sample_text_lower = sample_text.lower() if sample_text else ""

        # Journal indicators
        has_doi = bool(re.search(r"\b10\.\d{4,5}/", sample_text or ""))
        has_abstract = bool(re.search(r"\babstract\b", sample_text_lower))
        has_volume = bool(re.search(r"\bvol(?:ume)?\.?\s*\d+", sample_text_lower))
        has_journal_name = bool(re.search(r"\bjournal of\b", sample_text_lower))

        # Textbook indicators
        has_chapters = bool(toc_entries and len(toc_entries) >= 3)
        has_large_page_count = total_pages > 45

        # Decision Logic:
        # If <= 40 pages and has DOI or Abstract or Journal naming -> High confidence journal article
        if total_pages <= 40 and (has_doi or has_abstract or (has_volume and has_journal_name)):
            confidence = 0.95 if (has_doi and has_abstract) else 0.85
            return {
                "doc_type": "journal_article",
                "is_literature": True,
                "is_journal": True,
                "confidence": confidence,
                "reason": (
                    f"Page count ({total_pages} <= 40) with academic indicators "
                    f"(DOI={has_doi}, Abstract={has_abstract})"
                ),
            }

        # If has many chapters or page count is large (> 60 pages) -> Textbook
        if has_large_page_count or has_chapters:
            return {
                "doc_type": "textbook",
                "is_journal": False,
                "confidence": 0.90 if has_chapters else 0.75,
                "reason": (
                    f"Page count ({total_pages} pages) or multi-chapter structure "
                    f"({len(toc_entries or [])} chapters)"
                ),
            }

        # Borderline cases: short non-journal or single monograph
        if has_abstract or has_doi:
            return {
                "doc_type": "journal_article",
                "is_journal": True,
                "confidence": 0.70,
                "reason": "Borderline page count but contains academic article structure",
            }

        return {
            "doc_type": "standalone",
            "is_journal": False,
            "confidence": 0.60,
            "reason": "Standard single document",
        }

    @classmethod
    def _classify_pdf_on_disk(cls, pdf_file: Path) -> bool | None:
        """Inspects an existing PDF on disk via pdfinfo and pdftotext.

        Args:
            pdf_file: Path to an existing PDF file on disk.

        Returns:
            Boolean indicating if it is a journal article, or None if inspection failed.
        """
        try:
            logger.debug("Running pdfinfo on %s", pdf_file.name)
            info_out = subprocess.check_output(
                ["pdfinfo", str(pdf_file)],
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).decode("utf-8", errors="ignore")
            pages = 0
            for line in info_out.splitlines():
                if line.startswith("Pages:"):
                    pages = int(line.split(":")[1].strip())
                    break
            if pages <= 0:
                return None
            txt = subprocess.check_output(
                ["pdftotext", "-f", "1", "-l", str(min(2, pages)), str(pdf_file), "-"],
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).decode("utf-8", errors="ignore")
            res = cls.classify(pages, txt)
            return bool(res.get("is_journal", False))
        except Exception:
            logger.debug("Failed to inspect PDF on disk for classification: %s", pdf_file.name, exc_info=True)
            return None

    @classmethod
    def is_journal_article(cls, pdf_path: str | Path | None = None) -> bool:
        """Convenience method to check if a file is an academic journal article.

        Args:
            pdf_path: Path or filename string of the PDF to inspect.

        Returns:
            True if the document is classified as an academic journal article, False otherwise.
        """
        if not pdf_path:
            return False
        p_str = str(pdf_path)
        p_lower = p_str.lower()

        # Robust check if file exists on disk
        p = Path(pdf_path)
        if p.exists() and p.is_file() and p.suffix.lower() == ".pdf":
            disk_res = cls._classify_pdf_on_disk(p)
            if disk_res is not None:
                return disk_res

        return bool(
            re.search(
                r"\b(?:10\.\d{4,5}|[a-z]{2,8}-\d{4}-\d{4,6}|\d{4}-\d{5}-\d{3}|journal(?:\s+of)?|adolescence)\b",
                p_lower,
            )
        )

    @classmethod
    def is_literature(cls, pdf_path: str | Path | None = None) -> bool:
        """Convenience method to check if a file is an academic literature article.

        Args:
            pdf_path: Path or filename string of the PDF to inspect.

        Returns:
            True if the document is classified as academic literature, False otherwise.
        """
        return cls.is_journal_article(pdf_path)
