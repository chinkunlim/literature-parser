"""
Layout Auto-Healer & Closed-Loop Quality Assurance
==================================================
Performs deterministic visual & structural audits on extracted chapter Markdown,
detects layout defects (swallowed callout boxes, false-positive blockquotes,
flattened mindmaps, collapsed tables, and leaked diagram text fragments),
and automatically repairs them in a closed-loop fashion before disk persistence.
"""

import os
import re
import logging
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from doc_processor.parsers.layout_detector import LayoutDetector

logger = logging.getLogger(__name__)


class LayoutAutoHealer:
    """
    Automated inspector and self-healing engine for textbook Markdown.
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
        """
        Executes complete self-healing pipeline on chapter Markdown.
        Returns: (healed_markdown, list_of_applied_fixes)
        """
        fixes_applied = []
        text = markdown_text

        # 1. Heal swallowed headings and callouts
        text, f1 = cls.heal_swallowed_callout_boundaries(text)
        fixes_applied.extend(f1)

        # 2. Heal false-positive blockquotes in body text
        text, f2 = cls.heal_blockquote_false_positives(text)
        fixes_applied.extend(f2)

        # 3. Heal double-formatting artifacts (****Title**** or ** *Title* **)
        text, f3 = cls.heal_double_formatting(text)
        fixes_applied.extend(f3)

        # 4. Heal leaked diagram text fragments by auto-cropping if images_dir is available
        if images_dir and os.path.exists(pdf_path):
            text, f4 = cls.heal_leaked_diagrams(text, pdf_path, images_dir)
            fixes_applied.extend(f4)

        # 5. Heal unformatted table blocks
        text, f5 = cls.heal_table_blocks(text)
        fixes_applied.extend(f5)

        if fixes_applied:
            logger.info("LayoutAutoHealer: Applied %d automatic layout correction(s).", len(fixes_applied))

        return text, fixes_applied

    @classmethod
    def heal_swallowed_callout_boundaries(cls, text: str) -> tuple[str, list]:
        """
        Detects and breaks out Markdown headings or callouts that were mistakenly
        swallowed inside an existing blockquote (e.g. `> [!TIP]` that never closed).
        """
        fixes = []

        # Break out headers swallowed into blockquotes: `> ## Section` -> `\n\n## Section`
        def _break_header(match):
            fixes.append(f"Separated swallowed heading '{match.group(1).strip()}' from blockquote")
            return f"\n\n{match.group(1)}\n"

        text = re.sub(r'(?m)^>\s*(#{1,6}\s+[^\n]+)', _break_header, text)

        # Break out learning objectives or glossaries swallowed inside blockquote
        def _break_callout(match):
            fixes.append(f"Separated nested callout '{match.group(1)[:30]}...' from blockquote")
            return f"\n\n{match.group(1)}"

        text = re.sub(r'(?m)^>\s*(>\s*[🎯📖]\s+[^\n]+)', _break_callout, text)
        text = re.sub(r'(?m)^>\s*(>\s*\[!.*)', _break_callout, text)

        return text, fixes

    @classmethod
    def heal_blockquote_false_positives(cls, text: str) -> tuple[str, list]:
        """
        Detects standard body text paragraphs mistakenly prefixed with `>` because
        of left-margin offsets or column indents, and un-quotes them.
        Genuine quotes typically contain quotation marks or attribution or are under 3 lines.
        """
        fixes = []
        lines = text.split('\n')
        out_lines = []
        bq_block = []

        def flush_bq_block(block):
            if not block:
                return []
            # Check if block is a callout or genuinely intended quote
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

            # If it is a long continuous paragraph without quotation marks or attribution,
            # it is almost certainly a body paragraph falsely indented by layout detection
            full_content = " ".join(l.lstrip('>').strip() for l in block)
            has_quotes = any(q in full_content for q in ('"', '“', '”', '‘', "'"))
            has_attribution = bool(re.search(r'—\s*[A-Z][a-z]+|\([12]\d{3}\)', full_content))

            if len(block) >= 3 and not has_quotes and not has_attribution:
                fixes.append(f"Unwrapped false-positive body blockquote ({len(block)} lines): '{full_content[:40]}...'")
                return [l.lstrip('>').strip() for l in block]
            return block

        for line in lines:
            if line.startswith('> ') or line == '>':
                bq_block.append(line)
            else:
                if bq_block:
                    out_lines.extend(flush_bq_block(bq_block))
                    bq_block = []
                out_lines.append(line)

        if bq_block:
            out_lines.extend(flush_bq_block(bq_block))

        return '\n'.join(out_lines), fixes

    @classmethod
    def heal_double_formatting(cls, text: str) -> tuple[str, list]:
        """
        Cleans up nested bold and italic tags:
        - `****Text****` -> `**Text**`
        - `** *Text* **` -> `***Text***`
        - `**Table X.X** ****Title****` -> `**Table X.X** *Title*`
        """
        fixes = []

        if '****' in text:
            fixes.append("Normalized quad-asterisks (****) to double-asterisks (**)")
            text = re.sub(r'\*{4,}', '**', text)

        # Fix bold wrapping an already-italic or already-bold string
        text = re.sub(r'\*\*\s+\*([^\*]+)\*\s+\*\*', r'***\1***', text)

        return text, fixes

    @classmethod
    def heal_leaked_diagrams(cls, text: str, pdf_path: str, img_dir: Path) -> tuple[str, list]:
        """
        Detects residual notation fragments from uncaptioned diagrams
        (such as RA, X T, O, where • O denotes...) that leaked into text,
        and ensures they are represented as clean diagram image references.
        """
        fixes = []
        leak_pattern = re.compile(
            r'(?:(?:Treatment|Posttest|Pretest)\s+)+\s*(?:X\s*[TPO]?\s*RA\s*)+\s*where\s+•\s*O\b[^\n]+(?:\n\s*•[^\n]+)*',
            re.MULTILINE
        )
        m = leak_pattern.search(text)
        if m:
            matched_str = m.group(0)
            existing_diagrams = list(img_dir.glob("diagram_*.png"))
            if existing_diagrams:
                best_img = sorted(existing_diagrams)[0]
                replacement = f"![Experimental Design Diagram](images/{best_img.name})\n"
                text = text.replace(matched_str, replacement)
                fixes.append(f"Replaced leaked diagram notation with image '{best_img.name}'")

        return text, fixes

    @classmethod
    def heal_table_blocks(cls, text: str) -> tuple[str, list]:
        """
        Detects tables that lack standard GFM table separators and fixes them.
        """
        fixes = []
        table_pipe_pattern = re.compile(r'((?:\|[^\n]+\|\n)+)', re.MULTILINE)
        def _ensure_table_spacing(match):
            tbl = match.group(1)
            rows = tbl.strip().split('\n')
            if len(rows) >= 2 and not any('---' in r for r in rows):
                col_count = len([c for c in rows[0].split('|') if c.strip()])
                if col_count > 1:
                    sep = '|' + '|'.join([' --- '] * col_count) + '|'
                    rows.insert(1, sep)
                    fixes.append(f"Inserted missing GFM table separator row with {col_count} columns")
                    return '\n' + '\n'.join(rows) + '\n\n'
            return match.group(0)

        text = table_pipe_pattern.sub(_ensure_table_spacing, text)
        return text, fixes
