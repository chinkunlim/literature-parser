"""
Quality Invariant Guard & Circuit Breaker
=========================================
Enforces strict pre-condition and post-condition invariants at every pipeline stage
to prevent corrupted outputs from compounding and cascading downstream.
"""

import os
import re
import subprocess
from pathlib import Path
from book_processor.parsers.math_latex import MathLaTeXConverter


class InvariantViolationError(Exception):
    """Raised when a strict quality invariant is violated."""
    pass


class QualityInvariantGuard:
    """Validates structural and content invariants across the conversion lifecycle."""

    @staticmethod
    def check_pdf_pre_split(pdf_path: str) -> dict:
        """Asserts PDF file is valid, accessible, and has readable pages."""
        p = Path(pdf_path)
        if not p.exists():
            raise InvariantViolationError(f"Pre-split failure: Source file does not exist at '{pdf_path}'")
        if p.stat().st_size == 0:
            raise InvariantViolationError(f"Pre-split failure: Source file '{p.name}' is completely empty (0 bytes).")

        try:
            out = subprocess.check_output(['pdfinfo', str(p)], stderr=subprocess.DEVNULL, timeout=15).decode('utf-8', errors='ignore')
            pages = 0
            for line in out.splitlines():
                if line.startswith('Pages:'):
                    pages = int(line.split(':')[1].strip())
            if pages <= 0:
                raise InvariantViolationError(f"Pre-split failure: '{p.name}' contains 0 readable pages.")
            return {'valid': True, 'pages': pages}
        except Exception as e:
            if isinstance(e, InvariantViolationError):
                raise
            raise InvariantViolationError(f"Pre-split failure: Unable to read PDF header of '{p.name}': {e}")

    @staticmethod
    def check_split_chapter(ch_pdf: str, expected_pages: int = None) -> dict:
        """Asserts chapter PDF was cleanly split, is non-empty, and has expected page count."""
        p = Path(ch_pdf)
        if not p.exists() or p.stat().st_size == 0:
            raise InvariantViolationError(f"Post-split failure: Chapter PDF '{p.name}' was not created or is 0 bytes.")

        try:
            out = subprocess.check_output(['pdfinfo', str(p)], stderr=subprocess.DEVNULL, timeout=15).decode('utf-8', errors='ignore')
            actual_pages = 0
            for line in out.splitlines():
                if line.startswith('Pages:'):
                    actual_pages = int(line.split(':')[1].strip())

            if expected_pages is not None and actual_pages != expected_pages:
                raise InvariantViolationError(
                    f"Post-split failure: Chapter '{p.name}' page count mismatch. Expected: {expected_pages}, Found: {actual_pages}."
                )
            return {'valid': True, 'pages': actual_pages}
        except Exception as e:
            if isinstance(e, InvariantViolationError):
                raise
            raise InvariantViolationError(f"Post-split failure: Error checking chapter '{p.name}': {e}")

    @staticmethod
    def check_page_density(page_text: str, page_images: list, page_num: int) -> dict:
        """Validates that extracted page content is not an anomalous empty drop."""
        clean = page_text.strip()
        if len(clean) == 0 and len(page_images) == 0:
            return {
                'anomaly': True,
                'warning': f"Page {page_num} yielded 0 characters and 0 images (blank page or OCR extraction issue)."
            }
        return {'anomaly': False}

    @staticmethod
    def check_markdown_syntax(md_text: str, chapter_dir: str = None) -> dict:
        """
        Validates Markdown syntax:
        - Math delimiter parity ($ and $$)
        - Formula curly brace balance
        - Local image link existence
        - Absence of unparsed raw XML tags
        """
        issues = []

        # 1. LaTeX math balance check
        math_check = MathLaTeXConverter.check_equation_balance(md_text)
        if not math_check['balanced']:
            issues.extend(math_check['issues'])

        # 2. Raw unparsed XML tags check
        raw_xml_match = re.search(r'<(?:fontspec|page|text)\b[^>]*>', md_text)
        if raw_xml_match:
            issues.append(f"Leaked unparsed XML tag found in Markdown: '{raw_xml_match.group()}'")

        # 3. Local image link check
        if chapter_dir:
            ch_path = Path(chapter_dir)
            img_refs = re.findall(r'!\[.*?\]\((images/[^)]+)\)', md_text)
            for ref in img_refs:
                img_file = ch_path / ref
                if not img_file.exists():
                    issues.append(f"Missing referenced image file on disk: {ref}")

        return {
            'valid': len(issues) == 0,
            'issues': issues
        }


class CircuitBreaker:
    """
    Halts continuous automated pipelines if consecutive chapters fail severe verification,
    preventing error compounding and saving CPU cycles.
    """

    def __init__(self, max_consecutive_failures: int = 2):
        self.max_failures = max_consecutive_failures
        self.consecutive_failures = 0
        self.failure_history = []

    def record_success(self, chapter_name: str):
        self.consecutive_failures = 0
        self.failure_history.append({'chapter': chapter_name, 'passed': True})

    def record_failure(self, chapter_name: str, reason: str):
        self.consecutive_failures += 1
        self.failure_history.append({'chapter': chapter_name, 'passed': False, 'reason': reason})
        if self.consecutive_failures >= self.max_failures:
            return True  # Circuit tripped!
        return False

    def is_tripped(self) -> bool:
        return self.consecutive_failures >= self.max_failures
