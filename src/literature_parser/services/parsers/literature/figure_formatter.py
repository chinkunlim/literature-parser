"""
Figure Formatter for Academic Literature (FigureFormatter)
==========================================================
Encapsulates high-fidelity semantic <figure> and <figcaption> formatting
for academic literature, with image deduplication per page.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FigureFormatter:
    """Formats figures as HTML5 <figure> tags and deduplicates images per page."""

    @staticmethod
    def deduplicate_page_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates images extracted on the same page.
        If both a raw extracted image (e.g. 003_001.png) and a cropped vector figure
        (e.g. figure_1_.png) exist for the same figure on the same page, prefer the
        higher-quality genuine image and drop duplicates.
        """
        if len(images) <= 1:
            return images

        unique: List[Dict[str, Any]] = []
        seen_pages = {}

        for img in images:
            p = img.get('page', 0)
            fname = img.get('filename', '')
            # If we already have an image on this page, check if one is a duplicate vector crop
            if p in seen_pages:
                existing = seen_pages[p]
                # If existing is a vector crop like 'figure_1_.png' and new is genuine '003_001.png', replace
                if 'figure_' in existing.get('filename', '') and 'figure_' not in fname:
                    unique.remove(existing)
                    unique.append(img)
                    seen_pages[p] = img
                elif 'figure_' not in existing.get('filename', '') and 'figure_' in fname:
                    # Ignore duplicate vector crop
                    continue
                else:
                    unique.append(img)
            else:
                unique.append(img)
                seen_pages[p] = img

        return unique

    @staticmethod
    def render_figure_html(img_path: str, caption: str, alt_text: Optional[str] = None, max_width: int = 650) -> str:
        """Renders an academic <figure> block with <figcaption>."""
        caption_clean = re.sub(r'\s*\n\s*', ' ', caption).strip()
        alt = re.sub(r'\s*\n\s*', ' ', (alt_text or caption)).strip()

        # Extract Figure number prefix if present: "Figure 1." -> "<strong>Figure 1.</strong>"
        fig_prefix_m = re.match(r'^(Figure\s+\d+(?:\.\d+)*[a-zA-Z]?)\.?\s*[:\.]?\s*(.*)', caption_clean, re.IGNORECASE)
        if fig_prefix_m:
            num_part = fig_prefix_m.group(1).strip()
            rest_part = fig_prefix_m.group(2).strip()
            caption_html = f"<strong>{num_part}.</strong> {rest_part}" if rest_part else f"<strong>{num_part}.</strong>"
        else:
            caption_html = caption_clean

        return (
            f'<figure>\n'
            f'  <img src="{img_path}" alt="{alt}" style="max-width: {max_width}px; width: 100%;">\n'
            f'  <figcaption>{caption_html}</figcaption>\n'
            f'</figure>'
        )

    @classmethod
    def reposition_figures(cls, markdown_text: str) -> str:
        """Lifts all <figure> and <table> blocks, heals severed sentences, and anchors them after complete paragraphs."""
        return cls.reposition_figures_and_tables(markdown_text)

    @classmethod
    def reposition_figures_and_tables(cls, markdown_text: str) -> str:
        """
        Lifts all <figure>...</figure> and <table...>...</table> blocks from the markdown text,
        heals any prose sentences bisected by page cuts or image placements, and re-inserts
        each figure/table strictly after the complete logical paragraph or list block of its first mention.

        If an artifact is not cited in the text (fallback), places it at the end of the section
        before the next heading.
        """
        if not markdown_text or ("<figure" not in markdown_text and "<table" not in markdown_text):
            return markdown_text

        # 1. Extract Figures
        fig_pattern = re.compile(r'<figure[\s\S]*?</figure>')
        fig_matches = list(fig_pattern.finditer(markdown_text))
        figs = []
        text = markdown_text

        # Cut figures in reverse order to preserve string indices
        for m in reversed(fig_matches):
            fig_html = m.group(0)
            start, end = m.start(), m.end()

            # Extract Figure number (e.g. '1', '2', '1.1', '1-1')
            num_m = re.search(r'<strong>Figure\s+([0-9IVXLCDM]+(?:[\.\-–][0-9]+)*[a-zA-Z]?)[\.:]?', fig_html, re.IGNORECASE)
            if not num_m:
                num_m = re.search(r'Figure\s+([0-9IVXLCDM]+(?:[\.\-–][0-9]+)*[a-zA-Z]?)', fig_html, re.IGNORECASE)
            fig_id = num_m.group(1) if num_m else ''

            pre = text[:start].rstrip()
            post = text[end:].lstrip()

            # Check for page comment in post
            pg_m = re.match(r'^(<!--\s*Page\s+\d+\s*-->\s*)', post)
            pg_tag = ''
            if pg_m:
                pg_tag = pg_m.group(1).strip()
                post_content = post[pg_m.end():].lstrip()
            else:
                post_content = post

            is_broken = False
            if pre and post_content:
                if pre[-1] not in ('.', '?', '!', ':', '\"', '”', ')') and (post_content[0].islower() or post_content[0] in ('(', '[')):
                    is_broken = True

            if is_broken:
                text = pre + ' ' + post_content
            else:
                if pg_tag:
                    text = pre + '\n\n' + pg_tag + '\n\n' + post_content
                else:
                    text = pre + '\n\n' + post_content

            figs.append((fig_id, fig_html))

        figs.reverse()

        # 2. Extract Tables (support both dot Table 1.1 and hyphen Table 1-1 numbering, Refs: ISSUE-016)
        _tbl_id_pat = r'\d+(?:[\.\-–]\d+)*[a-zA-Z]?'
        p_tbl = re.compile(
            rf'((?:(?:\*\*Table\s+{_tbl_id_pat}\*\*[^\n]*\n+|<p\s+class="table-caption">Table\s+{_tbl_id_pat}</p>|###\s*Table\s+{_tbl_id_pat}[^\n]*\n+|(?<!\*)\bTable\s+{_tbl_id_pat}[^\n]*\n+)?\s*<table\b[^>]*>.*?</table>(?:\s*\n+<p\s+class="table-notes">.*?</p>)?))',
            re.DOTALL | re.IGNORECASE
        )
        tbl_matches = list(p_tbl.finditer(text))
        tbls = []
        if tbl_matches:
            # Cut tables in reverse order to preserve string indices
            for m in reversed(tbl_matches):
                start, end = m.span()
                tbl_html = m.group(1).strip()
                # Extract Table number (including hyphenated e.g. 1-1, 1-2, 16-1)
                num_m = re.search(rf'(?<!<)\bTable\s+({_tbl_id_pat})', tbl_html, re.IGNORECASE)
                tbl_id = num_m.group(1) if num_m else ''
                if not tbl_id:
                    # Unnumbered inline tables (e.g. Box 9-1..9-6 Transferable Skills) stay in place
                    continue

                pre = text[:start].rstrip()
                post = text[end:].lstrip()

                is_broken = False
                if pre and post:
                    if pre[-1] not in ('.', '?', '!', ':', '\"', '”', ')') and (post[0].islower() or post[0] in ('(', '[')):
                        is_broken = True

                if is_broken:
                    text = pre + ' ' + post
                else:
                    text = pre + '\n\n' + post

                tbls.append((tbl_id, tbl_html))

            tbls.reverse()

        # 3. Unified Paragraph-Based Anchoring
        # Identify which figures and tables are actually cited in the narrative text.
        # Concatenate multi-page continued tables sharing the same ID instead of overwriting.
        fig_dict: Dict[str, str] = {}
        for f_id, html in figs:
            if f_id:
                fig_dict[f_id] = f"{fig_dict[f_id]}\n\n{html}" if f_id in fig_dict else html

        tbl_dict: Dict[str, str] = {}
        for t_id, html in tbls:
            if t_id:
                tbl_dict[t_id] = f"{tbl_dict[t_id]}\n\n{html}" if t_id in tbl_dict else html

        cited_fig_ids = set()
        for f_id in fig_dict:
            norm_id = re.sub(r'[a-zA-Z]+$', '', f_id) or f_id
            if re.search(rf'\b(?:Figure|Fig\.)\s+{re.escape(norm_id)}[a-zA-Z]?\b', text):
                cited_fig_ids.add(f_id)

        cited_tbl_ids = set()
        for t_id in tbl_dict:
            norm_id = re.sub(r'[a-zA-Z]+$', '', t_id) or t_id
            if re.search(rf'(?<!<)\bTable\s+{re.escape(norm_id)}[a-zA-Z]?\b', text):
                cited_tbl_ids.add(t_id)

        blocks = re.split(r'\n\n+', text.strip())
        output_blocks = []
        mounted_figs = set()
        mounted_tbls = set()

        for idx, block in enumerate(blocks):
            b_clean = block.strip()
            if not b_clean:
                continue

            # If block is a heading (## ...) after the start of document, flush uncited orphans before it
            if b_clean.startswith('##') and idx > 0:
                for f_id, f_html in fig_dict.items():
                    if f_id not in cited_fig_ids and f_id not in mounted_figs:
                        output_blocks.append(f_html)
                        mounted_figs.add(f_id)
                for t_id, t_html in tbl_dict.items():
                    if t_id not in cited_tbl_ids and t_id not in mounted_tbls:
                        output_blocks.append(t_html)
                        mounted_tbls.add(t_id)

            output_blocks.append(b_clean)

            # Find all figure and table mentions inside this block
            found_artifacts = []

            # Figure mentions
            fig_mention_pat = re.compile(r'\b(?:Figure|Fig\.)\s+([0-9IVXLCDM]+(?:[\.\-–][0-9]+)*[a-zA-Z]?)\b')
            for m in fig_mention_pat.finditer(b_clean):
                raw_id = m.group(1)
                norm_id = re.sub(r'[a-zA-Z]+$', '', raw_id) or raw_id
                target_id = raw_id if raw_id in fig_dict else (norm_id if norm_id in fig_dict else None)
                if target_id and target_id not in mounted_figs:
                    found_artifacts.append((m.start(), fig_dict[target_id], 'fig', target_id))
                    mounted_figs.add(target_id)

            # Table mentions
            tbl_mention_pat = re.compile(r'(?<!<)\bTable\s+([0-9IVXLCDM]+(?:[\.\-–][0-9]+)*[a-zA-Z]?)\b')
            for m in tbl_mention_pat.finditer(b_clean):
                raw_id = m.group(1)
                norm_id = re.sub(r'[a-zA-Z]+$', '', raw_id) or raw_id
                target_id = raw_id if raw_id in tbl_dict else (norm_id if norm_id in tbl_dict else None)
                if target_id and target_id not in mounted_tbls:
                    found_artifacts.append((m.start(), tbl_dict[target_id], 'tbl', target_id))
                    mounted_tbls.add(target_id)

            # Sort artifacts by their mention position inside this block
            found_artifacts.sort(key=lambda x: x[0])
            for _, artifact_html, _, _ in found_artifacts:
                output_blocks.append(artifact_html)

        # Flush any remaining unmounted artifacts at end of document
        for f_id, f_html in fig_dict.items():
            if f_id not in mounted_figs:
                output_blocks.append(f_html)
                mounted_figs.add(f_id)
        for t_id, t_html in tbl_dict.items():
            if t_id not in mounted_tbls:
                output_blocks.append(t_html)
                mounted_tbls.add(t_id)
        for f_id, f_html in figs:
            if not f_id:
                output_blocks.append(f_html)
        for t_id, t_html in tbls:
            if not t_id:
                output_blocks.append(t_html)

        result = '\n\n'.join(output_blocks)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()


__all__ = ["FigureFormatter"]
