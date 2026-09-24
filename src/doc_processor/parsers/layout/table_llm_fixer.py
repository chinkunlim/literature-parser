"""
Local LLM Table Fixer
=====================
Dispatches complex or unbordered tabular text blocks to local Ollama (qwen2.5-coder:7b)
to reconstruct publication-grade Markdown tables with zero cloud token cost.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from doc_processor.config import (
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
        prompt = (
            "You are an expert data formatting AI. The following raw text represents a complex academic table.\n"
            f"Table Title: {caption}\n\n"
            "Raw Table Content:\n"
            f"```\n{table_text[:3000]}\n```\n\n"
            "Instructions:\n"
            "1. Output ONLY a clean, valid Markdown table with proper header row and alignment delimiters (| :--- | :---: |).\n"
            "2. Preserve all numbers, decimal places, minus signs, and statistical symbols (e.g., *, **, p, M, SD, F).\n"
            "3. Do NOT include any conversational preamble, explanations, or enclosing notes. Output ONLY the markdown table."
        )

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
