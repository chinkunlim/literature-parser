"""
EPUB 3 Exporter Engine
======================
Converts processed Markdown books and academic literature into standards-compliant
EPUB 3 digital publications:
- Hybrid adaptive execution: Pandoc (preferred) with pure-Python fallback
- EPUB 3 valid container packaging (uncompressed mimetype, container.xml, content.opf)
- Dual navigation: EPUB 3 nav.xhtml and EPUB 2 toc.ncx backward compatibility
- LaTeX math formula conversion to MathML (<math>)
- Multi-chapter textbook unification with hierarchical spine ordering
- High-resolution image bundling and responsive e-reader typography
"""

import datetime
import html
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from doc_processor.exporter.epub_styles import get_epub_css

logger = logging.getLogger("EpubExporter")


class LaTeXToMathML:
    """Lightweight, deterministic converter for LaTeX math formulas into EPUB 3 MathML."""

    GREEK_MAP = {
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
        r"\epsilon": "ε", r"\eta": "η", r"\theta": "θ", r"\mu": "μ",
        r"\nu": "ν", r"\xi": "ξ", r"\pi": "π", r"\rho": "ρ",
        r"\sigma": "σ", r"\tau": "τ", r"\phi": "φ", r"\chi": "χ",
        r"\psi": "ψ", r"\omega": "ω", r"\Delta": "Δ", r"\Sigma": "Σ",
    }

    SYMBOL_MAP = {
        r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥",
        r"\ne": "≠", r"\neq": "≠", r"\approx": "≈", r"\pm": "±",
        r"\times": "×", r"\div": "÷", r"\cdot": "·", r"\infty": "∞",
        r"\rightarrow": "→", r"\leftarrow": "←", r"\Rightarrow": "⇒",
    }

    @classmethod
    def convert_formula(cls, formula: str, display_block: bool = False) -> str:
        """Transforms inline or display LaTeX math into standard MathML."""
        clean = formula.strip()
        if not clean:
            return ""

        # Normalize common LaTeX tokens
        for token, sym in cls.GREEK_MAP.items():
            clean = clean.replace(token, sym)
        for token, sym in cls.SYMBOL_MAP.items():
            clean = clean.replace(token, sym)

        # Fractions: \frac{num}{den} -> <mfrac><mrow>num</mrow><mrow>den</mrow></mfrac>
        def _frac_sub(m):
            return f"<mfrac><mrow>{m.group(1)}</mrow><mrow>{m.group(2)}</mrow></mfrac>"
        clean = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', _frac_sub, clean)

        # Superscript: a^{b} or a^b
        clean = re.sub(r'([A-Za-z0-9α-ω\)]+)\^\{([^{}]+)\}', r'<msup><mrow>\1</mrow><mrow>\2</mrow></msup>', clean)
        clean = re.sub(r'([A-Za-z0-9α-ω\)]+)\^([A-Za-z0-9])', r'<msup><mrow>\1</mrow><mrow>\2</mrow></msup>', clean)

        # Subscript: a_{b} or a_b
        clean = re.sub(r'([A-Za-z0-9α-ω\)]+)_\{([^{}]+)\}', r'<msub><mrow>\1</mrow><mrow>\2</mrow></msub>', clean)
        clean = re.sub(r'([A-Za-z0-9α-ω\)]+)_([A-Za-z0-9])', r'<msub><mrow>\1</mrow><mrow>\2</mrow></msub>', clean)

        # Remove remaining LaTeX styling tokens (\text, \mathit, \mathbf)
        clean = re.sub(r'\\(?:text|mathit|mathbf|mathrm)\{([^{}]+)\}', r'\1', clean)
        clean = clean.replace(r"\,", " ").replace(r"\;", " ").replace(r"\quad", "  ")

        attr = ' display="block"' if display_block else ''
        return f'<math xmlns="http://www.w3.org/1998/Math/MathML"{attr}><mrow>{clean}</mrow></math>'

    @classmethod
    def process_markdown_math(cls, text: str) -> str:
        """Finds all $$block$$ and $inline$ formulas and replaces with MathML."""
        # 1. Protect currency like $15.50, $100 before math matching
        text = re.sub(r'(?<!\\)\$(\d+(?:\.\d+)?)', r'&#36;\1', text)

        # 2. Block math: $$ ... $$
        def _replace_block(m):
            return "\n\n" + cls.convert_formula(m.group(1), display_block=True) + "\n\n"
        text = re.sub(r'\$\$(.+?)\$\$', _replace_block, text, flags=re.DOTALL)

        # 3. Inline math: $ ... $ (strictly requiring non-space edges)
        def _replace_inline(m):
            content = m.group(1)
            return cls.convert_formula(content, display_block=False)
        text = re.sub(r'(?<![\w\\])\$(?!\s)([^\$\n]+?)(?<!\s)(?<!\\)\$(?!\w)', _replace_inline, text)
        return text


class MarkdownToXHTML:
    """Translates sanitized Markdown into XHTML5 suitable for EPUB 3 content docs."""

    @classmethod
    def clean_markdown_for_epub(cls, md: str) -> Tuple[str, Optional[str]]:
        """Strips in-line <style> blocks and extracts primary title."""
        # Extract title from first H1
        title_match = re.search(r'(?m)^#\s+([^\n]+)', md)
        title = title_match.group(1).strip() if title_match else None

        # Strip inline <style>...</style> tags
        cleaned = re.sub(r'<style\b[^>]*>.*?</style>', '', md, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip(), title

    VOID_TAGS = {"br", "hr", "img", "col", "input", "meta", "link"}

    @classmethod
    def to_xhtml_body(cls, md: str) -> str:
        """Converts Markdown text into well-formed XHTML5 body content."""
        # 1. MathML conversion
        content = LaTeXToMathML.process_markdown_math(md)

        # 2. Block replacements with HTML tag-stack tracking
        lines = content.splitlines()
        out_lines = []
        stack = []
        in_codeblock = False
        in_list = False
        in_blockquote = False

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                if in_list and not stack:
                    out_lines.append("</ul>")
                    in_list = False
                if in_blockquote and not stack:
                    out_lines.append("</blockquote>")
                    in_blockquote = False
                continue

            # Code block
            if trimmed.startswith("```"):
                if in_codeblock:
                    out_lines.append("</code></pre>")
                    in_codeblock = False
                else:
                    out_lines.append("<pre><code>")
                    in_codeblock = True
                continue
            if in_codeblock:
                out_lines.append(html.escape(line))
                continue

            # Track HTML tag nesting
            was_in_html = bool(stack)
            for m in re.finditer(r'<(/?)(\w+)(?:\s+[^>]*)?(/?)>', line):
                is_closing = m.group(1) == "/"
                tag = m.group(2).lower()
                is_self_closing = m.group(3) == "/" or tag in cls.VOID_TAGS
                if is_self_closing:
                    continue
                if is_closing:
                    if stack and stack[-1] == tag:
                        stack.pop()
                    elif tag in stack:
                        while stack and stack[-1] != tag:
                            stack.pop()
                        if stack:
                            stack.pop()
                else:
                    stack.append(tag)
            now_in_html = bool(stack)
            is_html = was_in_html or now_in_html or (trimmed.startswith("<") and trimmed.endswith(">"))

            if is_html:
                if in_list:
                    out_lines.append("</ul>")
                    in_list = False
                if in_blockquote:
                    out_lines.append("</blockquote>")
                    in_blockquote = False

                # Inside <details> list items like "- [Text](#link)"
                if trimmed.startswith(("- ", "* ")):
                    item_text = trimmed[2:].strip()
                    out_lines.append(f"<li>{cls._format_inline(item_text)}</li>")
                else:
                    out_lines.append(line)
                continue

            # Blockquote
            if trimmed.startswith(">"):
                if not in_blockquote:
                    out_lines.append("<blockquote>")
                    in_blockquote = True
                b_text = trimmed.lstrip(">").strip()
                out_lines.append(f"<p>{cls._format_inline(b_text)}</p>")
                continue
            elif in_blockquote:
                out_lines.append("</blockquote>")
                in_blockquote = False

            # Unordered list
            if trimmed.startswith(("- ", "* ")):
                if not in_list:
                    out_lines.append("<ul>")
                    in_list = True
                item_text = trimmed[2:].strip()
                out_lines.append(f"<li>{cls._format_inline(item_text)}</li>")
                continue
            elif in_list:
                out_lines.append("</ul>")
                in_list = False

            # Header (# to ######)
            header_match = re.match(r'^(#{1,6})\s+(.*)', trimmed)
            if header_match:
                level = len(header_match.group(1))
                h_text = cls._format_inline(header_match.group(2).strip())
                out_lines.append(f"<h{level}>{h_text}</h{level}>")
                continue

            # Markdown images: ![alt](src)
            img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', trimmed)
            if img_match:
                alt = html.escape(img_match.group(1))
                src = img_match.group(2).strip()
                out_lines.append(f'<figure><img src="{src}" alt="{alt}" /><figcaption>{alt}</figcaption></figure>')
                continue

            # Standard paragraph
            out_lines.append(f"<p>{cls._format_inline(trimmed)}</p>")

        if in_list:
            out_lines.append("</ul>")
        if in_blockquote:
            out_lines.append("</blockquote>")
        if in_codeblock:
            out_lines.append("</code></pre>")

        body = "\n".join(out_lines)

        # XML / XHTML compliance normalization
        # 1. Boolean attributes
        body = re.sub(r'<(details)\s+open>', r'<\1 open="open">', body)

        # 2. Void elements self-closing
        def _fix_img(m):
            tag = m.group(0)
            tag = " ".join(tag.split())
            if not tag.endswith("/>"):
                tag = tag[:-1].strip() + " />"
            return tag
        body = re.sub(r'<img\b[^>]*>', _fix_img, body, flags=re.DOTALL)
        body = re.sub(r'<(br|hr|col|input)(?:\s+([^/>]*))?>', r'<\1 \2/>', body)
        body = re.sub(r'\s+/>', ' />', body)

        # 3. Strip HTML comments (e.g. <!-- Page 4 -->)
        body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)

        # 4. Naked ampersands
        body = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', body)

        # 5. Non-XML named entities
        body = re.sub(
            r'&([a-zA-Z]+);',
            lambda m: html.unescape(m.group(0)) if m.group(1) not in ('amp', 'lt', 'gt', 'quot', 'apos') else m.group(0),
            body
        )

        return body

    @classmethod
    def _format_inline(cls, text: str) -> str:
        """Applies inline formatting: bold, italic, code, links, and escapes."""
        # Already handled math formulas shouldn't be escaped
        math_placeholders = []
        def _hide_math(m):
            idx = len(math_placeholders)
            math_placeholders.append(m.group(0))
            return f"__MATH_PH_{idx}__"
        text = re.sub(r'<math\b.*?</math>', _hide_math, text, flags=re.DOTALL)

        # Bold & Italic
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)

        # Inline code
        text = re.sub(r'`([^`]+)`', lambda m: f"<code>{html.escape(m.group(1))}</code>", text)

        # Markdown links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        # Restore MathML
        for idx, m_str in enumerate(math_placeholders):
            text = text.replace(f"__MATH_PH_{idx}__", m_str)

        return text


class PurePythonEpubBuilder:
    """
    Zero-dependency, pure-Python EPUB 3 zip packager compliant with IDPF specifications.
    Generates uncompressed mimetype, META-INF/container.xml, OEBPS package.opf,
    nav.xhtml, toc.ncx, and embeds images and CSS.
    """

    def __init__(self, book_title: str, author: str = "Unknown Author", language: str = "en"):
        self.book_title = book_title
        self.author = author
        self.language = language
        self.book_id = f"urn:uuid:{uuid.uuid4()}"
        self.chapters: List[Dict[str, str]] = []  # [{title, filename, xhtml_content}]
        self.images: Dict[str, Path] = {}  # {epub_relative_path: source_abs_path}

    def add_chapter(self, title: str, filename: str, xhtml_body: str):
        """Adds an XHTML document to the book spine."""
        full_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{self.language}">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="../styles/style.css" />
</head>
<body>
{xhtml_body}
</body>
</html>"""
        self.chapters.append({
            "id": f"sec_{len(self.chapters) + 1}",
            "title": title,
            "filename": filename,
            "content": full_xhtml,
        })

    def add_image(self, relative_path: str, source_path: Path):
        """Registers an image file to bundle inside OEBPS/images/."""
        clean_rel = relative_path.replace("\\", "/").lstrip("/")
        if not clean_rel.startswith("images/"):
            clean_rel = f"images/{Path(clean_rel).name}"
        self.images[clean_rel] = source_path

    def build(self, output_epub_path: Path):
        """Packages all registered elements into a valid EPUB 3 zip archive."""
        output_epub_path.parent.mkdir(parents=True, exist_ok=True)
        css_content = get_epub_css()
        mod_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with zipfile.ZipFile(output_epub_path, "w") as zf:
            # 1. mimetype (MUST be first entry, uncompressed ZIP_STORED)
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)

            # 3. OEBPS/styles/style.css
            zf.writestr("OEBPS/styles/style.css", css_content, compress_type=zipfile.ZIP_DEFLATED)

            # 4. Images
            for epub_rel, src_path in self.images.items():
                if src_path.exists():
                    zf.write(src_path, f"OEBPS/{epub_rel}", compress_type=zipfile.ZIP_DEFLATED)

            # 5. XHTML Chapters
            for ch in self.chapters:
                zf.writestr(f"OEBPS/text/{ch['filename']}", ch["content"], compress_type=zipfile.ZIP_DEFLATED)

            # 6. OEBPS/nav.xhtml (EPUB 3 Navigation Document)
            nav_items = "\n".join(
                f'      <li><a href="text/{ch["filename"]}">{html.escape(ch["title"])}</a></li>'
                for ch in self.chapters
            )
            nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{self.language}">
<head>
  <meta charset="utf-8" />
  <title>Table of Contents</title>
  <link rel="stylesheet" type="text/css" href="styles/style.css" />
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{nav_items}
    </ol>
  </nav>
</body>
</html>"""
            zf.writestr("OEBPS/nav.xhtml", nav_xhtml, compress_type=zipfile.ZIP_DEFLATED)

            # 7. OEBPS/toc.ncx (EPUB 2 NCX for backward compatibility)
            ncx_points = []
            for idx, ch in enumerate(self.chapters, 1):
                ncx_points.append(f"""    <navPoint id="navPoint-{idx}" playOrder="{idx}">
      <navLabel><text>{html.escape(ch['title'])}</text></navLabel>
      <content src="text/{ch['filename']}"/>
    </navPoint>""")
            ncx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{self.book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(self.book_title)}</text></docTitle>
  <navMap>
{chr(10).join(ncx_points)}
  </navMap>
</ncx>"""
            zf.writestr("OEBPS/toc.ncx", ncx_content, compress_type=zipfile.ZIP_DEFLATED)

            # 8. OEBPS/content.opf (Package Manifest & Spine)
            manifest_items = [
                '    <item id="style" href="styles/style.css" media-type="text/css"/>',
                '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
            ]
            for ch in self.chapters:
                props = ' properties="mathml"' if "<math" in ch["content"] else ""
                manifest_items.append(
                    f'    <item id="{ch["id"]}" href="text/{ch["filename"]}" media-type="application/xhtml+xml"{props}/>'
                )

            for idx, epub_rel in enumerate(self.images.keys(), 1):
                ext = Path(epub_rel).suffix.lower()
                mtype, _ = mimetypes.guess_type(epub_rel)
                mtype = mtype or ("image/png" if ext == ".png" else "image/jpeg")
                manifest_items.append(
                    f'    <item id="img_{idx}" href="{epub_rel}" media-type="{mtype}"/>'
                )

            spine_items = [f'    <itemref idref="{ch["id"]}"/>' for ch in self.chapters]

            content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{self.book_id}</dc:identifier>
    <dc:title>{html.escape(self.book_title)}</dc:title>
    <dc:creator>{html.escape(self.author)}</dc:creator>
    <dc:language>{self.language}</dc:language>
    <meta property="dcterms:modified">{mod_time}</meta>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
</package>"""
            zf.writestr("OEBPS/content.opf", content_opf, compress_type=zipfile.ZIP_DEFLATED)

        logger.info("Successfully packaged EPUB 3 with pure-Python engine: %s", output_epub_path)
        return output_epub_path


class EpubExporter:
    """
    Main controller for converting books and literature into high-fidelity EPUB 3 archives.
    Auto-detects Pandoc; falls back to pure-Python engine if Pandoc is absent.
    """

    @classmethod
    def is_pandoc_available(cls) -> bool:
        """Checks if pandoc CLI is installed and accessible in system PATH."""
        return shutil.which("pandoc") is not None

    @classmethod
    def export_literature(
        cls,
        doc_dir_or_md: Path,
        output_epub_path: Optional[Path] = None,
        engine: str = "auto"
    ) -> Path:
        """Converts an academic literature Markdown document into a standalone EPUB 3 file."""
        doc_dir_or_md = Path(doc_dir_or_md).resolve()
        if doc_dir_or_md.is_file() and doc_dir_or_md.suffix.lower() == ".md":
            md_path = doc_dir_or_md
            doc_dir = md_path.parent
        elif doc_dir_or_md.is_dir():
            doc_dir = doc_dir_or_md
            md_candidates = [
                f for f in doc_dir.glob("*.md")
                if not f.name.endswith("_Verified.md") and f.name != "audit_report.md"
            ]
            if not md_candidates:
                raise FileNotFoundError(f"No primary Markdown file found in literature directory: {doc_dir}")
            md_path = sorted(md_candidates)[0]
        else:
            raise FileNotFoundError(f"Literature path does not exist: {doc_dir_or_md}")

        doc_name = md_path.stem
        if output_epub_path is None:
            output_epub_path = doc_dir / f"{doc_name}.epub"
        else:
            output_epub_path = Path(output_epub_path).resolve()

        print(f"\n📖 [EPUB EXPORTER] 轉換學術文獻: {doc_name} ➔ {output_epub_path.name}")

        use_pandoc = (engine == "pandoc") or (engine == "auto" and cls.is_pandoc_available())
        if use_pandoc:
            try:
                cls._export_with_pandoc(md_path, output_epub_path, doc_dir)
                print(f"  [✓] 使用 Pandoc 引擎成功生成: {output_epub_path}")
                return output_epub_path
            except Exception as e:
                logger.warning("Pandoc export failed (%s), falling back to pure-Python engine.", e)
                print(f"  [!] Pandoc 轉檔受阻，無縫回退至純 Python 引擎...")

        # Python fallback engine
        cls._export_literature_with_python(md_path, output_epub_path, doc_dir)
        print(f"  [✓] 使用純 Python EPUB 3 引擎成功生成: {output_epub_path}")
        return output_epub_path

    @classmethod
    def export_book(
        cls,
        book_dir: Path,
        output_epub_path: Optional[Path] = None,
        chapter: Optional[str] = None,
        engine: str = "auto"
    ) -> Path:
        """
        Converts a textbook directory into a unified multi-chapter EPUB 3 file.
        If chapter is specified, exports only that chapter.
        """
        book_dir = Path(book_dir).resolve()
        if not book_dir.exists():
            raise FileNotFoundError(f"Book directory not found: {book_dir}")

        book_name = book_dir.name
        chapters_root = book_dir / "chapters"
        if not chapters_root.exists():
            # If pointing directly to a chapter folder
            if (book_dir / f"{book_name}.md").exists():
                return cls.export_literature(book_dir, output_epub_path=output_epub_path, engine=engine)
            raise FileNotFoundError(f"Book directory missing 'chapters/' subfolder: {book_dir}")

        chapter_dirs = sorted([d for d in chapters_root.iterdir() if d.is_dir()])
        if chapter:
            clean_ch = chapter.strip().lower()
            chapter_dirs = [d for d in chapter_dirs if clean_ch in d.name.lower()]
            if not chapter_dirs:
                raise ValueError(f"Target chapter '{chapter}' not found in {book_dir}")

        if output_epub_path is None:
            if chapter and len(chapter_dirs) == 1:
                output_epub_path = chapter_dirs[0] / f"{chapter_dirs[0].name}.epub"
            else:
                output_epub_path = book_dir / f"{book_name}.epub"
        else:
            output_epub_path = Path(output_epub_path).resolve()

        print(f"\n📚 [EPUB EXPORTER] 打包教科書 ({len(chapter_dirs)} 個章節): {book_name} ➔ {output_epub_path.name}")

        use_pandoc = (engine == "pandoc") or (engine == "auto" and cls.is_pandoc_available())

        # Collect chapter markdown files and images
        chapter_data = []
        builder = PurePythonEpubBuilder(book_title=book_name, author="Author", language="en")

        for c_idx, c_dir in enumerate(chapter_dirs, 1):
            md_files = [f for f in c_dir.glob("*.md") if not f.name.endswith("_Verified.md")]
            if not md_files:
                continue
            c_md_path = md_files[0]
            c_text = c_md_path.read_text(encoding="utf-8")
            c_cleaned, c_title = MarkdownToXHTML.clean_markdown_for_epub(c_text)
            c_title = c_title or c_dir.name
            c_filename = f"chapter_{c_idx:02d}.xhtml"

            # Register chapter images
            img_dir = c_dir / "images"
            if img_dir.exists():
                for img_f in img_dir.iterdir():
                    if img_f.is_file() and img_f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        builder.add_image(f"images/{c_idx:02d}_{img_f.name}", img_f)
                        # Relink in chapter text
                        c_cleaned = c_cleaned.replace(f"images/{img_f.name}", f"../images/{c_idx:02d}_{img_f.name}")

            xhtml_body = MarkdownToXHTML.to_xhtml_body(c_cleaned)
            builder.add_chapter(title=c_title, filename=c_filename, xhtml_body=xhtml_body)
            chapter_data.append((c_md_path, c_title))

        if not builder.chapters:
            raise ValueError(f"No valid markdown chapters found to package in {book_dir}")

        if use_pandoc and not chapter:
            # Attempt multi-chapter pandoc compilation
            try:
                cls._export_book_with_pandoc(chapter_data, output_epub_path, book_dir)
                print(f"  [✓] 使用 Pandoc 引擎成功生成全書 EPUB: {output_epub_path}")
                return output_epub_path
            except Exception as e:
                logger.warning("Pandoc book export failed (%s), using pure-Python builder.", e)
                print(f"  [!] Pandoc 轉檔受阻，無縫回退至純 Python 引擎...")

        builder.build(output_epub_path)
        print(f"  [✓] 使用純 Python EPUB 3 引擎成功生成全書 EPUB: {output_epub_path}")
        return output_epub_path

    @classmethod
    def _export_literature_with_python(cls, md_path: Path, output_epub_path: Path, doc_dir: Path):
        """Helper to build single literature EPUB via pure-Python engine."""
        raw_text = md_path.read_text(encoding="utf-8")
        cleaned_md, title = MarkdownToXHTML.clean_markdown_for_epub(raw_text)
        title = title or md_path.stem

        # Extract author from .author-name if present
        m_auth = re.search(r'<div class="author-name">([^<]+)</div>', raw_text)
        author = m_auth.group(1).strip() if m_auth else "Academic Author"

        builder = PurePythonEpubBuilder(book_title=title, author=author, language="en")

        # Scan images directory
        img_dir = doc_dir / "images"
        if img_dir.exists():
            for img_f in img_dir.iterdir():
                if img_f.is_file() and img_f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    builder.add_image(f"images/{img_f.name}", img_f)

        # Relink images in xhtml body
        xhtml_body = MarkdownToXHTML.to_xhtml_body(cleaned_md)
        # In EPUB structure, chapter is at OEBPS/text/doc.xhtml, images are at OEBPS/images/
        xhtml_body = re.sub(r'src="(?:images/|/images/|./images/)([^"]+)"', r'src="../images/\1"', xhtml_body)

        builder.add_chapter(title=title, filename="document.xhtml", xhtml_body=xhtml_body)
        builder.build(output_epub_path)

    @classmethod
    def _export_with_pandoc(cls, md_path: Path, output_epub_path: Path, doc_dir: Path):
        """Compiles a single markdown into EPUB using external Pandoc."""
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False, encoding="utf-8") as tmp_css:
            tmp_css.write(get_epub_css())
            css_path = tmp_css.name

        try:
            cmd = [
                "pandoc",
                str(md_path),
                "-o", str(output_epub_path),
                "--mathml",
                f"--css={css_path}",
                f"--resource-path={doc_dir}",
                "--epub-chapter-level=2",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("Pandoc stdout: %s", res.stdout)
        finally:
            if os.path.exists(css_path):
                os.remove(css_path)

    @classmethod
    def _export_book_with_pandoc(cls, chapter_data: List[Tuple[Path, str]], output_epub_path: Path, book_dir: Path):
        """Compiles multiple chapter markdowns into a unified EPUB using external Pandoc."""
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False, encoding="utf-8") as tmp_css:
            tmp_css.write(get_epub_css())
            css_path = tmp_css.name

        try:
            cmd = [
                "pandoc",
                *[str(md_p) for md_p, _ in chapter_data],
                "-o", str(output_epub_path),
                "--mathml",
                f"--css={css_path}",
                f"--resource-path={book_dir}:{book_dir}/chapters",
                "--toc",
                "--epub-chapter-level=1",
                f"--metadata=title:{book_dir.name}",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("Pandoc book stdout: %s", res.stdout)
        finally:
            if os.path.exists(css_path):
                os.remove(css_path)
