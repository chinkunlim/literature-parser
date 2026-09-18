"""
Book Style Configuration
========================
Central stylesheet for all book-to-Markdown formatting decisions.
Think of this as a CSS stylesheet for the output Markdown.

Override for a specific book by creating a ``book_style_override.py``
in the book's output directory (e.g. ``output/My Book/book_style_override.py``).
The override file must define a dict named ``STYLE_OVERRIDE`` with only the keys
you want to change — it is shallow-merged on top of this default STYLE.

Example override file:
    STYLE_OVERRIDE = {
        "concept_map_type": "graph TD",
        "lo_emoji": "📌",
    }
"""

STYLE: dict = {

    # ── Learning Objectives ────────────────────────────────────────────────
    # If False, do NOT prepend list bullet "- " before objective items.
    "lo_use_bullets": False,
    # Emoji prepended before each learning objective item.
    "lo_emoji": "🎯",
    # If True, prepend "Learning Objective" label text; if False, omit it.
    "lo_show_label": False,
    # Python format string for the objective number. {num} = e.g. "1.1"
    "lo_number_format": "**{num}**",
    # If True, add a colon after the number (e.g. "**1.1**: Describe…")
    "lo_colon_after_number": False,

    # ── Margin Glossary (Key Term callouts in page margins) ────────────────
    # Placement of margin glossary terms: "chapter_end" (recommended) or "inline"
    "gloss_placement": "chapter_end",
    # Format of chapter-end terms: "anki" (collapsible <details> + TSV) or "bullet" (clean list)
    "gloss_format": "anki",
    # Section title used when glossaries are placed at chapter end
    "gloss_section_title": "## 🗂️ Chapter Key Terms & Active Recall",
    # Emoji shown at start of each glossary callout/item.
    "gloss_emoji": "📖",
    # If True, prepend a "Key Term: " label before the term name.
    "gloss_show_prefix": False,
    # Separator between term and definition (e.g. "—" em-dash, ":", " — ").
    "gloss_separator": "—",
    # If True, add a [↩] back-link to the Key Terms anchor at the end.
    "gloss_backlink": True,
    # The HTML id used as the Key Terms section anchor target.
    "gloss_backlink_anchor": "key-terms-and-concepts",

    # ── In-text Block Quotations ───────────────────────────────────────────
    # How to render indented quotation blocks.
    # "github" = plain `> text` blockquote
    # "admonition" = `> [!NOTE]\n> text`
    "blockquote_style": "github",

    # ── Concept / Mind Map ─────────────────────────────────────────────────
    # Mermaid diagram type used for concept maps.
    # Options: "graph LR", "graph TD", "mindmap"
    "concept_map_type": "graph LR",

    # ── Table Rendering ────────────────────────────────────────────────────
    # If True, complex tables with category bands or notes use semantic HTML <table>
    "table_html_semantic": True,
    # How to render tables extracted from the PDF.
    # "bold-label"    = **Table X.X** *Title*  followed by list (matches PDF design)
    # "gfm-table"     = full GitHub-Flavored Markdown pipe table
    # "html-table"    = semantic HTML table with classes
    "table_heading_style": "bold-label",
    # How to render numbered table rows (e.g. Table 1.2 criteria).
    # "ordered-list"  = `1. Item`
    # "gfm-table"     = pipe table row
    "table_numbered_style": "ordered-list",
    # How to render bullet table rows (e.g. Table 1.1 bullet items).
    # "bullet-list"   = `- Item`
    # "gfm-table"     = pipe table row
    "table_bullet_style": "bullet-list",

    # ── Dialogue & Case Blocks ─────────────────────────────────────────────
    # If True, wrap counseling session dialogues in semantic <div class="dialogue-block">
    "dialogue_html_semantic": True,
    # If True, wrap critical incidents in semantic <aside class="critical-incident">
    "critical_incident_html_semantic": True,

    # ── Study Question / Review Question Callout ───────────────────────────
    # GitHub callout alert type for Study Question boxes.
    # Options: "[!TIP]", "[!NOTE]", "[!IMPORTANT]", "blockquote"
    "study_question_callout": "[!TIP]",

    # ── Figure Captions ────────────────────────────────────────────────────
    # If True, wrap figure captions in *italics*.
    "figure_caption_italic": True,
    # Uniform padding (in PDF points) added around all four sides of a figure crop.
    "figure_uniform_pad_pt": 13.0,

    # ── CSS Typography (injected into output Markdown) ─────────────────────
    # If True, add `text-align: justify` to body paragraphs only.
    "css_justify_body": True,
    # CSS text-align for all heading levels (h1–h6).
    "css_heading_align": "left",
    # CSS text-align for blockquote elements.
    "css_blockquote_align": "left",

    # ── Chapter Title Guard ────────────────────────────────────────────────
    # If True and no top-level # heading exists in extracted text, auto-prepend
    # `# {chapter_name}` as the document title.
    "prepend_chapter_title_if_missing": True,

    # ── End-of-Chapter Section Detection ──────────────────────────────────
    # Generic regex patterns to identify EOC section headings in any textbook.
    # The extractor scans all pages for these headings dynamically.
    "eoc_heading_patterns": [
        r"^Key Terms and Concepts\b",
        r"^Related Internet Sites\b",
        r"^Practice Test\b",
        r"^Challenge Exercises\b",
        r"^Summary\b",
        r"^Review Questions\b",
        r"^Discussion Questions\b",
        r"^Critical Thinking\b",
        r"^Further Reading\b",
        r"^References\b",
    ],

    # ── Table of Contents (TOC) Guard ──────────────────────────────────────
    # If True, automatically generates a clickable markdown Table of Contents
    # at the start of each chapter from its ## and ### headings.
    "generate_toc": True,
}


