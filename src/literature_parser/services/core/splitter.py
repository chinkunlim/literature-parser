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
    def split_chapter(pdf_path: str, start: int, end: int, out_filepath: str):
        """
        Extracts pages start to end from pdf_path into out_filepath.
        Uses native PyMuPDF for instant in-memory splitting with fallback to pdfseparate/pdfunite.
        """
        os.makedirs(os.path.dirname(out_filepath), exist_ok=True)

        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            sub_doc = pymupdf.open()
            # 0-based indexing: from_page to to_page (inclusive)
            from_idx = max(0, start - 1)
            to_idx = min(len(doc) - 1, end - 1)
            sub_doc.insert_pdf(doc, from_page=from_idx, to_page=to_idx)
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
