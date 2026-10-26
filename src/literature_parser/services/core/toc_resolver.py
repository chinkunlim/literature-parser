"""
TOC Resolver Engine
===================
Hierarchical table-of-contents scanner, alignment engine, and hyperlinking formatter.
Extracts document structure from Markdown chapters, aligns with textbook taxonomy,
and generates both publishing-grade in-book TOC pages and standards-compliant
EPUB 3 multi-level navigation documents (nav.xhtml).
"""

import html
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from literature_parser.services.utils.text_utils import get_primary_chapter_markdown

logger = logging.getLogger("TOCResolver")


@dataclass
class TOCNode:
    """Represents a hierarchical table-of-contents entry.

    Attributes:
        title: Display title for the TOC item.
        level: Hierarchy level ('part', 'chapter', or 'section').
        target_file: Relative path to the destination file.
        anchor_id: Optional HTML anchor fragment for section navigation.
        page_number: Optional physical or virtual page number.
        children: Subordinate items (e.g. sections within a chapter).
    """

    title: str
    level: str  # 'part', 'chapter', 'section'
    target_file: str = ""
    anchor_id: str = ""
    page_number: Optional[str] = None
    children: List["TOCNode"] = field(default_factory=list)


class TOCResolver:
    """Discovers, normalizes, and renders hierarchical table of contents for textbooks."""

    @staticmethod
    def slugify_anchor(text: str) -> str:
        """Converts arbitrary heading text into a valid, deterministic HTML anchor slug.

        Args:
            text: Raw heading text.

        Returns:
            URL-friendly slug (e.g. 'methods-of-knowing').
        """
        # Remove markdown bold/italic/links
        clean = re.sub(r"[*_`\[\]]", "", text)
        clean = re.sub(r"<[^>]+>", "", clean)
        # Convert non-alphanumeric chars to dashes
        clean = re.sub(r"[^\w\s-]", "", clean).strip().lower()
        return re.sub(r"[-\s]+", "-", clean)

    @classmethod
    def scan_book_hierarchy(cls, book_dir: Path) -> List[TOCNode]:
        """Scans all chapter Markdown files in a book directory to extract hierarchical headings.

        Args:
            book_dir: Root directory of the book (containing chapters/ subfolder).

        Returns:
            List of top-level TOCNode items (Parts or Chapters).
        """
        chapters_root = book_dir / "chapters"
        if not chapters_root.exists():
            return []

        # Find all chapter subdirectories sorted by name
        ch_dirs = sorted([d for d in chapters_root.iterdir() if d.is_dir()])
        top_nodes: List[TOCNode] = []

        # Extract Part definitions from 00-07-TOC or raw TOC if available
        part_map = cls._extract_part_structure(chapters_root)

        current_part_node: Optional[TOCNode] = None

        for ch_dir in ch_dirs:
            # Skip TOC itself from being an entry inside its own TOC, but allow Preface/Cover etc
            primary_md = get_primary_chapter_markdown(ch_dir)
            if not primary_md:
                continue
            if ch_dir.name in ("00-07-TOC", "TOC"):
                continue

            content = primary_md.read_text(encoding="utf-8", errors="replace")
            ch_node = cls._parse_chapter_markdown(ch_dir.name, primary_md, content)

            # Check if this chapter belongs under a Part
            part_name = part_map.get(ch_dir.name)
            if part_name:
                if not current_part_node or current_part_node.title != part_name:
                    current_part_node = TOCNode(
                        title=part_name,
                        level="part",
                        children=[],
                    )
                    top_nodes.append(current_part_node)
                current_part_node.children.append(ch_node)
            else:
                current_part_node = None
                top_nodes.append(ch_node)

        return top_nodes

    FRONT_MATTER_TITLES = {
        "00-01-cover": "Cover",
        "00-02-halftitle": "Half Title",
        "00-03-title-page": "Title Page",
        "00-04-publish": "Copyright & Publication Details",
        "00-05-dedication": "Dedication",
        "00-06-brief-contents": "Brief Contents",
        "00-07-toc": "Contents",
        "00-08-about-authors": "About the Authors",
        "00-09-preface": "Preface",
        "appendix": "Appendix",
        "references": "References",
        "glossary": "Glossary",
        "index": "Index",
    }

    @classmethod
    def _extract_part_structure(cls, chapters_root: Path) -> Dict[str, str]:
        """Attempts to infer Part/Unit groupings from 00-07-TOC.md if available.

        Args:
            chapters_root: Path to the chapters/ directory.

        Returns:
            Mapping of chapter directory name to Part title.
        """
        part_map: Dict[str, str] = {}
        toc_candidates = list(chapters_root.glob("*TOC*/*.md"))
        if not toc_candidates:
            return part_map

        raw_text = toc_candidates[0].read_text(encoding="utf-8", errors="replace")
        part_pat = re.compile(
            r"(?i)\bPART\s+([IVXLCDM\d]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)\b[^\n]*"
        )
        ch_pat = re.compile(r"(?i)(?:Chapter\s+(\d+)|####\s+(\d+))\b")

        current_part = ""
        ch_to_part: Dict[int, str] = {}

        for line in raw_text.splitlines():
            # First strip all HTML tags and unescape any nested entities
            clean_line = re.sub(r"<[^>]+>", " ", line)
            while "&" in clean_line:
                unesc = html.unescape(clean_line)
                if unesc == clean_line:
                    break
                clean_line = unesc

            from literature_parser.services.utils.text_utils import clean_shadow_duplicates
            clean_line = clean_shadow_duplicates(clean_line)

            m_part = part_pat.search(clean_line)
            if m_part:
                clean_part = re.sub(r"[*#]", "", m_part.group(0)).strip()
                # Remove trailing numbers like '354' or page numbers
                clean_part = re.sub(r"\s+\d+(?:\s+\d+)*$", "", clean_part).strip()
                clean_part = clean_part.rstrip(":;—–- ")
                if len(clean_part) >= 6:
                    current_part = clean_part
            m_ch = ch_pat.search(clean_line)
            if m_ch and current_part:
                num = int(m_ch.group(1) or m_ch.group(2))
                ch_to_part[num] = current_part

        # Map chapter directory names (e.g. 'Ch01-Introduction...') to Part
        for d in chapters_root.iterdir():
            if not d.is_dir():
                continue
            m_dir_num = re.search(r"(?i)(?:ch(?:apter)?[-_]?(\d+))", d.name)
            if m_dir_num:
                c_num = int(m_dir_num.group(1))
                if c_num in ch_to_part:
                    part_map[d.name] = ch_to_part[c_num]

        return part_map

    @classmethod
    def _parse_chapter_markdown(cls, dir_name: str, md_path: Path, content: str) -> TOCNode:
        """Parses a chapter's Markdown content to extract H1, H2, anchors, and page numbers.

        Args:
            dir_name: Directory name of the chapter.
            md_path: Path to the chapter's primary Markdown file.
            content: Raw Markdown content.

        Returns:
            TOCNode for the chapter containing section children.
        """
        # Determine Chapter Title from first H1 or standard taxonomy, explicit chapter heading, or clean directory name
        dir_clean_key = dir_name.lower().replace("_", "-")
        ch_title: Optional[str] = None

        if dir_clean_key in cls.FRONT_MATTER_TITLES:
            ch_title = cls.FRONT_MATTER_TITLES[dir_clean_key]
        else:
            # 1. Search for explicit Chapter/Part heading at the top of content (within first 8000 chars)
            ch_heading_match = re.search(
                r"(?im)^\s*#{1,3}\s*((?:Chapter\s+\d+|Part\s+[IVXLCDM\d]+|Appendix\s+[A-Z\d]+)[:\s\.\-].*)$",
                content[:8000],
            )
            if not ch_heading_match:
                ch_heading_match = re.search(
                    r"(?im)^\s*#{1,3}\s*(Chapter\s+\d+\b.*)$",
                    content[:8000],
                )

            if ch_heading_match:
                cand = ch_heading_match.group(1).strip()
                ch_title = re.sub(r"\s+", " ", cand)
            else:
                # 2. Check if directory name is a standardized ChXX name
                m_dir = re.match(r"^Ch(\d+)[\-_](.*)$", dir_name, re.IGNORECASE)
                if m_dir:
                    ch_num = int(m_dir.group(1))
                    rest = m_dir.group(2).replace("-", " ").replace("_", " ").strip()
                    ch_title = f"Chapter {ch_num}: {rest}"
                else:
                    # 3. Check for early H1 that is not prose
                    h1_match = re.search(r"(?m)^#\s+([^\n]+)", content[:8000])
                    if h1_match:
                        cand = h1_match.group(1).strip()
                        if len(cand) < 80 and not cand.endswith((".", "?")) and not cand.startswith(("<", "#")):
                            ch_title = cand

                    if not ch_title:
                        ch_title = dir_name.replace("-", " ").replace("_", " ").strip()

        # Find initial page number
        p_match = re.search(r"<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>", content)
        page_num = p_match.group(1) if p_match else None

        ch_node = TOCNode(
            title=ch_title,
            level="chapter",
            target_file=f"../{dir_name}/{md_path.name}",
            anchor_id=cls.slugify_anchor(ch_title),
            page_number=page_num,
        )

        # Extract H2 sections
        lines = content.splitlines()
        current_page = page_num
        for line in lines:
            m_p = re.match(r"^<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>$", line.strip())
            if m_p:
                current_page = m_p.group(1)
                continue

            m_h2 = re.match(r"^##\s+([^\n]+)", line)
            if m_h2:
                sec_title = m_h2.group(1).strip()
                if len(sec_title) < 2 or sec_title.lower() in ("contents", "table of contents"):
                    continue
                sec_slug = cls.slugify_anchor(sec_title)
                ch_node.children.append(
                    TOCNode(
                        title=sec_title,
                        level="section",
                        target_file=f"../{dir_name}/{md_path.name}",
                        anchor_id=sec_slug,
                        page_number=current_page,
                    )
                )

        return ch_node

    @classmethod
    def render_in_book_toc_html(
        cls,
        nodes: List[TOCNode],
        for_epub: bool = False,
        chapter_id_map: Optional[Dict[str, str]] = None,
    ) -> str:
        """Renders publishing-grade hierarchical TOC HTML with dot leaders and hyperlinks.

        Args:
            nodes: Hierarchical tree of TOCNodes.
            for_epub: True if rendering for EPUB (linking to text/chapter_XX.xhtml).
            chapter_id_map: Optional mapping of chapter filename to EPUB chapter filename.

        Returns:
            XHTML-compliant structured Table of Contents string.
        """
        out: List[str] = [
            '<div class="textbook-toc">',
            '  <h2 class="toc-heading">Contents</h2>',
        ]

        def _resolve_link(node: TOCNode) -> str:
            if not node.target_file:
                return "#"
            if for_epub:
                # Target in EPUB is chapter_XX.xhtml#anchor
                clean_name = Path(node.target_file).name
                epub_name = clean_name.replace(".md", ".xhtml")
                if chapter_id_map and clean_name in chapter_id_map:
                    epub_name = chapter_id_map[clean_name]
                if node.anchor_id and node.level == "section":
                    return f"{epub_name}#{node.anchor_id}"
                return epub_name
            else:
                if node.anchor_id and node.level == "section":
                    return f"{node.target_file}#{node.anchor_id}"
                return node.target_file

        from literature_parser.services.utils.text_utils import clean_shadow_duplicates

        for node in nodes:
            if node.level == "part":
                # Ensure part title is pure text without any HTML tags or unescaped entities
                clean_title = re.sub(r"<[^>]+>", " ", node.title)
                while "&" in clean_title:
                    unesc = html.unescape(clean_title)
                    if unesc == clean_title:
                        break
                    clean_title = unesc
                clean_title = clean_shadow_duplicates(clean_title).strip().rstrip(":;—–- ")
                out.append(f'  <div class="toc-part-header">{html.escape(clean_title)}</div>')
                out.append('  <ul class="toc-list">')
                for ch in node.children:
                    cls._render_chapter_li(ch, out, _resolve_link)
                out.append("  </ul>")
            else:
                out.append('  <ul class="toc-list">')
                cls._render_chapter_li(node, out, _resolve_link)
                out.append("  </ul>")

        out.append("</div>")
        return "\n".join(out)

    @classmethod
    def _render_chapter_li(cls, ch: TOCNode, out: List[str], link_fn) -> None:
        """Renders an individual chapter item and any nested sections."""
        from literature_parser.services.utils.text_utils import clean_shadow_duplicates

        link_url = link_fn(ch)
        is_real_page = False
        if ch.page_number:
            p_str = str(ch.page_number).strip()
            if p_str.isdigit() and int(p_str) > 1:
                is_real_page = True
            elif not p_str.isdigit() and p_str != "1":
                is_real_page = True
        page_html = f'<span class="toc-page">{ch.page_number}</span>' if is_real_page else ""
        ch_title = clean_shadow_duplicates(ch.title).strip()
        out.append('    <li class="toc-item toc-chapter">')
        out.append(
            f'      <a href="{html.escape(link_url)}" class="toc-link">'
            f'<span class="toc-title">{html.escape(ch_title)}</span>'
            f'<span class="toc-dots"></span>'
            f"{page_html}</a>"
        )

        if ch.children:
            out.append('      <ul class="toc-sublist">')
            for sec in ch.children:
                sec_url = link_fn(sec)
                sec_real_page = False
                if sec.page_number:
                    sec_p_str = str(sec.page_number).strip()
                    if sec_p_str.isdigit() and int(sec_p_str) > 1:
                        sec_real_page = True
                    elif not sec_p_str.isdigit() and sec_p_str != "1":
                        sec_real_page = True
                sec_page = f'<span class="toc-page">{sec.page_number}</span>' if sec_real_page else ""
                sec_title = clean_shadow_duplicates(sec.title).strip()
                out.append('        <li class="toc-item toc-section">')
                out.append(
                    f'          <a href="{html.escape(sec_url)}" class="toc-link">'
                    f'<span class="toc-title">{html.escape(sec_title)}</span>'
                    f'<span class="toc-dots"></span>'
                    f"{sec_page}</a>"
                )
                out.append("        </li>")
            out.append("      </ul>")
        out.append("    </li>")

    @classmethod
    def render_epub_nav_xhtml(
        cls,
        nodes: List[TOCNode],
        book_title: str,
        chapter_id_map: Optional[Dict[str, str]] = None,
        language: str = "en",
    ) -> str:
        """Generates an EPUB 3 Navigation Document (nav.xhtml) with nested hierarchy.

        Args:
            nodes: Hierarchical tree of TOCNodes.
            book_title: Main book title for the header.
            chapter_id_map: Mapping from markdown filename to EPUB chapter filename.
            language: Document language code (e.g. 'en').

        Returns:
            Well-formed XML EPUB 3 nav.xhtml document string.
        """
        def _resolve_epub_url(node: TOCNode) -> str:
            if not node.target_file:
                return "#"
            clean_name = Path(node.target_file).name
            epub_name = clean_name.replace(".md", ".xhtml")
            if chapter_id_map and clean_name in chapter_id_map:
                epub_name = chapter_id_map[clean_name]
            # In nav.xhtml (at OEBPS/nav.xhtml), chapters are in text/chapter_XX.xhtml
            base_url = f"text/{epub_name}"
            if node.anchor_id and node.level == "section":
                return f"{base_url}#{node.anchor_id}"
            return base_url

        def _render_ol(items: List[TOCNode], indent: int) -> List[str]:
            lines: List[str] = [f"{' ' * indent}<ol>"]
            for item in items:
                url = _resolve_epub_url(item)
                title = html.escape(item.title)
                if item.children:
                    lines.append(f"{' ' * (indent + 2)}<li>")
                    lines.append(f"{' ' * (indent + 4)}<a href=\"{html.escape(url)}\">{title}</a>")
                    lines.extend(_render_ol(item.children, indent + 4))
                    lines.append(f"{' ' * (indent + 2)}</li>")
                else:
                    lines.append(f"{' ' * (indent + 2)}<li><a href=\"{html.escape(url)}\">{title}</a></li>")
            lines.append(f"{' ' * indent}</ol>")
            return lines

        ol_lines = _render_ol(nodes, 4)
        nav_body = "\n".join(ol_lines)

        return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{language}">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(book_title)} - Table of Contents</title>
  <link rel="stylesheet" type="text/css" href="styles/style.css" />
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
{nav_body}
  </nav>
</body>
</html>"""
