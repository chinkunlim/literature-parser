"""
PDF Outline & Structure Analyzer
================================
Extracts table of contents from PDF bookmarks or scans page text structures.
"""

import logging
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from literature_parser.services.utils.text_utils import (
    format_appendix_title,
    format_chapter_title,
    sanitize_filename,
)

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Analyzes PDF bookmarks / text to identify chapter sections."""

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        # 1. Native PyMuPDF fast path
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            cnt = len(doc)
            doc.close()
            return cnt
        except Exception:
            pass

        # 2. External CLI pdfinfo fallback
        try:
            out = subprocess.check_output(
                ['pdfinfo', pdf_path],
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode('utf-8', errors='ignore')
            for line in out.splitlines():
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except subprocess.TimeoutExpired:
            logger.warning("pdfinfo timed out (15s) for %s", pdf_path)
        except Exception as e:
            logger.debug("pdfinfo not available for %s: %s, falling back to pure Python", pdf_path, e)

        # 3. Pure Python fallback
        try:
            with open(pdf_path, 'rb') as f:
                content = f.read()
            matches = re.findall(rb'/Type\s*/Pages[^>]*?/Count\s+(\d+)', content, re.DOTALL)
            if matches:
                return max(int(m) for m in matches)
        except Exception as e:
            logger.debug("Pure Python page count failed for %s: %s", pdf_path, e)
        return 0

    @staticmethod
    def get_outline_xml(pdf_path: str):
        # 1. Native PyMuPDF fast path
        try:
            import html
            import pymupdf  # type: ignore
            doc = pymupdf.open(pdf_path)
            toc = doc.get_toc()
            doc.close()
            if toc:
                xml_parts = ['<outline>']
                for lvl, title, page in toc:
                    esc_title = html.escape(str(title))
                    xml_parts.append(f'<item page="{page}">{esc_title}</item>')
                xml_parts.append('</outline>')
                return ET.fromstring(''.join(xml_parts))
        except Exception as e:
            logger.debug("PyMuPDF get_outline_xml failed for %s: %s, falling back to pdftohtml", pdf_path, e)

        # 2. External CLI pdftohtml fallback
        try:
            proc = subprocess.run(
                ['pdftohtml', '-stdout', '-xml', '-nodrm', '-i', '-f', '1', '-l', '1', pdf_path],
                capture_output=True, check=False, timeout=30
            )
            data = proc.stdout
            start = data.find(b'<outline>')
            if start == -1:
                return None
            end = data.rfind(b'</outline>') + len(b'</outline>')
            return ET.fromstring(data[start:end].decode('utf-8', errors='ignore'))
        except subprocess.TimeoutExpired:
            logger.warning("pdftohtml outline timed out (30s) for %s", pdf_path)
            return None
        except Exception as e:
            logger.debug("pdftohtml outline extraction failed for %s: %s", pdf_path, e)
            return None

    @classmethod
    def parse_node(cls, elem, depth=0):
        res = []
        i = 0
        while i < len(elem):
            child = elem[i]
            if child.tag == 'item':
                page = int(child.attrib.get('page', 0))
                title = (child.text or '').strip()
                sub_outline = None
                if i + 1 < len(elem) and elem[i + 1].tag == 'outline':
                    sub_outline = elem[i + 1]
                    i += 1
                res.append((page, title, sub_outline, depth))
            i += 1
        return res

    @classmethod
    def match_front_matter_slug(cls, title: str, taxonomy: list) -> str:
        """Matches a section title against the front matter taxonomy to return its canonical slug.

        Args:
            title: Section title or page header text.
            taxonomy: List of front matter category definitions.

        Returns:
            Canonical slug (e.g. '00-01-Cover', '00-07-TOC') or empty string if unmatched.
        """
        if not title:
            return ""
        t_clean = title.strip()
        for cat in taxonomy:
            patterns = cat.get("regex_patterns", [])
            for pat in patterns:
                if re.search(pat, t_clean):
                    return str(cat.get("canonical_slug", ""))
        return ""

    @classmethod
    def detect_front_matter_from_text(cls, pdf_path: str, end_page: int) -> list:
        """Scans pages 1 to end_page of a PDF to identify standard Front Matter sections.

        Args:
            pdf_path: Path to PDF file.
            end_page: Upper page boundary (typically start of Chapter 1 minus 1).

        Returns:
            List of (page_number, canonical_slug) tuples.
        """
        if end_page < 1:
            return []

        from literature_parser.services.config_manager import ConfigManager
        taxonomy = ConfigManager.load_front_matter_taxonomy()

        results = [(1, "00-01-Cover")]
        seen_slugs = {"00-01-Cover"}

        scan_limit = min(end_page, 35)
        for p in range(1, scan_limit + 1):
            try:
                proc = subprocess.run(
                    ['pdftotext', '-f', str(p), '-l', str(p), pdf_path, '-'],
                    capture_output=True, timeout=10, check=False
                )
                text = proc.stdout.decode('utf-8', errors='ignore').strip()
            except Exception:
                text = ""

            if not text:
                continue

            first_lines = text[:400]
            matched_slug = cls.match_front_matter_slug(first_lines, taxonomy)
            if matched_slug and matched_slug not in seen_slugs and p > results[-1][0]:
                results.append((p, matched_slug))
                seen_slugs.add(matched_slug)

        return results

    @classmethod
    def verify_and_isolate_chapter1(
        cls,
        pdf_path: str,
        targets: list,
        total_pages: int
    ) -> list:
        """Ensures Chapter 1 does not start at Cover/TOC and prepends missing Front Matter.

        Args:
            pdf_path: Path to the target PDF file.
            targets: List of (page_number, section_name) candidate tuples.
            total_pages: Total page count of the PDF document.

        Returns:
            Adjusted and complete list of (page_number, section_name) targets.
        """
        if not targets:
            return targets

        targets.sort(key=lambda x: x[0])
        first_target_page, first_target_name = targets[0]

        # 1. Check if first target is Chapter 1 but placed at page <= 3
        is_ch1 = bool(re.search(r'^(?:00-.*)?Ch(?:apter)?\s*0?1\b', first_target_name, re.IGNORECASE))
        if is_ch1 and first_target_page <= 3:
            real_ch1_page = None
            scan_max = min(40, total_pages)
            for p in range(first_target_page, scan_max + 1):
                try:
                    proc = subprocess.run(
                        ['pdftotext', '-f', str(p), '-l', str(p), pdf_path, '-'],
                        capture_output=True, timeout=10, check=False
                    )
                    text = proc.stdout.decode('utf-8', errors='ignore').strip()
                except Exception:
                    text = ""
                if re.search(r'(?i)\bChapter\s+(?:1|One)\b', text[:300]):
                    real_ch1_page = p
                    break

            if real_ch1_page and real_ch1_page > first_target_page:
                logger.info(
                    "Chapter 1 bookmark was at p.%d; relocated to genuine start at p.%d",
                    first_target_page,
                    real_ch1_page
                )
                targets = [t for t in targets if not re.search(r'^(?:00-.*)?Ch(?:apter)?\s*0?1\b', t[1], re.IGNORECASE)]
                targets.append((real_ch1_page, first_target_name))
                targets.sort(key=lambda x: x[0])
                first_target_page = targets[0][0]

        # 2. If the first target starts at page > 1, fill in Front Matter
        if first_target_page > 1:
            fm_targets = cls.detect_front_matter_from_text(pdf_path, first_target_page - 1)
            fm_targets = [t for t in fm_targets if t[0] < first_target_page]
            targets = fm_targets + targets
            targets.sort(key=lambda x: x[0])

        return targets

    @classmethod
    def get_sections_from_outline(cls, pdf_path: str, total_pages: int):
        root = cls.get_outline_xml(pdf_path)
        if root is None:
            return None

        top_items = cls.parse_node(root)
        if not top_items:
            return None

        flattened = []
        for page, title, sub, depth in top_items:
            t_clean = title.strip()
            if re.search(r'^(Part|Section|Unit)\b', t_clean, re.IGNORECASE) and sub is not None:
                sub_items = cls.parse_node(sub, depth=depth + 1)
                first = True
                for sp, st, ssub, sd in sub_items:
                    if first and sp > page:
                        flattened.append((page, st, ssub))
                    else:
                        flattened.append((sp, st, ssub))
                    first = False
            elif re.search(r'^APPENDICES\b', t_clean, re.IGNORECASE) and sub is not None:
                sub_items = cls.parse_node(sub, depth=depth + 1)
                for sp, st, ssub, sd in sub_items:
                    flattened.append((sp, format_appendix_title(st), ssub))
            else:
                flattened.append((page, t_clean, sub))

        # Match front matter against canonical shared taxonomy
        from literature_parser.services.config_manager import ConfigManager
        taxonomy = ConfigManager.load_front_matter_taxonomy()

        fm_candidates = []
        body_items = []

        for page, title, sub in flattened:
            matched_slug = cls.match_front_matter_slug(title, taxonomy)
            if matched_slug:
                fm_candidates.append((page, matched_slug))
            else:
                body_items.append((page, title))

        fm_candidates.sort(key=lambda x: x[0])
        unique_fm = []
        seen_fm_names = set()
        for p, slug in fm_candidates:
            if slug not in seen_fm_names:
                unique_fm.append((p, slug))
                seen_fm_names.add(slug)

        all_targets = []
        for p, slug in unique_fm:
            all_targets.append((p, slug))

        for p, title in body_items:
            m = re.search(r'^(?:Chapter\s+)?(\d+)[\.\s:\-]+(.*)', title, re.IGNORECASE)
            if m:
                all_targets.append((p, format_chapter_title(title)))
            elif title.lower().startswith('appendix'):
                all_targets.append((p, format_appendix_title(title)))
            else:
                c_name = sanitize_filename(title)
                for std in ['References', 'Index', 'Subject Index', 'Name Index', 'Glossary']:
                    if c_name.lower() == std.lower():
                        c_name = std
                        break
                all_targets.append((p, c_name))

        all_targets.sort(key=lambda x: x[0])

        # Verify Chapter 1 start and isolate Front Matter if missing or misattributed
        all_targets = cls.verify_and_isolate_chapter1(pdf_path, all_targets, total_pages)

        unique_targets = []
        for p, name in all_targets:
            if unique_targets and unique_targets[-1][0] == p:
                continue
            unique_targets.append((p, name))

        if not unique_targets:
            return None

        results = []
        for i in range(len(unique_targets)):
            start_p = unique_targets[i][0]
            end_p = unique_targets[i + 1][0] - 1 if i + 1 < len(unique_targets) else total_pages
            name = unique_targets[i][1]
            if start_p <= end_p and start_p <= total_pages:
                results.append({
                    'start': start_p,
                    'end': min(end_p, total_pages),
                    'name': name
                })

        return results

    @classmethod
    def get_sections_from_text(cls, pdf_path: str, total_pages: int):
        """Fallback for PDFs without outline: scans page headers."""
        try:
            raw_text = subprocess.check_output(
                ['pdftotext', pdf_path, '-'],
                stderr=subprocess.DEVNULL,
                timeout=45
            ).decode('utf-8', errors='ignore')
        except subprocess.TimeoutExpired:
            logger.warning("pdftotext timed out (45s) for %s", pdf_path)
            return None
        except Exception as e:
            logger.debug("pdftotext extraction error for %s: %s", pdf_path, e)
            return None

        pages = raw_text.split('\x0c')
        if len(pages) > 1 and pages[-1] == '':
            pages = pages[:-1]

        # Check document classification first: journals stay single section
        from literature_parser.services.fingerprinting.document_classifier import DocumentClassifier
        p1_text = pages[0] if pages else ""
        classification = DocumentClassifier.classify(total_pages, p1_text)
        if classification["is_journal"]:
            doc_name = sanitize_filename(Path(pdf_path).stem)
            logger.info("Classified as journal article (%s): preserving single section 1..%d", doc_name, total_pages)
            return [{'start': 1, 'end': total_pages, 'name': doc_name}]

        toc_titles = {}
        for p_idx in range(min(20, len(pages))):
            p_text = pages[p_idx]
            if re.search(r'\b(contents|table of contents)\b', p_text[:200], re.IGNORECASE):
                matches = re.findall(r'Chapter\s+(\d+)\s*\n([^\n]+)', p_text, re.IGNORECASE)
                for c_num, c_t in matches:
                    c_num = int(c_num)
                    if c_num not in toc_titles:
                        toc_titles[c_num] = c_t.strip()

        sections = []
        sections.append((1, '00-01-Cover'))

        found_publish = False
        found_content = False
        found_preface = False
        seen_chapters = set()

        for idx, page_txt in enumerate(pages, 1):
            lines = [l.strip() for l in page_txt.splitlines() if l.strip()]
            if not lines:
                continue

            if not found_publish and 1 < idx <= 6:
                if any('copyright' in l.lower() or 'all rights reserved' in l.lower() or 'cengage' in l.lower() or 'isbn' in l.lower() for l in lines):
                    sections.append((idx, '00-04-Publish'))
                    found_publish = True

            if not found_content and idx <= 15:
                if re.search(r'^(contents|brief contents)\b', lines[0], re.IGNORECASE):
                    sections.append((idx, '00-07-TOC'))
                    found_content = True

            if not found_preface and idx <= 25:
                if re.search(r'^preface\b', lines[0], re.IGNORECASE):
                    sections.append((idx, '00-09-Preface'))
                    found_preface = True

            m_ch = re.match(r'^Chapter\s+(\d+)', lines[0], re.IGNORECASE)
            if m_ch:
                ch_num = int(m_ch.group(1))
                if ch_num not in seen_chapters:
                    seen_chapters.add(ch_num)
                    title = toc_titles.get(ch_num, '')
                    if not title:
                        title = lines[1] if len(lines) > 1 else ''
                    title = sanitize_filename(title)
                    name = f"Ch{ch_num:02d}-{title}".strip('-') if title and title != "untitled" else f"Ch{ch_num:02d}"
                    sections.append((idx, name))

            if idx > total_pages * 0.8:
                if re.match(r'^references\b', lines[0], re.IGNORECASE):
                    if not any(s[1] == 'References' for s in sections):
                        sections.append((idx, 'References'))
                elif re.match(r'^index\b', lines[0], re.IGNORECASE):
                    if not any(s[1] == 'Index' for s in sections):
                        sections.append((idx, 'Index'))

        if not seen_chapters:
            doc_name = sanitize_filename(Path(pdf_path).stem)
            return [{'start': 1, 'end': total_pages, 'name': doc_name}]

        sections = cls.verify_and_isolate_chapter1(pdf_path, sections, total_pages)
        sections.sort(key=lambda x: x[0])

        unique_sections = []
        for p, name in sections:
            if unique_sections and unique_sections[-1][0] == p:
                continue
            unique_sections.append((p, name))

        results = []
        for i in range(len(unique_sections)):
            start_p = unique_sections[i][0]
            end_p = unique_sections[i + 1][0] - 1 if i + 1 < len(unique_sections) else total_pages
            name = unique_sections[i][1]
            if start_p <= end_p and start_p <= total_pages:
                results.append({
                    'start': start_p,
                    'end': min(end_p, total_pages),
                    'name': name
                })

        return results

    @classmethod
    def get_sections(cls, pdf_path: str):
        total_pages = cls.get_page_count(pdf_path)
        if total_pages == 0:
            return None, 0

        sections = cls.get_sections_from_outline(pdf_path, total_pages)
        if sections and len(sections) >= 3:
            return sections, total_pages

        sections = cls.get_sections_from_text(pdf_path, total_pages)
        return sections, total_pages
