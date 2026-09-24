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


__all__ = ["FigureFormatter"]
