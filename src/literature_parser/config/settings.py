"""Configuration layer: the ONLY layer allowed to read environment variables.

Loads settings once at startup into an immutable `AppConfig` so every other layer
receives plain values instead of touching `os.environ`.

Data lives OUTSIDE the project folder: `DATA_DIR` (default `../../projects-data/literature-parser`) holds
input/, output/, needs_review/, state/, db/ and logs/. The project folder only holds code,
docs and small test fixtures. A relative `DATA_DIR` is resolved from the project folder (never
from the current working directory), so the project and its data can be moved together.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = "../../projects-data/literature-parser"


def resolve_data_dir(raw: str) -> Path:
    """Turn a `DATA_DIR` value into an absolute path.

    Args:
        raw: Value from `.env`; relative paths are relative to the project folder, `~` is expanded.

    Returns:
        The absolute data folder.
    """
    path = Path(raw.strip()).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


PROJECT_FILE_WINS = ("DATA_DIR",)


def load_dotenv_file(path: Path) -> None:
    """Load `KEY=value` lines from a `.env` file without overriding variables that are already set.

    Keys in `PROJECT_FILE_WINS` override `os.environ` so inherited shell variables
    (e.g. Open WebUI's DATA_DIR) cannot redirect the project's data folder.

    Args:
        path: The `.env` file (missing files are ignored).
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            k, v = key.strip(), value.strip().strip("\"'")
            if k in PROJECT_FILE_WINS:
                os.environ[k] = v
            else:
                os.environ.setdefault(k, v)


@dataclass(frozen=True)
class AppConfig:
    """Immutable application settings.

    Attributes:
        app_env: Deployment environment name, e.g. `development` or `production`.
        log_level: Logging level name, e.g. `INFO` or `DEBUG`.
        log_to_file: Also write `<data_dir>/logs/app.log` and `errors.log` (default on; tests turn it off).
        timeout_seconds: Timeout for outgoing API calls.
        ollama_base_url: Local Ollama endpoint (always 127.0.0.1, never localhost / 0.0.0.0).
        data_dir: Root folder for all data, outside the project folder.
    """

    app_env: str = "development"
    log_level: str = "INFO"
    log_to_file: bool = True
    timeout_seconds: int = 15
    ollama_base_url: str = "http://127.0.0.1:11434"
    data_dir: Path = resolve_data_dir(DEFAULT_DATA_DIR)

    @property
    def input_dir(self) -> Path:
        """Folder with files waiting to be processed.

        Returns:
            `<data_dir>/input`.
        """
        return self.data_dir / "input"

    @property
    def output_dir(self) -> Path:
        """Folder for produced results.

        Returns:
            `<data_dir>/output`.
        """
        return self.data_dir / "output"

    @property
    def needs_review_dir(self) -> Path:
        """Quarantine for failed or low-confidence items (batches never stop for them).

        Returns:
            `<data_dir>/needs_review`.
        """
        return self.data_dir / "needs_review"

    @property
    def processed_dir(self) -> Path:
        """Base folder for processed archives.

        Returns:
            `<data_dir>/input/processed`.
        """
        return self.input_dir / "processed"

    @property
    def processed_books_dir(self) -> Path:
        """Folder for fully processed and verified books.

        Returns:
            `<data_dir>/input/processed/processed-books`.
        """
        return self.input_dir / "processed" / "processed-books"

    @property
    def processed_literature_dir(self) -> Path:
        """Folder for fully processed and verified literature.

        Returns:
            `<data_dir>/input/processed/processed-literature`.
        """
        return self.input_dir / "processed" / "processed-literature"

    @property
    def state_dir(self) -> Path:
        """Folder for progress / resume state.

        Returns:
            `<data_dir>/state`.
        """
        return self.data_dir / "state"

    @property
    def logs_dir(self) -> Path:
        """Folder for log files.

        Returns:
            `<data_dir>/logs`.
        """
        return self.data_dir / "logs"


def _flag(value: str) -> bool:
    """Interpret an environment flag.

    Args:
        value: Raw text such as `1`, `true`, `yes`.

    Returns:
        True for 1 / true / yes / on (case-insensitive).
    """
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_config() -> AppConfig:
    """Read and validate configuration from `.env` and environment variables.

    Returns:
        A populated `AppConfig`.

    Raises:
        ValueError: When a numeric setting is not an integer.
    """
    load_dotenv_file(PROJECT_ROOT / ".env")
    data_dir = resolve_data_dir(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR))
    return AppConfig(
        app_env=os.environ.get("APP_ENV", "development").strip(),
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper(),
        log_to_file=_flag(os.environ.get("LOG_TO_FILE", "true")),
        timeout_seconds=int(os.environ.get("API_TIMEOUT_SECONDS", "15")),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/"),
        data_dir=data_dir,
    )
