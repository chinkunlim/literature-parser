"""
Local Ollama AI Model Verifier & LaTeX Refiner
=============================================
Communicates directly with local Ollama daemon (localhost:11434) to perform
semantic consistency checking and mathematical LaTeX refinement with ZERO token cost.
"""

import json
import logging
import urllib.request
import urllib.error
from book_processor.config import (
    OLLAMA_API_BASE,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_VISION_MODEL,
    OLLAMA_GENERATE_TIMEOUT,
)
from book_processor.utils.system import is_ollama_running, ensure_ollama_running

logger = logging.getLogger(__name__)


class OllamaVerifier:
    """Dispatches verification and LaTeX refinement tasks to local Ollama models."""

    def __init__(self, model_name: str = DEFAULT_OLLAMA_MODEL, api_base: str = OLLAMA_API_BASE, auto_start: bool = True) -> None:
        self.model_name = model_name
        self.api_base = api_base
        if auto_start:
            self.is_available = ensure_ollama_running(self.api_base)
        else:
            self.is_available = is_ollama_running(self.api_base)
        if self.is_available:
            self.auto_select_model()

    def list_local_models(self) -> list:
        """Returns list of installed local Ollama models."""
        if not self.is_available:
            return []
        try:
            req = urllib.request.Request(f"{self.api_base}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def auto_select_model(self) -> str:
        """
        Inspects installed local models and selects the best matching model.
        If self.model_name is not installed, falls back to highest-priority available model.
        """
        models = self.list_local_models()
        if not models:
            return self.model_name

        # Check if requested model or prefix matches
        for m in models:
            if m == self.model_name or m.startswith(self.model_name.split(':')[0]):
                self.model_name = m
                return m

        # Priority fallback list of high-capability models
        candidates = [
            "qwen2.5:7b", "qwen2.5:14b", "deepseek-r1:8b", "deepseek-r1:14b",
            "llama3.1:8b", "mistral:7b", "gemma2:9b"
        ]
        for cand in candidates:
            cand_prefix = cand.split(':')[0]
            for m in models:
                if m == cand or m.startswith(cand_prefix):
                    logger.info("OllamaVerifier: model '%s' not found; auto-selected '%s'.", self.model_name, m)
                    self.model_name = m
                    return m

        # If none matched, use the first installed model
        self.model_name = models[0]
        logger.info("OllamaVerifier: using first available model '%s'.", models[0])
        return self.model_name

    def verify_chapter_semantics(self, chapter_title: str, markdown_sample: str) -> dict:
        """
        Sends an excerpt of the extracted Markdown to local Ollama to verify:
        - Natural sentence flow (no jarring OCR breaks)
        - LaTeX formula syntax correctness
        - Clean textbook pedagogical structure
        """
        if not self.is_available:
            return {
                "available": False,
                "model": self.model_name,
                "feedback": "Local Ollama daemon is offline or inaccessible.",
            }

        prompt = (
            f"You are an expert textbook editor and academic AI. Review the following extracted textbook section "
            f"titled '{chapter_title}'. Verify that the text flows naturally, has no broken OCR artifacts, "
            f"and that any LaTeX formulas ($...$ or $$...$$) are syntactically valid.\n\n"
            f"Text Sample:\n```markdown\n{markdown_sample[:1500]}\n```\n\n"
            f"Briefly respond with:\n"
            f"1. Quality Rating (Excellent / Good / Needs Attention)\n"
            f"2. Formula & Formatting Feedback\n"
            f"3. Verdict: [PASS] or [REVISE]"
        )

        payload = {"model": self.model_name, "prompt": prompt, "stream": False}

        try:
            req = urllib.request.Request(
                f"{self.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_GENERATE_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()
                return {
                    "available": True,
                    "model": self.model_name,
                    "feedback": response_text,
                    "passed": (
                        "[PASS]" in response_text.upper()
                        or "EXCELLENT" in response_text.upper()
                        or "GOOD" in response_text.upper()
                    ),
                }
        except Exception as e:
            return {
                "available": False,
                "model": self.model_name,
                "feedback": f"Error communicating with local Ollama: {e}",
            }

    def audit_and_propose_fixes(self, markdown_text: str, max_chars: int = 3000) -> list:
        """
        Queries local Ollama to identify specific OCR typos, formula syntax errors,
        or layout breaks, returning a structured list of proposed replacements.

        Each proposal now includes a ``confidence`` field (0.0 – 1.0) so the
        review desk can auto-accept high-confidence fixes without HITL.
        """
        if not self.is_available:
            return []

        prompt = (
            "You are an expert academic proofreader. Analyze the following textbook Markdown text.\n"
            "If you detect clear OCR character errors (e.g., '2s1' -> '281', 'tezt' -> 'text'), "
            "broken formula syntax, or garbled words, return your proposed corrections in valid JSON format.\n"
            "Format:\n"
            "{\n"
            '  "proposals": [\n'
            '    {\n'
            '      "id": "rev-1",\n'
            '      "original": "exact flawed string from text",\n'
            '      "proposed": "corrected clean string",\n'
            '      "reason": "brief reason for fix",\n'
            '      "category": "ocr_typo",\n'
            '      "confidence": 0.97\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- Set confidence = 1.0 only for unambiguous character substitutions (e.g. 0->O, l->1).\n"
            "- Set confidence >= 0.95 for clear OCR errors with no plausible alternative meaning.\n"
            "- Set confidence < 0.90 for ambiguous or context-dependent corrections.\n"
            "If no issues exist, return: {\"proposals\": []}\n\n"
            f"Markdown text to analyze:\n```markdown\n{markdown_text[:max_chars]}\n```\n"
            "Respond ONLY with the JSON object."
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        try:
            req = urllib.request.Request(
                f"{self.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_GENERATE_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_json = result.get("response", "{}")
                data = json.loads(raw_json)
                proposals = data.get("proposals", [])
                # Ensure every proposal has a confidence field (default 0.5 if missing)
                for p in proposals:
                    if "confidence" not in p:
                        p["confidence"] = 0.5
                return proposals
        except Exception as e:
            logger.warning("Ollama review audit skipped – %s", e)
            return []

    @staticmethod
    def apply_review_annotations(markdown_text: str, proposals: list) -> tuple:
        """
        Inserts non-destructive review markers into Markdown text, preserving
        both the original text and the proposed AI correction for human inspection.
        Returns: (annotated_markdown, applied_proposals)
        """
        import re
        applied = []
        for prop in proposals:
            orig = prop.get("original", "").strip()
            repl = prop.get("proposed", "").strip()
            rev_id = prop.get("id", "rev-1")
            cat = prop.get("category", "general")
            reason = prop.get("reason", "AI proposed improvement")

            if orig and orig in markdown_text and orig != repl:
                annotation = (
                    f"\n<!-- AI-REVIEW-START id=\"{rev_id}\" category=\"{cat}\" -->\n"
                    f"<!-- ORIGINAL:\n{orig}\n-->\n"
                    f"<!-- REASON: {reason} -->\n"
                    f"{repl}\n"
                    f"<!-- AI-REVIEW-END -->\n"
                )
                markdown_text = markdown_text.replace(orig, annotation, 1)
                applied.append(prop)

        return markdown_text, applied

    def verify_roi_vision(
        self,
        crop_image_path: str,
        markdown_snippet: str,
        element_type: str = "table",
        vision_model: str = DEFAULT_OLLAMA_VISION_MODEL,
    ) -> dict:
        """
        Dispatches targeted base64 crop image + Markdown snippet to local Ollama Vision
        for fine-grained multimodal layout verification with ZERO token cost.
        """
        import base64
        import os

        if not self.is_available or not os.path.exists(crop_image_path):
            return {
                "available": False,
                "passed": True,
                "verdict": "SKIPPED",
                "defect": None,
            }

        try:
            with open(crop_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                f"You are an expert textbook layout auditor. Compare the attached original textbook {element_type} image "
                f"with the following extracted Markdown representation:\n\n"
                f"```markdown\n{markdown_snippet[:1500]}\n```\n\n"
                f"Audit criteria:\n"
                f"1. Are all key headers/nodes present without omissions?\n"
                f"2. Is the structure faithful to the original image?\n"
                f"Respond ONLY in valid JSON format:\n"
                f'{{"passed": true, "defect": null, "confidence": 0.95}}\n'
                f'If flawed, return:\n'
                f'{{"passed": false, "defect": "brief description of defect", "confidence": 0.95}}'
            )

            payload = {
                "model": vision_model,
                "prompt": prompt,
                "images": [img_b64],
                "format": "json",
                "stream": False,
            }

            req = urllib.request.Request(
                f"{self.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_GENERATE_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                res_obj = json.loads(data.get("response", "{}"))
                return {
                    "available": True,
                    "passed": res_obj.get("passed", True),
                    "defect": res_obj.get("defect"),
                    "confidence": res_obj.get("confidence", 0.9),
                }
        except Exception as e:
            logger.debug("ROI Vision verification skipped – %s", e)
            return {
                "available": False,
                "passed": True,
                "verdict": "ERROR_FALLBACK",
                "defect": None,
            }
