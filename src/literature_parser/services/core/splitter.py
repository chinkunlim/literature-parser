"""
PDF Chapter Splitter
====================
Extracts specific page ranges into self-contained chapter PDF files.
"""

import logging
import os
import re
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class PDFSplitter:
    """Extracts and merges page ranges into chapter PDF files."""

    @staticmethod
    def split_chapter(pdf_path: str, start: int, end: int, out_filepath: str) -> None:
        """Extracts pages `start` to `end` from `pdf_path` into `out_filepath` while preserving sub-chapter TOC bookmarks.

        Uses native PyMuPDF for instant in-memory splitting with fallback to pdfseparate/pdfunite (Refs: ADR-011).

        Args:
            pdf_path: Source book PDF path.
            start: 1-indexed start page number.
            end: 1-indexed end page number (inclusive).
            out_filepath: Destination chapter PDF file path.

        Returns:
            None.
        """
        os.makedirs(os.path.dirname(out_filepath), exist_ok=True)

        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            if getattr(doc, "is_encrypted", False):
                try:
                    doc.authenticate("")
                except Exception:
                    pass
            sub_doc = pymupdf.open()
            # 0-based indexing: from_page to to_page (inclusive)
            from_idx = max(0, start - 1)
            to_idx = min(len(doc) - 1, end - 1)
            sub_doc.insert_pdf(doc, from_page=from_idx, to_page=to_idx)

            # Preserve sub-chapter outline bookmarks shifted to local chapter pages (1..N)
            try:
                raw_toc = doc.get_toc(simple=True) or []
                ch_toc = []
                for entry in raw_toc:
                    if len(entry) >= 3:
                        lvl, title, pg = int(entry[0]), str(entry[1]).strip(), int(entry[2])
                        if start <= pg <= end and title:
                            ch_toc.append([lvl, title, pg - start + 1])
                if ch_toc:
                    # Normalize bookmark hierarchy so first entry starts at level 1 and increments by at most +1
                    min_lvl = min(item[0] for item in ch_toc)
                    norm_toc = []
                    prev_lvl = 1
                    for idx_t, (lvl, title, local_pg) in enumerate(ch_toc):
                        shifted_lvl = max(1, lvl - min_lvl + 1)
                        if idx_t == 0:
                            shifted_lvl = 1
                        elif shifted_lvl > prev_lvl + 1:
                            shifted_lvl = prev_lvl + 1
                        norm_toc.append([shifted_lvl, title, local_pg])
                        prev_lvl = shifted_lvl
                    sub_doc.set_toc(norm_toc)
            except Exception as toc_err:
                logger.debug("Preserving sub-chapter TOC skipped for '%s': %s", out_filepath, toc_err)

            sub_doc.save(out_filepath)
            sub_doc.close()
            doc.close()
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning("PyMuPDF split failed for '%s': %s, falling back to CLI", pdf_path, e)

        if start == end:
            subprocess.run(
                ['pdfseparate', '-f', str(start), '-l', str(start), pdf_path, out_filepath],
                stderr=subprocess.DEVNULL, check=True, timeout=60
            )
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                pattern = os.path.join(tmpdir, 'page-%d.pdf')
                subprocess.run(
                    ['pdfseparate', '-f', str(start), '-l', str(end), pdf_path, pattern],
                    stderr=subprocess.DEVNULL, check=True, timeout=120
                )
                page_files = [
                    os.path.join(tmpdir, f) for f in sorted(
                        os.listdir(tmpdir),
                        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0
                    ) if f.endswith('.pdf')
                ]
                subprocess.run(
                    ['pdfunite'] + page_files + [out_filepath],
                    stderr=subprocess.DEVNULL, check=True, timeout=120
                )
