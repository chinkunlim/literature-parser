"""
Processing Status Manifest & Checkpoint Manager
================================================
Tracks chapter state in both a human-readable Markdown dashboard
(processing_status.md) and machine-readable JSON (processing_status.json)
to support graceful pause & resume.

All file writes use an atomic temp-file → rename pattern to prevent
checkpoint corruption if the process is killed mid-write.
"""

import datetime
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _atomic_write(path: Path, text: str) -> None:
    """Write *text* to *path* atomically via a sibling temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class CheckpointManager:
    """Manages chapter lifecycle states: PENDING, SPLIT, CONVERTED, VERIFIED, FAILED."""

    def __init__(self, book_dir: str, book_title: str) -> None:
        self.book_dir = Path(book_dir)
        self.book_title = book_title
        self.json_path = self.book_dir / "processing_status.json"
        self.md_path = self.book_dir / "processing_status.md"
        self.data = self._load()

    def _load(self) -> dict:
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "CheckpointManager: could not load '%s' – %s. Starting fresh.",
                    self.json_path.name, e,
                )
        return {
            "book_title": self.book_title,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chapters": {},
        }

    def init_chapters(self, sections: list) -> None:
        """Initializes chapters in manifest if not already present."""
        for s in sections:
            name = s["name"]
            if name not in self.data["chapters"]:
                self.data["chapters"][name] = {
                    "start_page": s["start"],
                    "end_page": s["end"],
                    "total_pages": s["end"] - s["start"] + 1,
                    "status": "PENDING",
                    "split_pdf": False,
                    "markdown_generated": False,
                    "images_count": 0,
                    "verification_pass": None,
                    "accuracy_percent": None,
                    "last_updated": None,
                }
        self.save()

    def update_status(self, chapter_name: str, **kwargs) -> None:
        """Updates status of a specific chapter."""
        self.data = self._load()
        if chapter_name not in self.data["chapters"]:
            self.data["chapters"][chapter_name] = {}
        self.data["chapters"][chapter_name].update(kwargs)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data["chapters"][chapter_name]["last_updated"] = now
        self.data["last_updated"] = now
        self.save()

    def is_chapter_verified(self, chapter_name: str) -> bool:
        """Returns True if the chapter has been verified and can be skipped on resume."""
        self.data = self._load()
        ch = self.data["chapters"].get(chapter_name, {})
        return ch.get("status") == "VERIFIED" and ch.get("split_pdf") and ch.get("markdown_generated") and ch.get("verification_pass") is True


    def get_pending_chapters(self) -> list:
        """Returns list of chapter names that still need processing."""
        return [
            name
            for name, info in self.data["chapters"].items()
            if info.get("status") != "VERIFIED"
        ]

    def save(self) -> None:
        """Atomically writes both JSON checkpoint and Markdown progress dashboard."""
        os.makedirs(self.book_dir, exist_ok=True)

        # 1. Save JSON (atomic)
        try:
            _atomic_write(
                self.json_path,
                json.dumps(self.data, indent=2, ensure_ascii=False),
            )
        except OSError as e:
            logger.error("CheckpointManager: failed to write JSON checkpoint – %s", e)

        # 2. Render Markdown Dashboard (atomic)
        try:
            _atomic_write(self.md_path, self._render_markdown())
        except OSError as e:
            logger.error("CheckpointManager: failed to write Markdown dashboard – %s", e)

        # 3. Synchronize with Global State Manager (atomic)
        try:
            from doc_processor.core.global_state import GlobalStateManager
            gsm = GlobalStateManager()
            doc_type = "literature" if "literature" in str(self.book_dir) else "book"
            gsm.update_book(self.book_title, self.data.get("chapters", {}), doc_type=doc_type)
        except Exception as e:
            logger.debug("CheckpointManager: global state sync skipped – %s", e)

    def _render_markdown(self) -> str:

        total = len(self.data["chapters"])
        verified = sum(
            1 for c in self.data["chapters"].values() if c.get("status") in ("VERIFIED", "CONVERTED")
        )
        percent = (verified / total * 100) if total > 0 else 0

        # Visual progress bar (20 characters)
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)

        lines = [
            f"# Processing Status: {self.book_title}\n",
            f"**Progress**: `[{bar}]` **{percent:.1f}%** ({verified}/{total} completed)\n",
            f"- **Total Chapters**: {total}",
            f"- **Verified & Complete**: {verified} / {total} ({percent:.1f}%)",
            f"- **Last Session Updated**: {self.data['last_updated']}",
            "- **Resume Command**: `python3 doc_processor.py resume --file \"<path_to_book>\"`\n",
            "| Chapter | Page Range | Split PDF | Markdown | Images | Verification | Status |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |",
        ]

        for name, info in self.data["chapters"].items():
            p_range = f"pp. {info.get('start_page', '?')}-{info.get('end_page', '?')}"
            split_str = "[✓]" if info.get("split_pdf") else "[ ]"
            md_str = "[✓]" if info.get("markdown_generated") else "[ ]"
            img_str = str(info.get("images_count", 0))

            v_pass = info.get("verification_pass")
            acc = info.get("accuracy_percent")
            if v_pass is True:
                v_str = f"✅ PASS ({acc:.1f}%)" if acc is not None else "✅ PASS"
            elif v_pass is False:
                v_str = f"❌ FAIL ({acc:.1f}%)" if acc is not None else "❌ FAIL"
            else:
                v_str = "⏳ Pending"

            status = info.get("status", "PENDING")
            status_badge = {
                "VERIFIED": "🟢 `VERIFIED`",
                "CONVERTED": "🟢 `CONVERTED`",
                "FAILED": "🔴 `FAILED`",
                "SPLIT": "🟡 `SPLIT`",
                "PENDING": "⚪ `PENDING`"
            }.get(status, f"`{status}`")

            lines.append(
                f"| **{name}** | {p_range} | {split_str} | {md_str} | {img_str} | {v_str} | {status_badge} |"
            )

        return "\n".join(lines) + "\n"

