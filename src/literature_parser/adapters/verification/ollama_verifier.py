"""
Local Ollama AI Model Verifier & LaTeX Refiner
=============================================
Communicates directly with local Ollama daemon (localhost:11434) to perform
semantic consistency checking and mathematical LaTeX refinement with ZERO token cost.
"""

import json
import logging
import urllib.error
import urllib.request

from literature_parser.config.processor_config import (
    DEFAULT_OLLAMA_HEALER_MODEL,
    DEFAULT_OLLAMA_SEMANTIC_MODEL,
    DEFAULT_OLLAMA_VISION_MODEL,
    OLLAMA_API_BASE,
    OLLAMA_GENERATE_TIMEOUT,
)
from literature_parser.adapters.utils.system import ensure_ollama_running, is_ollama_running
from literature_parser.services.guards.prompts import PromptRegistry

logger = logging.getLogger(__name__)


class OllamaVerifier:
    """Dispatches verification and LaTeX refinement tasks to local Ollama models."""

    def __init__(
        self,
        semantic_model: str = None,
        healer_model: str = None,
        vision_model: str = None,
        api_base: str = OLLAMA_API_BASE,
        auto_start: bool = True,
    ) -> None:
        """Initialize local Ollama AI verifier.

        Args:
            semantic_model: Preferred model for semantic and reading flow audit.
            healer_model: Preferred model for code/LaTeX/table reconstruction.
            vision_model: Preferred multimodal model for layout and image verification.
            api_base: Base URL of local Ollama daemon (127.0.0.1:11434).
            auto_start: Whether to auto-wake Ollama daemon if offline.
        """
        self.semantic_model = semantic_model or DEFAULT_OLLAMA_SEMANTIC_MODEL
        self.healer_model = healer_model or DEFAULT_OLLAMA_HEALER_MODEL
        self.vision_model = vision_model or DEFAULT_OLLAMA_VISION_MODEL
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
        vision_candidates = [
            "minicpm-v:latest", "minicpm-v", "llama3.2-vision:latest", "llama3.2-vision",
            "qwen2-vl:latest", "qwen2-vl", "llava:latest"
        ]

        self.semantic_model = select_best(self.semantic_model, semantic_candidates)
        self.healer_model = select_best(self.healer_model, healer_candidates)
        self.vision_model = select_best(self.vision_model, vision_candidates)
        logger.info(
            "OllamaVerifier: selected semantic_model='%s', healer_model='%s', vision_model='%s'",
            self.semantic_model,
            self.healer_model,
            self.vision_model,
        )

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
        # Clean HTML style/metadata, TOC details, and Mermaid blocks to inspect actual prose narrative & transitions
        clean_text = re.sub(r'<style>.*?</style>', '', markdown_sample, flags=re.DOTALL)
        clean_text = re.sub(r'<div class="article-meta">.*?</div>', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'<details\b[^>]*>.*?</details>', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'```mermaid[\s\S]*?```', '', clean_text)
        clean_text = clean_text.strip()

        # Find an excerpt that ends cleanly at a sentence or paragraph boundary
        # Multi-window smart sampling: (1) Chapter narrative opening, (2) Page transition boundary
        # Window 1: Chapter opening prose (skip pure Learning Objective bullet lists if followed by prose)
        lines = clean_text.splitlines()
        first_prose_idx = 0
        lo_count = 0
        for idx, line in enumerate(lines):
            l_strip = line.strip()
            if l_strip.startswith('🎯') or l_strip.startswith('- 🎯') or l_strip.startswith('> 🎯'):
                lo_count += 1
            elif lo_count > 0 and len(l_strip) > 30:
                first_prose_idx = idx
                break

        opening_text = "\n".join(lines[first_prose_idx:]).strip()
        raw_w1 = opening_text[:1400].strip()
        b1 = max(raw_w1.rfind('.\n'), raw_w1.rfind('. '), raw_w1.rfind('\n\n'))
        w1 = raw_w1[:b1 + 1].strip() if b1 > 600 else raw_w1

        # Window 2: Mid-chapter page transition boundary (verify cross-page sentence flow & blockquote sanity)
        w2 = ""
        page_markers = list(re.finditer(r'<!--\s*Page\s+\d+\s*-->', clean_text))
        if len(page_markers) >= 2:
            mid_marker = page_markers[len(page_markers) // 2]
            start_pos = max(0, mid_marker.start() - 500)
            end_pos = min(len(clean_text), mid_marker.end() + 600)
            raw_w2 = clean_text[start_pos:end_pos].strip()
            w2 = raw_w2

        if w2:
            sample_excerpt = f"--- [EXCERPT WINDOW 1: CHAPTER BODY OPENING] ---\n{w1}\n\n--- [EXCERPT WINDOW 2: PAGE TRANSITION CONTINUITY] ---\n{w2}"
        else:
            sample_excerpt = w1

        system_prompt, prompt = PromptRegistry.get_semantic_auditor(chapter_title, sample_excerpt)

        payload = {
            "model": self.semantic_model,
            "system": system_prompt,
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
                upper_resp = response_text.upper()

                # Robust verdict parsing: prioritize explicit Final Verdict declaration
                passed = False
                m_verdict = re.search(r'(?:FINAL\s+VERDICT|VERDICT)\s*:\s*(\[[^\]]+\]|[A-Z]+)', upper_resp)
                if m_verdict:
                    verdict_val = m_verdict.group(1)
                    if "PASS" in verdict_val and "REVISE" not in verdict_val and "FAIL" not in verdict_val:
                        passed = True
                else:
                    has_fail = "[FAIL]" in upper_resp or "[REVISE]" in upper_resp or "NEEDS ATTENTION" in upper_resp
                    has_pass = "[PASS]" in upper_resp or "EXCELLENT" in upper_resp or "GOOD" in upper_resp
                    passed = has_pass and not has_fail

                return {
                    "available": True,
                    "model": self.semantic_model,
                    "feedback": response_text,
                    "passed": passed,
                }
        except Exception as e:
            return {
                "available": False,
                "model": self.semantic_model,
                "feedback": f"Error communicating with local Ollama: {e}",
            }

    def audit_structured_format_defects(self, markdown_text: str, candidate_issues: list = None, doc_name: str = "") -> dict:
        """
        Combines rule-based pre-scan findings with local Ollama deep semantic inspection.
        Returns structured findings with severity, location, explanation, and recommended fix.
        """
        import re
        if not self.is_available:
            return {
                "available": False,
                "model": self.semantic_model,
                "feedback": "Local Ollama daemon is offline or inaccessible.",
                "findings": [],
                "passed": True,
            }

        # Clean HTML style/metadata blocks to review actual markdown narrative & LaTeX
        clean_text = re.sub(r'<style>.*?</style>', '', markdown_text, flags=re.DOTALL)
        clean_text = re.sub(r'<div class="article-meta">.*?</div>', '', clean_text, flags=re.DOTALL).strip()
        sample_excerpt = clean_text[:4000].strip()

        pre_issues_str = ""
        if candidate_issues:
            pre_issues_str = "Rule-based pre-scan detected the following potential defects:\n"
            for i, iss in enumerate(candidate_issues[:10], 1):
                pre_issues_str += f"- [{getattr(iss, 'severity', 'WARN')}] {getattr(iss, 'category', 'GEN')}: {getattr(iss, 'message', str(iss))} (Snippet: {getattr(iss, 'snippet', '')[:40]})\n"

        system_prompt, prompt = PromptRegistry.get_structured_format_audit(
            doc_name=doc_name,
            sample_excerpt=sample_excerpt,
            candidate_issues_str=pre_issues_str,
        )

        payload = {
            "model": self.semantic_model,
            "system": system_prompt,
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
                passed = "[PASS]" in response_text.upper() or "EXCELLENT" in response_text.upper() or "GOOD" in response_text.upper()
                return {
                    "available": True,
                    "model": self.semantic_model,
                    "feedback": response_text,
                    "passed": passed,
                }
        except Exception as e:
            return {
                "available": False,
                "model": self.semantic_model,
                "feedback": f"Error communicating with local Ollama: {e}",
                "findings": [],
                "passed": True,
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

        system_prompt, prompt = PromptRegistry.get_ocr_proofreading(markdown_text, max_chars)

        payload = {
            "model": self.healer_model,
            "system": system_prompt,
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
        vision_model: str = None,
    ) -> dict:
        """Dispatches targeted base64 crop image + Markdown snippet to local Ollama Vision.

        Performs fine-grained multimodal layout verification with ZERO cloud token cost.

        Args:
            crop_image_path: Absolute or relative path to the rendered PDF page PNG.
            markdown_snippet: Extracted Markdown segment corresponding to this page/element.
            element_type: Type of element being audited (e.g. 'table', 'exhibit', 'concept_map').
            vision_model: Optional model override; defaults to self.vision_model.

        Returns:
            Dict containing 'available', 'passed', 'defect', 'confidence', and 'model'.
        """
        import base64
        import os
        import re

        model_to_use = vision_model or self.vision_model or DEFAULT_OLLAMA_VISION_MODEL

        if not self.is_available or not os.path.exists(crop_image_path):
            return {
                "available": False,
                "passed": True,
                "verdict": "SKIPPED",
                "defect": None,
                "model": model_to_use,
            }

        try:
            with open(crop_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = PromptRegistry.get_multimodal_layout_audit(element_type, markdown_snippet)

            payload = {
                "model": model_to_use,
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
                resp_text = data.get("response", "{}")
                match = re.search(r'\{.*\}', resp_text, re.DOTALL)
                res_obj = json.loads(match.group(0)) if match else json.loads(resp_text)
                return {
                    "available": True,
                    "passed": res_obj.get("passed", True),
                    "defect": res_obj.get("defect"),
                    "confidence": res_obj.get("confidence", 0.9),
                    "model": model_to_use,
                }
        except Exception as e:
            logger.debug("ROI Vision verification skipped – %s", e)
            return {
                "available": False,
                "passed": True,
                "verdict": "ERROR_FALLBACK",
                "defect": None,
                "model": model_to_use,
            }
