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

        # ----------------------------------------------------------------
        # Post-pass 1: Table Note Bonding
        # Bind table notes (Note., *p < , BART indicates …) immediately
        # following a </table> block so they don't drift to the next page.
        # ----------------------------------------------------------------
        result = cls._bond_table_notes(result, config)

        # ----------------------------------------------------------------
        # Post-pass 2: OCR Statistical Symbol Healing
        # Fix common OCR errors in statistical output (APA style).
        # ----------------------------------------------------------------
        result = cls._fix_ocr_stats(result, config)

        return result

    @classmethod
    def _bond_table_notes(cls, md: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Ensures table notes immediately following a Markdown table stay attached.
        Patterns like 'Note.', 'BART indicates', '*p <', statistical footnote markers
        that appear on a blank line after a table are re-attached.
        """
        publisher_cfg = (config or {}).get("publisher_config", {})
        note_pats_raw = publisher_cfg.get("table_note_patterns", [])
        # Always-active generic patterns
        _TABLE_NOTE_PATS = [re.compile(p, re.I) for p in note_pats_raw] + [
            re.compile(r'^Note\.\s+', re.I),
            re.compile(r'^\*Note\.\s+', re.I),
            re.compile(r'^BART indicates\b', re.I),
            re.compile(r'^Adapted from\b', re.I),
            re.compile(r'^\*{1,3}p\s*[<>]', re.I),
            re.compile(r'^[a-z]\s+[A-Z]'),   # superscript footnote like "a The ..."
            re.compile(r'^(?:CI|SD|SE|df|n|N|M)\s*='),
        ]

        def is_table_note(line):
            s = line.strip()
            return any(p.match(s) for p in _TABLE_NOTE_PATS)

        lines = md.split('\n')
        result = []
        i = 0
        while i < len(lines):
            result.append(lines[i])
            # After a line that ends a table (last | row), collect following notes
            stripped = lines[i].strip()
            if stripped.startswith('|') and (i + 1 >= len(lines) or not lines[i + 1].strip().startswith('|')):
                # Peek ahead: skip blank lines, collect table notes
                j = i + 1
                note_lines = []
                while j < len(lines) and (lines[j].strip() == '' or is_table_note(lines[j])):
                    if lines[j].strip():
                        note_lines.append(lines[j].strip())
                    j += 1
                if note_lines:
                    result.append('')
                    result.extend(f'*{nl}*' if not nl.startswith('*') else nl for nl in note_lines)
                    i = j
                    continue
            i += 1
        return '\n'.join(result)

    @classmethod
    def _fix_ocr_stats(cls, md: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Heals common OCR artefacts in statistical text from APA and Elsevier papers.
        Handles garbled p-values, r-values, copyright symbols.
        """
        publisher_cfg = (config or {}).get("publisher_config", {})
        custom_pats = publisher_cfg.get("ocr_stat_fix_patterns", [])

        # Generic fixes (always applied)
        fixes = [
            # p o 0 01 or p o 0.01 → p < 0.01
            (re.compile(r'\bp\s+o\s+0\s+(\d{2})\b'), r'$p < 0.\1$'),
            (re.compile(r'\bp\s+o\s+(0\.\d+)\b'), r'$p < \1$'),
            # r = 0$ 82 → r = 0.82
            (re.compile(r'\br\s*=\s*0\$\s*(\d+)\b'), r'$r = 0.\1$'),
            # r 2 = 0$ 42 → r² = 0.42
            (re.compile(r'\br\s+2\s*=\s*0\$\s*(\d+)\b'), r'$r^2 = 0.\1$'),
            # "r 2003" or "r 2002" at line start (copyright) → © 2003
            (re.compile(r'(?<!\w)r\s+((?:19|20)\d{2})\b'), r'© \1'),
            # Garbled © from PDF: "C 2003" after line break
            (re.compile(r'(?:^|\n)\s*C\s+((?:19|20)\d{2})\s+(Elsevier|APA|American Psychological|Wiley)', re.M),
             r'\n© \1 \2'),
        ]

        result = md
        for pat, repl in fixes:
            result = pat.sub(repl, result)

        # Apply publisher-specific custom patterns (format: [pattern_str, replacement_str])
        for entry in custom_pats:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                try:
                    result = re.sub(entry[0], entry[1], result)
                except Exception:
                    pass

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
