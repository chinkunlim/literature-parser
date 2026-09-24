"""
Academic Literature Pipeline (LiteraturePipeline)
=================================================
Dedicated, modular processing pipeline for academic literature (journal articles,
conference papers, preprints, dissertations). Standardized superset of JournalPipeline
with domain-specific subtype discovery, IEEE boilerplate cleanup, Index Terms formatting,
and preprint advisory alert injection.
"""

import re
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from book_processor.pipelines.journal_pipeline import JournalPipeline

logger = logging.getLogger(__name__)


class LiteraturePipeline(JournalPipeline):
    """
    Advanced academic literature pipeline with domain customization:
    - Subtypes: journal | ieee | dissertation | preprint
    - Automatic IEEE Author Biography & license watermark removal
    - IEEE/ACM Index Terms to Obsidian markdown tag blocks
    - Preprint peer-review caution alert callouts
    """

    SUBTYPE_JOURNAL = "journal"
    SUBTYPE_IEEE = "ieee"
    SUBTYPE_DISSERTATION = "dissertation"
    SUBTYPE_PREPRINT = "preprint"

    # -------------------------------------------------------------------------
    # Subtype Detection
    # -------------------------------------------------------------------------
    @classmethod
    def detect_subtype(cls, md_head: str, total_pages: int = 0, publisher: Optional[str] = None) -> str:
        """Determines literature subtype based on publisher metadata, length, and text signatures."""
        pub_lower = (publisher or "").lower()
        if "ieee" in pub_lower:
            return cls.SUBTYPE_IEEE

        head_sample = md_head[:3000]

        # Preprint signals
        if re.search(r'\barXiv:\s*\d{4}\.\d+', head_sample, re.I) or re.search(r'\b(?:bioRxiv|medRxiv)\b', head_sample, re.I):
            return cls.SUBTYPE_PREPRINT
        if re.search(r'\b(?:Submitted to|Under review at|Preprint)\b', head_sample, re.I):
            return cls.SUBTYPE_PREPRINT


        # IEEE textual signal (if publisher was not explicitly recognized)
        if re.search(r'IEEE\s+(?:Transactions|Journal|Access|Conferences?)\b', head_sample, re.I):
            return cls.SUBTYPE_IEEE

        # Dissertation signals (length + explicit chapters)
        if total_pages > 45 and re.search(r'^\s*#+\s*(?:Chapter|CHAPTER)\s+[0-9IVXLCDM]+', md_head, re.M):
            return cls.SUBTYPE_DISSERTATION

        return cls.SUBTYPE_JOURNAL

    # -------------------------------------------------------------------------
    # Domain Cleaners & Transformers
    # -------------------------------------------------------------------------
    @classmethod
    def clean_ieee_boilerplate(cls, md: str) -> str:
        """Strips Author Biography sections and IEEE licensing disclaimers."""
        # 1. Remove Author Biography / Biographies sections until the end or next major header
        cleaned = re.sub(
            r'#+\s*(?:Author\s+Biograph(?:y|ies)|About the Authors?|Biographies)\b.*?(?=\n#+\s+[^\n]+|\Z)',
            '',
            md,
            flags=re.S | re.I
        )

        # 2. Remove IEEE license and access restrictions
        cleaned = re.sub(
            r'Authorized licensed use limited to:.*?Restrictions apply\.',
            '',
            cleaned,
            flags=re.S
        )

        # 3. Remove standalone DOI footers for IEEE
        cleaned = re.sub(
            r'(?:Digital Object Identifier|DOI):\s*10\.1109/[A-Za-z0-9\.\-]+',
            '',
            cleaned,
            flags=re.I
        )

        return cleaned.strip()

    @classmethod
    def format_index_terms(cls, md: str) -> str:
        """Transforms IEEE/ACM Index Terms into an Obsidian-friendly tag block."""
        match = re.search(r'(?:#+\s*)?Index Terms[—–\-:]\s*(.+?)(?=\n\n|\n#+|\Z)', md, re.I | re.S)
        if not match:
            return md

        raw_terms = match.group(1).strip()
        # Split terms by comma or semicolon
        terms = [t.strip().strip('.') for t in re.split(r'[,;]', raw_terms) if t.strip()]
        if not terms:
            return md

        tag_pills = " · ".join(f"`{term}`" for term in terms)
        callout = (
            f"\n\n> [!NOTE] **🏷️ 關鍵領域詞 (Index Terms)**\n"
            f"> {tag_pills}\n\n"
        )

        return md[:match.start()] + callout + md[match.end():]

    # -------------------------------------------------------------------------
    # Pipeline Execution with Domain Post-Processing
    # -------------------------------------------------------------------------
    def process(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """Runs the standard JournalPipeline, then applies domain literature adaptations."""
        res = super().process(pdf_path, **kwargs)

        md_file_str = res.get("markdown_file")
        if not md_file_str or not Path(md_file_str).exists():
            return res

        md_path = Path(md_file_str)
        try:
            full_md = md_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("LiteraturePipeline: could not read markdown %s: %s", md_path, e)
            return res

        # Retrieve page count and publisher from result if available
        v_res = res.get("verification", {})
        total_pages = v_res.get("expected_pages", 0)

        # Subtype detection
        subtype = self.detect_subtype(full_md, total_pages=total_pages)
        res["literature_subtype"] = subtype

        modified = False

        if subtype == self.SUBTYPE_IEEE:
            cleaned = self.clean_ieee_boilerplate(full_md)
            cleaned = self.format_index_terms(cleaned)
            if cleaned != full_md:
                full_md = cleaned
                modified = True

        elif subtype == self.SUBTYPE_PREPRINT:
            warning_callout = (
                "> [!WARNING] **學術預印本提要 (Preprint Document)**\n"
                "> 本文為未經同行評審 (Non-Peer-Reviewed) 之學術預印本，數據與結論可能與最終出版物有所出入。\n\n"
            )
            if "學術預印本提要" not in full_md:
                # Insert warning right after any injected CSS or at the top
                css_end = full_md.find("</style>")
                if css_end != -1:
                    insert_pos = css_end + len("</style>")
                    full_md = full_md[:insert_pos] + "\n\n" + warning_callout + full_md[insert_pos:].lstrip()
                else:
                    full_md = warning_callout + full_md
                modified = True

        if modified:
            try:
                md_path.write_text(full_md.strip() + "\n", encoding="utf-8")
                logger.info("LiteraturePipeline: successfully applied %s post-processing", subtype)
            except Exception as e:
                logger.error("LiteraturePipeline: failed to write updated markdown: %s", e)

        return res


__all__ = ["LiteraturePipeline", "JournalPipeline"]
