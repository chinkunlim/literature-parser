"""
Layout Auto-Healer & Closed-Loop Quality Assurance
==================================================
Performs deterministic visual & structural audits on extracted chapter Markdown,
detects layout defects (swallowed callout boxes, false-positive blockquotes,
corrupted headings, broken ligatures, collapsed/unformatted tables, and leaked
diagram text fragments), and automatically repairs them in a closed-loop fashion
before disk persistence.
"""

import logging
import os
import re
from pathlib import Path

from literature_parser.services.parsers.layout.table_parser import TableParser
from literature_parser.services.utils.text_utils import repair_broken_ligatures

logger = logging.getLogger(__name__)


class LayoutAutoHealer:
    """Automated inspector and self-healing engine for textbook Markdown.
    Diagnoses layout regressions and applies deterministic corrections.
    """

    @classmethod
    def audit_and_heal_chapter(
        cls,
        markdown_text: str,
        pdf_path: str,
        chapter_dir: str,
        images_dir: Path = None,
        use_ollama_vision: bool = False,
    ) -> tuple[str, list]:
        """Executes complete self-healing pipeline on chapter Markdown.

        Args:
            markdown_text: Raw extracted Markdown content for the chapter.
            pdf_path: Path to the source PDF file.
            chapter_dir: Output directory of the chapter.
            images_dir: Optional directory containing extracted chapter images.
            use_ollama_vision: Whether to invoke local Ollama vision healing.

        Returns:
            Tuple of `(healed_markdown, list_of_applied_fixes)`.
        """
        fixes_applied = []
        text = markdown_text

        # 0. Repair broken fi/fl/ffi/ffl ligatures and U+00AD soft hyphens (Refs: ISSUE-017)
        if "\xad" in text:
            text = re.sub(r"([a-zA-Z]+)-\xad[ \t]*\n[ \t]*([a-zA-Z]+)", r"\1-\2", text)
            text = re.sub(r"([a-zA-Z]+)\xad[ \t]*\n[ \t]*([a-zA-Z]+)", r"\1\2", text)
            text = text.replace("\xad", "")
            fixes_applied.append("Repaired and stripped U+00AD soft hyphens")
        repaired_lig = repair_broken_ligatures(text)
        if repaired_lig != text:
            fixes_applied.append("Repaired broken fi/fl/ffi/ffl ligature words")
            text = repaired_lig

        # 1. Heal swallowed headings and callouts
        text, f1 = cls.heal_swallowed_callout_boundaries(text)
        fixes_applied.extend(f1)

        # 2. Heal false-positive blockquotes in body text
        text, f2 = cls.heal_blockquote_false_positives(text)
        fixes_applied.extend(f2)

        # 3. Heal double-formatting artifacts (****Title**** or ** *Title* **)
        text, f3 = cls.heal_double_formatting(text)
        fixes_applied.extend(f3)

        # 4. Heal corrupted headings (cross-column prose intrusion, split multi-line headings, drop-caps)
        text, f_head = cls.heal_corrupted_headings(text)
        fixes_applied.extend(f_head)

        # 4.5. Heal Mermaid syntax corruptions (—> -> -->) and orphan ** lines (Refs: ISSUE-016)
        text, f_mermaid = cls.heal_mermaid_and_divider_syntax(text)
        fixes_applied.extend(f_mermaid)

        # 5. Heal leaked diagram text fragments by auto-cropping if images_dir is available
        if images_dir and os.path.exists(pdf_path):
            text, f4 = cls.heal_leaked_diagrams(text, pdf_path, images_dir)
            fixes_applied.extend(f4)

        # 6. Heal unformatted or list-degraded table blocks
        text, f5 = cls.heal_table_blocks(text)
        fixes_applied.extend(f5)

        if fixes_applied:
            logger.info(
                "LayoutAutoHealer: Applied %d automatic layout correction(s).",
                len(fixes_applied),
            )

        return text, fixes_applied

    @classmethod
    def heal_corrupted_headings(cls, text: str) -> tuple[str, list]:
        """Repairs headings corrupted by cross-column prose intrusion, split multi-line
        continuations, single-letter drop caps, or decorative dingbats.

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []

        # 1. Stitch consecutive split headings where the second heading starts with a lowercase connector
        # or where both are short uppercase/title headings (e.g. '## CAREER\n\n## COUNSELING')
        def _stitch_split_headings(match):
            h_hashes = match.group(1)
            part1 = match.group(2).strip()
            part2 = match.group(3).strip()
            fixes.append(f"Stitched split multi-line heading: '{part1} {part2}'")
            return f"{h_hashes} {part1} {part2}"

        text = re.sub(
            r"(?m)^(#{2,5})\s+([^\n]+?)\n{1,2}#{2,6}\s+((?:and|or|of|in|to|for|with|on|at|from|by|as|into|between|the|a|an)\b[^\n]+|[a-z][^\n]{1,55})$",
            _stitch_split_headings,
            text,
        )
        text = re.sub(
            r"(?m)^(#{2,4})\s+([A-Z][A-Z\s,&\-]{2,35})\n{1,2}\1\s+([A-Z][A-Z\s,&\-]{2,45})$",
            _stitch_split_headings,
            text,
        )

        # 1b. Stitch headings ending with a dangling connector/colon or numbered chapter title followed by a short non-sentence title line (Refs: ISSUE-017)
        # (e.g. '#### 14 Sleep, Dreaming, and Circadian\n\nRhythms 371' or '### Chapter 2 ...:\n\nSelected Theories 21')
        def _stitch_dangling_heading_line(match):
            h_hashes = match.group(1)
            part1 = match.group(2).strip()
            part2 = match.group(3).strip()
            fixes.append(f"Stitched dangling heading continuation: '{part1} {part2}'")
            return f"{h_hashes} {part1} {part2}"

        text = re.sub(
            r"(?m)^(#{2,5})\s+([^\n]*?(?:\b(?:and|or|of|in|to|for|with|on|from|by|the|a|an|&)|:)\s*|Chapter\s+\d+[^\n]*|\d{1,2}\s+[A-Z][^\n]{5,55})\n{1,2}([A-Z][^\n.!?;]{1,65}?)$",
            _stitch_dangling_heading_line,
            text,
        )

        lines = text.split("\n")
        out_lines = []
        for line in lines:
            s = line.strip()
            m_h = re.match(r"^(#{2,6})\s+(.+)$", s)
            if not m_h:
                out_lines.append(line)
                continue

            hashes, h_body = m_h.group(1), m_h.group(2).strip()
            clean_h = re.sub(r"^[\*_`]+|[\*_`]+$", "", h_body).strip()

            # Drop decorative symbol headings (e.g. ## •~———)
            if not clean_h or not re.search(r"[A-Za-z0-9]", clean_h):
                fixes.append(f"Removed decorative symbol heading '{s}'")
                continue

            # Strip leading decorative dingbat prefixes from valid headings (e.g. '## •~--- 7. How...')
            if re.match(r"^[•~—\-]+\s+", clean_h):
                clean_h = re.sub(r"^[•~—\-]+\s+", "", clean_h).strip()
                h_body = clean_h
                line = f"{hashes} {clean_h}"
                fixes.append(f"Stripped leading decorative dingbats from heading '{clean_h[:40]}'")

            # Demote URL headings or 1-2 char non-Index headings (e.g. ## e, ## rou)
            if re.match(r"^(?:https?://|www\.)", clean_h, re.IGNORECASE) or (
                len(clean_h) < 3 and not re.fullmatch(r"[A-Z]", clean_h)
            ):
                fixes.append(f"Demoted invalid short/URL heading '{s}'")
                out_lines.append(clean_h)
                continue

            # Check if heading starts with lowercase (prose fragment or cross-column merge)
            if clean_h[0].islower():
                # Check if there is a sentence end followed by an uppercase heading at the end
                m_split = re.search(r"^(.+?[.?!])\s+([A-Z][A-Za-z0-9\s\-\–:,\'’\(\)\?]{3,80})$", clean_h)
                if m_split:
                    prose_part = m_split.group(1).strip()
                    real_head = m_split.group(2).strip()
                    fixes.append(f"Separated leading prose from heading '{real_head}'")
                    out_lines.append(prose_part)
                    out_lines.append("")
                    out_lines.append(f"{hashes} {real_head}")
                else:
                    fixes.append(f"Demoted lowercase heading fragment '{clean_h[:50]}'")
                    out_lines.append(h_body)
                continue

            # Check for mid-heading sentence period intrusion (excluding abbreviations)
            scrubbed = re.sub(
                r"\b(?:e\.g|i\.e|vs|et al|Dr|Mr|Mrs|Ms|Prof|St|Jr|Sr|Inc|Ltd|Co|No|Vol|Ch|Fig|pp|Ed|U\.S|U\.K|Ph\.D|M\.A|B\.A)\.\s+",
                " ",
                clean_h,
                flags=re.IGNORECASE,
            )
            if re.search(r"[a-z]{2,}\.\s+[A-Z][a-z]", scrubbed) or (
                len(clean_h) > 85 and re.search(r"[a-z][.?!]\s+[A-Z]", scrubbed)
            ):
                # Split at the sentence boundary
                m_sent = re.match(r"^(.+?[a-z]{2,}[.?!])\s+([A-Z].+)$", clean_h)
                if m_sent:
                    part_a = m_sent.group(1).strip()
                    part_b = m_sent.group(2).strip()
                    # Decide which part is the heading (shorter title-like part without a trailing period)
                    if not part_b.endswith(".") and len(part_b) < 75:
                        fixes.append(f"Extracted heading '{part_b}' from merged prose line")
                        out_lines.append(part_a)
                        out_lines.append("")
                        out_lines.append(f"{hashes} {part_b}")
                        continue
                fixes.append(f"Demoted prose-intruded heading '{clean_h[:60]}...'")
                out_lines.append(h_body)
                continue

            out_lines.append(line)

        return "\n".join(out_lines), fixes

    @classmethod
    def heal_swallowed_callout_boundaries(cls, text: str) -> tuple[str, list]:
        """Detects and breaks out Markdown headings or callouts that were mistakenly
        swallowed inside an existing blockquote (e.g. `> [!TIP]` that never closed).

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []

        def _break_header(match):
            fixes.append(
                f"Separated swallowed heading '{match.group(1).strip()}' from blockquote"
            )
            return f"\n\n{match.group(1)}\n"

        text = re.sub(r"(?m)^>\s*(#{1,6}\s+[^\n]+)", _break_header, text)

        def _break_callout(match):
            fixes.append(
                f"Separated nested callout '{match.group(1)[:30]}...' from blockquote"
            )
            return f"\n\n{match.group(1)}"

        text = re.sub(r"(?m)^>\s*(>\s*[🎯📖]\s+[^\n]+)", _break_callout, text)
        text = re.sub(r"(?m)^>\s*(>\s*\[!.*)", _break_callout, text)

        # Unwrap tables swallowed inside blockquotes (e.g. '> **Table 5.2** ... \n>\n> <table ... > ... > </table>')
        def _unwrap_quoted_table(match: re.Match) -> str:
            raw_block = match.group(0)
            unquoted = "\n".join(re.sub(r"^>\s?", "", ln) for ln in raw_block.splitlines())
            fixes.append("Separated swallowed Table block from blockquote")
            return "\n\n" + unquoted.strip() + "\n"

        text = re.sub(
            r"(?m)(?:^>\s*\*\*Table\s+[^\n]+\n(?:^>\s*\n)*)?^>\s*<table\b[^\n]*\n(?:^>[^\n]*\n)+?^>\s*</table>",
            _unwrap_quoted_table,
            text,
        )

        return text, fixes

    @classmethod
    def heal_blockquote_false_positives(cls, text: str) -> tuple[str, list]:
        """Detects standard body text paragraphs mistakenly prefixed with `>` because
        of left-margin offsets or column indents, and un-quotes them.

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []
        lines = text.split("\n")
        out_lines = []
        bq_block = []

        def flush_bq_block(block):
            if not block:
                return []
            first_line = block[0].lstrip(">").strip()
            is_callout = (
                first_line.startswith("[!")
                or first_line.startswith("🎯")
                or first_line.startswith("📖")
                or first_line.startswith("Table")
                or first_line.startswith("Figure")
            )
            if is_callout:
                return block

            full_content = " ".join(line.lstrip(">").strip() for line in block)
            has_quotes = any(q in full_content for q in ('"', "“", "”", "‘", "'"))
            has_attribution = bool(
                re.search(r"—\s*[A-Z][a-z]+|\([12]\d{3}\)", full_content)
            )

            if len(block) >= 3 and not has_quotes and not has_attribution:
                fixes.append(
                    f"Unwrapped false-positive body blockquote ({len(block)} lines): '{full_content[:40]}...'"
                )
                return [line.lstrip(">").strip() for line in block]
            return block

        for line in lines:
            if line.startswith("> ") or line == ">":
                bq_block.append(line)
            else:
                if bq_block:
                    out_lines.extend(flush_bq_block(bq_block))
                    bq_block = []
                out_lines.append(line)

        if bq_block:
            out_lines.extend(flush_bq_block(bq_block))

        return "\n".join(out_lines), fixes

    @classmethod
    def heal_double_formatting(cls, text: str) -> tuple[str, list]:
        """Cleans up nested bold/italic tags (`****Text****` -> `**Text**`), stray `**` inside
        HTML cells, and unbalanced `**` markers on single lines (Refs: ISSUE-017).

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []

        if "****" in text:
            fixes.append("Normalized quad-asterisks (****) to double-asterisks (**)")
            text = re.sub(r"\*{4,}", "**", text)

        text = re.sub(r"\*\*\s+\*([^\*]+)\*\s+\*\*", r"***\1***", text)

        # Strip stray '**' inside HTML tags like <td>Simple correlation ( r )**</td> or <strong>Multiple regression**</strong>
        def _clean_html_bold_leak(match: re.Match) -> str:
            fixes.append("Stripped stray '**' inside HTML table/inline tag")
            return f"{match.group(1)}{match.group(2)}"

        text = re.sub(
            r"(<(?:td|th|strong|em|b|i|span)[^>]*>[^<\n]*?)\*\*([^<\n]*?</(?:td|th|strong|em|b|i|span)>)",
            _clean_html_bold_leak,
            text,
        )

        # Collapse '** ** **Text**' -> '** **Text**' -> '**Text**'
        if re.search(r"\*\*\s+\*\*\s+\*\*", text):
            text = re.sub(r"(\*\*[^*\n]+\*\*)\s+\*\*\s+(\*\*[^*\n]+\*\*)", r"\1 \2", text)
            fixes.append("Removed empty '**' between bold spans")

        # Line-by-line check for unbalanced '**' (odd count of '**' on a single line)
        out_lines = []
        for line in text.split("\n"):
            s = line.strip()
            # Drop pure symbol OCR garbage lines like '**~** ** **-ll•J!•Jt—**'
            if s.startswith("**") and len(re.sub(r"[^A-Za-z]", "", s)) <= 3 and re.search(r"[~•!—\-]{2,}", s):
                fixes.append(f"Removed symbol OCR garbage line '{s[:30]}'")
                continue
            if line.count("**") % 2 == 1:
                # Case 1: '**Prefix** ** ShortTitle' -> '**Prefix** **ShortTitle**' or '**Prefix** rest of sentence'
                m_dup = re.match(r"^(\s*\*\*[^*\n]+\*\*)\s+\*\*\s*(.*)$", line)
                if m_dup:
                    prefix, rest = m_dup.group(1), m_dup.group(2).strip()
                    if rest and len(rest) <= 35 and rest[0].isupper() and not rest.endswith((".", "!", "?")):
                        line = f"{prefix} **{rest}**"
                        fixes.append(f"Closed unbalanced bold title '{rest}'")
                    else:
                        line = f"{prefix} {rest}".rstrip()
                        fixes.append("Removed dangling duplicate '**' after bold span")
                elif line.lstrip().startswith("**") and line.count("**") == 1:
                    # Leading '**' at start of paragraph with no closing '**' on the line
                    clean_rest = line.lstrip()[2:].strip()
                    # If there is a sentence break or colon early in the line, close bold there; otherwise strip leading '**'
                    m_lead = re.match(r"^(\d+\.\s+[^.:\n]{2,40}[.:])\s+(.*)$", clean_rest)
                    if m_lead:
                        line = f"**{m_lead.group(1)}** {m_lead.group(2)}"
                        fixes.append("Closed leading bold numbered item header")
                    else:
                        line = line.replace("**", "", 1)
                        fixes.append("Removed unclosed leading '**'")
                else:
                    # Strip the last stray '**' to restore balanced bold pairs
                    r_idx = line.rfind("**")
                    if r_idx != -1:
                        line = line[:r_idx] + line[r_idx + 2 :]
                        fixes.append("Removed trailing unbalanced '**' on line")
            out_lines.append(line)

        return "\n".join(out_lines), fixes

    @classmethod
    def heal_mermaid_and_divider_syntax(cls, text: str) -> tuple[str, list]:
        """Repairs corrupted Mermaid arrows (`—>` -> `-->`), em-dash corrupted GFM table
        separator rows (`| — |` -> `| --- |`), and orphan `**` lines left by sliced bold headings.

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []

        # 1. Repair —> and –> inside ```mermaid blocks
        def _fix_mermaid(match: re.Match) -> str:
            block = match.group(0)
            if "—>" in block or "–>" in block:
                fixes.append("Repaired corrupted em-dash arrow ('—>') inside Mermaid block to '-->'")
                block = block.replace("—>", "-->").replace("–>", "-->")
            return block

        text = re.sub(r"```mermaid\b.*?```", _fix_mermaid, text, flags=re.DOTALL)

        # 2. Repair | — | or | -- | GFM table separator rows
        def _fix_gfm_sep(match: re.Match) -> str:
            row = match.group(0)
            fixes.append("Repaired corrupted em-dash table separator row ('| — |') to '| --- |'")
            return re.sub(r"[—–]|(?<!-)-(?!-)", "---", row)

        text = re.sub(r"(?m)^\|(?:\s*:?[—–\-]{1,2}:?\s*\|)+$", _fix_gfm_sep, text)

        # 3. Clean up orphan standalone '**' lines and 'Table X-Y** *Title*'
        if re.search(r"(?m)^\*\*\s*$", text):
            text = re.sub(r"(?m)^\*\*\s*\n+", "", text)
            fixes.append("Removed orphan standalone '**' line")
        if re.search(r"(?m)^Table\s+(\d+(?:[\.\-–]\d+)*)\*\*", text):
            text = re.sub(r"(?m)^Table\s+(\d+(?:[\.\-–]\d+)*)\*\*", r"**Table \1**", text)
            fixes.append("Restored leading '**' on sliced Table heading")

        return text, fixes

    @classmethod
    def heal_leaked_diagrams(
        cls, text: str, pdf_path: str, img_dir: Path
    ) -> tuple[str, list]:
        """Detects residual notation fragments from uncaptioned diagrams that leaked into text,
        and replaces them with diagram image references.

        Args:
            text: Chapter Markdown string.
            pdf_path: Path to the chapter PDF.
            img_dir: Path to the chapter images directory.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []
        leak_pattern = re.compile(
            r"(?:(?:Treatment|Posttest|Pretest)\s+)+\s*(?:X\s*[TPO]?\s*RA\s*)+\s*where\s+•\s*O\b[^\n]+(?:\n\s*•[^\n]+)*",
            re.MULTILINE,
        )
        m = leak_pattern.search(text)
        if m:
            matched_str = m.group(0)
            existing_diagrams = list(img_dir.glob("diagram_*.png"))
            if existing_diagrams:
                best_img = sorted(existing_diagrams)[0]
                replacement = (
                    f"![Experimental Design Diagram](images/{best_img.name})\n"
                )
                text = text.replace(matched_str, replacement)
                fixes.append(
                    f"Replaced leaked diagram notation with image '{best_img.name}'"
                )

        return text, fixes

    @classmethod
    def heal_table_blocks(cls, text: str) -> tuple[str, list]:
        """Detects tables that lack GFM separators, comparison-card divs, or standalone
        Table headings followed by naked bullet/numbered lists or raw rows, and converts
        them into semantic HTML `<table class="textbook-table">` blocks.

        Args:
            text: Chapter Markdown string.

        Returns:
            Tuple of `(healed_text, fixes_list)`.
        """
        fixes = []

        # 1. Fix pipe tables missing separator rows
        table_pipe_pattern = re.compile(r"((?:\|[^\n]+\|\n)+)", re.MULTILINE)

        def _ensure_table_spacing(match):
            tbl = match.group(1)
            rows = tbl.strip().split("\n")
            if len(rows) >= 2 and not any("---" in r for r in rows):
                col_count = len([c for c in rows[0].split("|") if c.strip()])
                if col_count > 1:
                    sep = "|" + "|".join([" --- "] * col_count) + "|"
                    rows.insert(1, sep)
                    fixes.append(
                        f"Inserted missing GFM table separator row with {col_count} columns"
                    )
                    return "\n" + "\n".join(rows) + "\n\n"
            return match.group(0)

        text = table_pipe_pattern.sub(_ensure_table_spacing, text)

        # 2. Convert <div class="comparison-card">...</div> into <table class="textbook-table">
        comp_card_re = re.compile(
            r'<div class="comparison-card">\s*(.*?)\s*</div>\s*</div>',
            re.DOTALL,
        )

        def _convert_comp_card(match):
            inner = match.group(0)
            banners = re.findall(
                r'<div class="banner-header">(.*?)</div>\s*<ul class="banner-list">(.*?)</ul>',
                inner,
                re.DOTALL,
            )
            if not banners:
                return inner
            t_lines = [
                '<table class="textbook-table" style="width: auto; max-width: 100%; border-collapse: collapse; margin: 1.5em 0;">',
                "  <thead><tr><th>Comparison Summary</th></tr></thead>",
                "  <tbody>",
            ]
            for b_title, ul_body in banners:
                t_lines.append(
                    f'    <tr class="category-header"><td><strong>{b_title.strip()}</strong></td></tr>'
                )
                for li in re.findall(r"<li>(.*?)</li>", ul_body, re.DOTALL):
                    t_lines.append(f"    <tr><td>• {li.strip()}</td></tr>")
            t_lines.extend(["  </tbody>", "</table>"])
            fixes.append("Converted comparison-card div to semantic HTML table")
            return "\n".join(t_lines)

        text = comp_card_re.sub(_convert_comp_card, text)

        # 3. Convert standalone Table headings followed by bullet/numbered list or raw text rows into HTML tables
        blocks = re.split(r"\n{2,}", text)
        out_blocks = []
        i = 0
        tbl_head_re = re.compile(
            r"^(?:###+\s*Table\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\s*(.*)"
            r"|\*\*Table\s+(\d+(?:[\.\-–]\d+)*[a-zA-Z]?)\.?\*\*\s*(.*)"
            r"|Table\s+(\d+(?:[\.\-–]\d+)+)\.\s+([A-Z][^\n]{3,90}))$",
            re.IGNORECASE,
        )

        while i < len(blocks):
            b = blocks[i].strip()
            lines_b = [ln.strip() for ln in b.splitlines() if ln.strip()]
            first_ln = lines_b[0] if lines_b else ""
            m_t = tbl_head_re.match(first_ln)
            if not m_t:
                out_blocks.append(blocks[i])
                i += 1
                continue

            # Check if a <table> or | --- | already exists in this block or the next 2 blocks
            lookahead_str = "\n\n".join(blocks[i : min(len(blocks), i + 3)])
            if "<table" in lookahead_str or re.search(r"\|\s*:?-{3,}:?\s*\|", lookahead_str):
                out_blocks.append(blocks[i])
                i += 1
                continue

            t_num = m_t.group(1) or m_t.group(3) or m_t.group(5)
            raw_title = (m_t.group(2) or m_t.group(4) or m_t.group(6) or "").strip()
            clean_title = re.sub(r"^[\*_]+|[\*_]+$", "", raw_title).strip()
            tbl_header = (
                f"**Table {t_num}** *{clean_title}*"
                if clean_title
                else f"**Table {t_num}**"
            )

            collected_items = []
            # If the current block has lines after the first line, collect them
            for extra_ln in lines_b[1:]:
                collected_items.append(extra_ln)

            j = i + 1
            while j < len(blocks) and len(collected_items) < 40:
                nxt = blocks[j].strip()
                if (
                    not nxt
                    or nxt.startswith(("<!--", "#", "> [!", "![", "<table", "|"))
                    or tbl_head_re.match(nxt.splitlines()[0].strip())
                ):
                    break
                nxt_lines = [ln.strip() for ln in nxt.splitlines() if ln.strip()]
                is_list_block = all(
                    re.match(
                        r"^(?:[-*•❏☐☑]|\(?\d+[\.\)]|Step\s+\d+|Decision\s+Rule|If:|Then:|Conclusion:|[IVX]+\.\s+[A-Z])\s*",
                        ln,
                    )
                    for ln in nxt_lines
                )
                is_short_tabular = len(nxt_lines) >= 2 and all(len(ln) < 120 for ln in nxt_lines)
                if is_list_block or is_short_tabular or (not collected_items and len(nxt) < 450):
                    collected_items.extend(nxt_lines)
                    j += 1
                    if is_list_block and len(collected_items) >= 2:
                        # Continue collecting consecutive list blocks
                        continue
                else:
                    break

            if collected_items:
                html_tbl = TableParser._render_items_as_html_table(
                    tbl_header, collected_items, clean_title=clean_title
                )
                out_blocks.append(html_tbl)
                fixes.append(
                    f"Converted unformatted Table {t_num} block ({len(collected_items)} items) into HTML <table>"
                )
                i = j
            else:
                out_blocks.append(blocks[i])
                i += 1

        return "\n\n".join(out_blocks), fixes
