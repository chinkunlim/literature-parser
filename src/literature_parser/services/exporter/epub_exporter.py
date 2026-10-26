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
import html.parser
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
from typing import Any, Dict, List, Optional, Tuple

from literature_parser.services.core.toc_resolver import TOCResolver, TOCNode
from literature_parser.services.exporter.epub_styles import get_epub_css
from literature_parser.services.utils.text_utils import get_primary_chapter_markdown

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


class MermaidToSVGConverter:
    """Renders Mermaid graph/flowchart blocks into standards-compliant inline SVG diagrams for EPUB 3."""

    @classmethod
    def convert_to_svg(cls, mermaid_code: str) -> str:
        """Converts Mermaid graph LR/TD syntax into an XHTML figure containing an inline SVG diagram.

        Args:
            mermaid_code: Raw text content inside a ```mermaid fenced block.

        Returns:
            XHTML `<figure class="concept-map-figure"><svg ...>...</svg></figure>` string.
        """
        node_labels: Dict[str, str] = {}
        edges: List[Tuple[str, str]] = []
        node_order: List[str] = []

        def _reg_node(nid: str, lbl: Optional[str] = None) -> None:
            nid = nid.strip()
            if not nid:
                return
            if nid not in node_order:
                node_order.append(nid)
            if lbl:
                clean_lbl = lbl.strip().strip('"').strip("'")
                node_labels[nid] = clean_lbl
            elif nid not in node_labels:
                node_labels[nid] = nid

        for raw_line in mermaid_code.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("graph ", "flowchart ", "%%")):
                continue
            # Extract all inline node definitions like N5["Characteristics"]
            for m_node in re.finditer(r'([A-Za-z0-9_]+)\s*\[\s*"([^"]+)"\s*\]', line):
                _reg_node(m_node.group(1), m_node.group(2))
            # Check for directed edge: A --> B
            if "-->" in line:
                parts = line.split("-->")
                for i in range(len(parts) - 1):
                    left_id = re.sub(r'\[.*?\]', '', parts[i]).strip()
                    right_id = re.sub(r'\[.*?\]', '', parts[i + 1]).strip()
                    if left_id and right_id:
                        _reg_node(left_id)
                        _reg_node(right_id)
                        edges.append((left_id, right_id))

        if not node_order:
            escaped = html.escape(mermaid_code.strip())
            return f'<div class="concept-map-fallback"><pre>{escaped}</pre></div>'

        children_map: Dict[str, List[str]] = {n: [] for n in node_order}
        in_degree: Dict[str, int] = {n: 0 for n in node_order}
        for u, v in edges:
            if v not in children_map.get(u, []):
                children_map.setdefault(u, []).append(v)
                in_degree[v] = in_degree.get(v, 0) + 1

        roots = [n for n in node_order if in_degree.get(n, 0) == 0]
        if not roots:
            roots = [node_order[0]]

        # If multiple disconnected roots exist (e.g. 'Root' declared standalone and 'N5' has edges),
        # attach secondary roots with children under the primary Root if Root has no outgoing edges
        if len(roots) > 1 and not children_map.get(roots[0]):
            primary_root = roots[0]
            for r in roots[1:]:
                children_map[primary_root].append(r)
                in_degree[r] = 1
            roots = [primary_root]

        # Assign horizontal depth levels via BFS
        depth_map: Dict[str, int] = {}
        queue: List[Tuple[str, int]] = [(r, 0) for r in roots]
        visited = set()
        while queue:
            curr, d = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            depth_map[curr] = d
            for ch in children_map.get(curr, []):
                if ch not in visited:
                    queue.append((ch, d + 1))
        for n in node_order:
            if n not in depth_map:
                depth_map[n] = 1

        # Compute vertical positions via DFS leaf ordering
        y_coords: Dict[str, float] = {}
        leaf_counter = [0]
        row_h = 44.0

        def _assign_y(node: str, seen: set) -> float:
            if node in y_coords:
                return y_coords[node]
            seen.add(node)
            ch_list = [c for c in children_map.get(node, []) if c not in seen]
            if not ch_list:
                y_val = 28.0 + leaf_counter[0] * row_h
                leaf_counter[0] += 1
                y_coords[node] = y_val
                return y_val
            child_ys = [_assign_y(c, seen) for c in ch_list]
            y_val = sum(child_ys) / len(child_ys)
            y_coords[node] = y_val
            return y_val

        seen_dfs: set = set()
        for r in roots:
            _assign_y(r, seen_dfs)
        for n in node_order:
            if n not in y_coords:
                y_coords[n] = 28.0 + leaf_counter[0] * row_h
                leaf_counter[0] += 1

        max_depth = max(depth_map.values()) if depth_map else 0
        col_w = 235.0
        box_w = 195.0
        box_h = 30.0
        svg_w = int(max(520.0, (max_depth + 1) * col_w + 30.0))
        svg_h = int(max(90.0, (max(y_coords.values()) if y_coords else 60.0) + 45.0))

        svg_elements: List[str] = [
            f'<figure class="concept-map-figure" style="margin: 1.2em 0; text-align: center;">',
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" height="auto" style="max-width: {svg_w}px; font-family: sans-serif;">',
        ]

        # Draw edges first
        for u, v in edges:
            x1 = 20.0 + depth_map.get(u, 0) * col_w + box_w
            y1 = y_coords.get(u, 28.0)
            x2 = 20.0 + depth_map.get(v, 1) * col_w
            y2 = y_coords.get(v, 28.0)
            mid_x = (x1 + x2) / 2.0
            svg_elements.append(
                f'  <path d="M {x1:.1f} {y1:.1f} C {mid_x:.1f} {y1:.1f}, {mid_x:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="#8a6d7b" stroke-width="1.6" />'
            )

        # Also draw implicit edges from primary root if connected synthetically
        for r in roots:
            for ch in children_map.get(r, []):
                if (r, ch) not in edges:
                    x1 = 20.0 + depth_map.get(r, 0) * col_w + box_w
                    y1 = y_coords.get(r, 28.0)
                    x2 = 20.0 + depth_map.get(ch, 1) * col_w
                    y2 = y_coords.get(ch, 28.0)
                    mid_x = (x1 + x2) / 2.0
                    svg_elements.append(
                        f'  <path d="M {x1:.1f} {y1:.1f} C {mid_x:.1f} {y1:.1f}, {mid_x:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}" '
                        f'fill="none" stroke="#8a6d7b" stroke-width="1.4" stroke-dasharray="4,3" />'
                    )

        # Draw node boxes and labels
        for n in node_order:
            d = depth_map.get(n, 0)
            x = 20.0 + d * col_w
            y = y_coords.get(n, 28.0) - box_h / 2.0
            raw_lbl = node_labels.get(n, n)
            display_lbl = raw_lbl if len(raw_lbl) <= 45 else (raw_lbl[:42].rstrip() + "…")
            f_size = "9.5" if len(display_lbl) > 28 else "11"
            esc_lbl = html.escape(display_lbl)
            if d == 0:
                fill, stroke, txt_color, weight = "#782b4d", "#5a1e38", "#ffffff", "bold"
            elif d == 1:
                fill, stroke, txt_color, weight = "#f3eaf0", "#782b4d", "#222222", "bold"
            else:
                fill, stroke, txt_color, weight = "#ffffff", "#b89aa9", "#333333", "normal"

            svg_elements.append(
                f'  <rect x="{x:.1f}" y="{y:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" rx="6" ry="6" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.4" />'
            )
            text_x = x + box_w / 2.0
            text_y = y + box_h / 2.0 + 4.0
            svg_elements.append(
                f'  <text x="{text_x:.1f}" y="{text_y:.1f}" fill="{txt_color}" font-size="{f_size}" '
                f'font-weight="{weight}" text-anchor="middle">{esc_lbl}</text>'
            )

        svg_elements.append("</svg>")
        svg_elements.append("</figure>")
        return "\n".join(svg_elements)


class MarkdownToXHTML:
    """Translates sanitized Markdown into XHTML5 suitable for EPUB 3 content docs."""

    @classmethod
    def clean_markdown_for_epub(cls, md: str) -> Tuple[str, Optional[str]]:
        """Strips in-line <style> blocks, Obsidian navigation wikilinks, and comments, and extracts primary title."""
        # Extract title from first H1 (or H2/H3 if no H1 exists)
        # Extract title from explicit chapter heading or early non-prose H1 (within first 8000 chars)
        title_match = re.search(
            r"(?im)^\s*#{1,3}\s*((?:Chapter\s+\d+|Part\s+[IVXLCDM\d]+|Appendix\s+[A-Z\d]+)[:\s\.\-].*)",
            md[:8000],
        )
        if not title_match:
            title_match = re.search(r"(?im)^\s*#{1,3}\s*(Chapter\s+\d+\b.*)", md[:8000])
        if not title_match:
            title_match = re.search(r"(?m)^#\s+([^\n]+)", md[:8000])
            if title_match:
                cand = title_match.group(1).strip()
                if len(cand) > 80 or cand.endswith((".", "?")) or cand.startswith(("<", "#")):
                    title_match = None
        if not title_match:
            title_match = re.search(r"(?m)^#{1,3}\s+([^\n]+)", md[:8000])
        title = title_match.group(1).strip() if title_match else None

        # Strip Obsidian navigation blocks and center navigation divs
        cleaned = re.sub(r'<![—–-]+\s*OBSIDIAN_NAV_START[\s\S]*?OBSIDIAN_NAV_END\s*[—–-]+>', '', md)
        cleaned = re.sub(r'<div\s+align="center">\s*\[\[.*?\]\].*?</div>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', cleaned)

        # Strip all HTML comments (both standard <!-- ... --> and dash-corrupted <!-— ... —>)
        cleaned = re.sub(r'<![—–-][\s\S]*?[—–-]>', '', cleaned)

        # Strip inline <style>...</style> tags
        cleaned = re.sub(r'<style\b[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Strip empty bold/italic tokens (Refs: ISSUE-017)
        cleaned = re.sub(r'\*\*\s*\*\*', '', cleaned)
        cleaned = re.sub(r'\*\*\*\s*\*\*\*', '', cleaned)

        # Separate touching bold and italic markers in numbered items (e.g. **2.***Temporality.* -> **2.** *Temporality.*)
        cleaned = re.sub(r'(?<=\d\.)\*\*\*(?=[a-zA-Z])', r'** *', cleaned)

        # Strip decorative Part divider texture slices in regular chapters (001_001..001_005)
        cleaned = re.sub(
            r"!\[(?:Illustration)?\]\((?:[^)]*001_00\d[^)]*)\)\s*(?:\*Illustration\*)?",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        # Deduplicate drop-shadow doubled tokens and lines (Refs: ISSUE-017)
        from literature_parser.services.utils.text_utils import clean_shadow_duplicates
        cleaned = clean_shadow_duplicates(cleaned)

        return cleaned.strip(), title

    VOID_TAGS = {"br", "hr", "img", "col", "input", "meta", "link"}

    @classmethod
    def _convert_pipe_table_lines(cls, table_lines: List[str]) -> str:
        """Converts a block of GFM pipe table lines into a semantic XHTML `<table>` (Refs: ISSUE-017).

        Args:
            table_lines: List of raw Markdown table rows starting and ending with `|`.

        Returns:
            XHTML string containing `<div class="table-container"><table ...>...</table></div>`.
        """
        rows: List[List[str]] = []
        sep_idx: Optional[int] = None
        for idx, r_line in enumerate(table_lines):
            stripped = r_line.strip()
            if stripped.startswith("|"):
                stripped = stripped[1:]
            if stripped.endswith("|"):
                stripped = stripped[:-1]
            cells = [c.strip() for c in stripped.split("|")]
            if sep_idx is None and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                sep_idx = idx
            rows.append(cells)

        if not rows:
            return ""

        if sep_idx is None:
            # Buffer did not contain a '| --- |' divider; render as standard paragraphs
            p_lines = []
            for ln in table_lines:
                clean_ln = re.sub(r'(?m)(^|[ \t>\[\(])\|[ \t]+(?=[a-z]{1,15}\b)', r'\1I ', ln)
                clean_ln = clean_ln.strip().strip("|").strip()
                if clean_ln:
                    p_lines.append(f"<p>{cls._format_inline(clean_ln)}</p>")
            return "\n".join(p_lines)

        out = ['<div class="table-container"><table class="textbook-table">']
        if sep_idx is not None and sep_idx > 0:
            out.append("  <thead>")
            for h_row in rows[:sep_idx]:
                ths = "".join(f"<th>{cls._format_inline(c)}</th>" for c in h_row)
                out.append(f"    <tr>{ths}</tr>")
            out.append("  </thead>")
            body_rows = rows[sep_idx + 1 :]
        else:
            body_rows = [r for i, r in enumerate(rows) if i != sep_idx]

        if body_rows:
            out.append("  <tbody>")
            for b_row in body_rows:
                tds = "".join(f"<td>{cls._format_inline(c)}</td>" for c in b_row)
                out.append(f"    <tr>{tds}</tr>")
            out.append("  </tbody>")
        out.append("</table></div>")
        return "\n".join(out)

    @classmethod
    def to_xhtml_body(cls, md: str, toc_href: Optional[str] = None) -> str:
        """Converts Markdown text into well-formed XHTML5 body content (Refs: ISSUE-017)."""
        # 1. MathML conversion
        content = LaTeXToMathML.process_markdown_math(md)

        # 2. Block replacements with HTML tag-stack tracking, Mermaid SVG rendering, and GFM Pipe Tables
        lines = content.splitlines()
        out_lines = []
        stack = []
        in_codeblock = False
        codeblock_lang = ""
        codeblock_buf: List[str] = []
        in_list = False
        in_blockquote = False
        in_references = False
        pipe_table_buf: List[str] = []
        has_h1 = bool(re.search(r'(?m)^#\s+', content))
        first_h_linked = False
        last_h1_text = ""

        def _flush_pipe_table() -> None:
            nonlocal pipe_table_buf
            if not pipe_table_buf:
                return
            if len(pipe_table_buf) >= 2:
                out_lines.append(cls._convert_pipe_table_lines(pipe_table_buf))
            else:
                # Single line with pipes (e.g. OCR artifact '| want you to...' or '| i |')
                single = pipe_table_buf[0].strip()
                if re.fullmatch(r"\|\s*[iI1l]?\s*\|", single):
                    pass
                else:
                    cleaned_single = re.sub(r"^\|\s+(?=[a-zA-Z])", "I ", single)
                    out_lines.append(f"<p>{cls._format_inline(cleaned_single)}</p>")
            pipe_table_buf = []

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                _flush_pipe_table()
                if in_list and not stack:
                    out_lines.append("</ul>")
                    in_list = False
                if in_blockquote and not stack:
                    out_lines.append("</blockquote>")
                    in_blockquote = False
                continue

            # Code block (with special Mermaid -> SVG handling for EPUB)
            if trimmed.startswith("```"):
                _flush_pipe_table()
                if in_codeblock:
                    if codeblock_lang == "mermaid":
                        out_lines.append(MermaidToSVGConverter.convert_to_svg("\n".join(codeblock_buf)))
                    else:
                        out_lines.append("<pre><code>")
                        out_lines.extend(html.escape(c_ln) for c_ln in codeblock_buf)
                        out_lines.append("</code></pre>")
                    in_codeblock = False
                    codeblock_lang = ""
                    codeblock_buf = []
                else:
                    in_codeblock = True
                    codeblock_lang = trimmed[3:].strip().lower()
                    codeblock_buf = []
                continue
            if in_codeblock:
                codeblock_buf.append(line)
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
                _flush_pipe_table()
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
                    # Also convert Markdown links [text](url) and stray ** inside HTML lines
                    formatted_html_line = re.sub(
                        r'\[([^\]]+)\]\(([^)]+)\)',
                        r'<a href="\2">\1</a>',
                        line,
                    )
                    formatted_html_line = re.sub(
                        r'\*\*([^\*<>]+)\*\*',
                        r'<strong>\1</strong>',
                        formatted_html_line,
                    )
                    # Strip any remaining unbalanced '**' inside HTML text
                    formatted_html_line = formatted_html_line.replace("**", "")
                    out_lines.append(formatted_html_line)
                continue

            # GFM Pipe Table row detection
            if trimmed.startswith("|") and (trimmed.endswith("|") or trimmed.count("|") >= 2):
                if in_list:
                    out_lines.append("</ul>")
                    in_list = False
                if in_blockquote:
                    out_lines.append("</blockquote>")
                    in_blockquote = False
                pipe_table_buf.append(trimmed)
                continue
            else:
                _flush_pipe_table()

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
                h_text_raw = header_match.group(2).strip()

                # Suppress immediate duplicate subheadings identical to the chapter H1 title
                if level > 1 and last_h1_text:
                    norm_curr = re.sub(r'[^a-zA-Z0-9]', '', h_text_raw).lower()
                    norm_h1 = re.sub(r'[^a-zA-Z0-9]', '', last_h1_text).lower()
                    if norm_curr and (norm_curr == norm_h1 or norm_curr.startswith(norm_h1) or norm_h1.startswith(norm_curr)):
                        continue

                if level == 1:
                    last_h1_text = h_text_raw

                if re.search(r'^\s*references\s*$', h_text_raw, re.IGNORECASE):
                    in_references = True
                elif level <= 2:
                    in_references = False

                from literature_parser.services.core.toc_resolver import TOCResolver
                h_slug = TOCResolver.slugify_anchor(h_text_raw)
                h_text = cls._format_inline(h_text_raw)
                id_attr = f' id="{h_slug}"' if h_slug else ""
                should_link = toc_href and (level == 1 or (not has_h1 and not first_h_linked))
                if should_link:
                    h_text = f'<a href="{html.escape(toc_href)}" class="toc-backlink" title="Return to Table of Contents">{h_text}</a>'
                    first_h_linked = True
                out_lines.append(f"<h{level}{id_attr}>{h_text}</h{level}>")
                continue

            # Markdown images: ![alt](src)
            img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', trimmed)
            if img_match:
                alt = html.escape(img_match.group(1))
                src = img_match.group(2).strip()
                caption_html = f"<figcaption>{alt}</figcaption>" if alt and alt.lower() != "illustration" else ""
                out_lines.append(f'<figure><img src="{src}" alt="{alt}" />{caption_html}</figure>')
                continue

            # Standard paragraph
            p_class = ' class="hanging-indent"' if in_references else ""
            out_lines.append(f"<p{p_class}>{cls._format_inline(trimmed)}</p>")

        _flush_pipe_table()
        if in_list:
            out_lines.append("</ul>")
        if in_blockquote:
            out_lines.append("</blockquote>")
        if in_codeblock:
            if codeblock_lang == "mermaid":
                out_lines.append(MermaidToSVGConverter.convert_to_svg("\n".join(codeblock_buf)))
            else:
                out_lines.append("<pre><code>")
                out_lines.extend(html.escape(c_ln) for c_ln in codeblock_buf)
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

        # 3. Strip HTML comments (including dash-corrupted <!-— ... —> and Obsidian blocks) (Refs: ISSUE-017)
        body = re.sub(r'<![—–-]+\s*OBSIDIAN_NAV_START[\s\S]*?OBSIDIAN_NAV_END\s*[—–-]+>', '', body)
        body = re.sub(r'<div\s+align="center">\s*\[\[.*?\]\].*?</div>', '', body, flags=re.DOTALL)
        body = re.sub(r'<![—–-][\s\S]*?[—–-]>', '', body)
        body = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', body)

        # 3.5. Convert bare angle-bracket autolink URLs (<http://...>) to valid XHTML anchors (Refs: ISSUE-017)
        body = re.sub(r'<(https?://[^>]+)>', r'<a href="\1">\1</a>', body)

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

        # Autolink angle-bracket URLs (<http://...>)
        text = re.sub(r'<(https?://[^>]+)>', r'<a href="\1">\1</a>', text)

        # 1. Balanced 3 stars: ***...***
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)

        # 2. Unbalanced mixed stars: ***A**B* -> <em><strong>A</strong>B</em> (Refs: ISSUE-017)
        text = re.sub(r'(?<!\*)\*\*\*([^*\n]+?)\*\*([^*\n]+?)\*(?!\*)', r'<em><strong>\1</strong>\2</em>', text)
        text = re.sub(r'(?<!\*)\*\*\*([^*\n]+?)\*([^*\n]+?)\*\*(?!\*)', r'<strong><em>\1</em>\2</strong>', text)
        text = re.sub(r'(?<!\*)\*([^*\n]+?)\*\*([^*\n]+?)\*\*\*(?!\*)', r'<em>\1<strong>\2</strong></em>', text)
        text = re.sub(r'(?<!\*)\*\*([^*\n]+?)\*([^*\n]+?)\*\*\*(?!\*)', r'<strong>\1<em>\2</em></strong>', text)

        # 3. Balanced 2 stars: **...** (not adjacent to *)
        text = re.sub(r'(?<!\*)\*\*(.*?)(?<!\*)\*\*(?!\*)', r'<strong>\1</strong>', text)

        # 4. Balanced 1 star: *...* (not adjacent to *)
        text = re.sub(r'(?<!\*)\*([^*\n]+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)

        # Inline code
        text = re.sub(r'`([^`]+)`', lambda m: f"<code>{html.escape(m.group(1))}</code>", text)

        # Markdown links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        # Strip any unrendered/broken bold tokens (Refs: ISSUE-017)
        text = text.replace("**", "")

        # Restore MathML
        for idx, m_str in enumerate(math_placeholders):
            text = text.replace(f"__MATH_PH_{idx}__", m_str)

        return text

    @classmethod
    def markdown_to_xhtml(
        cls,
        md: str,
        title: str = "",
        stylesheet: str = "styles/style.css",
        toc_href: Optional[str] = None,
    ) -> str:
        """Converts Markdown text into a standalone valid XHTML document.

        Args:
            md: Markdown source string.
            title: Document title for the XHTML <title> tag.
            stylesheet: Relative path to the CSS stylesheet.
            toc_href: Optional href to the Table of Contents chapter for h1 backlink.

        Returns:
            Well-formed standalone XHTML5 document string.
        """
        body = cls.to_xhtml_body(md, toc_href=toc_href)
        return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="{stylesheet}" />
</head>
<body>
{body}
</body>
</html>"""


class XHTMLSanitizer(html.parser.HTMLParser):
    """Lenient HTML parser that balances and repairs tags into strictly well-formed XHTML.

    Attributes:
        VOID_TAGS: Set of HTML tags that are self-closing in XML/XHTML.
    """

    VOID_TAGS = {"br", "hr", "img", "col", "input", "meta", "link"}

    def __init__(self) -> None:
        """Initializes the sanitizer stack and output buffer."""
        super().__init__()
        self.stack: List[str] = []
        self.output: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """Handles opening HTML tags, enforcing XHTML self-closing or pushing to tag stack.

        Args:
            tag: HTML tag name.
            attrs: List of (name, value) attribute pairs.
        """
        attr_str = ""
        if attrs:
            formatted_attrs = []
            for k, v in attrs:
                if v is None:
                    formatted_attrs.append(k)
                else:
                    clean_v = v.replace("&", "&amp;").replace('"', "&quot;")
                    formatted_attrs.append(f'{k}="{clean_v}"')
            attr_str = " " + " ".join(formatted_attrs)
        if tag.lower() in self.VOID_TAGS:
            self.output.append(f"<{tag}{attr_str} />")
        else:
            self.stack.append(tag)
            self.output.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        """Handles closing HTML tags, unwinding stack to repair mismatched tags.

        Args:
            tag: HTML tag name.
        """
        tag_lower = tag.lower()
        if tag_lower in self.VOID_TAGS:
            return
        if tag_lower in self.stack:
            reopen = []
            while self.stack and self.stack[-1] != tag_lower:
                unclosed = self.stack.pop()
                self.output.append(f"</{unclosed}>")
                reopen.append(unclosed)
            if self.stack and self.stack[-1] == tag_lower:
                self.stack.pop()
                self.output.append(f"</{tag_lower}>")
            for r in reversed(reopen):
                self.stack.append(r)
                self.output.append(f"<{r}>")

    def handle_data(self, data: str) -> None:
        """Handles raw text data, escaping bare XML special characters.

        Args:
            data: Raw text data.
        """
        self.output.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        """Handles XML/HTML entity references.

        Args:
            name: Entity name (e.g. 'amp', 'nbsp').
        """
        if name in ("amp", "lt", "gt", "quot", "apos"):
            self.output.append(f"&{name};")
        else:
            char = html.unescape(f"&{name};")
            self.output.append(html.escape(char, quote=False))

    def handle_charref(self, name: str) -> None:
        """Handles character numeric references.

        Args:
            name: Numeric character reference (e.g. '#160', '#x00a0').
        """
        self.output.append(f"&#{name};")

    def close(self) -> str:
        """Closes the parser, emitting any unclosed tags on the stack.

        Returns:
            Well-formed XHTML string.
        """
        super().close()
        while self.stack:
            unclosed = self.stack.pop()
            self.output.append(f"</{unclosed}>")
        return "".join(self.output)


class PurePythonEpubBuilder:
    """
    Zero-dependency, pure-Python EPUB 3 zip packager compliant with IDPF specifications.
    Generates uncompressed mimetype, META-INF/container.xml, OEBPS package.opf,
    nav.xhtml, toc.ncx, and embeds images and CSS.
    """

    def __init__(
        self,
        book_title: str,
        author: str = "Unknown Author",
        language: str = "en",
        toc_nodes: Optional[List[Any]] = None,
        chapter_id_map: Optional[Dict[str, str]] = None,
        book_id: Optional[str] = None,
    ):
        self.book_title = book_title
        self.author = author
        self.language = language
        self.book_id = book_id or f"urn:uuid:{uuid.uuid4()}"
        self.chapters: List[Dict[str, str]] = []  # [{title, filename, xhtml_content}]
        self.images: Dict[str, Path] = {}  # {epub_relative_path: source_abs_path}
        self.toc_nodes = toc_nodes or []
        self.chapter_id_map = chapter_id_map or {}
        self.cover_image_key: Optional[str] = None

    def add_chapter(self, title: str, filename: str, xhtml_body: str):
        """Adds an XHTML document to the book spine with XML well-formedness validation."""
        # Strip any residual comments or Obsidian navigation tags
        xhtml_body = re.sub(r'<![—–-]+\s*OBSIDIAN_NAV_START[\s\S]*?OBSIDIAN_NAV_END\s*[—–-]+>', '', xhtml_body)
        xhtml_body = re.sub(r'<div\s+align="center">\s*\[\[.*?\]\].*?</div>', '', xhtml_body, flags=re.DOTALL)
        xhtml_body = re.sub(r'<![—–-][\s\S]*?[—–-]>', '', xhtml_body)

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

        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(full_xhtml.encode("utf-8"))
        except Exception as parse_err:
            logger.warning("Chapter '%s' XML validation flagged %s; applying auto-healing", filename, parse_err)
            sanitizer = XHTMLSanitizer()
            sanitizer.feed(xhtml_body)
            healed_body = sanitizer.close()
            full_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{self.language}">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="../styles/style.css" />
</head>
<body>
{healed_body}
</body>
</html>"""
            try:
                ET.fromstring(full_xhtml.encode("utf-8"))
            except Exception as final_err:
                logger.error("Auto-healed chapter '%s' still flagged XML error: %s", filename, final_err)

        self.chapters.append({
            "id": f"sec_{len(self.chapters) + 1}",
            "title": title,
            "filename": filename,
            "content": full_xhtml,
        })

    def add_image(self, relative_path: str, source_path: Path, is_cover: bool = False):
        """Registers an image file to bundle inside OEBPS/images/.

        Args:
            relative_path: Target relative path inside EPUB (e.g. 'images/01_cover.jpeg').
            source_path: Path or Path-like object pointing to source image on disk.
            is_cover: Whether this image is the official book cover thumbnail.
        """
        clean_rel = relative_path.replace("\\", "/").lstrip("/")
        if not clean_rel.startswith("images/"):
            clean_rel = f"images/{Path(clean_rel).name}"
        self.images[clean_rel] = source_path
        if is_cover or (self.cover_image_key is None and ("cover" in clean_rel.lower() or "01_001_001" in clean_rel)):
            self.cover_image_key = clean_rel

    def build(self, output_epub_path: Path):
        """Packages all registered elements into a valid EPUB 3 zip archive."""
        output_epub_path = Path(output_epub_path)
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

            # 6. OEBPS/nav.xhtml (EPUB 3 Navigation Document with nested hierarchy) (Refs: ISSUE-017)
            if self.toc_nodes:
                nav_xhtml = TOCResolver.render_epub_nav_xhtml(
                    self.toc_nodes,
                    self.book_title,
                    chapter_id_map=self.chapter_id_map,
                    language=self.language,
                )
            else:
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

            # 7. OEBPS/toc.ncx (EPUB 2 NCX with hierarchical navPoints)
            if self.toc_nodes:
                ncx_points: List[str] = []
                play_order = 1

                def _build_ncx(nodes: List[TOCNode]) -> List[str]:
                    nonlocal play_order
                    lines: List[str] = []
                    for n in nodes:
                        clean_name = Path(n.target_file).name if n.target_file else ""
                        epub_name = self.chapter_id_map.get(clean_name, clean_name.replace(".md", ".xhtml")) if clean_name else ""
                        if not epub_name and not n.children:
                            continue
                        src_url = f"text/{epub_name}" if epub_name else "text/chapter_01.xhtml"
                        if n.anchor_id and n.level == "section":
                            src_url = f"{src_url}#{n.anchor_id}"

                        p_id = f"navPoint-{play_order}"
                        curr_order = play_order
                        play_order += 1

                        lines.append(f'    <navPoint id="{p_id}" playOrder="{curr_order}">')
                        lines.append(f'      <navLabel><text>{html.escape(n.title)}</text></navLabel>')
                        lines.append(f'      <content src="{src_url}"/>')
                        if n.children:
                            lines.extend(_build_ncx(n.children))
                        lines.append('    </navPoint>')
                    return lines

                ncx_points = _build_ncx(self.toc_nodes)
            else:
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
    <meta name="dtb:depth" content="2"/>
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
                if epub_rel == self.cover_image_key:
                    manifest_items.append(
                        f'    <item id="cover-image" href="{epub_rel}" media-type="{mtype}" properties="cover-image"/>'
                    )
                else:
                    manifest_items.append(
                        f'    <item id="img_{idx}" href="{epub_rel}" media-type="{mtype}"/>'
                    )

            spine_items = [f'    <itemref idref="{ch["id"]}"/>' for ch in self.chapters]

            meta_cover_tag = '    <meta name="cover" content="cover-image"/>\n' if self.cover_image_key else ""
            guide_block = ""
            cover_ch = next(
                (ch for ch in self.chapters if "cover" in ch["title"].lower() or "00-01" in ch["filename"].lower()),
                None,
            )
            if cover_ch:
                guide_block = f"""  <guide>
    <reference type="cover" title="Cover" href="text/{cover_ch['filename']}"/>
  </guide>
"""

            content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{self.book_id}</dc:identifier>
    <dc:title>{html.escape(self.book_title)}</dc:title>
    <dc:creator>{html.escape(self.author)}</dc:creator>
    <dc:language>{self.language}</dc:language>
    <meta property="dcterms:modified">{mod_time}</meta>
{meta_cover_tag}  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
{chr(10).join(spine_items)}
  </spine>
{guide_block}</package>"""
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

        # Build chapter filename mapping and scan hierarchical TOC structure (Refs: ISSUE-017)
        chapter_id_map: Dict[str, str] = {}
        for c_idx, c_dir in enumerate(chapter_dirs, 1):
            primary_md = get_primary_chapter_markdown(c_dir)
            if primary_md:
                chapter_id_map[primary_md.name] = f"chapter_{c_idx:02d}.xhtml"

        toc_nodes = TOCResolver.scan_book_hierarchy(book_dir) if not chapter else []

        # Collect chapter markdown files and images
        chapter_data = []
        toc_filename: Optional[str] = None
        for c_idx, c_dir in enumerate(chapter_dirs, 1):
            if c_dir.name in ("00-07-TOC", "TOC") or "contents" in c_dir.name.lower():
                toc_filename = f"chapter_{c_idx:02d}.xhtml"
                break

        toc_title_map: Dict[str, str] = {}
        def _collect_toc_titles(nodes: List[TOCNode]) -> None:
            for n in nodes:
                if n.target_file:
                    parent_part = Path(n.target_file).parent.name
                    if parent_part and parent_part != "..":
                        toc_title_map[parent_part] = n.title
                    else:
                        toc_title_map[Path(n.target_file).name] = n.title
                if n.children:
                    _collect_toc_titles(n.children)
        _collect_toc_titles(toc_nodes)

        builder = PurePythonEpubBuilder(
            book_title=book_name,
            author="Author",
            language="en",
            toc_nodes=toc_nodes,
            chapter_id_map=chapter_id_map,
        )

        for c_idx, c_dir in enumerate(chapter_dirs, 1):
            c_md_path = get_primary_chapter_markdown(c_dir)
            if not c_md_path:
                continue
            c_text = c_md_path.read_text(encoding="utf-8")
            c_cleaned, c_title = MarkdownToXHTML.clean_markdown_for_epub(c_text)
            c_title = toc_title_map.get(c_dir.name, c_title or c_dir.name)
            c_filename = f"chapter_{c_idx:02d}.xhtml"

            is_cover_chapter = ("cover" in c_dir.name.lower() or "00-01" in c_dir.name.lower() or c_idx == 1)

            # Register chapter images (including .jpx converted to .png for EPUB 3 reader compatibility)
            img_dir = c_dir / "images"
            if img_dir.exists():
                for img_f in img_dir.iterdir():
                    if not img_f.is_file():
                        continue
                    ext_low = img_f.suffix.lower()
                    is_img_cover = is_cover_chapter and ("cover" in img_f.name.lower() or "001_001" in img_f.name.lower())
                    if ext_low == ".jpx":
                        png_equiv = img_f.with_suffix(".png")
                        if not png_equiv.exists():
                            try:
                                import pymupdf
                                pymupdf.Pixmap(str(img_f)).save(str(png_equiv))
                            except Exception:
                                pass
                        target_img = png_equiv if png_equiv.exists() else img_f
                        builder.add_image(f"images/{c_idx:02d}_{target_img.name}", target_img, is_cover=is_img_cover)
                        c_cleaned = c_cleaned.replace(f"images/{img_f.name}", f"../images/{c_idx:02d}_{target_img.name}")
                    elif ext_low in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
                        builder.add_image(f"images/{c_idx:02d}_{img_f.name}", img_f, is_cover=is_img_cover)
                        # Relink in chapter text
                        c_cleaned = c_cleaned.replace(f"images/{img_f.name}", f"../images/{c_idx:02d}_{img_f.name}")

            # If this is the TOC chapter, render structured hierarchical TOC with hyperlinks
            if toc_nodes and (c_dir.name in ("00-07-TOC", "TOC") or "contents" in c_title.lower()):
                in_book_toc_html = TOCResolver.render_in_book_toc_html(
                    toc_nodes, for_epub=True, chapter_id_map=chapter_id_map
                )
                xhtml_body = in_book_toc_html
            else:
                current_toc_href = toc_filename if c_filename != toc_filename else None
                xhtml_body = MarkdownToXHTML.to_xhtml_body(c_cleaned, toc_href=current_toc_href)

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

        # Gate 2: Trigger EPUB Visual & Layout Multimodal Audit
        try:
            from literature_parser.services.verification.epub_visual_auditor import EpubVisualAuditor
            audit_dir = book_dir / "epub_visual_audit"
            auditor = EpubVisualAuditor()
            audit_report = auditor.audit_epub(
                output_epub_path,
                output_dir=audit_dir,
                sample_pages=[0, 3, 4, 24],
                use_ollama=True,
            )
            print(f"  [🛡️ GATE 2 AUDIT] EPUB 視覺與排版雙重驗收評分: {audit_report.get('average_rating')}/10 (檢出缺陷: {audit_report.get('defects_count')} 處)")
        except Exception as audit_err:
            logger.debug("Gate 2 EPUB visual audit encountered error: %s", audit_err)

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
