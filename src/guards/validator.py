"""
Input Validation & Output Self-Healing Validator
================================================
Implements the two mandatory Ollama triggers:
1. Input Guard: Validates file consistency against manifest.json and auto-diagnoses with Ollama if discrepancies exist.
2. Output Guard: Intercepts broken LaTeX / syntax errors, auto-repairs via Ollama, or quarantines to data/needs_review/.
"""

import os
import re
import json
import shutil
from pathlib import Path
from src.utils.logger import get_diagnostic_logger
from src.guards.ollama_guard import OllamaGuard
from src.guards.prompts import (
    SYSTEM_LATEX_HEALER,
    PROMPT_LATEX_HEALER_TEMPLATE,
    SYSTEM_MANIFEST_VALIDATOR,
    PROMPT_MANIFEST_VALIDATOR_TEMPLATE,
)

logger = get_diagnostic_logger("Validator")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUARANTINE_DIR = PROJECT_ROOT / "data" / "needs_review"


class ValidatorGuard:
    """Orchestrates input schema validation and output self-healing."""

    def __init__(self, ollama: OllamaGuard = None):
        self.ollama = ollama or OllamaGuard()
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    # ==========================================
    # 1. Input Guard: Manifest & File Matching
    # ==========================================
    def validate_input_manifest(self, input_dir: Path) -> dict:
        """
        Inspects input_dir for manifest.json or metadata.json.
        Verifies actual files match the JSON descriptions.
        If discrepancies occur, auto-invokes Ollama to diagnose.
        """
        input_dir = Path(input_dir)
        manifest_path = None
        for cand in ["manifest.json", "metadata.json", "book_manifest.json"]:
            p = input_dir / cand
            if p.exists():
                manifest_path = p
                break

        if not manifest_path:
            return {"valid": True, "has_manifest": False, "message": "No manifest found; bypassing schema check."}

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception as e:
            return {"valid": False, "has_manifest": True, "error": f"Corrupted JSON: {e}"}

        # Check expected files / chapters
        expected_items = manifest_data.get("chapters", []) or manifest_data.get("files", [])
        actual_files = [f.name for f in input_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

        discrepancies = []
        for exp in expected_items:
            fname = exp if isinstance(exp, str) else exp.get("filename") or exp.get("title")
            if fname and not any(fname.lower() in act.lower() for act in actual_files):
                discrepancies.append(f"Missing expected item from manifest: '{fname}'")

        if not discrepancies:
            return {"valid": True, "has_manifest": True, "discrepancies": []}

        logger.warning(
            where="ValidatorGuard.validate_input_manifest",
            why=f"Manifest mismatch found: {len(discrepancies)} discrepancies.",
            how_to_fix="Review input folder or let Ollama generate repair plan.",
        )

        # Trigger Ollama for semantic diagnosis using pre-defined prompt template
        prompt = PROMPT_MANIFEST_VALIDATOR_TEMPLATE.format(
            manifest_json=json.dumps(manifest_data, indent=2),
            actual_files=actual_files,
            discrepancies=discrepancies,
        )
        res = self.ollama.safe_generate(
            prompt=prompt,
            system_prompt=SYSTEM_MANIFEST_VALIDATOR,
        )

        return {
            "valid": False,
            "has_manifest": True,
            "discrepancies": discrepancies,
            "ollama_diagnosis": res.get("response") if res.get("success") else "Ollama unavailable for diagnosis.",
        }

    # ==========================================
    # 2. Output Guard: LaTeX & Syntax Self-Healing
    # ==========================================
    def quarantine_issue(self, category: str, raw_content: str, details: str, context: str = "", confidence: float = 0.0) -> Path:
        """
        Quarantines any unresolved, low-confidence, or failing artifact into data/needs_review/.
        Ensures the main batch pipeline never crashes.
        """
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_hash = abs(hash(raw_content + details)) % 100000
        quarantine_file = QUARANTINE_DIR / f"{category.lower().replace(' ', '_')}_{file_hash}.md"

        content = (
            f"# 🚨 [Needs Review] {category}\n\n"
            f"- **時間 (Timestamp)**: {now_str}\n"
            f"- **問題類型 (Category)**: {category}\n"
            f"- **AI 信度評估 (Confidence)**: {confidence:.2f} (門檻: 0.80)\n"
            f"- **原因說明 (Diagnosis)**: {details}\n\n"
            f"## 原始內容 (Raw Content)\n```text\n{raw_content}\n```\n\n"
        )
        if context:
            content += f"## 周邊語境 (Context)\n> {context}\n\n"
        content += (
            "## 👨‍💻 人工處理建議 (Recommended Human Action)\n"
            "1. 檢查上述原始內容是否有語法或 OCR 瑕疵。\n"
            "2. 修正後直接替換產出的 Markdown 檔案對應位置。\n"
            "3. 確認無誤後可將本檔案刪除。\n"
        )

        quarantine_file.write_text(content, encoding="utf-8")
        logger.warning(
            where=f"ValidatorGuard.quarantine_issue ({category})",
            why=f"{details} (Confidence: {confidence:.2f})",
            how_to_fix=f"Issue quarantined to {quarantine_file} for human inspection.",
        )
        return quarantine_file

    def repair_math_latex(self, broken_latex: str, context: str = "", min_confidence: float = 0.8) -> dict:
        """
        Attempts to repair broken LaTeX math formulas via Ollama using pre-defined prompt.
        If repair fails, returns invalid syntax, or confidence is below min_confidence,
        automatically quarantines the issue to data/needs_review/.
        """
        prompt = PROMPT_LATEX_HEALER_TEMPLATE.format(
            context=context,
            broken_latex=broken_latex,
        )

        res = self.ollama.safe_generate(
            prompt=prompt,
            system_prompt=SYSTEM_LATEX_HEALER,
        )

        if res.get("success") and res.get("response"):
            repaired = res["response"].strip()
            # Basic sanity check on returned LaTeX syntax
            if "$" in repaired and repaired.count("{") == repaired.count("}"):
                logger.info("Ollama auto-repaired LaTeX formula successfully.")
                return {"repaired": True, "latex": repaired, "quarantined": False}
            else:
                fail_reason = "Repaired formula failed balanced-delimiter validation."
        else:
            fail_reason = res.get("reason") or "Ollama service unavailable or timed out."

        # Quarantine if anything failed, was invalid, or confidence is uncertain
        q_path = self.quarantine_issue(
            category="LaTeX Math Error",
            raw_content=broken_latex,
            details=fail_reason,
            context=context,
            confidence=0.0,
        )

        return {"repaired": False, "latex": broken_latex, "quarantined": True, "file": str(q_path)}
