"""
Global Configuration & Constants for Book Processor
===================================================
All tuneable thresholds, paths, and defaults in one place.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rendering & Image Settings
# ---------------------------------------------------------------------------
DEFAULT_DPI = 300
# If an image covers >= COVERAGE_THRESHOLD fraction of the page area, treat it as
# a full-page background scan and discard it (not a pedagogical figure).
COVERAGE_THRESHOLD = 0.80
# Minimum pixel dimensions to be considered a full-page scan.
FULL_PAGE_MIN_PX = 1000
MIN_IMAGE_SIZE_BYTES = 100
MAX_FILENAME_LEN = 120

# ---------------------------------------------------------------------------
# Local Paths & Dictionaries
# ---------------------------------------------------------------------------
# System dictionary – try common locations; gracefully skip if absent.
_DICT_CANDIDATES = [
    "/usr/share/dict/words",   # macOS + most Linux distros
    "/usr/dict/words",          # older BSD / Solaris
    "/usr/share/dict/american-english",  # Debian/Ubuntu
]
DEFAULT_DICT_PATH = next((p for p in _DICT_CANDIDATES if os.path.exists(p)), "")

from literature_parser.config.settings import load_config as _load_app_config
_app_cfg = _load_app_config()

DEFAULT_DATA_DIR = str(_app_cfg.data_dir)
DEFAULT_INPUT_DIR = str(_app_cfg.input_dir / "books")
DEFAULT_OUTPUT_DIR = str(_app_cfg.output_dir / "books")
DEFAULT_INBOX_DIR = str(_app_cfg.input_dir / "books")
DEFAULT_PROCESSED_DIR = str(_app_cfg.processed_dir)
DEFAULT_PROCESSED_BOOKS_DIR = str(_app_cfg.processed_books_dir)
DEFAULT_PROCESSED_LITERATURE_DIR = str(_app_cfg.processed_literature_dir)
DEFAULT_NEEDS_REVIEW_DIR = str(_app_cfg.needs_review_dir)
DEFAULT_STATE_DIR = str(_app_cfg.state_dir)

# Global learned-rules store (survives individual book cleanups).
GLOBAL_RULES_DIR = Path.home() / ".doc_processor"

# ---------------------------------------------------------------------------
# System Watchdog Thresholds
# ---------------------------------------------------------------------------
MIN_DISK_FREE_GB = 5.0
MAX_CPU_LOAD_PERCENT = 85.0
DEFAULT_WATCHDOG_INTERVAL_SECS = 5.0
MAX_ALERT_LOG_BYTES = 1_000_000  # 1 MB – rotate when exceeded

# ---------------------------------------------------------------------------
# Local Ollama AI Settings
# ---------------------------------------------------------------------------
OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_SEMANTIC_MODEL = "gemma4:12b"             # General semantic/reading model
DEFAULT_OLLAMA_HEALER_MODEL = "qwen2.5-coder:7b"         # Specialized coding/healing model
DEFAULT_OLLAMA_VISION_MODEL = "minicpm-v:latest"         # Local multimodal model (MiniCPM-V)
OLLAMA_GENERATE_TIMEOUT = 180.0  # seconds; allows 7b-14b local models sufficient evaluation time

# ---------------------------------------------------------------------------
# AI Review Confidence
# ---------------------------------------------------------------------------
# Proposals with confidence >= this threshold are auto-accepted without HITL.
AUTO_ACCEPT_CONFIDENCE_THRESHOLD = 0.95

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------
# Number of consecutive chapter failures that trip the circuit breaker.
CIRCUIT_BREAKER_MAX_FAILURES = 3

# ---------------------------------------------------------------------------
# Noise Filtering Regex Patterns (Running footers / copyright statements to strip)
# ---------------------------------------------------------------------------
FOOTER_NOISE_PATTERNS = [
    r'\bcopyright\s+\d{4}\b',
    r'\ball\s+rights\s+reserved\b',
    r'\bmay\s+not\s+be\s+copied\b',
    r'\bwcn\s+02-\d+\b',
    r'\bisbn\b',
    r'\bdigitized\s+by\s+the\s+internet\s+archive\b'
]

# ---------------------------------------------------------------------------
# Running Header Identification Patterns
# ---------------------------------------------------------------------------
HEADER_NOISE_PATTERNS = [
    r'^(?:[ivxlcdm]+|\d+)\s*$',
    r'^(?:Chapter|Part|Section|Contents)\b',
    r'/\s*(?:contents|index|[ivxlcdm]+|\d+)\b'
]
