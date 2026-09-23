"""
Ollama Service & Auto-Wake Guard
================================
Monitors local Ollama daemon, checks installed models, automatically wakes
the daemon if offline, and provides graceful degradation when hardware or service fails.
"""

import json
import time
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from src.utils.logger import get_diagnostic_logger
from src.guards.hardware import check_hardware_safety

logger = get_diagnostic_logger("OllamaGuard")

DEFAULT_API_BASE = "http://localhost:11434"
DEFAULT_DESIRED_MODEL = "qwen2.5:7b"


class OllamaGuard:
    """Manages Ollama health, auto-spawning, model verification, and safe query execution."""

    def __init__(self, api_base: str = DEFAULT_API_BASE, target_model: str = DEFAULT_DESIRED_MODEL):
        self.api_base = api_base.rstrip("/")
        self.target_model = target_model

    def is_service_alive(self) -> bool:
        """Pings Ollama endpoint."""
        try:
            req = urllib.request.Request(f"{self.api_base}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_installed_models(self) -> list:
        """Returns list of installed model tags."""
        try:
            req = urllib.request.Request(f"{self.api_base}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def ensure_service_ready(self, auto_wake: bool = True) -> dict:
        """
        Ensures Ollama is ready and running.
        If offline and auto_wake=True, attempts background start.
        """
        if self.is_service_alive():
            models = self.list_installed_models()
            return {
                "ready": True,
                "alive": True,
                "models": models,
                "selected_model": self._pick_best_model(models),
                "message": "Ollama service is online.",
            }

        if not auto_wake:
            return {
                "ready": False,
                "alive": False,
                "models": [],
                "selected_model": None,
                "message": "Ollama service is offline and auto_wake is disabled.",
            }

        logger.info("Ollama is offline. Attempting automatic background wake ('ollama serve')...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Wait up to 5 seconds for Ollama to become responsive
            for _ in range(10):
                time.sleep(0.5)
                if self.is_service_alive():
                    models = self.list_installed_models()
                    logger.info("Ollama successfully auto-started!")
                    return {
                        "ready": True,
                        "alive": True,
                        "models": models,
                        "selected_model": self._pick_best_model(models),
                        "message": "Ollama successfully auto-started.",
                    }
        except FileNotFoundError:
            logger.warning(
                where="OllamaGuard.ensure_service_ready",
                why="The 'ollama' binary was not found in PATH.",
                how_to_fix="Install Ollama via 'brew install ollama' or download from ollama.com",
            )
        except Exception as e:
            logger.warning(
                where="OllamaGuard.ensure_service_ready",
                why=f"Failed to auto-spawn Ollama process: {e}",
                how_to_fix="Start Ollama manually via application launcher or 'ollama serve'",
            )

        return {
            "ready": False,
            "alive": False,
            "models": [],
            "selected_model": None,
            "message": "Failed to auto-wake Ollama.",
        }

    def _pick_best_model(self, installed_models: list) -> str:
        """Picks the target model or the most capable installed model."""
        if not installed_models:
            return None
        # Exact or prefix match
        target_prefix = self.target_model.split(":")[0]
        for m in installed_models:
            if m == self.target_model or m.startswith(target_prefix):
                return m

        candidates = [
            "qwen2.5:7b", "qwen2.5-coder:7b", "qwen2.5:14b",
            "gemma4", "gemma2:9b", "deepseek-r1:8b", "llama3.1:8b", "llama3:latest",
        ]
        for cand in candidates:
            cand_prefix = cand.split(":")[0]
            for m in installed_models:
                if m == cand or m.startswith(cand_prefix):
                    return m
        return installed_models[0]

    def safe_generate(self, prompt: str, system_prompt: str = "", timeout: float = 30.0) -> dict:
        """
        Executes an LLM call guarded by hardware safety and service health.
        If unsafe or unavailable, returns a fallback payload without crashing.
        """
        # 1. Hardware Guard
        hw = check_hardware_safety()
        if not hw["safe_for_heavy_llm"]:
            reason_str = "; ".join(hw["reasons"])
            logger.warning(
                where="OllamaGuard.safe_generate",
                why=f"Hardware guard tripped: {reason_str}",
                how_to_fix="Close unused applications or connect AC charger.",
            )
            return {
                "success": False,
                "fallback": True,
                "reason": f"Hardware constraint: {reason_str}",
                "response": None,
            }

        # 2. Service Ready Guard
        service = self.ensure_service_ready(auto_wake=True)
        if not service["ready"] or not service["selected_model"]:
            return {
                "success": False,
                "fallback": True,
                "reason": service["message"],
                "response": None,
            }

        model = service["selected_model"]

        # 3. Invoke Generate API
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            req = urllib.request.Request(
                f"{self.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "fallback": False,
                    "model": model,
                    "response": data.get("response", "").strip(),
                }
        except Exception as e:
            logger.error(
                where="OllamaGuard.safe_generate",
                why=f"Ollama API call error: {e}",
                how_to_fix="Check if model is corrupted or Ollama ran out of memory.",
            )
            return {
                "success": False,
                "fallback": True,
                "reason": str(e),
                "response": None,
            }
