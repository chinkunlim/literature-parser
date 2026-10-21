"""
Publisher & Venue Detector
==========================
Automatically identifies academic publishers and book publishers from PDF
metadata, DOI strings, copyright declarations, and running header text.
"""

import re

# Common academic DOI prefixes and their corresponding publishers
DOI_PREFIX_MAP: dict[str, str] = {
    "10.1037": "apa",  # American Psychological Association
    "10.1016": "elsevier",  # Elsevier / ScienceDirect / Academic Press
    "10.1111": "wiley",  # Wiley-Blackwell
    "10.1002": "wiley",  # Wiley Online Library
    "10.1007": "springer",  # Springer Nature / Psychonomic Society
    "10.1038": "springer",  # Nature Publishing Group
    "10.1177": "sage",  # SAGE Publications / APS
    "10.1093": "oup",  # Oxford University Press
    "10.1017": "cup",  # Cambridge University Press
    "10.3389": "frontiers",  # Frontiers Media
    "10.1371": "plos",  # Public Library of Science
    "10.1080": "taylor_francis",  # Taylor & Francis / Routledge
    "10.1063": "aip",  # AIP Publishing (American Institute of Physics)
    "10.1146": "annual_reviews",  # Annual Reviews
}

# Text signatures found on title or copyright pages
PUBLISHER_TEXT_SIGNATURES: list[tuple[str, str]] = [
    (
        r"(?:American Psychological Association|apa\.org|Journal of Experimental Psychology|"
        r"Psychological Review|Experimental and Clinical Psychopharmacology|Psychotherapy)",
        "apa",
    ),
    (
        r"(?:Elsevier\s*(?:B\.V\.|Science|Inc\.)|ScienceDirect|Academic Press|"
        r"Journal of Adolescence|Cognition)",
        "elsevier",
    ),
    (r"(?:John Wiley & Sons|Wiley-Blackwell|wileyonlinelibrary\.com)", "wiley"),
    (r"(?:Springer\s*(?:Nature|Science|Verlag)|Psychonomic Society|nature\.com)", "springer"),
    (r"(?:SAGE Publications|Association for Psychological Science|Psychological Science)", "sage"),
    (r"(?:Taylor & Francis|Routledge)", "taylor_francis"),
    (r"(?:Oxford University Press)", "oup"),
    (
        r"(?:Cambridge University Press|cambridge\.org/bil|Bilingualism: Language and Cognition)",
        "cup",
    ),
    (r"(?:AIP Advances|American Institute of Physics|pubs\.aip\.org/aip)", "aip"),
    (r"(?:Annual Reviews|annualreviews\.org|Annu\. Rev\.)", "annual_reviews"),
    (r"(?:Pearson Education|Allyn & Bacon|Prentice Hall)", "pearson"),
    (r"(?:Cengage Learning|Wadsworth|Brooks/Cole)", "cengage"),
    (r"(?:McGraw-Hill)", "mcgraw_hill"),
    (r"(?:Frontiers in Psychology|Frontiers Media)", "frontiers"),
    (r"(?:PLOS ONE|Public Library of Science)", "plos"),
]


class PublisherDetector:
    """Detects the publishing entity and matching profile name from text and metadata."""

    @classmethod
    def detect_from_text(cls, text: str | None) -> str | None:
        """Inspects text (typically from page 1 or front matter) to detect the publisher.

        Args:
            text: Raw text extracted from the document front matter or first page.

        Returns:
            Normalized publisher key (e.g. 'apa', 'elsevier', 'wiley', 'pearson'), or None.
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
    def get_profile_name(
        cls,
        publisher_key: str | None,
        is_literature: bool = False,
        is_journal: bool = False,
    ) -> str:
        """Returns the appropriate profile filename based on publisher key and document type.

        Args:
            publisher_key: Normalized publisher identifier key.
            is_literature: Whether the document is academic literature.
            is_journal: Whether the document is a journal article.

        Returns:
            Profile JSON filename matching the publisher and document archetype.
        """
        if not publisher_key:
            return "global_profile.json"

        # Literature profiles
        if (
            is_literature
            or is_journal
            or publisher_key
            in (
                "apa",
                "elsevier",
                "wiley",
                "springer",
                "sage",
                "taylor_francis",
                "frontiers",
                "plos",
                "aip",
                "cup",
                "annual_reviews",
            )
        ):
            literature_profile = f"literature_{publisher_key}.json"
            return literature_profile

        # Textbook profiles
        if publisher_key in ("pearson", "cengage"):
            return f"publisher_{publisher_key}.json"

        return "global_profile.json"
