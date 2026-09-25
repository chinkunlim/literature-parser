"""
Ollama Model Download Advisor & Setup Helper
============================================
Checks local Ollama availability, inspects installed models against recommended
textbook processing models, and provides interactive prompting or one-command pulling.

Recommended Models:
- Text & Structural Extraction: qwen2.5:7b (32k context, exceptional JSON formatting) or llama3:latest
- Visual Inspection & Layout: llama3.2-vision:latest (11B multimodal vision model)
"""

import json
import logging
import subprocess
import urllib.request
from typing import Dict, List

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"

# Recommended model roster (ordered by preference within each role)
# "text_structuring" → fast JSON generation, large context window
# "vision_audit"     → visual page inspection and layout QA
# "vision_quick"     → lightweight 1.7 GB model for fast initial scans
RECOMMENDED_MODELS = {
    "text_structuring": "qwen2.5:7b",          # 32K context, best JSON reliability
    "text_fallback":    "llama3:latest",        # Fallback if qwen2.5 not installed
    "vision_audit":     "llava:13b",            # Full vision audit (8 GB, needs ≥16 GB RAM)
    "vision_quick":     "moondream:latest",     # ★ 1.7 GB — fast initial scan, Apple Silicon OK
}

# Minimum recommended model: just these two cover all basic use cases
MINIMUM_RECOMMENDED = ["moondream:latest", "qwen2.5:7b"]


def probe_ollama(url: str = DEFAULT_OLLAMA_URL, timeout: float = 2.0) -> bool:
    """Checks if Ollama is running and responding to HTTP requests."""
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_installed_models(url: str = DEFAULT_OLLAMA_URL, timeout: float = 2.0) -> List[str]:
    """Returns list of model names currently installed in local Ollama."""
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def check_models_status(url: str = DEFAULT_OLLAMA_URL) -> Dict[str, any]:
    """
    Checks status of recommended models.
    Returns:
        {
            "ollama_online": bool,
            "installed_models": list,
            "recommended": dict,
            "missing_minimum": list,   # critical missing (moondream + qwen2.5)
            "missing_full": list,      # optional full roster missing
        }
    """
    online = probe_ollama(url)
    if not online:
        return {
            "ollama_online": False,
            "installed_models": [],
            "recommended": RECOMMENDED_MODELS,
            "missing_minimum": [(m, m) for m in MINIMUM_RECOMMENDED],
            "missing_full": list(RECOMMENDED_MODELS.items()),
        }

    installed = get_installed_models(url)

    def _is_installed(model_name: str) -> bool:
        base = model_name.split(":")[0]
        return any(model_name in inst or base in inst for inst in installed)

    missing_minimum = [m for m in MINIMUM_RECOMMENDED if not _is_installed(m)]
    missing_full    = [(role, m) for role, m in RECOMMENDED_MODELS.items() if not _is_installed(m)]

    return {
        "ollama_online": True,
        "installed_models": installed,
        "recommended": RECOMMENDED_MODELS,
        "missing_minimum": missing_minimum,
        "missing_full": missing_full,
    }


def pull_model(model_name: str) -> bool:
    """Pulls an Ollama model using local CLI command 'ollama pull <model_name>'."""
    print(f"\n[📦 Ollama Model Advisor] Pulling '{model_name}'...")
    try:
        proc = subprocess.run(
            ["ollama", "pull", model_name],
            check=True
        )
        print(f"[✓] Successfully downloaded '{model_name}'.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to pull model %s: %s", model_name, e)
        print(f"[✗] Failed to download '{model_name}'. Error code: {e.returncode}")
        return False
    except FileNotFoundError:
        logger.error("'ollama' command line tool not found in PATH.")
        print("[✗] 'ollama' command line tool not found in PATH.")
        return False


def prompt_and_install_missing(auto_pull: bool = False, interactive: bool = True) -> List[str]:
    """
    Checks for missing minimum models and either prompts the user or pulls automatically.
    Shows RAM-tier advice for model selection.
    Returns list of currently available + newly pulled model names.
    """
    status = check_models_status()
    if not status["ollama_online"]:
        print("[⚠️  Ollama Advisor] Ollama service is not running at http://127.0.0.1:11434.")
        print("   Start it with 'ollama serve' in your terminal if you wish to use local LLMs.")
        print()
        print("   Recommended install order (smallest → largest):")
        print("   1. moondream:latest   — 1.7 GB  (Apple Silicon friendly, quick visual scan)")
        print("   2. qwen2.5:7b         — 4.7 GB  (best JSON output, 32K context)")
        print("   3. llava:13b          — 8.0 GB  (full vision audit, needs ≥16 GB RAM)")
        return []

    installed = status["installed_models"]
    missing_min = status["missing_minimum"]

    if not missing_min:
        print("[✓ Ollama Advisor] Minimum recommended models are installed:")
        for inst in installed:
            print(f"   • {inst}")
        return installed

    print(f"\n[💡 Ollama Advisor] Missing {len(missing_min)} minimum recommended model(s):\n")
    ram_advice = {
        "moondream:latest": "1.7 GB — ★ Start here. Fast visual scan, works on 8 GB RAM.",
        "qwen2.5:7b":       "4.7 GB — JSON structuring (32K context). Needs ≥8 GB RAM.",
        "llava:13b":        "8.0 GB — Full vision audit. Needs ≥16 GB RAM.",
        "llama3:latest":    "4.7 GB — Text fallback. Needs ≥8 GB RAM.",
    }
    for model_name in missing_min:
        advice = ram_advice.get(model_name, "see https://ollama.com/library")
        print(f"   • {model_name:<24}  ({advice})")

    print()
    installed_now = []
    for model_name in missing_min:
        if auto_pull:
            if pull_model(model_name):
                installed_now.append(model_name)
        elif interactive:
            try:
                advice = ram_advice.get(model_name, "")
                resp = input(f"Download '{model_name}' ({advice})? [y/N]: ").strip().lower()
                if resp in ('y', 'yes'):
                    if pull_model(model_name):
                        installed_now.append(model_name)
                else:
                    print(f"  Skipped '{model_name}'. Continuing with built-in archetype defaults.")
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                break

    return installed + installed_now


if __name__ == "__main__":
    import sys
    auto = "--auto" in sys.argv
    prompt_and_install_missing(auto_pull=auto, interactive=True)
