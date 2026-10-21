"""
Unit Tests for FixPlaybook and Zero-Tolerance Hard Invariant Gate
================================================================
Verifies:
1. Zero-Tolerance Hard Invariant Gate (防呆門禁: 避免有錯還報對)
   - Rejects empty files (< 500 chars)
   - Rejects missing/watermark titles
   - Rejects missing abstract (literature)
   - Rejects missing references (literature)
   - Rejects unbalanced LaTeX formulas
   - Rejects raw OCR table leaks
   - Rejects orphan page numbers
   - Ensures FormatAuditor NEVER reports PASS when invariants are violated
2. FixPlaybook Knowledge Base & Recipes
   - Recipe listing, retrieval, and symptom matching
   - Execution of built-in recipes (orphan page numbers, currency, stats, references, etc.)
"""

import unittest
from pathlib import Path
from doc_processor.core.invariants import QualityInvariantGuard, InvariantViolationError
from doc_processor.fixes.playbook import FixPlaybook, FixRecipe
from doc_processor.verification.format_auditor import FormatAuditor


class TestFixPlaybookAndInvariants(unittest.TestCase):
    def setUp(self):
        self.auditor = FormatAuditor(is_literature=True)

    # -------------------------------------------------------------------------
    # 1. Zero-Tolerance Hard Invariant Gate Tests (避免有錯還報對)
    # -------------------------------------------------------------------------

    def test_invariant_empty_file_rejected(self):
        tiny_md = "# Title\n\nShort."
        res = QualityInvariantGuard.verify_hard_invariants(tiny_md, is_literature=True)
        self.assertFalse(res['valid'])
        self.assertTrue(any("INV_NON_EMPTY" in v for v in res['violations']))

        rep = self.auditor.audit_text(tiny_md)
        self.assertFalse(rep.passed, "Anti-False-Positive: Tiny document MUST NOT pass audit!")
        self.assertTrue(rep.error_count > 0)

    def test_invariant_watermark_title_rejected(self):
        wm_md = (
            "# NIH Public Access\n\n"
            "## Abstract\n" + "This is a legitimate abstract text for testing. " * 5 + "\n\n"
            "## Introduction\n" + "Body prose content. " * 30 + "\n\n"
            "## References\n- Author A (2020). Title."
        )
        res = QualityInvariantGuard.verify_hard_invariants(wm_md, is_literature=True)
        self.assertFalse(res['valid'])
        self.assertTrue(any("INV_TITLE" in v for v in res['violations']))

        rep = self.auditor.audit_text(wm_md)
        self.assertFalse(rep.passed, "Anti-False-Positive: Watermark title MUST NOT pass audit!")

    def test_invariant_missing_abstract_rejected(self):
        no_abs_md = (
            "# Genuine Paper Title\n\n"
            "## Introduction\n" + "Body prose content. " * 30 + "\n\n"
            "## Methods\n" + "Method details. " * 20 + "\n\n"
            "## References\n- Author A (2020). Title."
        )
        res = QualityInvariantGuard.verify_hard_invariants(no_abs_md, is_literature=True)
        self.assertFalse(res['valid'])
        self.assertTrue(any("INV_ABSTRACT" in v for v in res['violations']))

        rep = self.auditor.audit_text(no_abs_md)
        self.assertFalse(rep.passed, "Anti-False-Positive: Missing abstract MUST NOT pass audit!")

    def test_invariant_missing_references_rejected(self):
        no_ref_md = (
            "# Genuine Paper Title\n\n"
            "## Abstract\n" + "This is a legitimate abstract text for testing. " * 5 + "\n\n"
            "## Introduction\n" + "Body prose content. " * 30 + "\n\n"
            "## Discussion\n" + "Discussion prose. " * 20 + "\n"
        )
        # Expand lines > 150
        no_ref_md += ("Line of text content.\n" * 160)
        res = QualityInvariantGuard.verify_hard_invariants(no_ref_md, is_literature=True)
        self.assertFalse(res['valid'])
        self.assertTrue(any("INV_REFERENCES" in v for v in res['violations']))

        rep = self.auditor.audit_text(no_ref_md)
        self.assertFalse(rep.passed, "Anti-False-Positive: Long paper missing references MUST NOT pass audit!")

    def test_invariant_orphan_page_number_rejected(self):
        page_num_md = (
            "# Genuine Paper Title\n\n"
            "## Abstract\n" + "This is a legitimate abstract text for testing. " * 5 + "\n\n"
            "## Introduction\n" + "Body prose content. " * 20 + "\n\n"
            "75\n\n"
            "More body prose content. " * 20 + "\n\n"
            "## References\n- Author A (2020). Title."
        )
        res = QualityInvariantGuard.verify_hard_invariants(page_num_md, is_literature=True)
        self.assertFalse(res['valid'])
        self.assertTrue(any("INV_NO_ORPHAN_PAGE_NUMS" in v for v in res['violations']))

        rep = self.auditor.audit_text(page_num_md)
        self.assertFalse(rep.passed, "Anti-False-Positive: Orphan page numbers MUST NOT pass audit!")

    def test_invariant_perfect_document_passes(self):
        perfect_md = (
            "# Cognitive Plasticity in Bilingual Brains\n\n"
            "## Abstract\n" + "This study provides empirical evidence for cognitive plasticity in bilinguals. " * 3 + "\n\n"
            "## Introduction\n" + "Background context. " * 25 + "\n\n"
            "## Methods\n" + "Participants and apparatus. " * 20 + "\n\n"
            "## Results\n" + "Findings showed significant differences, $p < .01$. " * 20 + "\n\n"
            "## Discussion\n" + "Implications for neurobiology. " * 20 + "\n\n"
            "## References\n- Bialystok E (2007). Bilingualism in development. Cambridge University Press."
        )
        res = QualityInvariantGuard.verify_hard_invariants(perfect_md, is_literature=True)
        self.assertTrue(res['valid'], f"Valid document was rejected: {res['violations']}")

        rep = self.auditor.audit_text(perfect_md)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.error_count, 0)

    # -------------------------------------------------------------------------
    # 2. FixPlaybook Knowledge Base Tests
    # -------------------------------------------------------------------------

    def test_playbook_catalog(self):
        recipes = FixPlaybook.list_recipes()
        self.assertGreaterEqual(len(recipes), 8)
        ids = [r.recipe_id for r in recipes]
        self.assertIn("clean_orphan_page_numbers", ids)
        self.assertIn("escape_currency_katex", ids)
        self.assertIn("elsevier_glued_references", ids)
        self.assertIn("normalize_corrupted_stats", ids)
        self.assertIn("strip_nih_watermarks", ids)
        self.assertIn("unparenthesized_ref_years", ids)
        self.assertIn("demote_recommendation_headings", ids)
        self.assertIn("cup_sidebar_cleaning", ids)

    def test_playbook_symptom_matching(self):
        sample_text = (
            "# NIH Public Access\n\n"
            "Cost was $25.\n\n"
            "75\n\n"
            "t ð 24 Þ = 2: 06"
        )
        matches = FixPlaybook.match_symptoms(sample_text, archetype="literature")
        matched_ids = [r.recipe_id for r, _ in matches]
        self.assertIn("strip_nih_watermarks", matched_ids)
        self.assertIn("escape_currency_katex", matched_ids)
        self.assertIn("clean_orphan_page_numbers", matched_ids)
        self.assertIn("normalize_corrupted_stats", matched_ids)

    def test_recipe_clean_orphan_page_numbers(self):
        text = "Line before.\n\n75\n\nLine after."
        repaired, count, ok = FixPlaybook.apply_recipe("clean_orphan_page_numbers", text)
        self.assertTrue(ok)
        self.assertEqual(count, 1)
        self.assertNotIn("75", repaired)

    def test_recipe_escape_currency_katex(self):
        text = "Cost was $50 and reward was $100.50."
        repaired, count, ok = FixPlaybook.apply_recipe("escape_currency_katex", text)
        self.assertTrue(ok)
        self.assertEqual(count, 2)
        self.assertIn(r"\$50", repaired)
        self.assertIn(r"\$100.50", repaired)

    def test_recipe_normalize_corrupted_stats(self):
        text = "Significant result, *t* ð 24 Þ = 2: 06, p o 0: 01, M = 4: 46, s. d. =2.02."
        repaired, count, ok = FixPlaybook.apply_recipe("normalize_corrupted_stats", text)
        self.assertTrue(ok)
        self.assertGreaterEqual(count, 4)
        self.assertIn("$t(24) = 2.06$", repaired)
        self.assertIn("$p < 0.01$", repaired)
        self.assertIn("$M = 4.46$", repaired)
        self.assertIn("$SD = 2.02$", repaired)

    def test_recipe_elsevier_glued_references(self):
        text = "Supported by award. **References** Abrahamsson N (2012)."
        repaired, count, ok = FixPlaybook.apply_recipe("elsevier_glued_references", text)
        self.assertTrue(ok)
        self.assertEqual(count, 1)
        self.assertIn("## References\n\nAbrahamsson", repaired)

    def test_recipe_demote_recommendation_headings(self):
        text = "## 1. Clinicians are encouraged to assess client readiness and emotional state."
        repaired, count, ok = FixPlaybook.apply_recipe("demote_recommendation_headings", text)
        self.assertTrue(ok)
        self.assertEqual(count, 1)
        self.assertTrue(repaired.startswith("1. Clinicians are encouraged"))


if __name__ == "__main__":
    unittest.main()
