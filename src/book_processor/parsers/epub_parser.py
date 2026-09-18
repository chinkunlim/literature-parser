"""
EPUB Book Parser
================
Converts EPUB XHTML content into structured Markdown with rich formatting
(bold, italic, underline), LaTeX formulas, and localized chapter images.
"""

import os
import re
import zipfile
from pathlib import Path
from html.parser import HTMLParser
from book_processor.utils.text_utils import sanitize_filename
from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.parsers.layout_detector import LayoutDetector
from book_processor.style_loader import load_style



class HTMLToMarkdownParser(HTMLParser):
    """Converts HTML/XHTML from EPUB to structured Markdown with rich formatting & inline images."""

    def __init__(self, image_map=None):
        super().__init__()
        self.image_map = image_map or {}
        self.pieces = []
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attr_dict = dict(attrs)

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self.pieces.append('\n\n' + '#' * level + ' ')
        elif tag == 'p':
            self.pieces.append('\n\n')
        elif tag == 'br':
            self.pieces.append('\n')
        elif tag == 'li':
            self.pieces.append('\n- ')
        elif tag == 'blockquote':
            self.pieces.append('\n\n> ')
        elif tag in ('strong', 'b'):
            self.pieces.append('**')
        elif tag in ('em', 'i'):
            self.pieces.append('*')
        elif tag == 'u':
            self.pieces.append('<u>')
        elif tag == 'code':
            self.pieces.append('`')
        elif tag == 'img':
            src = attr_dict.get('src', '')
            alt = attr_dict.get('alt', 'Illustration').strip() or 'Illustration'
            md_image_path = None
            clean_src = src.split('#')[0].replace('\\', '/')
            for k, v in self.image_map.items():
                if k in clean_src or clean_src in k or Path(k).name == Path(clean_src).name:
                    md_image_path = v
                    break
            if md_image_path:
                self.pieces.append(f'\n\n![{alt}]({md_image_path})\n\n')

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag in ('strong', 'b'):
            self.pieces.append('**')
        elif tag in ('em', 'i'):
            self.pieces.append('*')
        elif tag == 'u':
            self.pieces.append('</u>')
        elif tag == 'code':
            self.pieces.append('`')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote'):
            self.pieces.append('\n')

    def handle_data(self, data):
        self.pieces.append(data)

    def get_markdown(self) -> str:
        text = ''.join(self.pieces)
        lines = [l.rstrip() for l in text.splitlines()]
        cleaned = []
        for l in lines:
            if l:
                cleaned.append(l)
            elif cleaned and cleaned[-1] != '':
                cleaned.append('')
        res = '\n'.join(cleaned).strip()
        res = re.sub(r'\n{3,}', '\n\n', res)
        # Convert statistical / math notation to LaTeX
        res = MathLaTeXConverter.process_text(res)
        return res


class EPUBProcessor:
    """Processes EPUB archives: extracts images to chapter subfolders & outputs structured Markdown."""

    @classmethod
    def process(cls, epub_path: str, base_output_dir: str):
        book_name = Path(epub_path).stem
        book_out = os.path.join(base_output_dir, sanitize_filename(book_name))
        chapters_root = os.path.join(book_out, 'chapters')
        os.makedirs(chapters_root, exist_ok=True)
        from book_processor.core.checkpoint import CheckpointManager
        style = load_style(book_out)
        ckpt = CheckpointManager(book_out, book_name)

        with zipfile.ZipFile(epub_path, 'r') as z:
            namelist = z.namelist()

            img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
            all_epub_images = sorted([n for n in namelist if Path(n).suffix.lower() in img_exts])

            toc_files = [n for n in namelist if 'toc.xhtml' in n.lower() or 'nav.xhtml' in n.lower()]
            chapter_links = []
            if toc_files:
                toc_raw = z.read(toc_files[0]).decode('utf-8', errors='ignore')
                links = re.findall(r'<a\s+[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>([^<]+)</a>', toc_raw)
                for href, title in links:
                    clean_href = href.split('#')[0]
                    clean_title = title.strip()
                    toc_dir = Path(toc_files[0]).parent
                    full_p = str(toc_dir / clean_href) if str(toc_dir) != '.' else clean_href
                    full_p = full_p.replace('\\', '/')
                    if full_p in namelist and (full_p, clean_title) not in chapter_links:
                        chapter_links.append((full_p, clean_title))

            if not chapter_links:
                html_files = sorted([n for n in namelist if Path(n).suffix.lower() in ('.xhtml', '.html', '.htm')])
                chapter_links = [(h, Path(h).stem) for h in html_files]

            global_photo_seq = 1

            print(f"  [*] Processing {len(chapter_links)} EPUB chapters/sections...")

            for ch_idx, (ch_path, ch_title) in enumerate(chapter_links, 1):
                clean_title = sanitize_filename(ch_title, max_len=70)
                ch_folder_name = f"{ch_idx:03d}_{clean_title}"
                ch_dir = os.path.join(chapters_root, ch_folder_name)
                ch_images_dir = os.path.join(ch_dir, 'images')
                os.makedirs(ch_dir, exist_ok=True)

                raw_html = z.read(ch_path).decode('utf-8', errors='ignore')
                img_srcs = re.findall(r'<img\s+[^>]*src=[\"\']([^\"\']+)[\"\']', raw_html, re.I)
                image_map = {}

                for src in img_srcs:
                    clean_src = src.split('#')[0].replace('\\', '/')
                    found_asset = None
                    for asset in all_epub_images:
                        if asset.endswith(clean_src) or Path(asset).name == Path(clean_src).name:
                            found_asset = asset
                            break

                    if found_asset:
                        os.makedirs(ch_images_dir, exist_ok=True)
                        ext = Path(found_asset).suffix.lower().lstrip('.')
                        if ext == 'jpeg':
                            ext = 'jpg'
                        new_img_filename = f"{ch_idx:03d}_{global_photo_seq:03d}.{ext}"
                        dest_img_path = os.path.join(ch_images_dir, new_img_filename)

                        with open(dest_img_path, 'wb') as f_out:
                            f_out.write(z.read(found_asset))

                        image_map[src] = f"images/{new_img_filename}"
                        global_photo_seq += 1

                parser = HTMLToMarkdownParser(image_map=image_map)
                parser.feed(raw_html)
                md_content = parser.get_markdown()

                # Apply layout detection passes (lists, code blocks, tables)
                md_content = LayoutDetector.detect_and_format_lists(md_content)
                md_content = LayoutDetector.detect_and_format_code_blocks(md_content)

                if not md_content.startswith('#'):
                    md_content = f"# {ch_title}\n\n{md_content}"

                if '<style>' not in md_content:
                    css_lines = ["<style>", "  /* Textbook typographic styling */"]
                    if style.get("css_justify_body", True):
                        css_lines += ["  p {", "    text-align: justify;", "    text-justify: inter-word;", "  }"]
                    ha = style.get("css_heading_align", "left")
                    css_lines += [f"  h1, h2, h3, h4, h5, h6 {{ text-align: {ha}; }}"]
                    ba = style.get("css_blockquote_align", "left")
                    css_lines += [f"  blockquote {{ text-align: {ba}; }}", "</style>", ""]
                    md_content = "\n".join(css_lines) + "\n" + md_content

                md_file_path = os.path.join(ch_dir, f"{ch_folder_name}.md")

                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(md_content + '\n')

                ckpt.update_status(
                    ch_folder_name,
                    status="CONVERTED",
                    markdown_generated=True
                )

            print(f"  [✓] Finished EPUB: {book_name} ({len(chapter_links)} chapters, {global_photo_seq - 1} images extracted)")
