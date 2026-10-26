"""Glossary Anchor Service (GlossaryAnchor).
=========================================
Extracts terms and definitions from textbook Glossary back-matter documents,
injects domain vocabulary into LexicalAuditor to eliminate false-positive spelling
penalties on technical terms, and enriches Markdown with bidirectional cross-links.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional, Set, Tuple

from literature_parser.services.verification.lexical_auditor import LexicalAuditor

logger = logging.getLogger(__name__)


class GlossaryAnchor:
    """Provides glossary parsing, domain dictionary injection, and term linking."""

    @classmethod
    def extract_terms(cls, glossary_markdown: str) -> Dict[str, str]:
        """Extracts terminology and definitions from a glossary markdown string.

        Args:
            glossary_markdown: Markdown content of the Glossary chapter/appendix.

        Returns:
            Dictionary mapping term title to definition string.
        """
        terms: Dict[str, str] = {}
        lines = glossary_markdown.splitlines()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Pattern 1: **Term**: Definition or - **Term**: Definition
            m1 = re.match(r'^(?:[-*•]\s*)?\*\*([^\*:]+)\*\*[:\s]+(.+)$', stripped)
            if m1:
                term = m1.group(1).strip()
                definition = m1.group(2).strip()
                terms[term] = definition
                continue

            # Pattern 2: ### Term\nDefinition
            m2 = re.match(r'^#{2,4}\s+([A-Za-z0-9\s\-\'\(\)]+)$', stripped)
            if m2:
                term = m2.group(1).strip()
                if not term.lower().startswith(('glossary', 'key terms', 'appendix')):
                    terms[term] = ""

        return terms

    @classmethod
    def inject_domain_vocabulary(cls, lexical_auditor: LexicalAuditor, terms: Dict[str, str]) -> None:
        """Injects domain terminology words into LexicalAuditor known words set.

        Args:
            lexical_auditor: Instance of LexicalAuditor to expand.
            terms: Dictionary of glossary terms.
        """
        if not terms or not hasattr(lexical_auditor, "dict_words"):
            return

        target_set = getattr(lexical_auditor, "dict_words", None)
        if target_set is None:
            return

        for term in terms.keys():
            # Add entire term lowercased
            clean_term = re.sub(r'[^a-zA-Z0-9\s\-]', '', term).strip().lower()
            if clean_term:
                target_set.add(clean_term)
            # Add individual words
            for w in clean_term.split():
                if len(w) > 2:
                    target_set.add(w)

        logger.debug("Injected %d glossary terms into LexicalAuditor domain vocabulary.", len(terms))

    @classmethod
    def link_terms_in_markdown(
        cls,
        markdown_text: str,
        terms: Dict[str, str],
        glossary_href: str = "00-09-Glossary.xhtml",
    ) -> Tuple[str, int]:
        """Wraps the first occurrence of each glossary term with a semantic hyperlink.

        Args:
            markdown_text: Chapter markdown text to annotate.
            terms: Dictionary of glossary terms.
            glossary_href: Target EPUB XHTML href of the glossary file.

        Returns:
            Tuple of (annotated_markdown, linked_count).
        """
        if not terms:
            return (markdown_text, 0)

        linked_count = 0
        current_md = markdown_text

        # Sort terms by descending length to match multi-word phrases first
        sorted_terms = sorted(terms.keys(), key=lambda t: len(t), reverse=True)

        for term in sorted_terms:
            if len(term) < 3:
                continue

            slug = re.sub(r'[^a-zA-Z0-9]', '', term).lower()
            escaped_term = re.escape(term)
            pattern = re.compile(rf'(?<![\[\#\w])({escaped_term})(?![\]\w])', re.IGNORECASE)

            match = pattern.search(current_md)
            if match:
                matched_text = match.group(1)
                replacement = f'<a href="{glossary_href}#{slug}" class="glossary-term">{matched_text}</a>'
                # Replace only first occurrence
                current_md = current_md[:match.start()] + replacement + current_md[match.end():]
                linked_count += 1

        return (current_md, linked_count)
