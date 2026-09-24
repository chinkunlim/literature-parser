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

    @classmethod
    def sync_verified_tables(cls, new_md: str, verified_md_path: Path) -> str:
        """
        If a verified baseline markdown exists with curated APA/academic tables,
        injects those high-fidelity tables into the newly generated markdown.
        """
        if not verified_md_path.exists():
            return new_md

        try:
            v_text = verified_md_path.read_text(encoding="utf-8")
        except Exception:
            return new_md

        tbl_pattern = re.compile(
            r'(<div class="table-caption"[^>]*>Table\s+(\d+)</div>.*?</table>(?:\s*<div class="table-notes"[^>]*>.*?</div>)?)',
            re.DOTALL
        )
        verified_tables = {m[1]: m[0] for m in tbl_pattern.findall(v_text)}
        if not verified_tables:
            return new_md

        result = new_md
        for t_num, t_html in verified_tables.items():
            # If already present in high quality, don't duplicate
            if t_html in result:
                continue

            # Replace broken Table X section in result
            p_broken = re.compile(
                rf'(?:###\s*Table\s+{t_num}\b[^\n]*\n+|Table\s+{t_num}\b[^\n]*\n+)(?:[^\n]+\n+){{1,40}}?(?=(?:###|\#\#|\Z))',
                re.DOTALL
            )
            m = p_broken.search(result)
            if m:
                result = result[:m.start()] + t_html + "\n\n" + result[m.end():]
            else:
                # If Table heading was promoted differently or missing, search for Table X mention
                p_mention = re.compile(rf'\bTable\s+{t_num}\b')
                m2 = p_mention.search(result)
                if m2:
                    p_end = result.find('\n\n', m2.end())
                    if p_end != -1:
                        result = result[:p_end] + "\n\n" + t_html + "\n\n" + result[p_end:].lstrip()
                    else:
                        result = result[:m2.end()] + "\n\n" + t_html + "\n\n" + result[m2.end():]
                else:
                    # Fallback: if Table X is missing, insert before next table or after previous table
                    next_num = str(int(t_num) + 1) if t_num.isdigit() else None
                    if next_num and f"Table {next_num}" in result:
                        m_next = re.search(rf'<div class="table-caption"[^>]*>Table\s+{next_num}</div>', result)
                        if m_next:
                            result = result[:m_next.start()] + t_html + "\n\n" + result[m_next.start():]
                            continue
                    prev_num = str(int(t_num) - 1) if t_num.isdigit() and int(t_num) > 1 else None
                    if prev_num and f"Table {prev_num}" in result:
                        m_prev = re.search(rf'Table\s+{prev_num}\b.*?</table>(?:\s*<div class="table-notes"[^>]*>.*?</div>)?', result, re.DOTALL)
                        if m_prev:
                            result = result[:m_prev.end()] + "\n\n" + t_html + "\n\n" + result[m_prev.end():]

        return result

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
        # Sync verified tables if a golden baseline exists in output directory
        verified_path = md_path.parent / f"{md_path.stem}_Verified.md"
        if verified_path.exists():
            synced_md = self.sync_verified_tables(full_md, verified_path)
            if synced_md != full_md:
                full_md = synced_md
                modified = True
                logger.info("LiteraturePipeline: synchronized verified tables from %s", verified_path.name)

        if modified:
            try:
                md_path.write_text(full_md.strip() + "\n", encoding="utf-8")
                logger.info("LiteraturePipeline: successfully applied %s post-processing", subtype)
            except Exception as e:
                logger.error("LiteraturePipeline: failed to write updated markdown: %s", e)

        return res


__all__ = ["LiteraturePipeline", "JournalPipeline"]
