"""Unit tests for GlossaryAnchor (domain vocabulary injection and bidirectional cross-linking).
"""

from __future__ import annotations

import unittest
from literature_parser.services.verification.glossary_anchor import GlossaryAnchor
from literature_parser.services.verification.lexical_auditor import LexicalAuditor


class TestGlossaryAnchor(unittest.TestCase):
    """Verifies extracting glossary terms, injecting domain vocabulary, and linking terms."""

    def setUp(self):
        self.sample_glossary_md = """# Glossary

**Career Counseling**: A specialized counseling approach facilitating vocational exploration.
**Neuroplasticity**: The ability of neural networks in the brain to change through growth.
**Crystallization**: In Super's theory, the process of formulating a generalized vocational goal.
"""

    def test_extract_terms(self):
        """Verifies parsing glossary markdown into terms dictionary."""
        terms = GlossaryAnchor.extract_terms(self.sample_glossary_md)
        self.assertEqual(len(terms), 3)
        self.assertIn("Career Counseling", terms)
        self.assertIn("Neuroplasticity", terms)
        self.assertIn("Crystallization", terms)
        self.assertIn("vocational exploration", terms["Career Counseling"])

    def test_inject_domain_vocabulary(self):
        """Verifies injecting domain glossary terms into LexicalAuditor known words."""
        terms = GlossaryAnchor.extract_terms(self.sample_glossary_md)
        auditor = LexicalAuditor()

        # Before injection, neuroplasticity might not be in basic word list
        GlossaryAnchor.inject_domain_vocabulary(auditor, terms)
        self.assertIn("neuroplasticity", auditor.dict_words)
        self.assertIn("crystallization", auditor.dict_words)

    def test_link_terms_in_markdown(self):
        """Verifies wrapping first occurrence of glossary term with link/dfn anchor."""
        terms = GlossaryAnchor.extract_terms(self.sample_glossary_md)
        text = """# Chapter 1

Recent research highlights the role of neuroplasticity in adult learning.
Furthermore, neuroplasticity continues throughout lifespan development.
"""
        linked_md, count = GlossaryAnchor.link_terms_in_markdown(
            markdown_text=text,
            terms=terms,
            glossary_href="00-09-Glossary.xhtml",
        )
        self.assertEqual(count, 1)  # Only first occurrence linked
        self.assertIn('href="00-09-Glossary.xhtml#neuroplasticity"', linked_md)
        self.assertIn('class="glossary-term"', linked_md)


if __name__ == "__main__":
    unittest.main()
