"""
Global State Manager
====================
Maintains data/state/global_status.json as the central source of truth
for all book and literature processing lifecycle states across the project.

Updated atomically whenever CheckpointManager saves a chapter state.
Supports bootstrapping from existing data/output/ directories.
"""

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

_STATE_FILE_NAME = "global_status.json"


def find_project_root() -> Path:
    """Finds project root by looking for pyproject.toml or run.py upwards."""
    cur = Path(__file__).resolve().parent
    for parent in [cur] + list(cur.parents):
        if (parent / "pyproject.toml").exists() or (parent / "run.py").exists():
            return parent
    return cur.parents[3]  # fallback


class GlobalStateManager:
    """
    Centralized progress state manager with atomic JSON writes.
    Path: <project_root>/data/state/global_status.json
    """

    def __init__(self, state_dir: Optional[Path | str] = None):
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            from literature_parser.config.settings import load_config
            self.state_dir = load_config().state_dir

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / _STATE_FILE_NAME

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_updated": None, "books": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.state_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, str(self.state_file))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def update_book(self, book_title: str, chapters: Dict[str, Any], doc_type: str = "book") -> Dict[str, Any]:
        """
        Recomputes aggregated progress metrics for a book and saves atomically.
        """
        data = self._load()
        total = len(chapters)
        verified = sum(
            1 for c in chapters.values()
            if c.get("status") in ("VERIFIED", "COMPLETE") or c.get("verification_pass") is True
        )
        failed = sum(
            1 for c in chapters.values()
            if c.get("status") == "FAILED" or c.get("verification_pass") is False
        )
        pending_review = sum(
            1 for c in chapters.values()
            if c.get("has_pending_review") is True or c.get("ai_review_saved") is True
        )

        if total > 0 and verified == total:
            status = "COMPLETE"
        elif failed > 0:
            status = "HAS_FAILURES"
        elif verified > 0:
            status = "IN_PROGRESS"
        else:
            status = "PENDING"

        progress_pct = round(verified / total * 100) if total > 0 else 0

        data.setdefault("books", {})[book_title] = {
            "doc_type": doc_type,
            "total_chapters": total,
            "verified": verified,
            "failed": failed,
            "pending_review": pending_review,
            "status": status,
            "progress_pct": progress_pct,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self._save(data)
        return data["books"][book_title]

    def sync_from_output_dir(self, output_root: Optional[Path | str] = None) -> int:
        """
        Scans data/output/ recursively for processing_status.json files
        and reconstructs global_status.json.
        """
        if not output_root:
            from literature_parser.config.settings import load_config
            output_root = load_config().output_dir
        out_path = Path(output_root)
        if not out_path.is_dir():
            return 0

        synced = 0
        for status_json in out_path.rglob("processing_status.json"):
            try:
                with open(status_json, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                title = book_data.get("book_title") or book_data.get("doc_name") or status_json.parent.name
                doc_type = "literature" if ("literature" in str(status_json) or book_data.get("archetype") == "journal") else "book"
                if book_data.get("chapters"):
                    chapters = book_data["chapters"]
                else:
                    passed = book_data.get("passed", False)
                    chapters = {
                        title: {
                            "status": "VERIFIED" if passed else "FAILED",
                            "verification_pass": passed,
                        }
                    }
                self.update_book(title, chapters, doc_type=doc_type)
                synced += 1
            except Exception:
                continue
        return synced


    def get_all(self) -> Dict[str, Any]:
        """Returns the complete global state dictionary."""
        return self._load()
