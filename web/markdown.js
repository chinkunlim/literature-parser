/**
 * @file High-Fidelity Markdown to EPUB-Style HTML Parser for Literature Studio.
 * Converts headings, markdown tables, callout blockquotes, lists, images,
 * and page synchronization anchor tags into responsive, publication-grade DOM elements.
 */

/**
 * Escapes HTML special characters in plain text.
 * @param {string} str - Raw string to escape.
 * @returns {string} Escaped HTML-safe string.
 */
function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Formats inline Markdown syntax (bold, italic, inline code, links).
 * @param {string} text - Raw inline text.
 * @returns {string} Formatted HTML snippet.
 */
function formatInlineMarkdown(text) {
  if (!text) return "";
  return text
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="epub-inline-code">$1</code>')
    // Bold & Italic
    .replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="epub-link" target="_blank" rel="noopener">$1</a>');
}

/**
 * Parses a block of Markdown table lines into an HTML table.
 * @param {string[]} lines - Consecutive lines of a Markdown table.
 * @returns {string} HTML string representing the styled table.
 */
function parseTableBlock(lines) {
  if (lines.length < 2) return lines.join("\n");

  const headerLine = lines[0];
  const alignLine = lines[1];
  const bodyLines = lines.slice(2);

  const cleanCells = (line) =>
    line.replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

  const headers = cleanCells(headerLine);
  const alignments = cleanCells(alignLine).map((col) => {
    if (col.startsWith(":") && col.endsWith(":")) return "center";
    if (col.endsWith(":")) return "right";
    return "left";
  });

  let ths = headers
    .map((h, i) => {
      const align = alignments[i] || "left";
      return `<th style="text-align:${align};">${formatInlineMarkdown(h)}</th>`;
    })
    .join("");

  let trs = "";
  for (const bLine of bodyLines) {
    if (!bLine.trim()) continue;
    const cells = cleanCells(bLine);
    const tds = cells
      .map((c, i) => {
        const align = alignments[i] || "left";
        return `<td style="text-align:${align};">${formatInlineMarkdown(c)}</td>`;
      })
      .join("");
    trs += `<tr>${tds}</tr>`;
  }

  return `
    <div class="epub-table-container">
      <table class="epub-table">
        <thead><tr>${ths}</tr></thead>
        <tbody>${trs}</tbody>
      </table>
    </div>
  `;
}

/**
 * Parses Markdown source into clean, publication-grade HTML with page anchors.
 * @param {string} md - Source Markdown text.
 * @returns {string} Formatted HTML.
 */
function parseMarkdownToHtml(md) {
  if (!md) return '<div class="preview-empty">無內容可預覽</div>';

  const lines = md.split("\n");
  const output = [];
  let idx = 0;

  while (idx < lines.length) {
    const line = lines[idx];
    const trimmed = line.trim();

    // 1. Page Divider Anchor: <!-- Page N -->
    const pageMatch = trimmed.match(/^<!--\s*page\s*0*(\d+)\s*-->$/i);
    if (pageMatch) {
      const pageNum = pageMatch[1];
      output.push(
        `<div id="epub-page-${pageNum}" class="epub-page-divider" data-page="${pageNum}"><span class="epub-page-pill">Page ${pageNum}</span></div>`
      );
      idx++;
      continue;
    }

    // 2. Fenced Code Block
    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      const codeLines = [];
      idx++;
      while (idx < lines.length && !lines[idx].trim().startsWith("```")) {
        codeLines.push(escapeHtml(lines[idx]));
        idx++;
      }
      if (idx < lines.length) idx++; // Consume closing fence
      output.push(
        `<pre class="epub-code-block" data-lang="${lang}"><code>${codeLines.join("\n")}</code></pre>`
      );
      continue;
    }

    // 3. Markdown Table
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      const tableLines = [];
      while (idx < lines.length && lines[idx].trim().startsWith("|") && lines[idx].trim().endsWith("|")) {
        tableLines.push(lines[idx].trim());
        idx++;
      }
      output.push(parseTableBlock(tableLines));
      continue;
    }

    // 4. Blockquotes
    if (trimmed.startsWith(">")) {
      const quoteLines = [];
      while (idx < lines.length && lines[idx].trim().startsWith(">")) {
        quoteLines.push(lines[idx].trim().replace(/^>\s?/, ""));
        idx++;
      }
      output.push(
        `<blockquote class="epub-blockquote">${formatInlineMarkdown(quoteLines.join(" "))}</blockquote>`
      );
      continue;
    }

    // 5. Headings
    if (trimmed.startsWith("#")) {
      const hMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (hMatch) {
        const level = hMatch[1].length;
        const hText = formatInlineMarkdown(hMatch[2]);
        output.push(`<h${level} class="epub-h${level}">${hText}</h${level}>`);
        idx++;
        continue;
      }
    }

    // 6. Horizontal Rules
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      output.push('<hr class="epub-hr">');
      idx++;
      continue;
    }

    // 7. Images: ![alt](url)
    const imgMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)$/);
    if (imgMatch) {
      const alt = escapeHtml(imgMatch[1]);
      const src = imgMatch[2];
      output.push(`
        <figure class="epub-figure">
          <img src="${src}" alt="${alt}" loading="lazy">
          ${alt ? `<figcaption class="epub-caption">${alt}</figcaption>` : ""}
        </figure>
      `);
      idx++;
      continue;
    }

    // 8. Unordered Lists
    if (/^[-*+]\s+/.test(trimmed)) {
      const listItems = [];
      while (idx < lines.length && /^[-*+]\s+/.test(lines[idx].trim())) {
        const itemText = lines[idx].trim().replace(/^[-*+]\s+/, "");
        listItems.push(`<li>${formatInlineMarkdown(itemText)}</li>`);
        idx++;
      }
      output.push(`<ul class="epub-list">${listItems.join("")}</ul>`);
      continue;
    }

    // 9. Ordered Lists
    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems = [];
      while (idx < lines.length && /^\d+\.\s+/.test(lines[idx].trim())) {
        const itemText = lines[idx].trim().replace(/^\d+\.\s+/, "");
        listItems.push(`<li>${formatInlineMarkdown(itemText)}</li>`);
        idx++;
      }
      output.push(`<ol class="epub-list epub-ordered">${listItems.join("")}</ol>`);
      continue;
    }

    // 10. Empty Lines
    if (!trimmed) {
      idx++;
      continue;
    }

    // 11. Normal Paragraphs (accumulate until next block element or blank line)
    const paraLines = [];
    while (
      idx < lines.length &&
      lines[idx].trim() &&
      !lines[idx].trim().startsWith("#") &&
      !lines[idx].trim().startsWith(">") &&
      !lines[idx].trim().startsWith("|") &&
      !lines[idx].trim().startsWith("```") &&
      !/^[-*+]\s+/.test(lines[idx].trim()) &&
      !/^\d+\.\s+/.test(lines[idx].trim()) &&
      !/^<!--\s*page/i.test(lines[idx].trim()) &&
      !/^!\[/.test(lines[idx].trim())
    ) {
      paraLines.push(lines[idx].trim());
      idx++;
    }
    if (paraLines.length > 0) {
      output.push(`<p class="epub-paragraph">${formatInlineMarkdown(paraLines.join(" "))}</p>`);
    }
  }

  return `<div class="epub-reading-flow">${output.join("\n")}</div>`;
}
