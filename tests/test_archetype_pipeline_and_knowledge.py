"""
Unit Tests for Archetype Pipelines, Hierarchical Config & Shared Knowledge
========================================================================
Tests:
  - ConfigManager: 4-tier configuration loading, deep merging, and harvesting
  - ReferenceParser: Hanging indent citation boundary parsing & formatting
  - IMRADResolver: Standard IMRAD heading promotion & emergent section resolution
  - OllamaHealer: Math/currency and continuity self-healing rules
"""

import json
import os
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from doc_processor.config_manager import ConfigManager, deep_merge
from doc_processor.parsers.literature.reference_parser import ReferenceParser
from doc_processor.parsers.literature.imrad_resolver import IMRADResolver
from doc_processor.verification.ollama_healer import OllamaHealer


class TestArchetypePipelineAndKnowledge(unittest.TestCase):

    def test_deep_merge(self):
        base = {"a": 1, "b": {"x": 10}, "list": [1, 2]}
        update = {"b": {"y": 20}, "c": 3, "list": [2, 3]}
        res = deep_merge(base, update)
        self.assertEqual(res["a"], 1)
        self.assertEqual(res["c"], 3)
        self.assertEqual(res["b"], {"x": 10, "y": 20})
        self.assertEqual(res["list"], [1, 2, 3])

    def test_config_manager_hierarchical_loading(self):
        cfg = ConfigManager.load_hierarchical_config(archetype="journal")
        self.assertEqual(cfg["archetype"], "journal")
        self.assertTrue(cfg.get("features", {}).get("is_journal_article"))
        self.assertFalse(cfg.get("features", {}).get("has_toc"))
        self.assertIn("shared_sections", cfg)
        self.assertIn("shared_symbols", cfg)

    def test_config_manager_textbook_archetype(self):
        cfg = ConfigManager.load_hierarchical_config(archetype="textbook")
        self.assertEqual(cfg["archetype"], "textbook")
        self.assertTrue(cfg.get("features", {}).get("has_toc"))
        self.assertTrue(cfg.get("features", {}).get("has_learning_objectives"))

    def test_reference_parser_apa_citations(self):
        sample = (
            "Blascovich, J., &amp; Tomaka, J. (1991). Measures of self-esteem. "
            "In J. P. Robinson (Ed.), *Measures of personality* (pp. 115–160). San Diego, CA: Academic Press. "
            "Centers for Disease Control (CDC). (2001). *Youth risk behavior surveillance system*. Atlanta, GA: CDC. "
            "DiClemente, R. J., Hansen, W. B., &amp; Ponton, L. E. (1995). *Handbook of adolescent health*. New York: Plenum."
        )
        entries = ReferenceParser.parse_citation_entries(sample)
        self.assertEqual(len(entries), 3)
        self.assertTrue(entries[0].startswith("Blascovich, J."))
        self.assertTrue(entries[1].startswith("Centers for Disease Control (CDC). (2001)."))
        self.assertTrue(entries[2].startswith("DiClemente, R. J."))

    def test_reference_parser_split_and_clean(self):
        full_doc = (
            "# Main Article\n\nSome introductory content.\n\n"
            "## References\n\n"
            "Hopko, D., &amp; Lejuez, C. (2006). Validity of BART. *J. Psych*, 28, 95–101. "
            "Killgore, W. (2007). Effects of sleep deprivation. *Psych Rep*, 100, 613–626.\n\n"
            "Received July 2, 2008\nAccepted September 17, 2008"
        )
        pre, header, body, post = ReferenceParser.split_references_section(full_doc)
        self.assertIn("Some introductory content.", pre)
        self.assertEqual(header, "## References")
        self.assertIn("Hopko", body)
        self.assertIn("Received July 2, 2008", post)

        cleaned = ReferenceParser.clean_document_references(full_doc)
        self.assertIn("Hopko, D., & Lejuez, C. (2006).", cleaned)
        self.assertIn("Killgore, W. (2007).", cleaned)
        self.assertIn("Received July 2, 2008", cleaned)

    def test_imrad_resolver_primary_and_secondary_headings(self):
        sample_md = (
            "# Study on BART\n\n"
            "Method\n\n"
            "Participants\n\nForty adolescents participated.\n\n"
            "Procedure\n\nParticipants completed the computer task.\n\n"
            "Results\n\nScores were significant.\n\n"
            "Discussion\n\nThese findings suggest valid assessment."
        )
        resolved = IMRADResolver.resolve_structure(sample_md)
        self.assertIn("## Method", resolved)
        self.assertIn("### Participants", resolved)
        self.assertIn("### Procedure", resolved)
        self.assertIn("## Results", resolved)
        self.assertIn("## Discussion", resolved)

    def test_imrad_resolver_emergent_sections(self):
        sample_md = (
            "# Paper Title\n\n"
            "Author Note\n\nCorrespondence concerning this article should be addressed to the author.\n\n"
            "## Introduction\n\nIntro text.\n\n"
            "## References\n\nAuthor, A. (2020). Book.\n\n"
            "Received 12 May 2020\nAccepted 15 June 2020"
        )
        resolved = IMRADResolver.resolve_structure(sample_md)
        self.assertIn("## Author Note & Acknowledgments", resolved)
        self.assertIn("### History & Received Dates", resolved)

    def test_imrad_resolver_blockquotes_removed_for_journals(self):
        sample_md = "> This was accidentally parsed as blockquote in two-column text."
        resolved = IMRADResolver.resolve_structure(sample_md)
        self.assertFalse(resolved.startswith("> "))
        self.assertEqual(resolved, "This was accidentally parsed as blockquote in two-column text.")

    def test_ollama_healer_math_syntax(self):
        healer = OllamaHealer(auto_start=False)
        raw = "Cost is $50 and another $12.50 was spent."
        healed, mod = healer._heal_math_syntax(raw, details="currency safety")
        self.assertTrue(mod)
        self.assertIn(r"\$50", healed)
        self.assertIn(r"\$12.50", healed)

    def test_ollama_healer_continuity(self):
        healer = OllamaHealer(auto_start=False)
        raw = "This is a broken sen-\n<!-- Page 2 -->\ntence across page."
        healed, mod = healer._heal_continuity(raw, details="continuity broken")
        self.assertTrue(mod)
        self.assertIn("sentence across page", healed)


if __name__ == '__main__':
    unittest.main()
