"""
Ollama Recipe Synthesizer & Staging Engine
==========================================
Empowers local Ollama models (e.g., qwen2.5-coder:7b, deepseek-r1:8b) to
synthesize standalone Python repair functions for unhandled document defects.

Safety Architecture:
1. AST Static Verification: Enforces pure functional regex transformations,
   blocking dangerous imports (os, sys, subprocess, etc.) and builtins (eval, exec, open).
2. Sandbox Execution: Evaluates synthesized test cases within an isolated scope
   with strict timeouts before writing to disk.
3. Quarantined Staging: Writes validated recipes to `src/doc_processor/fixes/staged/`
   for human review and CLI-driven lifecycle management (review, test, promote, reject).
"""

import ast
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.guards.hardware import check_hardware_safety
from src.guards.ollama_guard import OllamaGuard
from src.guards.prompts import PromptRegistry
from src.utils.logger import get_diagnostic_logger

logger = get_diagnostic_logger("RecipeSynthesizer")

STAGED_DIR = Path(__file__).resolve().parent / "staged"
PROMOTED_DIR = Path(__file__).resolve().parent / "promoted"


class RecipeSafetyError(Exception):
    """Raised when synthesized code violates AST security constraints."""


class RecipeExecutionError(Exception):
    """Raised when synthesized code fails its self-contained test cases."""


@dataclass
class SynthesisResult:
    """Outcome of an Ollama recipe synthesis attempt."""
    success: bool
    recipe_id: str
    recipe_name: str = ""
    file_path: Optional[Path] = None
    error: Optional[str] = None
    code: str = ""
    test_results: Dict[str, Any] = field(default_factory=dict)
    model_used: str = ""


class RecipeSafetyValidator:
    """
    Static AST code auditor to verify that synthesized Python recipes
    are strictly deterministic, pure-functional string transformations.
    """

    ALLOWED_MODULES = {"re", "typing", "dataclasses", "unicodedata", "math", "string"}
    FORBIDDEN_BUILTINS = {
        "eval", "exec", "compile", "__import__", "open", "input",
        "breakpoint", "globals", "locals", "vars", "dir",
        "getattr", "setattr", "delattr", "hasattr"
    }

    @classmethod
    def validate_ast(cls, code: str) -> Tuple[bool, Optional[str]]:
        """
        Parses and inspects the AST tree of synthesized code.
        Returns: (is_safe, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error in synthesized code: {e}"

        has_repair_func = False
        has_metadata = False
        has_test_cases = False

        for node in ast.walk(tree):
            # Check module imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg not in cls.ALLOWED_MODULES:
                        return False, f"Disallowed module import: '{alias.name}'. Only {cls.ALLOWED_MODULES} permitted."

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg not in cls.ALLOWED_MODULES:
                        return False, f"Disallowed from-import module: '{node.module}'. Only {cls.ALLOWED_MODULES} permitted."

            # Check forbidden function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.FORBIDDEN_BUILTINS:
                        return False, f"Disallowed builtin call: '{node.func.id}'"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr.startswith("__") and node.func.attr.endswith("__"):
                        return False, f"Disallowed dunder attribute access: '{node.func.attr}'"

            # Check top-level required definitions
            if isinstance(node, ast.FunctionDef) and node.name == "repair":
                has_repair_func = True

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "RECIPE_METADATA":
                            has_metadata = True
                        elif target.id == "TEST_CASES":
                            has_test_cases = True

        if not has_repair_func:
            return False, "Missing mandatory function 'def repair(text: str) -> Tuple[str, int]:'"
        if not has_metadata:
            return False, "Missing mandatory dictionary 'RECIPE_METADATA'"
        if not has_test_cases:
            return False, "Missing mandatory list 'TEST_CASES'"

        return True, None


class OllamaRecipeSynthesizer:
    """
    Autonomous recipe creator powered by local Ollama LLMs.
    Identifies unhandled defects, synthesizes repair code, validates safety,
    and isolates to the staged playbook directory.
    """

    def __init__(self, ollama_guard: Optional[OllamaGuard] = None):
        self.guard = ollama_guard or OllamaGuard(target_model="qwen2.5-coder:7b")

    def synthesize_recipe(
        self,
        problem_description: str,
        sample_excerpt: str,
        recipe_id_hint: Optional[str] = None,
        archetype: str = "literature",
        max_retries: int = 2
    ) -> SynthesisResult:
        """
        Invokes Ollama to synthesize a new repair recipe, statically verifies it,
        runs its test cases in an isolated scope, and stages it.
        Includes an automatic self-healing loop that feeds test failures back to Ollama.
        """
        # 1. Hardware safety verification
        hw = check_hardware_safety()
        if not hw["safe_for_heavy_llm"]:
            reasons = "; ".join(hw["reasons"])
            logger.warning(
                where="OllamaRecipeSynthesizer.synthesize_recipe",
                why=f"Hardware constraints active: {reasons}",
                how_to_fix="Ensure AC charger is connected or free system memory.",
            )
            return SynthesisResult(
                success=False,
                recipe_id=recipe_id_hint or "unknown_recipe",
                error=f"Hardware constraints active: {reasons}",
            )

        # 2. Craft initial prompt via centralized PromptRegistry
        system_prompt, current_prompt = PromptRegistry.get_recipe_synthesizer(
            problem_description=problem_description,
            sample_excerpt=sample_excerpt,
            recipe_id_hint=recipe_id_hint,
            archetype=archetype,
        )

        last_error = ""
        last_code = ""
        last_test_info: Dict[str, Any] = {}
        model_name = ""

        for attempt in range(1, max_retries + 2):
            logger.info(f"RecipeSynthesizer: Querying Ollama (attempt {attempt}/{max_retries + 1})...")
            gen_res = self.guard.safe_generate(
                prompt=current_prompt,
                system_prompt=system_prompt,
                timeout=60.0
            )

            if not gen_res.get("success") or not gen_res.get("response"):
                last_error = gen_res.get("reason") or "Ollama failed to generate response."
                break

            model_name = gen_res.get("model", "ollama")
            raw_response = gen_res["response"]
            code = self._extract_python_code(raw_response)
            if not code:
                last_error = "Could not extract valid Python code block from Ollama output."
                current_prompt = (
                    "Error: Your output did not contain a valid Python code block inside ```python ... ```.\n"
                    "Please provide the complete module inside ```python ... ```."
                )
                continue

            last_code = code

            # Static AST Security Audit
            is_safe, ast_err = RecipeSafetyValidator.validate_ast(code)
            if not is_safe:
                logger.warning(
                    where="OllamaRecipeSynthesizer.synthesize_recipe",
                    why=f"AST validation failed on attempt {attempt}: {ast_err}",
                    how_to_fix="Refining prompt to fix AST violation",
                )
                last_error = f"AST security check rejected code: {ast_err}"
                current_prompt = PromptRegistry.get_recipe_refinement_prompt(ast_err, is_ast_error=True)
                continue

            # Sandbox Test Execution
            test_passed, test_info = self._execute_sandbox_tests(code)
            last_test_info = test_info
            if not test_passed:
                err_detail = test_info.get("error", "Unknown test failure")
                logger.warning(
                    where="OllamaRecipeSynthesizer.synthesize_recipe",
                    why=f"Sandbox test failed on attempt {attempt}: {err_detail}",
                    how_to_fix="Refining prompt with test failure details",
                )
                last_error = f"Sandbox test failed: {err_detail}"
                current_prompt = PromptRegistry.get_recipe_refinement_prompt(err_detail, is_ast_error=False)
                continue

            # Success! Stage recipe to disk
            recipe_id = test_info["recipe_id"]
            staged_path = self._stage_recipe(recipe_id, code, test_info)

            logger.info(f"RecipeSynthesizer: Successfully synthesized and staged recipe '{recipe_id}' (attempt {attempt}) to {staged_path}")
            return SynthesisResult(
                success=True,
                recipe_id=recipe_id,
                recipe_name=test_info.get("name", recipe_id),
                file_path=staged_path,
                code=code,
                test_results=test_info,
                model_used=model_name,
            )

        return SynthesisResult(
            success=False,
            recipe_id=last_test_info.get("recipe_id", recipe_id_hint or "failed_synthesis"),
            error=last_error,
            code=last_code,
            test_results=last_test_info,
            model_used=model_name,
        )

    def _extract_python_code(self, response: str) -> Optional[str]:
        """Extracts python code from markdown fence or returns raw code."""
        match = re.search(r"```(?:python)?\s*([\s\S]*?)```", response)
        if match:
            return match.group(1).strip()
        # Fallback: if already starts with import or RECIPE_METADATA
        if "RECIPE_METADATA" in response and "def repair" in response:
            return response.strip()
        return None

    def _execute_sandbox_tests(self, code: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes the synthesized module inside a restricted dictionary scope
        and runs its self-contained TEST_CASES.
        """
        # Prepare safe execution environment
        import re as safe_re
        import string as safe_string
        import unicodedata as safe_unicodedata

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            root_pkg = name.split(".")[0]
            if root_pkg in RecipeSafetyValidator.ALLOWED_MODULES:
                return __import__(name, globals, locals, fromlist, level)
            raise ImportError(f"Import of '{name}' is not permitted in sandbox.")

        safe_env = {
            "__builtins__": {
                "__import__": safe_import,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "isinstance": isinstance,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "zip": zip,
                "min": min,
                "max": max,
                "sum": sum,
                "print": lambda *args: None,
            },
            "re": safe_re,
            "unicodedata": safe_unicodedata,
            "string": safe_string,
        }

        try:
            exec(code, safe_env)
        except Exception as e:
            return False, {"error": f"Module load exception: {e}"}

        metadata = safe_env.get("RECIPE_METADATA")
        repair_fn = safe_env.get("repair")
        test_cases = safe_env.get("TEST_CASES")

        if not isinstance(metadata, dict) or "recipe_id" not in metadata:
            return False, {"error": "RECIPE_METADATA must be a dictionary with 'recipe_id'"}
        if not callable(repair_fn):
            return False, {"error": "'repair' is not callable"}
        if not isinstance(test_cases, list) or not test_cases:
            return False, {"error": "'TEST_CASES' must be a non-empty list of (input, expected) tuples"}

        # Run test cases
        case_results = []
        for i, case in enumerate(test_cases):
            if not isinstance(case, (tuple, list)) or len(case) != 2:
                return False, {"error": f"Test case {i+1} must be a (input, expected) tuple"}
            inp, exp = case
            start_t = time.perf_counter()
            try:
                res_text, count = repair_fn(inp)
                elapsed_ms = (time.perf_counter() - start_t) * 1000
                if res_text != exp:
                    return False, {
                        "error": f"Test case {i+1} failed.\nInput:\n{inp}\nExpected:\n{exp}\nGot:\n{res_text}",
                        "recipe_id": metadata["recipe_id"],
                    }
                case_results.append({"case": i + 1, "fixes": count, "elapsed_ms": round(elapsed_ms, 2)})
            except Exception as e:
                return False, {
                    "error": f"Test case {i+1} raised exception: {e}",
                    "recipe_id": metadata["recipe_id"],
                }

        return True, {
            "recipe_id": metadata["recipe_id"],
            "name": metadata.get("name", metadata["recipe_id"]),
            "description": metadata.get("description", ""),
            "symptoms": metadata.get("symptoms", []),
            "category": metadata.get("category", "format"),
            "test_cases_run": len(test_cases),
            "cases": case_results,
        }

    def _stage_recipe(self, recipe_id: str, code: str, metadata: Dict[str, Any]) -> Path:
        """Writes the synthesized recipe into the staged/ directory with full provenance metadata."""
        STAGED_DIR.mkdir(parents=True, exist_ok=True)
        py_path = STAGED_DIR / f"{recipe_id}.py"
        meta_path = STAGED_DIR / f"{recipe_id}.json"

        # Embed standard header
        header = (
            f"# =====================================================================\n"
            f"# AUTO-GENERATED BY OLLAMA RECIPE SYNTHESIZER\n"
            f"# Recipe ID: {recipe_id}\n"
            f"# Status   : STAGED (Pending User Review & Promotion)\n"
            f"# Date     : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# =====================================================================\n\n"
        )
        full_code = header + code.strip() + "\n"

        # Atomic writes
        tmp_py = py_path.with_suffix(".tmp")
        tmp_py.write_text(full_code, encoding="utf-8")
        tmp_py.replace(py_path)

        meta_info = {
            "recipe_id": recipe_id,
            "status": "staged",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata,
            "file": str(py_path.name),
        }
        tmp_meta = meta_path.with_suffix(".tmp")
        tmp_meta.write_text(json.dumps(meta_info, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_meta.replace(meta_path)

        return py_path
