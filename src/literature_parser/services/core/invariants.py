"""
Quality Invariant Guard & Circuit Breaker
=========================================
Enforces strict pre-condition and post-condition invariants at every pipeline stage
to prevent corrupted outputs from compounding and cascading downstream.
"""

import re
import subprocess
from pathlib import Path

from literature_parser.services.parsers.math_latex import MathLaTeXConverter


class InvariantViolationError(Exception):
    """Raised when a strict quality invariant is violated."""


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

        pages = 0
        # 1. Native PyMuPDF fast path (in-memory, highly reliable)
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(str(p))
            pages = len(doc)
            doc.close()
        except Exception:
            pass

        # 2. External CLI pdfinfo fallback
        if pages <= 0:
            try:
                out = subprocess.check_output(
                    ['pdfinfo', str(p)], stderr=subprocess.DEVNULL, timeout=15
                ).decode('utf-8', errors='ignore')
                for line in out.splitlines():
                    if line.startswith('Pages:'):
                        pages = int(line.split(':')[1].strip())
            except Exception:
                pass

        # 3. Pure Python binary header regex fallback
        if pages <= 0:
            try:
                with open(p, 'rb') as f:
                    content = f.read()
                matches = re.findall(rb'/Type\s*/Pages[^>]*?/Count\s+(\d+)', content, re.DOTALL)
                if matches:
                    pages = max(int(m) for m in matches)
            except Exception as e:
                raise InvariantViolationError(f"Pre-split failure: Unable to read PDF header of '{p.name}': {e}")

        if pages <= 0:
            raise InvariantViolationError(f"Pre-split failure: '{p.name}' contains 0 readable pages.")
        return {'valid': True, 'pages': pages}

    @staticmethod
    def check_split_chapter(ch_pdf: str, expected_pages: int = None) -> dict:
        """Asserts chapter PDF was cleanly split, is non-empty, and has expected page count."""
        p = Path(ch_pdf)
        if not p.exists() or p.stat().st_size == 0:
            raise InvariantViolationError(f"Post-split failure: Chapter PDF '{p.name}' was not created or is 0 bytes.")

        actual_pages = 0
        # 1. Native PyMuPDF fast path
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(str(p))
            actual_pages = len(doc)
            doc.close()
        except Exception:
            pass

        # 2. External CLI pdfinfo fallback
        if actual_pages <= 0:
            try:
                out = subprocess.check_output(
                    ['pdfinfo', str(p)], stderr=subprocess.DEVNULL, timeout=15
                ).decode('utf-8', errors='ignore')
                for line in out.splitlines():
                    if line.startswith('Pages:'):
                        actual_pages = int(line.split(':')[1].strip())
            except Exception:
                pass

        # 3. Pure Python binary header regex fallback
        if actual_pages <= 0:
            try:
                with open(p, 'rb') as f:
                    content = f.read()
                matches = re.findall(rb'/Type\s*/Pages[^>]*?/Count\s+(\d+)', content, re.DOTALL)
                if matches:
                    actual_pages = max(int(m) for m in matches)
            except Exception as e:
                raise InvariantViolationError(f"Post-split failure: Unable to read PDF header of '{p.name}': {e}")

        if actual_pages <= 0:
            raise InvariantViolationError(f"Post-split failure: Chapter '{p.name}' contains 0 readable pages.")

        if expected_pages is not None and actual_pages != expected_pages:
            raise InvariantViolationError(
                f"Post-split failure: Chapter '{p.name}' page count mismatch. Expected: {expected_pages}, Found: {actual_pages}."
            )
        return {'valid': True, 'pages': actual_pages}

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

    @staticmethod
    def verify_hard_invariants(md_text: str, is_literature: bool = True, file_path: str = "") -> dict:
        """
        Zero-Tolerance Hard Invariant Gate (防呆門禁: 避免有錯還報對).
        Validates core non-negotiable structural and typographic invariants:
        1. Non-empty content (>= 500 bytes)
        2. Valid H1 title (not empty, not truncated, not a watermark)
        3. Abstract presence (for literature)
        4. References section presence (for literature)
        5. LaTeX delimiter parity and currency safety
        6. Absence of raw OCR floating number arrays
        7. Absence of orphan single-line page numbers

        If ANY invariant is violated, 'valid' is strictly False.
        """
        violations = []
        clean = md_text.strip()

        # 1. Non-empty check
        if len(clean) < 500:
            violations.append(f"INV_NON_EMPTY: File content is suspiciously small ({len(clean)} chars < 500 chars).")

        # 2. Title check
        m_title = re.search(r'(?m)^#\s+([^\n]+)', md_text)
        if not m_title or not m_title.group(1).strip():
            violations.append("INV_TITLE: Missing or empty document title (# Title).")
        else:
            t = m_title.group(1).strip()
            watermarks = ["NIH Public Access", "Author Manuscript", "ARTICLE IN PRESS", "RESEARCH ARTICLE"]
            if any(t.lower() == wm.lower() for wm in watermarks):
                violations.append(f"INV_TITLE: Document title was corrupted by publisher watermark ('{t}').")

        # 3. Abstract check (literature only)
        if is_literature:
            has_abs = bool(re.search(r'(?m)^##\s+Abstract\b', md_text, re.IGNORECASE)) or bool(re.search(r'(?m)^>\s+\*\*Abstract\*\*', md_text, re.IGNORECASE)) or bool(re.search(r'(?m)^>\s+.*?[A-Za-z]{30,}', md_text))
            if not has_abs:
                violations.append("INV_ABSTRACT: Academic literature is missing Abstract section (## Abstract or > blockquote).")

        # 4. References check (literature only, for papers > 150 lines)
        if is_literature and len(md_text.splitlines()) > 150:
            has_refs = bool(re.search(r'(?m)^##\s+(?:References|Literature Cited|Bibliography)\b', md_text, re.IGNORECASE))
            if not has_refs:
                violations.append("INV_REFERENCES: Academic literature is missing References section (## References).")

        # 5. LaTeX and currency delimiter parity
        math_check = MathLaTeXConverter.check_equation_balance(md_text)
        if not math_check['balanced']:
            violations.extend([f"INV_LATEX_BALANCED: {iss}" for iss in math_check['issues']])

        # 6. Absence of raw OCR tables leaking into body
        raw_ocr_leak = re.search(r'(?m)^Table\s+\d+\s*\n+(?:[ \t\d\.\-\—\*]+\n+){3,}', md_text)
        if raw_ocr_leak:
            violations.append("INV_NO_OCR_TABLE_LEAK: Unparsed raw OCR numerical matrix leaking into body text.")

        # 7. Absence of orphan page numbers
        lines = md_text.splitlines()
        orphan_pns = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if re.match(r'^\d{1,4}$', s) and not s.startswith("0") and len(s) <= 4:
                orphan_pns.append((idx, s))
        if orphan_pns:
            violations.append(f"INV_NO_ORPHAN_PAGE_NUMS: Found {len(orphan_pns)} orphan page number line(s) (e.g. line {orphan_pns[0][0]}: '{orphan_pns[0][1]}').")

        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'violation_count': len(violations),
        }

    @staticmethod
    def assert_hard_invariants(md_text: str, is_literature: bool = True, file_path: str = "") -> None:
        """Raises InvariantViolationError if any hard invariant is violated."""
        res = QualityInvariantGuard.verify_hard_invariants(md_text, is_literature=is_literature, file_path=file_path)
        if not res['valid']:
            viol_str = "; ".join(res['violations'])
            raise InvariantViolationError(f"Hard Invariant Gate Violation: {viol_str}")


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
