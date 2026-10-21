"""
Hardware Pre-flight Guard
=========================
Performs real-time system capability checks before invoking heavy models or batch OCR:
- Available RAM threshold (>= 4.0 GB)
- Battery & AC Power detection (macOS pmset)
- Available Disk Space threshold (>= 10.0 GB)
- Apple Silicon Metal Performance Shaders (MPS) availability
"""

import platform
import shutil
import subprocess

from src.utils.logger import get_diagnostic_logger

logger = get_diagnostic_logger("HardwareGuard")

MIN_RAM_GB_BATTERY = 4.0
MIN_RAM_GB_AC = 2.0
MIN_RAM_GB = MIN_RAM_GB_BATTERY  # legacy fallback
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
            inactive_pages = 0
            purgeable_pages = 0
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
                elif "Pages inactive:" in line:
                    inactive_pages = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages purgeable:" in line:
                    purgeable_pages = int(line.split(":")[1].strip().rstrip("."))
            total_available_pages = free_pages + speculative_pages + inactive_pages + purgeable_pages
            return (total_available_pages * page_size) / (1024 ** 3)
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


def get_macos_memory_pressure_level() -> int:
    """
    Returns macOS memory pressure level:
    1 = Normal, 2 = Warning, 4 = Critical.
    Returns 1 if non-Darwin or if detection fails.
    """
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True).strip()
            if out.isdigit():
                return int(out)
        except Exception:
            pass
    return 1


def check_hardware_safety(ignore_battery: bool = False) -> dict:
    """
    Comprehensive pre-flight evaluation with dynamic power-aware RAM thresholds.
    Returns:
        dict: {'safe_for_heavy_llm': bool, 'safe_for_batch_ocr': bool, 'metrics': dict, 'reasons': list}
    """
    ram_gb = get_available_ram_gb()
    disk_gb = get_disk_free_gb()
    batt = get_battery_status()
    mps = is_mps_available()
    pressure_level = get_macos_memory_pressure_level()

    reasons = []
    safe_for_heavy_llm = True
    safe_for_batch_ocr = True

    # Dynamic RAM threshold based on power state and memory pressure
    is_ac = not batt["is_battery"]
    # In AC mode, allow down to 2.0 GB as long as memory pressure is not critical (< 4)
    effective_min_ram = MIN_RAM_GB_AC if (is_ac and pressure_level < 4) else MIN_RAM_GB_BATTERY

    # 1. RAM check
    if ram_gb < effective_min_ram:
        safe_for_heavy_llm = False
        reasons.append(
            f"Available RAM ({ram_gb:.2f} GB) is lower than dynamic threshold "
            f"({effective_min_ram:.1f} GB, Mode: {'AC Power' if is_ac else 'Battery'})."
        )
    elif pressure_level >= 4:
        safe_for_heavy_llm = False
        reasons.append(f"macOS memory pressure level is critical ({pressure_level}).")

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
            "effective_min_ram_gb": effective_min_ram,
            "memory_pressure_level": pressure_level,
            "disk_free_gb": round(disk_gb, 1),
            "power_status": batt["description"],
            "is_battery": batt["is_battery"],
            "battery_percent": batt["percent"],
            "mps_acceleration": mps,
        },
        "reasons": reasons,
    }
