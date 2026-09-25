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
        Uses pdfseparate and pdfunite for fast, lossless splitting.
        """
        os.makedirs(os.path.dirname(out_filepath), exist_ok=True)
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
