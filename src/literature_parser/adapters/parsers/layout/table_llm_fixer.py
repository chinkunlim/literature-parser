"""
Local LLM Table Fixer
=====================
Dispatches complex or unbordered tabular text blocks to local Ollama (qwen2.5-coder:7b)
to reconstruct publication-grade Markdown tables with zero cloud token cost.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Optional

from literature_parser.config.processor_config import (
    OLLAMA_API_BASE,
    OLLAMA_GENERATE_TIMEOUT,
)

logger = logging.getLogger(__name__)


class TableLLMFixer:
    """Uses local Ollama code models to repair or restructure complex tabular data."""

    TABLE_FIX_MODEL = "qwen2.5-coder:7b"

    @classmethod
    def can_fix(cls, table_text: str, column_count: int) -> bool:
        """Determines if the table is complex enough to warrant local LLM repair."""
        if not table_text:
            return False
        # If columns >= 5 or text has high statistical density or complex multi-line cells
        lines = [l.strip() for l in table_text.splitlines() if l.strip()]
        return column_count >= 5 or len(lines) >= 8

    @classmethod
    def reconstruct_table_with_ollama(
        cls,
        table_text: str,
        caption: str = "",
        model_name: str = TABLE_FIX_MODEL,
        api_base: str = OLLAMA_API_BASE,
        timeout: float = OLLAMA_GENERATE_TIMEOUT,
    ) -> Optional[str]:
        """
        Sends raw tabular text to local Ollama to output a clean Markdown table.
        Returns the formatted markdown table string, or None if Ollama is unreachable.
        """
        from literature_parser.services.guards.prompts import PromptRegistry

        prompt = PromptRegistry.get_table_reconstruction(table_text=table_text, caption=caption)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
        }

        try:
            req = urllib.request.Request(
                f"{api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()

                # Extract markdown table block if wrapped in ```markdown
                if "```" in response_text:
                    parts = response_text.split("```")
                    for p in parts:
                        if "|" in p and "---" in p:
                            lines = p.strip().splitlines()
                            if lines and lines[0].lower().startswith("markdown"):
                                lines = lines[1:]
                            return "\n".join(lines).strip()

                if "|" in response_text and "---" in response_text:
                    return response_text

        except Exception as e:
            logger.debug("TableLLMFixer skipped – %s", e)

        return None
