"""
Shared CLI Utilities and Common Constants
==========================================
"""

import datetime
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def get_current_date() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.date.today().strftime("%Y-%m-%d")


def get_current_timestamp() -> str:
    """Returns current timestamp in YYYY-MM-DD HH:MM format."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def clean_dangling_tmp_files() -> int:
    """Scans and removes leftover *.tmp.* or *.tmp files from interrupted atomic writes."""
    pruned = 0
    for p in ROOT.rglob("*.tmp*"):
        if p.is_file() and not any(part in (".git", ".venv", "node_modules", "staged") for part in p.parts):
            try:
                p.unlink()
                pruned += 1
            except Exception:
                pass
    return pruned


def sync_markdown_dates() -> None:
    """Ensures memory/TASKS.md has today's date in header."""
    tasks_file = ROOT / "memory" / "TASKS.md"
    if tasks_file.exists():
        content = tasks_file.read_text(encoding="utf-8")
        today = get_current_date()
        updated = re.sub(r"最後更新日期：\d{4}-\d{2}-\d{2}", f"最後更新日期：{today}", content)
        tasks_file.write_text(updated, encoding="utf-8")
