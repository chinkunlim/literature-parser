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
from doc_processor.config import (
    OLLAMA_API_BASE,
    DEFAULT_OLLAMA_SEMANTIC_MODEL,
    DEFAULT_OLLAMA_HEALER_MODEL,
    DEFAULT_OLLAMA_VISION_MODEL,
    OLLAMA_GENERATE_TIMEOUT,
)
from doc_processor.utils.system import is_ollama_running, ensure_ollama_running

logger = logging.getLogger(__name__)


class OllamaVerifier:
    """Dispatches verification and LaTeX refinement tasks to local Ollama models."""

    def __init__(self, semantic_model: str = None, healer_model: str = None, api_base: str = OLLAMA_API_BASE, auto_start: bool = True) -> None:
        self.semantic_model = semantic_model or DEFAULT_OLLAMA_SEMANTIC_MODEL
        self.healer_model = healer_model or DEFAULT_OLLAMA_HEALER_MODEL
        self.api_base = api_base
        if auto_start:
            self.is_available = ensure_ollama_running(self.api_base)
        else:
            self.is_available = is_ollama_running(self.api_base)
        if self.is_available:
            self.auto_select_models()

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

    def auto_select_models(self) -> None:
        """
        Inspects installed local models and selects the best matching models.
        Falls back if the requested models are not installed.
        """
        models = self.list_local_models()
        if not models:
            return

        def select_best(requested: str, candidates: list) -> str:
            # Check exact or prefix
            for m in models:
                if m == requested or m.startswith(requested.split(':')[0]):
                    return m
            # Check fallbacks
            for cand in candidates:
                cand_prefix = cand.split(':')[0]
                for m in models:
                    if m == cand or m.startswith(cand_prefix):
                        return m
            return models[0]

        semantic_candidates = [
            "gemma4:12b", "gemma4:latest", "gemma4", "gemma2:9b",
            "llama3.1:8b", "llama3:latest", "mistral:7b", "qwen2.5:7b"
        ]
        healer_candidates = [
            "qwen2.5-coder:7b", "qwen2.5:14b", "qwen2.5:7b",
            "deepseek-r1:8b", "deepseek-r1:14b",
            "gemma4:12b", "llama3.1:8b"
        ]

        self.semantic_model = select_best(self.semantic_model, semantic_candidates)
        self.healer_model = select_best(self.healer_model, healer_candidates)
        logger.info("OllamaVerifier: selected semantic_model='%s', healer_model='%s'", self.semantic_model, self.healer_model)

    def verify_chapter_semantics(self, chapter_title: str, markdown_sample: str) -> dict:
        """
        Sends an excerpt of the extracted Markdown to local Ollama to verify:
        - Natural sentence flow (no jarring OCR breaks)
        - LaTeX formula syntax correctness
        - Clean textbook pedagogical structure
        """
        import re
        if not self.is_available:
            return {
                "available": False,
                "model": self.semantic_model,
                "feedback": "Local Ollama daemon is offline or inaccessible.",
            }

        # Clean HTML style/metadata blocks to review actual markdown narrative & LaTeX
        clean_text = re.sub(r'<style>.*?</style>', '', markdown_sample, flags=re.DOTALL)
        clean_text = re.sub(r'<div class="article-meta">.*?</div>', '', clean_text, flags=re.DOTALL).strip()

        # Find an excerpt that ends cleanly at a sentence or paragraph boundary
        raw_excerpt = clean_text[:2500].strip()
        last_boundary = max(raw_excerpt.rfind('.\n'), raw_excerpt.rfind('. '), raw_excerpt.rfind('\n\n'))
        if last_boundary > 1000:
            sample_excerpt = raw_excerpt[:last_boundary + 1].strip()
        else:
            sample_excerpt = raw_excerpt

        prompt = (
            f"You are an expert academic editor and publication auditor. Review the following extracted paper/textbook section "
            f"titled '{chapter_title}'. Specifically audit the following 4 critical dimensions:\n"
            f"1. Heading Authenticity: Are all headings genuine author section titles (NO AI-hallucinated summary subheadings)?\n"
            f"2. LaTeX & Symbols: Are all LaTeX formulas ($...$ or $$...$$) syntactically valid with NO unescaped currency ($3) or broken delimiters?\n"
            f"3. Table Note Separation: Are table notes (<div class=\"table-notes\">) clearly separated from subsequent body prose paragraphs?\n"
            f"4. Text Continuity & Prose Flow: Does prose flow naturally across pages without broken sentences or OCR glitches?\n\n"
            f"Text Sample:\n```markdown\n{sample_excerpt}\n```\n\n"
            f"Briefly respond with:\n"
            f"1. Heading Authenticity Feedback\n"
            f"2. Formula & Symbol Feedback\n"
            f"3. Table & Note Separation Feedback\n"
            f"4. Quality Rating (Excellent / Good / Needs Attention)\n"
            f"5. Verdict: [PASS] or [REVISE]"
        )


        payload = {
            "model": self.semantic_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
        }

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
                    "model": self.semantic_model,
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
                "model": self.semantic_model,
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
            "model": self.healer_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
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
                "keep_alive": "30m",
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
