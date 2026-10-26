"""
Obsidian Backlink Generator
===========================
Adds inter-chapter navigation footers and a book-level index.md
for Obsidian Graph View and inter-note cross-referencing.
"""

import datetime
import re
from pathlib import Path
from typing import Any, Dict, List


def sanitize_obsidian_slug(name: str) -> str:
    """Converts a chapter name to an Obsidian-safe wikilink slug."""
    clean = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[\s_]+', '_', clean).lower()


def generate_book_index(book_out_dir: Path | str, chapters: List[Dict[str, Any]]) -> Path:
    """
    Generates index.md in book_out_dir linking all chapters with Obsidian wikilinks.
    chapters: list of dicts with at least 'name' and 'md_path'.
    """
    out_dir = Path(book_out_dir)
    index_path = out_dir / "index.md"
    book_title = out_dir.name

    lines = [
        f"# 📚 {book_title}",
        "",
        "> [!NOTE] 本索引由系統自動生成，在 Obsidian 中開啟可瀏覽全局知識圖譜 (Graph View)。",
        "",
        "## 章節目錄",
        "",
    ]

    for ch in chapters:
        name = ch.get("name", "")
        slug = sanitize_obsidian_slug(name)
        lines.append(f"- [[{slug}|{name}]]")

    lines += [
        "",
        "---",
        f"*自動生成時間：{datetime.date.today().strftime('%Y-%m-%d')}*",
        "",
    ]

    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def inject_chapter_navigation(chapters: List[Dict[str, Any]]) -> int:
    """
    Appends prev/next navigation footer to each chapter's Markdown file.
    chapters: ordered list of dicts with 'name' and 'md_path' (Path or str).
    Returns count of files modified.
    """
    modified = 0
    n = len(chapters)

    for i, ch in enumerate(chapters):
        raw_path = ch.get("md_path")
        if not raw_path:
            continue
        md_path = Path(raw_path)
        if not md_path.exists():
            continue

        try:
            existing = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Remove any existing navigation blocks (standard or corrupted) to allow clean re-generation
        cleaned_existing = re.sub(r'<![-—–]+\s*OBSIDIAN_NAV_START[\s\S]*?OBSIDIAN_NAV_END\s*[-—–]+>', '', existing).rstrip()

        prev_link = ""
        next_link = ""
        if i > 0:
            prev_name = chapters[i - 1].get("name", "")
            prev_slug = sanitize_obsidian_slug(prev_name)
            prev_link = f"← [[{prev_slug}|{prev_name}]]"

        if i < n - 1:
            next_name = chapters[i + 1].get("name", "")
            next_slug = sanitize_obsidian_slug(next_name)
            next_link = f"[[{next_slug}|{next_name}]] →"

        if not prev_link and not next_link:
            continue

        sep = " &nbsp;&nbsp;|&nbsp;&nbsp; " if prev_link and next_link else ""
        nav = (
            "\n\n<!-- OBSIDIAN_NAV_START -->\n"
            "---\n\n"
            f"<div align=\"center\">\n\n{prev_link}{sep}{next_link}\n\n</div>\n"
            "<!-- OBSIDIAN_NAV_END -->\n"
        )

        new_text = cleaned_existing + nav
        if new_text != existing:
            md_path.write_text(new_text, encoding="utf-8")
            modified += 1

    return modified
