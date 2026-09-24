"""
Universal Academic Reference Parser
====================================
Parses, cleans, and standardizes hanging-indent academic citations in Markdown.
Handles APA, Harvard, Chicago, Vancouver, and numbered reference styles.
Prevents adjacent citations from merging into giant run-on paragraphs, and
safeguards trailing emergent sections (Received/Accepted dates, Author Notes).
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ReferenceParser:
    """Parses and formats academic journal reference lists."""

    # Matches author-year citation start, e.g.:
    # "Lejuez, C. W., Aklin, W. M., ... (2003a)."
    # "Centers for Disease Control (CDC). (2001)."
    # "Hopko, D., Lejuez, C., et al. (2006)."
    CITATION_REGEX = re.compile(
        r'(?:^|(?<=[\.\?!]\s)|(?<=\.\*\s)|(?<=\.\*\*\s))('
        r'[A-Z][a-zA-Z\-\'\s]+?,\s+[A-Z]\.(?:[^\(\)]*?)\((?:18|19|20)\d{2}[a-z]?\)'
        r'|[A-Z][a-zA-Z\-\'\s]+?\([A-Z0-9\-\s]+\)\.\s*\((?:18|19|20)\d{2}[a-z]?\)'
        r'|\[\d{1,4}\]\s+[A-Z]'
        r'|^\d{1,4}\.\s+[A-Z]'
        r')'
    )

    # Trailing sections that frequently follow references
    TRAILING_PATTERNS = [
        re.compile(r'^(Received\s+\w+\s+\d{1,2},\s+\d{4}.*)$', re.M | re.I),
        re.compile(r'^(Received\s+\d{1,2}\s+\w+\s+\d{4}.*)$', re.M | re.I),
        re.compile(r'^(Revision received\s+.*)$', re.M | re.I),
        re.compile(r'^(Accepted\s+.*)$', re.M | re.I),
        re.compile(r'^(Author Note\b.*)$', re.M | re.I),
        re.compile(r'^(Appendix\b.*)$', re.M | re.I),
    ]

    @classmethod
    def split_references_section(cls, full_md: str) -> Tuple[str, str, str, str]:
        """
        Splits full document into:
          (pre_refs_md, refs_header, refs_body, post_refs_md)
        """
        ref_header_pattern = re.compile(
            r'^(#{1,3}\s*(?:References|REFERENCES|Bibliography|Literature Cited))\s*$',
            re.M
        )
        match = ref_header_pattern.search(full_md)
        if not match:
            match = re.search(r'^\s*(References|REFERENCES)\s*$', full_md, re.M)
            if not match:
                return full_md, "", "", ""

        start_pos = match.start()
        header_text = match.group(0).strip()
        if not header_text.startswith("#"):
            header_text = f"## {header_text}"

        after_header = full_md[match.end():]

        # Check for post-references sections
        next_heading = re.search(r'\n(#{1,2}\s+[^\n]+)', after_header)
        if next_heading:
            body = after_header[:next_heading.start()]
            post = after_header[next_heading.start():]
        else:
            trailing_match = None
            for pat in cls.TRAILING_PATTERNS:
                m = pat.search(after_header)
                if m:
                    if trailing_match is None or m.start() < trailing_match.start():
                        trailing_match = m

            if trailing_match:
                body = after_header[:trailing_match.start()]
                post = after_header[trailing_match.start():]
            else:
                body = after_header
                post = ""

        pre = full_md[:start_pos]
        return pre, header_text, body, post

    @classmethod
    def parse_citation_entries(cls, refs_body: str) -> List[str]:
        """
        Separates merged reference text into individual citation entries.
        Detects hanging indents and citation starting signatures.
        """
        cleaned_body = refs_body.strip()
        if not cleaned_body:
            return []

        # Find all boundary matches
        matches = list(cls.CITATION_REGEX.finditer(cleaned_body))

        if not matches:
            # Fallback: line by line
            lines = [l.strip() for l in cleaned_body.split('\n') if l.strip() and not l.strip().startswith("<!--")]
            return lines

        entries = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_body)
            entry = cleaned_body[start:end].strip()
            if entry:
                # Fix line-break hyphenation within citation
                entry = re.sub(r'(\w+)-\s*\*\s*\*(\w+)', r'\1\2', entry)
                entry = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', entry)
                # Normalize internal newlines to single space
                entry = re.sub(r'\s*\n\s*', ' ', entry)
                # Remove orphan page markers inside citation text
                entry = re.sub(r'<!-- Page \d+ -->\s*', '', entry)
                entries.append(entry.strip())

        return entries

    @classmethod
    def format_references(cls, entries: List[str]) -> str:
        """Formats citation entries into clean markdown with a bulleted list."""
        if not entries:
            return ""
        return "\n".join(f"- {entry}" for entry in entries)

    @classmethod
    def clean_document_references(cls, full_md: str) -> str:
        """
        Universal entry point: parses and reconstructs the references section of a document.
        """
        pre, header, body, post = cls.split_references_section(full_md)
        if not header:
            return full_md

        entries = cls.parse_citation_entries(body)
        if not entries:
            return full_md

        formatted_refs = cls.format_references(entries)
        result = f"{pre.rstrip()}\n\n{header}\n\n{formatted_refs}"
        if post:
            result = f"{result}\n\n{post.lstrip()}"
        return result
