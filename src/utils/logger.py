"""
Structured Diagnostic Logger
============================
Mandates structured logging containing (Where, Why, How to Fix)
to ensure transparent, actionable error reporting without generic silent failures.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
DEFAULT_LOG_FILE = LOG_DIR / "process.log"


class DiagnosticLogger:
    """Wraps Python standard logger with structured diagnostic formatting."""

    def __init__(self, name: str, log_file: Path = DEFAULT_LOG_FILE):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            # Console handler (clean format)
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            c_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S")
            ch.setFormatter(c_formatter)
            self.logger.addHandler(ch)

            # File handler (detailed format)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            f_formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S")
            fh.setFormatter(f_formatter)
            self.logger.addHandler(fh)

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, **kwargs)

    def warning(self, where: str, why: str, how_to_fix: str = None):
        msg = f"\n⚠️  [DIAGNOSTIC WARNING]\n  • WHERE: {where}\n  • WHY:   {why}"
        if how_to_fix:
            msg += f"\n  • FIX:   {how_to_fix}"
        self.logger.warning(msg)

    def error(self, where: str, why: str, how_to_fix: str = None):
        msg = f"\n🛑 [DIAGNOSTIC ERROR]\n  • WHERE: {where}\n  • WHY:   {why}"
        if how_to_fix:
            msg += f"\n  • FIX:   {how_to_fix}"
        self.logger.error(msg)


def get_diagnostic_logger(name: str = "app") -> DiagnosticLogger:
    return DiagnosticLogger(name)
