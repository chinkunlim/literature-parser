"""
Ollama Profiler & Layout Analyzer
=================================
Analyzes book characteristics (TOC, longest chapter, appendix) using local
Ollama models (llama3 / llama3.2-vision) with robust timeout guards and
deterministic fallback defaults.

Saves per-book configuration to:
  output/{Book Name}/book_profile.json
"""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
PROBE_TIMEOUT = 2.0  # seconds to check if ollama is reachable
GENERATE_TIMEOUT = 30.0  # seconds max for generation


def is_ollama_available(url: str = DEFAULT_OLLAMA_URL) -> bool:
    """Checks if Ollama REST API is responding within PROBE_TIMEOUT."""
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_installed_models(url: str = DEFAULT_OLLAMA_URL) -> list:
    """Lists model names currently pulled in Ollama."""
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name") for m in data.get("models", [])]
    except Exception:
        return []


def generate_default_book_profile(book_dir: Path) -> Dict[str, Any]:
    """
    Returns robust, archetype-based default profile for textbook layouts
    without needing LLM inference.
    """
    return {
        "book_name": book_dir.name,
        "archetype": "textbook_heavy",
        "geometry": {
            "page_width": 918.0,
            "page_height": 1174.0,
            "header_cut_ratio": 0.04,
            "footer_cut_ratio": 0.04,
            "odd_page_margin_x": [0.70, 1.0],
            "even_page_margin_x": [0.0, 0.30]
        },
        "typography": {
            "h1_min_size": 22.0,
            "h2_min_size": 16.0,
            "h3_min_size": 13.0,
            "body_font_family": "MinionPro",
            "margin_font_family": "Frutiger"
        },
        "special_blocks": {
            "has_concept_map": True,
            "lo_pattern": r"^\d+\.\d+",
            "has_margin_glossary": True,
            "gloss_placement": "chapter_end",
            "exhibit_heading_pattern": r"^EXHIBIT\s+\d+\.\d+",
            "eoc_heading_patterns": [
                r"^Key Terms and Concepts\b",
                r"^Related Internet Sites\b",
                r"^Practice Test\b",
                r"^Challenge Exercises\b",
                r"^Summary\b"
            ]
        },
        # Accumulated per-book layout features (populated by SpecialBlockScanner)
        "discovered_blocks": [],
        # Column role classification (populated by SpecialBlockScanner)
        "column_roles": {
            "even_left":  "margin_glossary",
            "even_right": "body",
            "odd_left":   "body",
            "odd_right":  "margin_glossary"
        },
        # Set to True once SpecialBlockScanner has completed its initial scan
        "scan_complete": False,
        "section_rules": {
            "appendix": {
                "skip_concept_map": True,
                "table_strategy": "dense_list"
            },
            "glossary": {
                "skip_concept_map": True,
                "dense_columns": True
            },
            "index": {
                "skip_concept_map": True,
                "dense_columns": True
            }
        }
    }



def query_ollama_json(prompt: str, model: str = "llama3:latest", url: str = DEFAULT_OLLAMA_URL) -> Optional[Dict[str, Any]]:
    """Queries Ollama with format: 'json' and returns parsed dictionary."""
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/generate",
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=GENERATE_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            response_text = body.get("response", "{}")
            return json.loads(response_text)
    except Exception as e:
        logger.warning("Ollama query failed (%s): %s", model, e)
        return None


def create_or_update_book_profile(book_dir: Path, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Main entrypoint: analyzes book directory or loads existing book_profile.json.
    """
    profile_path = book_dir / "book_profile.json"
    if profile_path.exists() and not force_refresh:
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to read %s, re-generating: %s", profile_path, e)

    profile = generate_default_book_profile(book_dir)

    # If Ollama is available, optionally refine profile
    if is_ollama_available():
        installed = get_installed_models()
        chosen_model = None
        for candidate in ["llama3:latest", "llama3.2:latest", "qwen2.5:7b"]:
            if candidate in installed:
                chosen_model = candidate
                break
        
        if chosen_model:
            logger.info("Ollama is active. Profiling %s with %s", book_dir.name, chosen_model)
            # Sample TOC / Headings if available
            toc_files = list(book_dir.glob("*TOC*.html")) or list(book_dir.glob("*Chapter*1*.html"))
            sample_text = ""
            if toc_files:
                try:
                    with open(toc_files[0], "r", encoding="utf-8", errors="ignore") as tf:
                        sample_text = tf.read()[:2000]
                except Exception:
                    pass

            if sample_text:
                from src.guards.prompts import PromptRegistry
                prompt = PromptRegistry.get_profile_special_blocks(sample_text)
                refined = query_ollama_json(prompt, model=chosen_model)
                if refined and isinstance(refined, dict):
                    if "has_concept_map" in refined:
                        profile["special_blocks"]["has_concept_map"] = bool(refined["has_concept_map"])
                    if "has_margin_glossary" in refined:
                        profile["special_blocks"]["has_margin_glossary"] = bool(refined["has_margin_glossary"])

    # Always ensure Appendix section rules have skip_concept_map = True
    profile.setdefault("section_rules", {})
    profile["section_rules"].setdefault("appendix", {})
    profile["section_rules"]["appendix"]["skip_concept_map"] = True

    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        logger.info("Saved book profile to: %s", profile_path)
    except Exception as e:
        logger.error("Failed to write book profile: %s", e)

    return profile


class OllamaProfiler:
    """Object-oriented wrapper for profiling books."""

    def __init__(self, book_dir: Path, url: str = DEFAULT_OLLAMA_URL):
        self.book_dir = Path(book_dir)
        self.url = url

    def profile_book(self, force_refresh: bool = False) -> Dict[str, Any]:
        return create_or_update_book_profile(self.book_dir, force_refresh=force_refresh)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    target = Path("./data/output/books/Research Methods, Design, and Analysis 13th ed")
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    prof = create_or_update_book_profile(target, force_refresh=True)
    print(json.dumps(prof, indent=2))
