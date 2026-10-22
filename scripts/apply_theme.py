#!/usr/bin/env python3
"""
Theme & Styling Instant Applicator
==================================
Quickly refreshes CSS stylesheets (<style>...</style> and style.css) and TOCs
across existing Markdown output files without having to re-run expensive PDF parsing.

Usage:
    python3 scripts/apply_theme.py <book_output_dir>
    python3 scripts/apply_theme.py --all
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Ensure project src/ is on python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.parsers.layout_detector import generate_markdown_toc
from literature_parser.services.style_loader import load_style, load_theme

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def apply_theme_to_directory(output_dir: str | Path) -> int:
    """Applies theme settings to all Markdown files and style.css in an output directory.

    Args:
        output_dir: Directory containing Markdown chapters and optional theme.json.

    Returns:
        int: Number of Markdown files successfully refreshed.
    """
    out_path = Path(output_dir).resolve()
    if not out_path.is_dir():
        logger.error("Directory not found: %s", out_path)
        return 0

    theme = load_theme(out_path)
    style = load_style(out_path)

    # 1. Generate standalone style.css
    typo_cfg = theme.get("typography", {})
    palette_cfg = theme.get("palette", {})
    layout_cfg = theme.get("layout", {})

    css_block = build_textbook_css(style)

    # Strip <style> and </style> tags for external style.css
    raw_css = re.sub(r'</?style>', '', css_block).strip()
    style_css_path = out_path / "style.css"
    style_css_path.write_text(raw_css + "\n", encoding="utf-8")
    logger.info("Updated stylesheet: %s", style_css_path)

    # 2. Iterate through all chapter Markdown files
    md_files = sorted(out_path.glob("*.md"))
    updated_count = 0

    toc_mode = layout_cfg.get("toc_mode", "close")
    toc_depth = layout_cfg.get("toc_depth", 3)
    toc_title = layout_cfg.get("toc_title", "📑 Table of Contents")
    toc_min_headings = layout_cfg.get("toc_min_headings", 2)
    generate_toc = layout_cfg.get("generate_toc", True)
    embed_css = typo_cfg.get("embed_css", True)

    for md_file in md_files:
        # Skip audit reports or global index
        if md_file.name in ("AUDIT.md", "audit_report.md", "index.md"):
            continue

        text = md_file.read_text(encoding="utf-8")
        original_text = text

        # Update or inject embedded <style> block
        if embed_css:
            if "<style>" in text and "</style>" in text:
                text = re.sub(r'<style>[\s\S]*?</style>', css_block.strip(), text, count=1)
            else:
                # Prepend style block
                text = f"{css_block.strip()}\n\n{text}"
        else:
            # Strip embedded style block if embed_css is false
            text = re.sub(r'<style>[\s\S]*?</style>\n*', '', text)

        # Update Table of Contents if present and enabled
        if generate_toc:
            new_toc = generate_markdown_toc(
                text,
                toc_mode=toc_mode,
                toc_depth=toc_depth,
                toc_title=toc_title,
                toc_min_headings=toc_min_headings
            )
            # Check if TOC already exists in file
            toc_match = re.search(r'<details(?:\s+open)?>\s*<summary>📑\s*<b>[^<]*</b></summary>[\s\S]*?</details>\n*', text)
            if toc_match:
                if new_toc:
                    text = text[:toc_match.start()] + new_toc + text[toc_match.end():]
                else:
                    text = text[:toc_match.start()] + text[toc_match.end():]
            elif new_toc:
                # Insert TOC right after first H1
                m_h1 = re.search(r'^(#[^\n]+\n+)', text, re.MULTILINE)
                if m_h1:
                    text = text[:m_h1.end()] + new_toc + "\n" + text[m_h1.end():]

        if text != original_text:
            md_file.write_text(text, encoding="utf-8")
            updated_count += 1
            logger.info("Refreshed styling in: %s", md_file.name)

    return updated_count


def main():
    """Command-line interface entry point."""
    parser = argparse.ArgumentParser(
        description="Instantly apply theme and typography settings to converted Markdown documents."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Path to book output directory (default: current directory)."
    )
    args = parser.parse_args()

    count = apply_theme_to_directory(args.target)
    print(f"✅ Successfully refreshed {count} Markdown file(s) in {args.target}")


if __name__ == "__main__":
    main()
