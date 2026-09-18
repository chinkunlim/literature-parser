"""
Centralised Logging Setup
=========================
All book-processor modules use Python's standard `logging` module.
Call `setup_logging(book_dir)` once per pipeline run to configure:
  - A rotating file handler that writes DEBUG+ to `<book_dir>/error.log`
  - A StreamHandler that writes INFO+ to stdout

Modules import the package-level logger:
    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(book_dir: str | None = None, verbose: bool = False) -> None:
    """
    Configure logging for the book processor pipeline.

    Args:
        book_dir: If provided, attaches a RotatingFileHandler to ``<book_dir>/error.log``.
        verbose:  If True, stdout handler shows DEBUG messages (default: INFO).
    """
    root = logging.getLogger("book_processor")
    if root.handlers:
        # Already configured – avoid adding duplicate handlers on re-entry.
        return

    root.setLevel(logging.DEBUG)

    # ---- stdout handler ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root.addHandler(console)

    # ---- file handler ----
    if book_dir:
        log_path = Path(book_dir) / "error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            str(log_path),
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(fh)
