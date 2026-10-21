import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer


class TestV25LayoutHealer(unittest.TestCase):

    def test_swallowed_heading_healing(self):
        """Asserts swallowed headings are extracted from blockquotes."""
        raw_md = "\n".join([
            "> [!TIP] **Study Question 2.1**",
            "> What is an experimental approach?",
            "> ## 2.2 Variables in Research",
            "> This is the next section body."
        ])
        healed, fixes = LayoutAutoHealer.heal_swallowed_callout_boundaries(raw_md)
        self.assertNotIn("> ## 2.2", healed)
        self.assertIn("## 2.2 Variables in Research", healed)
        self.assertTrue(any("swallowed heading" in f for f in fixes))

    def test_swallowed_nested_callout_healing(self):
        """Asserts nested learning objectives and glossaries are split cleanly."""
        raw_md = "\n".join([
            "> [!TIP] **Study Question 2.1**",
            "> Details...",
            "> > 🎯 **2.2** Understand variable types."
        ])
        healed, fixes = LayoutAutoHealer.heal_swallowed_callout_boundaries(raw_md)
        self.assertNotIn("> > 🎯", healed)
        self.assertIn("> 🎯 **2.2**", healed)

    def test_blockquote_false_positive_healing(self):
        """Asserts body paragraphs falsely prefixed with > are unwrapped."""
        raw_md = "\n".join([
            "> Causation is one of those terms often used in everyday conversation.",
            "> When individuals discuss causation they are usually seeking the answer.",
            "> The following section discusses the primary methods of scientific inquiry."
        ])
        healed, fixes = LayoutAutoHealer.heal_blockquote_false_positives(raw_md)
        self.assertNotIn("> Causation", healed)
        self.assertNotIn("> When individuals", healed)
        self.assertTrue(healed.startswith("Causation is one of those"))
        self.assertTrue(any("Unwrapped false-positive" in f for f in fixes))

    def test_genuine_callout_not_unwrapped(self):
        """Asserts genuine tip and objective callouts remain intact."""
        raw_md = "\n".join([
            "> [!TIP] **Study Question 2.1**",
            "> Review this carefully.",
            "> Make sure you understand the concept."
        ])
        healed, fixes = LayoutAutoHealer.heal_blockquote_false_positives(raw_md)
        self.assertIn("> [!TIP]", healed)
        self.assertEqual(len(fixes), 0)

    def test_double_formatting_healing(self):
        """Asserts quad-asterisks are normalized to double asterisks."""
        raw_md = "**Table 2.1** ****Types of Variables**** and ** *Important Concepts* **"
        healed, fixes = LayoutAutoHealer.heal_double_formatting(raw_md)
        self.assertNotIn("****", healed)
        self.assertIn("**Types of Variables**", healed)
        self.assertIn("***Important Concepts***", healed)

    def test_table_pipe_healing(self):
        """Asserts tables lacking GFM separator rows receive auto-inserted separators."""
        raw_md = "\n".join([
            "| Variable Type | Key Characteristic | Example |",
            "| Independent Variable | Presumed cause manipulated by researcher | Treatment dose |",
            ""
        ])
        healed, fixes = LayoutAutoHealer.heal_table_blocks(raw_md)
        self.assertIn("| --- | --- | --- |", healed)
        self.assertTrue(any("Inserted missing GFM table separator" in f for f in fixes))


if __name__ == "__main__":
    unittest.main()
