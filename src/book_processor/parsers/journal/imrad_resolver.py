"""
Universal IMRAD Structure & Emergent Section Resolver
=====================================================
Identifies and standardizes academic journal IMRAD structure:
  - Abstract & Keywords
  - Introduction
  - Method (Participants, Measures, Procedure, Data Analysis)
  - Results
  - Discussion & Conclusions
  - References
  - Emergent Sections from Shared Knowledge (Author Note, Dates, Funding)

Automatically registers any newly discovered emergent sections into
the shared knowledge repository for cross-document reuse.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from book_processor.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class IMRADResolver:
    """Standardizes academic paper structure and emergent sections."""

    # Standard primary sections -> Level 2 headings (##)
    PRIMARY_SECTIONS = [
        ("Abstract", [r'^(?:#+\s*)?Abstract\b', r'^\*\*Abstract\*\*:?']),
        ("Introduction", [r'^(?:#+\s*)?Introduction\b', r'^\*\*Introduction\*\*']),
        ("Method", [r'^(?:#+\s*)?Methods?\b', r'^\*\*Methods?\*\*']),
        ("Results", [r'^(?:#+\s*)?Results?\b', r'^\*\*Results?\*\*']),
        ("Discussion", [r'^(?:#+\s*)?(?:General\s+)?Discussion\b', r'^\*\*(?:General\s+)?Discussion\*\*']),
        ("Conclusions", [r'^(?:#+\s*)?Conclusions?\b', r'^\*\*Conclusions?\*\*']),
        ("References", [r'^(?:#+\s*)?(?:References|REFERENCES|Bibliography)\b', r'^\*\*(?:References|REFERENCES)\*\*']),
    ]

    # Standard secondary subsections -> Level 3 headings (###)
    SECONDARY_SUBSECTIONS = [
        ("Participants", [r'^(?:#+\s*)?Participants?\b', r'^\*\*Participants?\*\*']),
        ("Subjects", [r'^(?:#+\s*)?Subjects?\b', r'^\*\*Subjects?\*\*']),
        ("Measures", [r'^(?:#+\s*)?Measures?\b', r'^\*\*Measures?\*\*']),
        ("Procedure", [r'^(?:#+\s*)?Procedures?\b', r'^\*\*Procedures?\*\*']),
        ("Materials", [r'^(?:#+\s*)?Materials?\b', r'^\*\*Materials?\*\*']),
        ("Apparatus", [r'^(?:#+\s*)?Apparatus\b', r'^\*\*Apparatus\*\*']),
        ("Data Analysis", [r'^(?:#+\s*)?Data\s+Analysis\b', r'^(?:#+\s*)?Statistical\s+Analys(?:is|es)\b']),
        ("Design", [r'^(?:#+\s*)?Experimental\s+Design\b']),
    ]

    @classmethod
    def resolve_structure(cls, full_md: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Resolves IMRAD headings and shared emergent sections throughout document markdown.
        """
        if config is None:
            config = ConfigManager.load_hierarchical_config(archetype="journal")

        shared_sections = config.get("shared_sections", [])
        lines = full_md.split('\n')
        new_lines = []

        i = 0
        in_code_block = False
        in_references = False
        last_emergent = ""

        while i < len(lines):
            line = lines[i]
            trimmed = line.strip()

            if trimmed.startswith("```"):
                in_code_block = not in_code_block
                new_lines.append(line)
                i += 1
                continue

            if in_code_block:
                new_lines.append(line)
                i += 1
                continue

            # Check if entering References
            if re.match(r'^(?:#{1,3}\s*)?(?:References|REFERENCES)\b', trimmed, re.I):
                in_references = True
                last_emergent = ""
                new_lines.append(f"## References")
                i += 1
                continue

            # Don't promote normal text inside References into IMRAD headings
            if in_references:
                # Check if an emergent section like Dates or Author Note appears after references
                matched_emergent = cls._match_emergent_section(trimmed, shared_sections)
                if matched_emergent:
                    in_references = False
                    sec_name = matched_emergent["name"]
                    if last_emergent != sec_name:
                        h_level = "#" * matched_emergent.get("target_heading_level", 2)
                        new_lines.append(f"{h_level} {sec_name}")
                        new_lines.append("")
                        last_emergent = sec_name
                    new_lines.append(trimmed)
                    i += 1
                    continue
                else:
                    new_lines.append(line)
                    i += 1
                    continue

            # 1. Check Primary IMRAD Sections (Level 2)
            promoted_primary = False
            for sec_name, patterns in cls.PRIMARY_SECTIONS:
                for pat in patterns:
                    if re.match(pat, trimmed, re.I) and len(trimmed) < 40:
                        if not re.search(r'[\.\;\:\,]', trimmed) or trimmed.endswith(':'):
                            new_lines.append(f"## {sec_name}")
                            promoted_primary = True
                            last_emergent = ""
                            break
                if promoted_primary:
                    break

            if promoted_primary:
                i += 1
                continue

            # 2. Check Secondary IMRAD Subsections (Level 3)
            promoted_secondary = False
            for sub_name, patterns in cls.SECONDARY_SUBSECTIONS:
                for pat in patterns:
                    if re.match(pat, trimmed, re.I) and len(trimmed) < 45:
                        if not re.search(r'[\.\;\:\,]', trimmed) or trimmed.endswith(':'):
                            new_lines.append(f"### {sub_name}")
                            promoted_secondary = True
                            last_emergent = ""
                            break
                if promoted_secondary:
                    break

            if promoted_secondary:
                i += 1
                continue

            # 3. Check Shared Emergent Sections (Author Note, Received Dates, Funding)
            matched_emergent = cls._match_emergent_section(trimmed, shared_sections)
            if matched_emergent:
                sec_name = matched_emergent["name"]
                if trimmed.lstrip('#').strip().lower() == sec_name.lower():
                    new_lines.append(trimmed)
                    last_emergent = sec_name
                    i += 1
                    continue
                if last_emergent != sec_name:
                    h_level = "#" * matched_emergent.get("target_heading_level", 2)
                    new_lines.append(f"{h_level} {sec_name}")
                    new_lines.append("")
                    last_emergent = sec_name
                new_lines.append(trimmed)
                i += 1
                continue

            # 4. Remove unwanted blockquotes in abstract or body
            if line.startswith("> ") and not config.get("features", {}).get("allow_blockquotes", False):
                line = line[2:]

            new_lines.append(line)
            i += 1

        result = '\n'.join(new_lines)
        return result

    @classmethod
    def _match_emergent_section(cls, text: str, shared_sections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Matches a line of text against shared emergent sections."""
        clean_text = text.lstrip('#').strip()
        for sec in shared_sections:
            if clean_text.lower() == sec.get("name", "").lower():
                return sec
            for alias in sec.get("aliases", []):
                if clean_text.lower() == alias.lower():
                    return sec
            for pat in sec.get("patterns", []):
                try:
                    if re.search(pat, text) or re.search(pat, clean_text):
                        return sec
                except Exception:
                    pass
        return None
