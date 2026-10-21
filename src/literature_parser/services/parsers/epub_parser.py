"""
EPUB Book Parser
================
Converts EPUB XHTML content into structured Markdown with rich formatting
(bold, italic, underline), LaTeX formulas, and localized chapter images.
"""

from html.parser import HTMLParser
import logging
import os
from pathlib import Path
import re
from typing import Any
import zipfile

from literature_parser.services.parsers.layout_detector import LayoutDetector
from literature_parser.services.parsers.math_latex import MathLaTeXConverter
from literature_parser.services.style_loader import load_style
from literature_parser.services.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)


class HTMLToMarkdownParser(HTMLParser):
    """Converts HTML/XHTML from EPUB to structured Markdown with rich formatting & inline images."""

    def __init__(self, image_map: dict[str, str] | None = None) -> None:
        """Initializes the HTML to Markdown parser with an optional image path mapping.

        Args:
            image_map: Mapping from original EPUB image src attributes to local Markdown image paths.
        """
        super().__init__()
        self.image_map: dict[str, str] = image_map or {}
        self.pieces: list[str] = []
        self.tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handles opening HTML tags and appends corresponding Markdown syntax.

        Args:
            tag: Lowercase HTML tag name.
            attrs: List of (name, value) attribute pairs on the tag.
        """
        self.tag_stack.append(tag)
        attr_dict = {k: (v or "") for k, v in attrs}

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.pieces.append("\n\n" + "#" * level + " ")
        elif tag == "p":
            self.pieces.append("\n\n")
        elif tag == "br":
            self.pieces.append("\n")
        elif tag == "li":
            self.pieces.append("\n- ")
        elif tag == "blockquote":
            self.pieces.append("\n\n> ")
        elif tag in ("strong", "b"):
            self.pieces.append("**")
        elif tag in ("em", "i"):
            self.pieces.append("*")
        elif tag == "u":
            self.pieces.append("<u>")
        elif tag == "code":
            self.pieces.append("`")
        elif tag == "img":
            self._handle_image_tag(attr_dict)

    def _handle_image_tag(self, attr_dict: dict[str, str]) -> None:
        """Resolves an HTML img tag against the image map and appends a Markdown image link.

        Args:
            attr_dict: Dictionary of HTML attributes on the img element.
        """
        src = attr_dict.get("src", "")
        alt = attr_dict.get("alt", "Illustration").strip() or "Illustration"
        md_image_path = None
        clean_src = src.split("#")[0].replace("\\", "/")
        for k, v in self.image_map.items():
            if k in clean_src or clean_src in k or Path(k).name == Path(clean_src).name:
                md_image_path = v
                break
        if md_image_path:
            self.pieces.append(f"\n\n![{alt}]({md_image_path})\n\n")

    def handle_endtag(self, tag: str) -> None:
        """Handles closing HTML tags and appends closing Markdown markers.

        Args:
            tag: Lowercase HTML tag name.
        """
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag in ("strong", "b"):
            self.pieces.append("**")
        elif tag in ("em", "i"):
            self.pieces.append("*")
        elif tag == "u":
            self.pieces.append("</u>")
        elif tag == "code":
            self.pieces.append("`")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote"):
            self.pieces.append("\n")

    def handle_data(self, data: str) -> None:
        """Appends character data inside HTML elements to the output buffer.

        Args:
            data: Text content inside the current HTML element.
        """
        self.pieces.append(data)

    def get_markdown(self) -> str:
        """Assembles and normalizes the accumulated Markdown text with LaTeX math conversion.

        Returns:
            Cleaned Markdown string representing the parsed HTML document.
        """
        text = "".join(self.pieces)
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned: list[str] = []
        for line in lines:
            if line:
                cleaned.append(line)
            elif cleaned and cleaned[-1] != "":
                cleaned.append("")
        res = "\n".join(cleaned).strip()
        res = re.sub(r"\n{3,}", "\n\n", res)
        # Convert statistical / math notation to LaTeX
        res = MathLaTeXConverter.process_text(res)
        return res


class EPUBProcessor:
    """Processes EPUB archives: extracts images to chapter subfolders & outputs structured Markdown."""

    @classmethod
    def _resolve_chapter_links(cls, z: zipfile.ZipFile, namelist: list[str]) -> list[tuple[str, str]]:
        """Extracts ordered (archive_path, title) pairs from EPUB navigation or HTML files.

        Args:
            z: Open ZipFile handle for the EPUB archive.
            namelist: List of member paths inside the EPUB archive.

        Returns:
            List of (chapter_path, chapter_title) tuples in reading order.
        """
        toc_files = [n for n in namelist if "toc.xhtml" in n.lower() or "nav.xhtml" in n.lower()]
        chapter_links: list[tuple[str, str]] = []
        if toc_files:
            toc_raw = z.read(toc_files[0]).decode("utf-8", errors="ignore")
            links = re.findall(r"<a\s+[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>([^<]+)</a>", toc_raw)
            toc_dir = Path(toc_files[0]).parent
            for href, title in links:
                clean_href = href.split("#")[0]
                clean_title = title.strip()
                full_p = str(toc_dir / clean_href) if str(toc_dir) != "." else clean_href
                full_p = full_p.replace("\\", "/")
                if full_p in namelist and (full_p, clean_title) not in chapter_links:
                    chapter_links.append((full_p, clean_title))

        if not chapter_links:
            html_files = sorted([n for n in namelist if Path(n).suffix.lower() in (".xhtml", ".html", ".htm")])
            chapter_links = [(h, Path(h).stem) for h in html_files]
        return chapter_links

    @classmethod
    def _extract_chapter_images(
        cls,
        z: zipfile.ZipFile,
        raw_html: str,
        all_epub_images: list[str],
        ch_images_dir: str,
        ch_idx: int,
        global_photo_seq: int,
    ) -> tuple[dict[str, str], int]:
        """Extracts images referenced in a chapter HTML file into the chapter images directory.

        Args:
            z: Open ZipFile handle for the EPUB archive.
            raw_html: Raw HTML content of the chapter.
            all_epub_images: All image member paths in the EPUB archive.
            ch_images_dir: Destination directory path for extracted chapter images.
            ch_idx: 1-based chapter index.
            global_photo_seq: Running global counter of extracted images.

        Returns:
            Tuple of (image_map mapping original src to local relative path, updated global_photo_seq).
        """
        img_srcs = re.findall(r"<img\s+[^>]*src=[\"\']([^\"\']+)[\"\']", raw_html, re.IGNORECASE)
        image_map: dict[str, str] = {}

        for src in img_srcs:
            clean_src = src.split("#")[0].replace("\\", "/")
            found_asset = next(
                (
                    asset
                    for asset in all_epub_images
                    if asset.endswith(clean_src) or Path(asset).name == Path(clean_src).name
                ),
                None,
            )
            if not found_asset:
                continue

            os.makedirs(ch_images_dir, exist_ok=True)
            ext = Path(found_asset).suffix.lower().lstrip(".")
            if ext == "jpeg":
                ext = "jpg"
            new_img_filename = f"{ch_idx:03d}_{global_photo_seq:03d}.{ext}"
            dest_img_path = os.path.join(ch_images_dir, new_img_filename)

            with open(dest_img_path, "wb") as f_out:
                f_out.write(z.read(found_asset))

            image_map[src] = f"images/{new_img_filename}"
            global_photo_seq += 1

        return image_map, global_photo_seq

    @staticmethod
    def _prepend_style_block(md_content: str, style: dict[str, Any]) -> str:
        """Prepends the textbook typographic CSS style block if not already present.

        Args:
            md_content: Markdown content of the chapter.
            style: Loaded typography style configuration dictionary.

        Returns:
            Markdown content with the prepended HTML style block.
        """
        if "<style>" in md_content:
            return md_content
        css_lines = ["<style>", "  /* Textbook typographic styling */"]
        if style.get("css_justify_body", True):
            css_lines += ["  p {", "    text-align: justify;", "    text-justify: inter-word;", "  }"]
        ha = style.get("css_heading_align", "left")
        css_lines += [f"  h1, h2, h3, h4, h5, h6 {{ text-align: {ha}; }}"]
        ba = style.get("css_blockquote_align", "left")
        css_lines += [f"  blockquote {{ text-align: {ba}; }}", "</style>", ""]
        return "\n".join(css_lines) + "\n" + md_content

    @classmethod
    def process(cls, epub_path: str, base_output_dir: str) -> None:
        """Processes an EPUB file into per-chapter Markdown files and localized image folders.

        Args:
            epub_path: File path to the input EPUB archive.
            base_output_dir: Root directory where the book output folder will be created.
        """
        book_name = Path(epub_path).stem
        book_out = os.path.join(base_output_dir, sanitize_filename(book_name))
        chapters_root = os.path.join(book_out, "chapters")
        os.makedirs(chapters_root, exist_ok=True)
        from literature_parser.services.core.checkpoint import CheckpointManager

        style = load_style(book_out)
        ckpt = CheckpointManager(book_out, book_name)

        with zipfile.ZipFile(epub_path, "r") as z:
            namelist = z.namelist()
            img_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
            all_epub_images = sorted([n for n in namelist if Path(n).suffix.lower() in img_exts])
            chapter_links = cls._resolve_chapter_links(z, namelist)
            global_photo_seq = 1

            logger.info("Processing %d EPUB chapters/sections for %s", len(chapter_links), book_name)

            for ch_idx, (ch_path, ch_title) in enumerate(chapter_links, 1):
                clean_title = sanitize_filename(ch_title, max_len=70)
                ch_folder_name = f"{ch_idx:03d}_{clean_title}"
                ch_dir = os.path.join(chapters_root, ch_folder_name)
                ch_images_dir = os.path.join(ch_dir, "images")
                os.makedirs(ch_dir, exist_ok=True)

                raw_html = z.read(ch_path).decode("utf-8", errors="ignore")
                image_map, global_photo_seq = cls._extract_chapter_images(
                    z, raw_html, all_epub_images, ch_images_dir, ch_idx, global_photo_seq
                )

                parser = HTMLToMarkdownParser(image_map=image_map)
                parser.feed(raw_html)
                md_content = parser.get_markdown()

                # Apply layout detection passes (lists, code blocks, tables)
                md_content = LayoutDetector.detect_and_format_lists(md_content)
                md_content = LayoutDetector.detect_and_format_code_blocks(md_content)

                if not md_content.startswith("#"):
                    md_content = f"# {ch_title}\n\n{md_content}"

                md_content = cls._prepend_style_block(md_content, style)
                md_file_path = os.path.join(ch_dir, f"{ch_folder_name}.md")

                with open(md_file_path, "w", encoding="utf-8") as f:
                    f.write(md_content + "\n")

                ckpt.update_status(ch_folder_name, status="CONVERTED", markdown_generated=True)

            logger.info(
                "Finished EPUB: %s (%d chapters, %d images extracted)",
                book_name,
                len(chapter_links),
                global_photo_seq - 1,
            )
