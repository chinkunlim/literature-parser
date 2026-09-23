"""
Hardware Pre-flight Guard
=========================
Performs real-time system capability checks before invoking heavy models or batch OCR:
- Available RAM threshold (>= 4.0 GB)
- Battery & AC Power detection (macOS pmset)
- Available Disk Space threshold (>= 10.0 GB)
- Apple Silicon Metal Performance Shaders (MPS) availability
"""

import sys
import shutil
import platform
import subprocess
from pathlib import Path
from src.utils.logger import get_diagnostic_logger

logger = get_diagnostic_logger("HardwareGuard")

MIN_RAM_GB = 4.0
MIN_DISK_GB = 10.0
MIN_BATTERY_PERCENT = 40


def get_available_ram_gb() -> float:
    """Returns available RAM in Gigabytes using psutil or macOS vm_stat fallback."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        pass

    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["vm_stat"], text=True)
            page_size = 4096
            free_pages = 0
            speculative_pages = 0
            for line in out.splitlines():
                if "page size of" in line:
                    parts = line.split()
                    for p in parts:
                        if p.isdigit():
                            page_size = int(p)
                            break
                elif "Pages free:" in line:
                    free_pages = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages speculative:" in line:
                    speculative_pages = int(line.split(":")[1].strip().rstrip("."))
            return ((free_pages + speculative_pages) * page_size) / (1024 ** 3)
        except Exception:
            return 8.0  # safe assumption if cannot detect
    return 8.0


def get_battery_status() -> dict:
    """Detects if running on battery and current percentage on macOS."""
    status = {"is_battery": False, "percent": 100, "description": "AC Power Connected"}
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
            if "Battery Power" in out:
                status["is_battery"] = True
                for line in out.splitlines():
                    if "%" in line:
                        parts = line.split("\t")
                        if len(parts) > 1:
                            pct_str = parts[1].split("%")[0].strip()
                            if pct_str.isdigit():
                                status["percent"] = int(pct_str)
                                status["description"] = f"Battery Mode ({status['percent']}%)"
                                break
            else:
                status["description"] = "AC Power Connected (Charging/Charged)"
        except Exception as e:
            status["description"] = f"Unknown power state: {e}"
    return status


def get_disk_free_gb(path: str = ".") -> float:
    """Returns free disk space in Gigabytes."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024 ** 3)
    except Exception:
        return 50.0


def is_mps_available() -> bool:
    """Checks if PyTorch Apple Silicon MPS acceleration is enabled."""
    try:
        import torch
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except Exception:
        return False


def check_hardware_safety(ignore_battery: bool = False) -> dict:
    """
    Comprehensive pre-flight evaluation.
    Returns:
        dict: {'safe_for_heavy_llm': bool, 'safe_for_batch_ocr': bool, 'metrics': dict, 'reasons': list}
    """
    ram_gb = get_available_ram_gb()
    disk_gb = get_disk_free_gb()
    batt = get_battery_status()
    mps = is_mps_available()

    reasons = []
    safe_for_heavy_llm = True
    safe_for_batch_ocr = True

    # 1. RAM check
    if ram_gb < MIN_RAM_GB:
        safe_for_heavy_llm = False
        reasons.append(f"Available RAM ({ram_gb:.2f} GB) is lower than safe threshold ({MIN_RAM_GB} GB).")

    # 2. Disk check
    if disk_gb < MIN_DISK_GB:
        safe_for_batch_ocr = False
        reasons.append(f"Available Disk ({disk_gb:.1f} GB) is lower than safe threshold ({MIN_DISK_GB} GB).")

    # 3. Battery check
    if batt["is_battery"] and not ignore_battery:
        if batt["percent"] < MIN_BATTERY_PERCENT:
            safe_for_heavy_llm = False
            reasons.append(f"Battery mode active and charge is low ({batt['percent']}% < {MIN_BATTERY_PERCENT}%).")

    return {
        "safe_for_heavy_llm": safe_for_heavy_llm,
        "safe_for_batch_ocr": safe_for_batch_ocr,
        "metrics": {
            "ram_available_gb": round(ram_gb, 2),
            "disk_free_gb": round(disk_gb, 1),
            "power_status": batt["description"],
            "is_battery": batt["is_battery"],
            "battery_percent": batt["percent"],
            "mps_acceleration": mps,
        },
        "reasons": reasons,
    }
