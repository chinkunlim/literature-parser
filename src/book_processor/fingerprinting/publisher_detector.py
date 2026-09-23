"""
Publisher & Venue Detector
==========================
Automatically identifies academic publishers and book publishers from PDF
metadata, DOI strings, copyright declarations, and running header text.
"""

import re
from typing import Optional, Dict, Any


# Common academic DOI prefixes and their corresponding publishers
DOI_PREFIX_MAP = {
    "10.1037": "apa",               # American Psychological Association
    "10.1016": "elsevier",          # Elsevier / ScienceDirect / Academic Press
    "10.1111": "wiley",             # Wiley-Blackwell
    "10.1002": "wiley",             # Wiley Online Library
    "10.1007": "springer",          # Springer Nature / Psychonomic Society
    "10.1038": "springer",          # Nature Publishing Group
    "10.1177": "sage",              # SAGE Publications / APS
    "10.1093": "oup",               # Oxford University Press
    "10.1017": "cup",               # Cambridge University Press
    "10.3389": "frontiers",         # Frontiers Media
    "10.1371": "plos",              # Public Library of Science
    "10.1080": "taylor_francis",     # Taylor & Francis / Routledge
}

# Text signatures found on title or copyright pages
PUBLISHER_TEXT_SIGNATURES = [
    (r"(?:American Psychological Association|apa\.org|Journal of Experimental Psychology|Psychological Review)", "apa"),
    (r"(?:Elsevier\s*(?:B\.V\.|Science|Inc\.)|ScienceDirect|Academic Press)", "elsevier"),
    (r"(?:John Wiley & Sons|Wiley-Blackwell|wileyonlinelibrary\.com)", "wiley"),
    (r"(?:Springer\s*(?:Nature|Science|Verlag)|Psychonomic Society|nature\.com)", "springer"),
    (r"(?:SAGE Publications|Association for Psychological Science|Psychological Science)", "sage"),
    (r"(?:Taylor & Francis|Routledge)", "taylor_francis"),
    (r"(?:Oxford University Press)", "oup"),
    (r"(?:Cambridge University Press)", "cup"),
    (r"(?:Pearson Education|Allyn & Bacon|Prentice Hall)", "pearson"),
    (r"(?:Cengage Learning|Wadsworth|Brooks/Cole)", "cengage"),
    (r"(?:McGraw-Hill)", "mcgraw_hill"),
    (r"(?:Frontiers in Psychology|Frontiers Media)", "frontiers"),
    (r"(?:PLOS ONE|Public Library of Science)", "plos"),
]


class PublisherDetector:
    """Detects the publishing entity and matching profile name from text and metadata."""

    @classmethod
    def detect_from_text(cls, text: str) -> Optional[str]:
        """
        Inspects text (typically from page 1 or front matter) to detect the publisher.
        Returns normalized publisher key (e.g. 'apa', 'elsevier', 'wiley', 'pearson').
        """
        if not text:
            return None

        # 1. Search for DOI prefixes
        doi_match = re.search(r'\b10\.(\d{4,5})/[^\s"<>]+', text)
        if doi_match:
            prefix = f"10.{doi_match.group(1)}"
            if prefix in DOI_PREFIX_MAP:
                return DOI_PREFIX_MAP[prefix]

        # 2. Search for text patterns
        for pattern, pub_key in PUBLISHER_TEXT_SIGNATURES:
            if re.search(pattern, text, re.IGNORECASE):
                return pub_key

        return None

    @classmethod
    def get_profile_name(cls, publisher_key: str, is_journal: bool = False) -> str:
        """
        Returns the appropriate profile filename based on publisher key and document type.
        """
        if not publisher_key:
            return "global_profile.json"

        # Journal profiles
        if is_journal or publisher_key in ("apa", "elsevier", "wiley", "springer", "sage", "taylor_francis", "frontiers", "plos"):
            journal_profile = f"journal_{publisher_key}.json"
            return journal_profile

        # Textbook profiles
        if publisher_key in ("pearson", "cengage"):
            return f"publisher_{publisher_key}.json"

        return "global_profile.json"
