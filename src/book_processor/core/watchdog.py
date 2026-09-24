"""
System & Input Watchdog Monitor
===============================
Monitors the inbox folder for newly added textbooks, inspects system health
(free disk space, CPU load, thermal safety), and notifies the user for immediate action.

NOTE: The canonical user-facing watchdog is ``run.py watchdog``, which monitors
``data/input/books/`` and ``data/input/literature/``.
WatchdogService is the underlying implementation and can be used for API integration.
Default directory constants in ``config.py`` now correctly point to ``data/input/books/``.
"""

import logging
import os
import sys
import time
import shutil
from pathlib import Path
from book_processor.config import (
    DEFAULT_INBOX_DIR,
    DEFAULT_PROCESSED_DIR,
    DEFAULT_OUTPUT_DIR,
    MIN_DISK_FREE_GB,
    MAX_CPU_LOAD_PERCENT,
    DEFAULT_WATCHDOG_INTERVAL_SECS,
    MAX_ALERT_LOG_BYTES,
)

logger = logging.getLogger(__name__)


class WatchdogService:
    """Monitors incoming books and host system health metrics."""

    def __init__(
        self,
        inbox_dir: str = DEFAULT_INBOX_DIR,
        processed_dir: str = DEFAULT_PROCESSED_DIR,
        output_dir: str = DEFAULT_OUTPUT_DIR
    ):
        self.inbox_dir = Path(inbox_dir).resolve()
        self.processed_dir = Path(processed_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.known_files = set()
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.output_dir / "watchdog_status.md"
        self.alerts_file = self.output_dir / "watchdog_alerts.log"

    def check_system_health(self) -> dict:
        """Audits available disk capacity and CPU load metrics."""
        health = {'healthy': True, 'warnings': []}

        # 1. Disk space check
        try:
            total, used, free = shutil.disk_usage(str(self.output_dir))
            free_gb = free / (1024 ** 3)
            health['free_disk_gb'] = round(free_gb, 2)
            if free_gb < MIN_DISK_FREE_GB:
                health['healthy'] = False
                health['warnings'].append(
                    f"LOW DISK SPACE WARNING: Only {free_gb:.1f} GB remaining on output volume (threshold: {MIN_DISK_FREE_GB} GB)."
                )
        except Exception as e:
            health['warnings'].append(f"Disk check error: {e}")

        # 2. CPU load check
        try:
            if hasattr(os, 'getloadavg'):
                load_1m, _, _ = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                load_pct = (load_1m / cpu_count) * 100.0
                health['cpu_load_pct'] = round(load_pct, 1)
                if load_pct > MAX_CPU_LOAD_PERCENT:
                    health['warnings'].append(
                        f"HIGH CPU LOAD WARNING: Current load is {load_pct:.1f}% ({load_1m:.2f} on {cpu_count} cores). Potential overheating risk."
                    )
        except Exception as e:
            health['warnings'].append(f"CPU check error: {e}")

        return health

    def scan_inbox(self) -> list:
        """Finds newly deposited PDF and EPUB files in the inbox directory."""
        if not self.inbox_dir.exists():
            return []

        candidates = [
            f for f in self.inbox_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ('.pdf', '.epub')
            and not f.name.startswith('.')
        ]

        # Verify file write completion (file size not currently changing)
        ready_files = []
        for f in candidates:
            try:
                s1 = f.stat().st_size
                time.sleep(0.05)
                s2 = f.stat().st_size
                if s1 == s2 and s1 > 0:
                    ready_files.append(f)
            except Exception:
                pass

        return ready_files

    def log_alert(self, message: str) -> None:
        """Appends timestamped alert to watchdog_alerts.log, rotating at MAX_ALERT_LOG_BYTES."""
        import book_processor.config as _cfg
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        try:
            # Rotate if too large (read threshold dynamically to allow patching in tests)
            limit = _cfg.MAX_ALERT_LOG_BYTES
            if self.alerts_file.exists() and self.alerts_file.stat().st_size >= limit:
                rotated = self.alerts_file.with_suffix(".log.1")
                self.alerts_file.replace(rotated)
            with open(self.alerts_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as e:
            logger.warning("Watchdog: could not write alert log – %s", e)


    def scan_stuck_books(self) -> list:
        """
        Scans the output directory for books that have FAILED or SPLIT chapters
        that were never converted.  Returns a list of (book_name, pending_count) tuples.
        """
        import json
        stuck = []
        if not self.output_dir.exists():
            return stuck
        for book_dir in self.output_dir.iterdir():
            if not book_dir.is_dir():
                continue
            status_json = book_dir / "processing_status.json"
            if not status_json.exists():
                continue
            try:
                with open(status_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pending = [
                    name
                    for name, info in data.get("chapters", {}).items()
                    if info.get("status") not in ("VERIFIED",)
                ]
                if pending:
                    stuck.append((book_dir.name, len(pending), pending[:3]))
            except (json.JSONDecodeError, OSError):
                pass
        return stuck

    def update_status_dashboard(self, new_books: list, health: dict) -> None:
        """Writes real-time status markdown for user and AI agents."""
        import tempfile
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "# Watchdog Monitor Dashboard",
            "",
            f"- **Last Audit Timestamp**: `{timestamp}`",
            f"- **Inbox Directory**: `{self.inbox_dir}`",
            f"- **Processed Directory**: `{self.processed_dir}`",
            f"- **Free Disk Space**: `{health.get('free_disk_gb', 'N/A')} GB`",
            f"- **CPU Load (1m avg)**: `{health.get('cpu_load_pct', 'N/A')}%`",
            "",
            "## System Health Status",
        ]
        if health.get("warnings"):
            for w in health["warnings"]:
                lines.append(f"> [!WARNING]\n> {w}\n")
        else:
            lines.append("> [✓] All system health metrics are normal.\n")

        lines.append(f"## Inbox Pending Books ({len(new_books)})")
        if new_books:
            lines.append("| Book File | Size | Status |")
            lines.append("| :--- | :--- | :--- |")
            for b in new_books:
                sz_mb = b.stat().st_size / (1024 * 1024)
                lines.append(f"| `{b.name}` | {sz_mb:.1f} MB | `AWAITING_PROCESSING` |")
        else:
            lines.append("*Inbox is currently empty. Drop new PDF or EPUB files here to begin.*")

        stuck = self.scan_stuck_books()
        lines.append(f"\n## Stuck / Partially Converted Books ({len(stuck)})")
        if stuck:
            lines.append("| Book | Pending Chapters | Examples |")
            lines.append("| :--- | :---: | :--- |")
            for book_name, count, examples in stuck:
                ex_str = ", ".join(examples)
                lines.append(f"| `{book_name}` | {count} | {ex_str}… |")
            lines.append("\n> [!NOTE]\n> Run `python3 book_processor.py resume --file <book_path>` to continue.\n")
        else:
            lines.append("*All output books are fully verified.*")

        lines.append("")
        try:
            fd, tmp = tempfile.mkstemp(dir=str(self.status_file.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            os.replace(tmp, str(self.status_file))
        except OSError as e:
            logger.warning("Watchdog: could not write status dashboard – %s", e)


    def start_monitoring(
        self,
        interactive: bool = True,
        auto_process: bool = False,
        interval: float = DEFAULT_WATCHDOG_INTERVAL_SECS,
        on_new_book_callback = None
    ):
        """
        Main monitoring loop.
        Notifies user interactively or executes callback upon detecting new books.
        """
        print(f"\n{'='*70}")
        print(f"[WATCHDOG STARTED] Monitoring '{self.inbox_dir}' (Interval: {interval}s)")
        print(f"{'='*70}")
        print(f"  • Inbox Path: {self.inbox_dir}")
        print(f"  • Processed Archive: {self.processed_dir}")
        print(f"  • Status Dashboard: {self.status_file}")
        print(f"  • Press Ctrl+C to halt monitor safely.\n")

        # Initial seed
        initial = self.scan_inbox()
        self.known_files = {f.name for f in initial}

        try:
            while True:
                health = self.check_system_health()
                current_files = self.scan_inbox()

                self.update_status_dashboard(current_files, health)

                # Report any health warnings
                if health['warnings']:
                    for w in health['warnings']:
                        print(f"\n[!] \033[33m{w}\033[0m")
                        self.log_alert(w)

                # Detect newly added files
                for book_file in current_files:
                    if book_file.name not in self.known_files:
                        self.known_files.add(book_file.name)
                        sz_mb = book_file.stat().st_size / (1024 * 1024)
                        msg = f"New textbook detected in inbox: '{book_file.name}' ({sz_mb:.1f} MB)"
                        print(f"\n[🔔 WATCHDOG ALERT] \033[32m{msg}\033[0m")
                        self.log_alert(msg)

                        if auto_process:
                            print(f"  -> Auto-processing enabled. Starting pipeline for: {book_file.name}...")
                            if on_new_book_callback:
                                on_new_book_callback(str(book_file))
                        elif interactive:
                            prompt = f"  Would you like to start processing '{book_file.name}' now? [y/N]: "
                            try:
                                ans = input(prompt).strip().lower()
                                if ans in ('y', 'yes'):
                                    if on_new_book_callback:
                                        on_new_book_callback(str(book_file))
                                else:
                                    print(f"  [i] Skipped for now. Book remains in inbox: {book_file.name}")
                            except (EOFError, KeyboardInterrupt):
                                print("\n[!] Watchdog interrupted.")
                                return

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[!] Watchdog stopped by user.")
