"""環境變數存取小工具：config 層是唯一允許讀取 os.environ 的地方，其他層請呼叫這裡的函式。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from literature_parser.config.settings import PROJECT_ROOT, load_dotenv_file

logger = logging.getLogger(__name__)

_TRUE_VALUES = ("1", "true", "yes", "on")
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def ensure_dotenv_loaded() -> None:
    """載入專案根目錄的 `.env`（不覆蓋已存在的環境變數）。"""
    load_dotenv_file(PROJECT_ROOT / ".env")


def get_env(name: str, default: str = "") -> str:
    """讀取環境變數字串。

    Args:
        name: 環境變數名稱。
        default: 未設定時的預設值。

    Returns:
        去除前後空白的值，未設定時回傳 default。
    """
    ensure_dotenv_loaded()
    return os.environ.get(name, default).strip()


def env_flag(name: str, default: bool = False) -> bool:
    """讀取布林旗標環境變數。

    Args:
        name: 環境變數名稱。
        default: 未設定時的預設值。

    Returns:
        值為 1/true/yes/on（不分大小寫）時為 True。
    """
    raw = get_env(name, "")
    if raw == "":
        return default
    return raw.lower() in _TRUE_VALUES


def env_float(name: str, default: float) -> float:
    """讀取浮點數環境變數。

    Args:
        name: 環境變數名稱。
        default: 未設定或格式錯誤時的預設值。

    Returns:
        解析後的浮點數。
    """
    raw = get_env(name, "")
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("環境變數 %s 不是數字，改用預設值 %s", name, default)
        return default


def child_process_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """回傳給子行程使用的環境變數副本。

    Args:
        extra: 額外要加入（或覆蓋）的變數。

    Returns:
        `os.environ` 的複本，並合併 extra。
    """
    env = os.environ.copy()
    if extra:
        env.update(extra)
    return env


def ollama_base_url() -> str:
    """取得本機 Ollama 位址（OLLAMA_HOST 優先，其次 OLLAMA_BASE_URL，預設 127.0.0.1）。

    Returns:
        不含結尾斜線的 URL；`localhost` 會被換成 `127.0.0.1`，缺少 scheme 時補上 http://。
    """
    raw = get_env("OLLAMA_HOST") or get_env("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_URL
    if "://" not in raw:
        raw = f"http://{raw}"
    raw = raw.replace("localhost", "127.0.0.1").replace("0.0.0.0", "127.0.0.1")
    return raw.rstrip("/")


def ollama_default_model(fallback: str) -> str:
    """取得預設 Ollama 模型名稱（OLLAMA_DEFAULT_MODEL）。

    Args:
        fallback: 未設定環境變數時使用的模型。

    Returns:
        模型名稱。
    """
    return get_env("OLLAMA_DEFAULT_MODEL", fallback) or fallback


def min_ram_available_gb(default: float = 4.0) -> float:
    """取得最低可用記憶體門檻（MIN_RAM_AVAILABLE_GB）。

    Args:
        default: 未設定時的預設值（GB）。

    Returns:
        門檻（GB）。
    """
    return env_float("MIN_RAM_AVAILABLE_GB", default)


def min_disk_free_gb(default: float = 5.0) -> float:
    """取得最低可用磁碟空間門檻（MIN_DISK_FREE_GB）。

    Args:
        default: 未設定時的預設值（GB）。

    Returns:
        門檻（GB）。
    """
    return env_float("MIN_DISK_FREE_GB", default)


def allow_battery_mode() -> bool:
    """是否允許在電池模式下執行（ALLOW_BATTERY_MODE）。

    Returns:
        允許時為 True。
    """
    return env_flag("ALLOW_BATTERY_MODE", False)


def allow_push() -> bool:
    """是否允許 git push（ALLOW_PUSH）。

    Returns:
        允許時為 True。
    """
    return env_flag("ALLOW_PUSH", False)


def resources_dir() -> Path:
    """內建 JSON 資源資料夾（archetypes / publishers / shared_knowledge / profiles）。

    Returns:
        `src/literature_parser/config/resources` 的絕對路徑。
    """
    return Path(__file__).resolve().parent / "resources"
