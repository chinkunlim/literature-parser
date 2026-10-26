"""
EPUB 3 Styling & Typographic Templates
======================================
Provides standards-compliant, responsive CSS for e-readers (Apple Books, Calibre, Kobo, etc.):
- Proportional font hierarchies and line spacing
- Native dark mode adaptability (@media prefers-color-scheme)
- Fluid APA-grade tables with horizontal overflow protection
- Centered figures and captions
- MathML inline and block formula styling
"""

EPUB_CORE_CSS = """/* EPUB 3 Standards-Compliant Responsive Styling */

@namespace "http://www.w3.org/1999/xhtml";

:root {
  --text-color: #222222;
  --bg-color: #ffffff;
  --border-color: #e0e0e0;
  --callout-bg: #f9f9fb;
  --primary-accent: #782b4d;
  --code-bg: #f5f5f5;
  --meta-color: #555555;
}

@media (prefers-color-scheme: dark) {
  :root {
    --text-color: #e6e6e6;
    --bg-color: #1a1a1a;
    --border-color: #333333;
    --callout-bg: #262626;
    --primary-accent: #b25d84;
    --code-bg: #2a2a2a;
    --meta-color: #aaaaaa;
  }
}

html, body {
  margin: 0;
  padding: 0 4%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  color: var(--text-color);
  background-color: var(--bg-color);
  line-height: 1.68;
  word-wrap: break-word;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  line-height: 1.25;
  margin-top: 1.4em;
  margin-bottom: 0.5em;
  color: var(--text-color);
  page-break-after: avoid;
  break-after: avoid;
}

h1 {
  font-size: 1.85em;
  border-bottom: 2px solid var(--primary-accent);
  padding-bottom: 0.3em;
  margin-top: 0.8em;
}

h2 {
  font-size: 1.45em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.25em;
}

h3 {
  font-size: 1.22em;
}

h4 {
  font-size: 1.08em;
}

p {
  margin: 0.8em 0;
  text-align: justify;
  text-justify: inter-word;
  hyphens: auto;
}

blockquote {
  margin: 1.4em 0;
  padding: 0.8em 1.2em;
  background-color: var(--callout-bg);
  border-left: 4px solid var(--primary-accent);
  color: var(--text-color);
  font-style: normal;
  border-radius: 0 4px 4px 0;
}

/* Metadata & Author Cards */
.article-meta {
  font-size: 0.9em;
  color: var(--meta-color);
  margin-bottom: 1.5em;
  padding-bottom: 0.8em;
  border-bottom: 1px solid var(--border-color);
}

.author-block {
  margin: 1.2em 0 1.6em 0;
  line-height: 1.5;
}

.author-name {
  font-weight: bold;
  font-size: 1.05em;
}

.author-affiliation {
  font-size: 0.92em;
  color: var(--meta-color);
  margin-bottom: 0.5em;
}

.author-note {
  font-size: 0.88em;
  color: var(--meta-color);
  border-top: 1px solid var(--border-color);
  margin-top: 2em;
  padding-top: 1em;
}

/* Figures & Images */
figure {
  margin: 1.6em 0;
  text-align: center;
  page-break-inside: avoid;
  break-inside: avoid;
}

figure img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

figcaption {
  font-size: 0.88em;
  color: var(--meta-color);
  margin-top: 0.6em;
  text-align: center;
  font-style: italic;
}

/* Tables */
.table-container {
  width: 100%;
  overflow-x: auto;
  margin: 1.5em 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.2em 0;
  font-size: 0.88em;
  line-height: 1.45;
  page-break-inside: avoid;
  break-inside: avoid;
}

th, td {
  padding: 8px 10px;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}

th {
  font-weight: 700;
  border-top: 2px solid var(--text-color);
  border-bottom: 1.5px solid var(--text-color);
}

tfoot {
  font-size: 0.85em;
  color: var(--meta-color);
}

/* Hanging Indent for References */
.references-list p,
.hanging-indent {
  padding-left: 2em;
  text-indent: -2em;
  margin: 0.6em 0;
}

/* Chapter Title Backlink to TOC */
a.toc-backlink {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

a.toc-backlink:hover {
  text-decoration: underline;
}

/* Code & Formulas */
code, pre {
  font-family: ui-monospace, Menlo, Monaco, "Cascadia Mono", monospace;
  font-size: 0.9em;
  background-color: var(--code-bg);
  border-radius: 3px;
}

code {
  padding: 2px 4px;
}

pre {
  padding: 12px;
  overflow-x: auto;
}

math {
  font-size: 1.05em;
}

math[display="block"] {
  display: block;
  text-align: center;
  margin: 1.2em 0;
  overflow-x: auto;
}

/* Textbook Hierarchical Table of Contents Styling (Refs: ISSUE-017) */
.textbook-toc {
  margin: 1.5em 0;
  font-family: inherit;
}

.textbook-toc .toc-heading {
  font-size: 1.6em;
  font-weight: 700;
  margin-bottom: 1em;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 0.3em;
}

.textbook-toc .toc-part-header {
  font-size: 1.2em;
  font-weight: 700;
  color: var(--primary-color);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.2em;
}

.textbook-toc .toc-list,
.textbook-toc .toc-sublist {
  list-style: none;
  padding: 0;
  margin: 0;
}

.textbook-toc .toc-item {
  margin: 0.4em 0;
  line-height: 1.4;
}

.textbook-toc .toc-chapter {
  font-weight: 600;
  margin-top: 0.8em;
}

.textbook-toc .toc-sublist {
  padding-left: 1.5em;
  margin-top: 0.2em;
}

.textbook-toc .toc-section {
  font-weight: 400;
  font-size: 0.95em;
  color: var(--text-color);
}

.textbook-toc .toc-link {
  display: flex;
  align-items: baseline;
  text-decoration: none;
  color: inherit;
  width: 100%;
}

.textbook-toc .toc-link:hover {
  color: var(--primary-color);
}

.textbook-toc .toc-title {
  flex-shrink: 1;
}

.textbook-toc .toc-dots {
  flex: 1;
  border-bottom: 1px dotted #9ca3af;
  margin: 0 8px;
  min-width: 16px;
  height: 0;
  align-self: flex-end;
  margin-bottom: 4px;
}

.textbook-toc .toc-page {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  font-size: 0.9em;
  color: #6b7280;
  margin-left: auto;
}
"""


def get_epub_css() -> str:
    """Returns the core EPUB 3 CSS stylesheet."""
    return EPUB_CORE_CSS.strip()
