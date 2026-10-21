"""
Unit Tests for Ollama Recipe Synthesizer, AST Safety Validator & Staged Playbook Lifecycle
==========================================================================================
"""

import ast
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from literature_parser.adapters.fixes.playbook import FixPlaybook, FixRecipe
from literature_parser.adapters.fixes.synthesizer import (
    OllamaRecipeSynthesizer,
    RecipeSafetyValidator,
    SynthesisResult,
)
from literature_parser.adapters.guards.hardware import (
    MIN_RAM_GB_AC,
    MIN_RAM_GB_BATTERY,
    check_hardware_safety,
    get_macos_memory_pressure_level,
)


class TestRecipeSafetyValidator(unittest.TestCase):
    """Verifies that the static AST security auditor strictly isolates synthesized code."""

    def test_valid_safe_code(self):
        valid_code = '''
import re
from typing import Tuple

RECIPE_METADATA = {
    "recipe_id": "test_safe_cleaner",
    "name": "Safe Cleaner",
    "description": "Cleans dummy token",
    "symptoms": [r"__DUMMY__"],
    "category": "format",
}

def repair(text: str) -> Tuple[str, int]:
    new_text, count = re.subn(r"__DUMMY__", "", text)
    return new_text, count

TEST_CASES = [
    ("Hello __DUMMY__ world", "Hello  world"),
]
'''
        is_safe, err = RecipeSafetyValidator.validate_ast(valid_code)
        self.assertTrue(is_safe, f"Expected safe code to pass AST audit, got: {err}")
        self.assertIsNone(err)

    def test_blocks_dangerous_import(self):
        malicious_code = '''
import os
from typing import Tuple

RECIPE_METADATA = {"recipe_id": "bad", "name": "bad"}
def repair(text: str) -> Tuple[str, int]:
    return text, 0
TEST_CASES = [("a", "a")]
'''
        is_safe, err = RecipeSafetyValidator.validate_ast(malicious_code)
        self.assertFalse(is_safe)
        self.assertIn("Disallowed module import", err)

    def test_blocks_dangerous_from_import(self):
        malicious_code = '''
from subprocess import Popen
from typing import Tuple

RECIPE_METADATA = {"recipe_id": "bad", "name": "bad"}
def repair(text: str) -> Tuple[str, int]:
    return text, 0
TEST_CASES = [("a", "a")]
'''
        is_safe, err = RecipeSafetyValidator.validate_ast(malicious_code)
        self.assertFalse(is_safe)
        self.assertIn("Disallowed from-import", err)

    def test_blocks_forbidden_builtin_eval(self):
        malicious_code = '''
import re
from typing import Tuple

RECIPE_METADATA = {"recipe_id": "bad", "name": "bad"}
def repair(text: str) -> Tuple[str, int]:
    eval("1 + 1")
    return text, 0
TEST_CASES = [("a", "a")]
'''
        is_safe, err = RecipeSafetyValidator.validate_ast(malicious_code)
        self.assertFalse(is_safe)
        self.assertIn("Disallowed builtin call", err)

    def test_missing_mandatory_components(self):
        no_repair = '''
import re
RECIPE_METADATA = {"recipe_id": "bad"}
TEST_CASES = []
'''
        is_safe, err = RecipeSafetyValidator.validate_ast(no_repair)
        self.assertFalse(is_safe)
        self.assertIn("Missing mandatory function", err)


class TestOllamaRecipeSynthesizerSandbox(unittest.TestCase):
    """Verifies that the sandbox test execution validates synthesized functions correctly."""

    def setUp(self):
        self.synthesizer = OllamaRecipeSynthesizer()

    def test_sandbox_success(self):
        code = '''
import re

RECIPE_METADATA = {
    "recipe_id": "strip_foo",
    "name": "Strip Foo",
    "description": "Removes foo words",
    "symptoms": [r"\\bfoo\\b"],
    "category": "format",
}

def repair(text: str):
    res, cnt = re.subn(r"\\bfoo\\b", "bar", text)
    return res, cnt

TEST_CASES = [
    ("test foo test", "test bar test"),
    ("hello foo world", "hello bar world"),
]
'''
        passed, info = self.synthesizer._execute_sandbox_tests(code)
        self.assertTrue(passed, f"Sandbox failed: {info}")
        self.assertEqual(info["test_cases_run"], 2)
        self.assertEqual(info["recipe_id"], "strip_foo")

    def test_sandbox_failure_on_incorrect_output(self):
        code = '''
RECIPE_METADATA = {"recipe_id": "broken_recipe"}
def repair(text: str):
    return text, 0  # Does not modify text!
TEST_CASES = [
    ("input_buggy", "expected_fixed"),
]
'''
        passed, info = self.synthesizer._execute_sandbox_tests(code)
        self.assertFalse(passed)
        self.assertIn("Test case 1 failed", info["error"])


class TestStagedPlaybookLifecycle(unittest.TestCase):
    """Verifies the complete lifecycle of staged recipes: staging, reviewing, testing, promoting, and rejecting."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.staged_dir = self.test_dir / "staged"
        self.promoted_dir = self.test_dir / "promoted"
        self.staged_dir.mkdir(parents=True)
        self.promoted_dir.mkdir(parents=True)

        self._orig_staged = FixPlaybook.STAGED_DIR
        self._orig_promoted = FixPlaybook.PROMOTED_DIR
        FixPlaybook.STAGED_DIR = self.staged_dir
        FixPlaybook.PROMOTED_DIR = self.promoted_dir

        self.synth = OllamaRecipeSynthesizer()

    def tearDown(self):
        FixPlaybook.STAGED_DIR = self._orig_staged
        FixPlaybook.PROMOTED_DIR = self._orig_promoted
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_staged_lifecycle(self):
        # 1. Manually stage a valid test recipe
        recipe_id = "test_custom_semicolon_fix"
        code = '''
import re

RECIPE_METADATA = {
    "recipe_id": "test_custom_semicolon_fix",
    "name": "Custom Semicolon Fixer",
    "description": "Normalizes double semicolons",
    "symptoms": [r";;"],
    "archetype": "literature",
    "category": "format",
}

def repair(text: str):
    return re.subn(r";;", ";", text)

TEST_CASES = [
    ("Item 1;; Item 2", "Item 1; Item 2"),
]
'''
        # Write directly to test staged dir
        py_file = self.staged_dir / f"{recipe_id}.py"
        json_file = self.staged_dir / f"{recipe_id}.json"
        py_file.write_text(code, encoding="utf-8")
        json_file.write_text(
            json.dumps({"recipe_id": recipe_id, "status": "staged", "metadata": {"name": "Test"}}, indent=2),
            encoding="utf-8"
        )

        # Test list_staged_recipes
        staged_list = FixPlaybook.list_staged_recipes()
        self.assertEqual(len(staged_list), 1)
        self.assertEqual(staged_list[0]["recipe_id"], recipe_id)

        # Test test_staged_recipe
        test_res = FixPlaybook.test_staged_recipe(recipe_id)
        self.assertTrue(test_res["success"])

        # Test promote_staged_recipe
        ok, msg = FixPlaybook.promote_staged_recipe(recipe_id)
        self.assertTrue(ok)
        self.assertIn("Successfully promoted", msg)

        # Check that it moved to promoted_dir
        self.assertFalse(py_file.exists())
        self.assertTrue((self.promoted_dir / f"{recipe_id}.py").exists())

        # Test execution of the newly promoted recipe
        repaired, count, succ = FixPlaybook.apply_recipe(recipe_id, "A;; B;; C")
        self.assertTrue(succ)
        self.assertEqual(count, 2)
        self.assertEqual(repaired, "A; B; C")

        # Clean up recipe from registry
        if recipe_id in FixPlaybook._recipes:
            del FixPlaybook._recipes[recipe_id]


class TestDynamicHardwareThreshold(unittest.TestCase):
    """Verifies the dynamic power-aware RAM threshold evaluation."""

    def test_dynamic_ram_ac_threshold(self):
        with patch("literature_parser.adapters.guards.hardware.get_battery_status", return_value={"is_battery": False, "percent": 100, "description": "AC Power Connected"}), \
             patch("literature_parser.adapters.guards.hardware.get_available_ram_gb", return_value=2.8), \
             patch("literature_parser.adapters.guards.hardware.get_disk_free_gb", return_value=25.0), \
             patch("literature_parser.adapters.guards.hardware.get_macos_memory_pressure_level", return_value=1):

            hw = check_hardware_safety()
            self.assertTrue(hw["safe_for_heavy_llm"])
            self.assertEqual(hw["metrics"]["effective_min_ram_gb"], MIN_RAM_GB_AC)

    def test_dynamic_ram_battery_threshold(self):
        with patch("literature_parser.adapters.guards.hardware.get_battery_status", return_value={"is_battery": True, "percent": 80, "description": "Battery Mode (80%)"}), \
             patch("literature_parser.adapters.guards.hardware.get_available_ram_gb", return_value=2.8), \
             patch("literature_parser.adapters.guards.hardware.get_disk_free_gb", return_value=25.0), \
             patch("literature_parser.adapters.guards.hardware.get_macos_memory_pressure_level", return_value=1):

            hw = check_hardware_safety()
            # In battery mode with 2.8 GB, should fail because battery mode requires 4.0 GB
            self.assertFalse(hw["safe_for_heavy_llm"])
            self.assertEqual(hw["metrics"]["effective_min_ram_gb"], MIN_RAM_GB_BATTERY)


if __name__ == "__main__":
    unittest.main()
