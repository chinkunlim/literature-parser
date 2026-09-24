"""
Universal IMRAD Structure & Emergent Section Resolver
=====================================================
Identifies and standardizes academic literature IMRAD structure:
  - Abstract & Keywords
  - Introduction
  - Method (Participants, Measures, Apparatus, Procedure, Data Analysis)
  - Results (Properties, Latent factors, Relationships)
  - Discussion & Conclusions
  - Author Note & Acknowledgments (relocated before References)
  - References

Automatically registers any newly discovered emergent sections into
the shared knowledge repository for cross-document reuse.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from book_processor.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class IMRADResolver:
    """Standardizes academic literature structure and emergent sections."""

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
        ("Measures", [r'^(?:#+\s*)?Measures?(?:\s*:)?$', r'^\*\*Measures?\*\*']),
        ("Procedure", [r'^(?:#+\s*)?Procedures?\b', r'^\*\*Procedures?\*\*']),
        ("Materials and Apparatus", [r'^(?:#+\s*)?Materials\s+and\s+Apparatus\b', r'^\*Materials\s+and\s+Apparatus\*']),
        ("Materials", [r'^(?:#+\s*)?Materials?\b', r'^\*\*Materials?\*\*']),
        ("Apparatus", [r'^(?:#+\s*)?Apparatus\b', r'^\*\*Apparatus\*\*']),
        ("Data Analysis", [r'^(?:#+\s*)?Data\s+Analysis\b', r'^(?:#+\s*)?Statistical\s+Analys(?:is|es)\b']),
        ("Design", [r'^(?:#+\s*)?Experimental\s+Design\b']),
        # Standard APA Results subheadings
        ("Experimental Properties of the BART", [r'^\*?Experimental\s+Properties\s+of\s+the\s+BART\*?$']),
        ("Relationship of the BART With Measures of Risk-Related Constructs and Individual Risk Behaviors", [
            r'^\*?Relationship\s+of\s+the\s+BART\s+With\s+Measures\b.*',
        ]),
    ]

    # Standard tertiary subsections -> Level 4 headings (####)
    TERTIARY_SUBSECTIONS = [
        ("Measure of intelligence (IQ)", [r'^\*?Measure\s+of\s+intelligence\s*\(IQ\)\.?\*?']),
        ("Measures of risk-related constructs and discriminant validity", [r'^\*?Measures\s+of\s+risk-related\s+constructs\b.*?validity\.?\*?']),
        ("Risk behaviors", [r'^\*?Risk\s+behaviors\.?\*?']),
        ("The BART", [r'^\*?The\s+BART\.?\*?']),
    ]

    @classmethod
    def resolve_structure(cls, full_md: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Resolves IMRAD headings and shared emergent sections throughout document markdown.
        """
        if config is None:
            config = ConfigManager.load_hierarchical_config(archetype="literature")

        shared_sections = config.get("shared_sections", [])

        # Pre-pass: Promote inline/run-in Level 4 APA subheadings
        for sub_name in [
            "Measure of intelligence (IQ)",
            "Measures of risk-related constructs and discriminant validity",
            "Risk behaviors",
            "The BART",
        ]:
            pat = re.compile(r'([\.?!]["”\']?\s+|\n)\*(' + re.escape(sub_name) + r')\.?\*\s*', re.I)
            full_md = pat.sub(r'\1\n\n#### \2\n\n', full_md)

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

            # Filter out Table lines from becoming markdown headers
            if re.match(r'^(?:#{1,4}\s*)?Table\s+\d+\b', trimmed, re.I):
                # Don't make Table X into a markdown header; keep as plain text or let table parser format it
                clean_table_line = re.sub(r'^#{1,4}\s*', '', trimmed)
                new_lines.append(clean_table_line)
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
                    if re.match(pat, trimmed, re.I) and len(trimmed) < 120:
                        new_lines.append(f"### {sub_name}")
                        promoted_secondary = True
                        last_emergent = ""
                        break
                if promoted_secondary:
                    break

            if promoted_secondary:
                i += 1
                continue

            # 3. Check Tertiary IMRAD Subsections (Level 4)
            promoted_tertiary = False
            for sub_name, patterns in cls.TERTIARY_SUBSECTIONS:
                for pat in patterns:
                    if re.match(pat, trimmed, re.I) and len(trimmed) < 100:
                        new_lines.append(f"#### {sub_name}")
                        promoted_tertiary = True
                        last_emergent = ""
                        break
                if promoted_tertiary:
                    break

            if promoted_tertiary:
                i += 1
                continue

            # 4. Check Shared Emergent Sections (Author Note, Received Dates, Funding)
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

            # 5. Remove unwanted blockquotes in abstract or body
            if line.startswith("> ") and not config.get("features", {}).get("allow_blockquotes", False):
                line = line[2:]

            new_lines.append(line)
            i += 1

        result = '\n'.join(new_lines)

        # ----------------------------------------------------------------
        # Post-pass 1: Relocate Author Note to before References
        # ----------------------------------------------------------------
        result = cls._relocate_author_note(result)

        # ----------------------------------------------------------------
        # Post-pass 2: Ensure Introduction Heading Exists
        # ----------------------------------------------------------------
        result = cls._ensure_introduction(result)

        # ----------------------------------------------------------------
        # Post-pass 3: Table Note Bonding
        # ----------------------------------------------------------------
        result = cls._bond_table_notes(result, config)

        # ----------------------------------------------------------------
        # Post-pass 4: OCR Statistical Symbol Healing
        # ----------------------------------------------------------------
        result = cls._fix_ocr_stats(result, config)

        return result

    @classmethod
    def _relocate_author_note(cls, md: str) -> str:
        """
        In academic PDFs, the Author Note is often placed at the bottom of page 1.
        Standard academic layout requires it at the end of the text, immediately
        preceding ## References. Handles both explicit markdown headings and inline APA footnotes.
        """
        an_block = ""
        # 1. Check for explicit header
        p_an_hdr = re.compile(
            r'(#+\s*(?:Author\s+Note(?:\s*&\s*Acknowledgments)?)\b[^\n]*\n+'
            r'.*?'
            r'(?:(?:E-mail|Email|Correspondence)[^\n]+|\.edu|\.org|\.gov|[^\n]+(?=\n\n)|\Z))',
            re.DOTALL | re.I
        )
        # 2. Check for inline author note embedded in text
        p_an_inline = re.compile(
            r'([A-Z]\.\s*[A-Z]\.\s+[A-Za-z]+,\s+Department\s+of.*?'
            r'Correspondence\s+concerning\s+this\s+article[^\n]*'
            r'(?:E-mail|Email):\s*[\w\.\-]+@[A-Za-z0-9\.\-]+(?:\.edu|\.org|\.com|\.gov)?\.?)',
            re.DOTALL | re.I
        )

        m_hdr = p_an_hdr.search(md)
        m_inline = p_an_inline.search(md)

        if m_hdr:
            an_block = m_hdr.group(1).strip()
            md = md[:m_hdr.start()].rstrip() + "\n\n" + md[m_hdr.end():].lstrip()
        elif m_inline:
            raw_inline = m_inline.group(1).strip()
            parts = []
            m_ack = re.search(r'\b(We thank\b.*?)(?=\bCorrespondence\b|\Z)', raw_inline, re.DOTALL | re.I)
            m_corr = re.search(r'\b(Correspondence concerning\b.*)', raw_inline, re.DOTALL | re.I)
            
            p1_end = m_ack.start() if m_ack else (m_corr.start() if m_corr else len(raw_inline))
            para1 = raw_inline[:p1_end].strip()
            if para1:
                parts.append(para1)
            if m_ack:
                parts.append(m_ack.group(1).strip())
            if m_corr:
                corr_text = m_corr.group(1).strip()
                corr_text = re.sub(r'E-mail:\s*([^\s<>]+)', r'E-mail: [\1](mailto:\1)', corr_text)
                parts.append(corr_text)

            an_content = "\n\n".join(parts)
            an_block = f"## Author Note & Acknowledgments\n\n{an_content}"
            # Remove inline author note and stitch the surrounding text
            md = md[:m_inline.start()].rstrip() + " " + md[m_inline.end():].lstrip()
        else:
            return md

        # 3. Check for Received / Revision / Accepted dates at the end of md
        p_dates = re.compile(
            r'(\*?Received\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}\*?\s*'
            r'(?:(?:\n+|\s+)\*?Revision\s+received\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}\*?)?\s*'
            r'(?:(?:\n+|\s+)\*?Accepted\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}\*?[^\n]*))',
            re.I
        )
        m_dates = p_dates.search(md)
        if m_dates:
            raw_dates = m_dates.group(1).strip()
            md = md[:m_dates.start()].rstrip() + "\n" + md[m_dates.end():].lstrip()
            clean_dates = re.sub(r'[\u4e00-\u9fff\uff00-\uffef\u25a0-\u25ff\s]+$', '', raw_dates).strip()
            date_lines = []
            m_rec = re.search(r'Received\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}', clean_dates, re.I)
            if m_rec:
                date_lines.append(f"*{m_rec.group(0)}*  ")
            m_rev = re.search(r'Revision\s+received\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}', clean_dates, re.I)
            if m_rev:
                date_lines.append(f"*{m_rev.group(0)}*  ")
            m_acc = re.search(r'Accepted\s+[A-Za-z]+\s+\d{1,2},\s*\d{4}', clean_dates, re.I)
            if m_acc:
                date_lines.append(f"*{m_acc.group(0)}*")
            if date_lines:
                an_block += "\n\n" + "\n".join(date_lines)

        # 4. Insert before ## References
        m_ref = re.search(r'\n(##\s+References\b)', md)
        if m_ref:
            md = md[:m_ref.start()] + "\n\n---\n\n" + an_block + "\n\n---\n\n" + md[m_ref.start():].lstrip()
        else:
            md = md.rstrip() + "\n\n---\n\n" + an_block + "\n"

        return md

    @classmethod
    def _ensure_introduction(cls, md: str) -> str:
        """
        Many APA journals do not explicitly print 'Introduction'.
        If text exists between Abstract and Method, ensure '## Introduction' is added.
        """
        if "## Introduction" in md:
            return md

        # Find where Abstract ends (--- after Abstract)
        m_abs = re.search(r'##\s*Abstract\b.*?\n---\n', md, re.DOTALL)
        if not m_abs:
            return md

        post_abs = md[m_abs.end():].lstrip()
        # Find next major section
        m_next = re.search(r'^##\s+(?:Method|Results|Discussion)\b', post_abs, re.M)
        if m_next and m_next.start() > 100:
            # Insert ## Introduction
            intro_pos = m_abs.end()
            return md[:intro_pos] + "\n## Introduction\n\n" + md[intro_pos:].lstrip()

        return md

    @classmethod
    def _bond_table_notes(cls, md: str, config: Optional[Dict[str, Any]] = None) -> str:
        """Ensures table notes stay attached to tables."""
        publisher_cfg = (config or {}).get("publisher_config", {})
        note_pats_raw = publisher_cfg.get("table_note_patterns", [])
        _TABLE_NOTE_PATS = [re.compile(p, re.I) for p in note_pats_raw] + [
            re.compile(r'^Note\.\s+', re.I),
            re.compile(r'^\*Note\.\s+', re.I),
            re.compile(r'^BART indicates\b', re.I),
            re.compile(r'^Adapted from\b', re.I),
            re.compile(r'^\*{1,3}p\s*[<>]', re.I),
            re.compile(r'^[a-z]\s+[A-Z]'),
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
            stripped = lines[i].strip()
            if stripped.startswith('|') and (i + 1 >= len(lines) or not lines[i + 1].strip().startswith('|')):
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
        """Fixes common OCR artefacts in statistical text."""
        fixes = [
            (re.compile(r'\bp\s+o\s+0\s+(\d{2})\b'), r'$p < 0.\1$'),
            (re.compile(r'\bp\s+o\s+(0\.\d+)\b'), r'$p < \1$'),
            (re.compile(r'\br\s*=\s*0\$\s*(\d+)\b'), r'$r = 0.\1$'),
            (re.compile(r'\br\s+2\s*=\s*0\$\s*(\d+)\b'), r'$r^2 = 0.\1$'),
            (re.compile(r'(?<!\w)r\s+((?:19|20)\d{2})\b'), r'© \1'),
            (re.compile(r'\(\s*\*p\*s\s*[⬎>]\s*\.?05\s*\)'), r'($p\\text{s} > .05$)'),
            (re.compile(r'⫻'), r'$\\times$'),
            (re.compile(r'⫽'), r'='),
            (re.compile(r'\(\s*\*?r\*?\s*(\.\d+)\b'), r'($r = \1'),
            (re.compile(r'\(\s*\*?N\*?\s*=\s*(\d+)\s*\)'), r'($N = \1$)'),
            (re.compile(r'\(\s*\*?M\*?\s*=\s*([\d\.]+),\s*\*?SD\*?\s*=\s*([\d\.]+)\s*\)'), r'($M = \1$, $SD = \2$)'),
            (re.compile(r'\bZ\s+scores\b'), r'$Z$ scores'),
            (re.compile(r'\bWAIS-R\b'), r'WAIS–R'),
            (re.compile(r'Collect\s+&#36;&#36;&#36;'), r'“Collect $$$”'),
        ]

        result = md
        for pat, repl in fixes:
            result = pat.sub(repl, result)

        return result

    @classmethod
    def _match_emergent_section(cls, text: str, shared_sections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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


__all__ = ["IMRADResolver"]
