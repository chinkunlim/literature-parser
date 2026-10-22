"""
Literature Style Configuration
==============================
Dedicated stylesheet and typographic configuration for academic literature
(peer-reviewed journals, conference proceedings, preprints, and dissertations).

Distinct from book_style.py (which handles multi-chapter textbooks).
"""

LITERATURE_STYLE: dict = {
    # ── Typographic Hierarchy ──────────────────────────────────────────────
    "font_family": "'Times New Roman', Times, Georgia, serif",
    "line_height": 1.65,
    "justify_body": True,
    "heading_align": "left",

    # ── Academic Structure & Metadata ──────────────────────────────────────
    "show_article_meta": True,
    "author_block_style": "card",       # "card" | "inline"
    "generate_toc": True,
    "toc_style": "details",             # "<details open>" collapsible TOC
    "allow_blockquotes": True,          # Keep > for Abstract & block quotations
    "abstract_style": "blockquote",     # "blockquote" | "section"

    # ── APA & Academic Tables ──────────────────────────────────────────────
    "table_style": "apa_three_line",    # Top line, bottom line, header line
    "table_caption_bold": True,
    "table_subtitle_italic": True,

    # ── Citations & References ─────────────────────────────────────────────
    "reference_format": "hanging_indent", # "- Author, A. A. (Year)..."
    "author_note_before_references": True,
}


ACADEMIC_LITERATURE_CSS = """<style>
  /* Google Fonts Dual-Mode Stack & Color Variables */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang TC', 'Noto Sans TC', sans-serif;
    --font-serif: 'Merriweather', 'Source Serif Pro', 'Georgia', 'Noto Serif TC', serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', 'Menlo', monospace;
    --color-text-main: #1f2937;
    --color-text-muted: #4b5563;
    --color-blue: #2563eb;
    --color-emerald: #059669;
    --color-amber: #d97706;
    --color-rose: #e11d48;
    --color-highlight: #fef08a;
  }

  body { font-family: var(--font-sans); color: var(--color-text-main); }
  h1, h2, h3, h4, h5, h6 { font-family: var(--font-serif); }
  code, pre { font-family: var(--font-mono); }

  /* Publishing Utility Color Classes */
  .text-blue { color: var(--color-blue); }
  .text-emerald { color: var(--color-emerald); }
  .text-amber { color: var(--color-amber); }
  .text-rose { color: var(--color-rose); }
  .text-muted { color: var(--color-text-muted); }
  mark.term { background: #fef3c7; color: #92400e; padding: 1px 4px; border-radius: 3px; font-weight: 600; }
  mark, .highlight { background: var(--color-highlight); padding: 1px 3px; }

  /* Adaptive HTML Table Styling */
  .book-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
    font-size: 0.9em;
  }
  .book-table th, .book-table td {
    border: 1px solid #d1d5db;
    padding: 8px 12px;
    text-align: left;
    vertical-align: top;
  }
  .book-table th {
    background-color: #f3f4f6;
    font-weight: 600;
  }

  /* Academic Literature Typographic Styling */
  p {
    text-align: justify;
    text-justify: inter-word;
    line-height: 1.65;
    margin-bottom: 1em;
  }
  h1, h2, h3, h4, h5, h6 {
    text-align: left;
    font-weight: 700;
  }
  h1 { margin-top: 1.2em; margin-bottom: 0.6em; }
  h2 { margin-top: 1.6em; margin-bottom: 0.6em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
  h3 { margin-top: 1.3em; margin-bottom: 0.5em; }
  h4 { margin-top: 1.1em; margin-bottom: 0.4em; }
  blockquote {
    border-left: 4px solid #842959;
    padding: 10px 18px;
    margin: 1.4em 0;
    background: #fbf8fa;
    color: #333;
  }
  .article-meta {
    font-size: 0.9em;
    color: #555;
    margin-bottom: 1.5em;
  }
  .author-block {
    margin: 1.2em 0 1.8em 0;
    line-height: 1.5;
  }
  .author-name {
    font-weight: bold;
    font-size: 1.05em;
  }
  .author-affiliation {
    font-size: 0.92em;
    color: #555;
    margin-bottom: 0.6em;
  }
  .author-note {
    font-size: 0.88em;
    color: #555;
    border-top: 1px solid #e1e4e8;
    margin-top: 2.5em;
    padding-top: 1.2em;
  }
  table {
    width: auto;
    max-width: 100%;
    border-collapse: collapse;
    margin: 1.8em 0;
    font-size: 0.88em;
  }
  th, td {
    padding: 8px 10px;
    border-bottom: 1px solid #ddd;
    text-align: left;
  }
  th {
    border-top: 2px solid #333;
    border-bottom: 1px solid #333;
    font-weight: bold;
    background: #f9f9f9;
  }
  tr.table-bottom-rule td {
    border-bottom: 2px solid #333;
  }
  .table-caption {
    font-weight: bold;
    margin-top: 1.8em;
    margin-bottom: 0.3em;
  }
  .table-subtitle {
    font-style: italic;
    margin-bottom: 0.6em;
  }
  .table-notes {
    font-size: 0.84em;
    color: #666;
    margin-top: 0.4em;
    margin-bottom: 1.8em;
  }
  figure {
    margin: 2em 0;
    text-align: center;
  }
  figcaption {
    font-size: 0.9em;
    color: #444;
    margin-top: 0.6em;
    text-align: justify;
  }
  .instruction-quote {
    background-color: #f6f8fa;
    border-left: 3px solid #0366d6;
    padding: 12px 18px;
    margin: 1.2em 0;
    font-style: normal;
  }
</style>
"""


def build_literature_css(style_dict: dict = None) -> str:
    """Builds and returns the dedicated CSS stylesheet for academic literature."""
    return ACADEMIC_LITERATURE_CSS.strip() + "\n"
