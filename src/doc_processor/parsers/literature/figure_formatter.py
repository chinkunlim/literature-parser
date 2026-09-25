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
        fig_prefix_m = re.match(r'^(Figure\s+\d+(?:\.\d+)*[a-zA-Z]?)\.?\s*[:\.]?\s*(.*)', caption_clean, re.I)
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
        """
        Lifts all <figure>...</figure> blocks from the markdown text, heals any
        prose sentences bisected by page cuts or image placements, and re-inserts
        each figure immediately after the paragraph of its first in-text mention.

        If a figure is not cited in the text (fallback), places the figure at the
        end of the section before the next heading.
        """
        if not markdown_text or ("<figure" not in markdown_text and "<table" not in markdown_text):
            return markdown_text

        # 0. Pre-split paragraphs where (see Figure N). or (Figure N). is immediately followed by a new sentence
        markdown_text = re.sub(
            r'(\((?:see\s+)?Figure\s+\d+\)\.)\s+([A-Z])',
            r'\1\n\n\2',
            markdown_text
        )

        fig_pattern = re.compile(r'<figure[\s\S]*?</figure>')
        matches = list(fig_pattern.finditer(markdown_text))

        figs = []
        text = markdown_text
        # Cut figures in reverse order to preserve string indices
        for m in reversed(matches):
            fig_html = m.group(0)
            start, end = m.start(), m.end()

            # Extract Figure number (e.g. '1', '2', '1.1')
            num_m = re.search(r'<strong>Figure\s+(\d+(?:\.\d+)*[a-zA-Z]?)[\.:]?', fig_html, re.I)
            if not num_m:
                num_m = re.search(r'Figure\s+(\d+(?:\.\d+)*[a-zA-Z]?)', fig_html, re.I)
            fig_id = num_m.group(1) if num_m else ''

            pre = text[:start]
            post = text[end:]

            pre_stripped = pre.rstrip()
            post_stripped = post.lstrip()

            # Check for page comment in post
            pg_m = re.match(r'^(<!--\s*Page\s+\d+\s*-->\s*)', post_stripped)
            pg_tag = ''
            if pg_m:
                pg_tag = pg_m.group(1).strip()
                post_content = post_stripped[pg_m.end():].lstrip()
            else:
                post_content = post_stripped

            is_broken_sentence = False
            if pre_stripped and post_content:
                last_char = pre_stripped[-1]
                first_char = post_content[0]
                if last_char not in {'.', '?', '!', ':', '”', '\"', ')'} and (first_char.islower() or first_char in {'(', '['}):
                    is_broken_sentence = True

            if is_broken_sentence:
                text = pre_stripped + ' ' + post_content
            else:
                if pg_tag:
                    text = pre_stripped + '\n\n' + pg_tag + '\n\n' + post_content
                else:
                    text = pre_stripped + '\n\n' + post_content

            figs.append((fig_id, fig_html))

        figs.reverse()

        # Re-insert each figure after the paragraph containing its first in-text mention
        for fig_id, fig_html in figs:
            inserted = False
            if fig_id:
                mention_pat = re.compile(rf'(?i)\b(?:Figure|Fig\.)\s+{re.escape(fig_id)}\b')
                for m in mention_pat.finditer(text):
                    m_start = m.start()
                    open_fig = text.rfind('<figure', 0, m_start)
                    close_fig = text.rfind('</figure>', 0, m_start)
                    if open_fig != -1 and (close_fig == -1 or close_fig < open_fig):
                        # Inside an already placed figure block, skip
                        continue

                    # Locate paragraph boundary after this citation
                    p_end = text.find('\n\n', m.end())
                    h_end = re.search(r'\n(?=[#])', text[m.end():])
                    candidate_ends = []
                    if p_end != -1:
                        candidate_ends.append(p_end)
                    if h_end:
                        candidate_ends.append(m.end() + h_end.start())

                    target_end = min(candidate_ends) if candidate_ends else len(text)
                    text = text[:target_end] + '\n\n' + fig_html + '\n\n' + text[target_end:].lstrip()
                    inserted = True
                    break

            if not inserted:
                # Fallback: check if image filename has page info (e.g. diagram_p03_01 or 003_001)
                pg_match = re.search(r'(?:_p|/)(\d+)_', fig_html)
                pg_num = int(pg_match.group(1)) if pg_match else None
                if pg_num:
                    next_pg_tag = f"<!-- Page {pg_num + 1} -->"
                    cur_pg_tag = f"<!-- Page {pg_num} -->"
                    next_pos = text.find(next_pg_tag)
                    if next_pos != -1:
                        text = text[:next_pos] + fig_html + '\n\n' + text[next_pos:]
                        inserted = True
                    else:
                        cur_pos = text.find(cur_pg_tag)
                        if cur_pos != -1:
                            next_h = re.search(r'(?m)^(?=##|\#\#\#)', text[cur_pos + len(cur_pg_tag):])
                            if next_h:
                                ins_pos = cur_pos + len(cur_pg_tag) + next_h.start()
                                text = text[:ins_pos] + fig_html + '\n\n' + text[ins_pos:]
                                inserted = True
                if not inserted:
                    # Place before next major heading after Introduction (e.g. Discussion, Method, References)
                    headings = list(re.finditer(r'(?m)^##\s+([^\n]+)', text))
                    cand_h = None
                    for h in headings:
                        h_name = h.group(1).lower()
                        if "introduction" not in h_name and "abstract" not in h_name:
                            cand_h = h
                            break
                    if cand_h:
                        text = text[:cand_h.start()] + fig_html + '\n\n' + text[cand_h.start():]
                    else:
                        text = text + '\n\n' + fig_html + '\n\n'

        # Re-position Tables after the paragraph containing their first in-text mention
        p_tbl = re.compile(
            r'((?:(?:\*\*Table\s+\d+[\.\d]*\*\*|<p\s+class="table-caption">Table\s+\d+[\.\d]*</p>|Table\s+\d+[\.\d]*[^\n]*)\s*\n+)?<table\b[^>]*>.*?</table>(?:\s*\n+<p\s+class="table-notes">.*?</p>)?)',
            re.DOTALL | re.I
        )
        tbl_matches = list(p_tbl.finditer(text))
        if tbl_matches:
            tbls = []
            for m in reversed(tbl_matches):
                start, end = m.span()
                tbl_html = m.group(1).strip()
                num_m = re.search(r'Table\s+(\d+(?:\.\d+)*)', tbl_html, re.I)
                tbl_id = num_m.group(1) if num_m else ''

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

            for tbl_id, tbl_html in tbls:
                if tbl_id:
                    mention_pat = re.compile(rf'(?i)\bTable\s+{re.escape(tbl_id)}\b')
                    m = mention_pat.search(text)
                    if m:
                        p_end = text.find('\n\n', m.end())
                        if p_end != -1:
                            text = text[:p_end] + '\n\n' + tbl_html + '\n\n' + text[p_end:].lstrip()
                        else:
                            text = text + '\n\n' + tbl_html + '\n\n'
                else:
                    text = text + '\n\n' + tbl_html + '\n\n'

        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


__all__ = ["FigureFormatter"]
