"""
PDF Outline & Structure Analyzer
================================
Extracts table of contents from PDF bookmarks or scans page text structures.
"""

import logging
import re
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from book_processor.utils.text_utils import sanitize_filename, format_chapter_title, format_appendix_title

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Analyzes PDF bookmarks / text to identify chapter sections."""

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
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
            logger.debug("Error getting page count for %s: %s", pdf_path, e)
        return 0

    @staticmethod
    def get_outline_xml(pdf_path: str):
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
            if re.search(r'^(Part|Section|Unit)\b', t_clean, re.I) and sub is not None:
                sub_items = cls.parse_node(sub, depth=depth + 1)
                first = True
                for sp, st, ssub, sd in sub_items:
                    if first and sp > page:
                        flattened.append((page, st, ssub))
                    else:
                        flattened.append((sp, st, ssub))
                    first = False
            elif re.search(r'^APPENDICES\b', t_clean, re.I) and sub is not None:
                sub_items = cls.parse_node(sub, depth=depth + 1)
                for sp, st, ssub, sd in sub_items:
                    flattened.append((sp, format_appendix_title(st), ssub))
            else:
                flattened.append((page, t_clean, sub))

        fm_candidates = []
        body_items = []

        for page, title, sub in flattened:
            tl = title.lower()
            if re.search(r'\bcover\b', tl):
                fm_candidates.append((page, 'Cover'))
            elif re.search(r'\b(title|copyright|publish)\b', tl):
                fm_candidates.append((page, 'Publish'))
            elif re.search(r'\babout (?:the )?authors?\b', tl):
                fm_candidates.append((page, 'About Authors'))
            elif re.search(r'\b(content|contents|brief contents)\b', tl):
                fm_candidates.append((page, 'Content'))
            elif re.search(r'\bcritical incident', tl):
                fm_candidates.append((page, 'Critical Incidents'))
            elif re.search(r'\b(preface|to the student|acknowledg|foreword|dedication)\b', tl):
                fm_candidates.append((page, 'Preface'))
            else:
                body_items.append((page, title))

        fm_candidates.sort(key=lambda x: x[0])
        unique_fm = []
        seen_fm_names = set()
        for p, name in fm_candidates:
            if name not in seen_fm_names:
                unique_fm.append((p, name))
                seen_fm_names.add(name)

        all_targets = []
        for fm_idx, (p, name) in enumerate(unique_fm):
            prefix = f"00-{fm_idx}"
            all_targets.append((p, f"{prefix}{name}"))

        for p, title in body_items:
            m = re.search(r'^(?:Chapter\s+)?(\d+)[\.\s:\-]+(.*)', title, re.I)
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
        from book_processor.fingerprinting.document_classifier import DocumentClassifier
        p1_text = pages[0] if pages else ""
        classification = DocumentClassifier.classify(total_pages, p1_text)
        if classification["is_journal"]:
            doc_name = sanitize_filename(Path(pdf_path).stem)
            logger.info("Classified as journal article (%s): preserving single section 1..%d", doc_name, total_pages)
            return [{'start': 1, 'end': total_pages, 'name': doc_name}]

        toc_titles = {}
        for p_idx in range(min(20, len(pages))):
            p_text = pages[p_idx]
            if re.search(r'\b(contents|table of contents)\b', p_text[:200], re.I):
                matches = re.findall(r'Chapter\s+(\d+)\s*\n([^\n]+)', p_text, re.I)
                for c_num, c_t in matches:
                    c_num = int(c_num)
                    if c_num not in toc_titles:
                        toc_titles[c_num] = c_t.strip()

        sections = []
        sections.append((1, '00-0Cover'))

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
                    sections.append((idx, '00-1Publish'))
                    found_publish = True

            if not found_content and idx <= 15:
                if re.search(r'^(contents|brief contents)\b', lines[0], re.I):
                    sections.append((idx, '00-2 Content'))
                    found_content = True

            if not found_preface and idx <= 25:
                if re.search(r'^preface\b', lines[0], re.I):
                    sections.append((idx, '00-3 Preface'))
                    found_preface = True

            m_ch = re.match(r'^Chapter\s+(\d+)', lines[0], re.I)
            if m_ch:
                ch_num = int(m_ch.group(1))
                if ch_num not in seen_chapters:
                    seen_chapters.add(ch_num)
                    title = toc_titles.get(ch_num, '')
                    if not title:
                        title = lines[1] if len(lines) > 1 else ''
                    title = sanitize_filename(title)
                    name = f"Ch{ch_num:02d} {title}".strip()
                    sections.append((idx, name))

            if idx > total_pages * 0.8:
                if re.match(r'^references\b', lines[0], re.I):
                    if not any(s[1] == 'References' for s in sections):
                        sections.append((idx, 'References'))
                elif re.match(r'^index\b', lines[0], re.I):
                    if not any(s[1] == 'Index' for s in sections):
                        sections.append((idx, 'Index'))

        if not seen_chapters:
            doc_name = sanitize_filename(Path(pdf_path).stem)
            return [{'start': 1, 'end': total_pages, 'name': doc_name}]

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
