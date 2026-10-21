"""
Hierarchical Configuration & Cross-Document Knowledge Manager
=============================================================
Manages four-tier configuration inheritance:
  Level 1: Global Archetype JSON (journal / textbook)
  Level 2: Publisher Specific JSON (apa / elsevier / wiley / springer / ieee)
  Level 3: Shared Cross-Document Knowledge JSON (emergent sections / symbol mappings)
  Level 4: Local Instance Profile JSON (book_profile.json)

Enables emergent structures learned from one document to be harvested into shared
knowledge and applied across all subsequent documents of the same archetype.
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def deep_merge(base: dict, update: dict) -> dict:
    """Recursively merges update dict into base dict."""
    result = dict(base)
    for k, v in update.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        elif k in result and isinstance(result[k], list) and isinstance(v, list):
            # Union of lists preserving order without duplicates for primitives/dicts
            merged_list = list(result[k])
            for item in v:
                if item not in merged_list:
                    merged_list.append(item)
            result[k] = merged_list
        else:
            result[k] = v
    return result


class ConfigManager:
    """Four-tier hierarchical config and shared knowledge repository manager."""

    @classmethod
    def get_config_root(cls) -> Path:
        """Locates the configuration resources directory."""
        # 1. Package resources directory: src/literature_parser/config/resources/
        candidate_pkg = Path(__file__).resolve().parent.parent / "config" / "resources"
        if candidate_pkg.exists() and candidate_pkg.is_dir():
            return candidate_pkg
        # 2. Project root config/
        candidate1 = Path(__file__).resolve().parent.parent.parent.parent / "config"
        if candidate1.exists() and candidate1.is_dir():
            return candidate1
        # 3. Current working directory config/
        candidate2 = Path.cwd() / "config"
        if candidate2.exists() and candidate2.is_dir():
            return candidate2
        return candidate_pkg

    @classmethod
    def load_json(cls, path: Path) -> dict:
        """Safely loads a JSON file, returning empty dict on failure."""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load JSON config from %s: %s", path, e)
            return {}

    @classmethod
    def save_json(cls, path: Path, data: dict):
        """Safely writes a JSON file formatted with 2 spaces indent."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error("Failed to save JSON config to %s: %s", path, e)

    # -------------------------------------------------------------------------
    # Tier 1: Archetype
    # -------------------------------------------------------------------------
    @classmethod
    def load_archetype(cls, archetype: str = "literature") -> dict:
        """Loads Level 1 Global Archetype configuration.
        
        Note: 'journal' is a legacy alias for 'literature' — both map to literature.json.
        """
        config_dir = cls.get_config_root() / "archetypes"
        # Normalize legacy 'journal' alias to the renamed 'literature' config file
        normalized = "literature" if archetype.lower() in ("journal", "literature") else archetype.lower()
        file_path = config_dir / f"{normalized}.json"
        return cls.load_json(file_path)

    # -------------------------------------------------------------------------
    # Tier 2: Publisher
    # -------------------------------------------------------------------------
    @classmethod
    def load_publisher(cls, publisher: str) -> dict:
        """Loads Level 2 Publisher Specific configuration."""
        if not publisher:
            return {}
        config_dir = cls.get_config_root() / "publishers"
        file_path = config_dir / f"{publisher.lower()}.json"
        return cls.load_json(file_path)

    # -------------------------------------------------------------------------
    # Tier 3: Shared Cross-Document Knowledge
    # -------------------------------------------------------------------------
    @classmethod
    def load_shared_knowledge(cls) -> dict:
        """Loads Level 3 Shared Cross-Document Knowledge repository."""
        config_dir = cls.get_config_root() / "shared_knowledge"
        # Prefer renamed literature_sections.json; fall back to legacy journal_sections.json
        sections_file = config_dir / "literature_sections.json"
        if not sections_file.exists():
            sections_file = config_dir / "journal_sections.json"
        sections_data = cls.load_json(sections_file)
        symbols_data = cls.load_json(config_dir / "symbol_mappings.json")
        return {
            "shared_sections": sections_data.get("emergent_sections", []),
            "shared_symbols": symbols_data.get("unicode_to_latex", {}),
        }

    # -------------------------------------------------------------------------
    # Tier 4: Instance Profile
    # -------------------------------------------------------------------------
    @classmethod
    def load_instance_profile(cls, instance_path) -> dict:
        """Loads Level 4 local book/document profile JSON if exists.
        
        Prefers document_profile.json; falls back to legacy book_profile.json.
        """
        if not instance_path:
            return {}
        p = Path(instance_path)
        if p.is_dir():
            doc_profile = p / "document_profile.json"
            book_profile = p / "book_profile.json"
            p = doc_profile if doc_profile.exists() else book_profile
        return cls.load_json(p)

    # -------------------------------------------------------------------------
    # Archetype & Publisher Detection
    # -------------------------------------------------------------------------
    @classmethod
    def detect_archetype(cls, pdf_path: str, total_pages: Optional[int] = None) -> str:
        """
        Detects whether the document is a 'journal' article or a 'textbook'.
        Heuristic:
          - <= 40 pages and contains academic keywords (Abstract, DOI, Volume, References) -> journal
          - > 40 pages or contains explicit chapters / Table of Contents -> textbook
        """
        if total_pages is None:
            total_pages = cls.get_page_count(pdf_path)

        if total_pages > 45:
            return "textbook"

        from literature_parser.services.fingerprinting.document_classifier import DocumentClassifier
        if DocumentClassifier.is_journal_article(pdf_path):
            return "literature"

        # Check outline/bookmarks for textbook chapter markers
        try:
            proc = subprocess.run(
                ['pdftohtml', '-stdout', '-xml', '-nodrm', '-i', '-f', '1', '-l', '1', pdf_path],
                capture_output=True, check=False, timeout=15
            )
            data = proc.stdout
            if b'<outline>' in data:
                if re.search(rb'chapter\s+\d+|part\s+[ivx\d]+', data, re.IGNORECASE):
                    return "textbook"
        except Exception:
            pass

        # Check text content of first 2 pages
        sample_text = cls.extract_sample_text(pdf_path, max_pages=2)
        academic_signals = [
            r'\babstract\b',
            r'\bdoi(?:\.org)?[:\s/]',
            r'\bvolume\s+\d+\b',
            r'\bjournal\s+of\b',
            r'\bdepartment\s+of\b',
            r'\buniversity\b',
            r'\bapa\b',
            r'\belsevier\b',
            r'\bwiley\b',
            r'\bspringer\b',
            r'\bcorrespondence\s+concerning\b',
            r'\breferences\b',
        ]
        match_count = sum(1 for pat in academic_signals if re.search(pat, sample_text, re.IGNORECASE))

        if total_pages <= 35 and match_count >= 2 or total_pages <= 20:
            return "literature"

        return "textbook" if total_pages > 40 else "literature"

    @classmethod
    def detect_publisher(cls, pdf_path: Optional[str] = None, sample_text: str = "") -> Optional[str]:
        """Detects publisher (apa, elsevier, wiley, springer, ieee) from DOI or keywords."""
        text = sample_text
        if not text and pdf_path and os.path.exists(pdf_path):
            text = cls.extract_sample_text(pdf_path, max_pages=2)

        if not text:
            return None

        # 1. DOI Prefixes
        if re.search(r'10\.1037[/\w\.\-]', text) or re.search(r'american\s+psychological\s+association', text, re.IGNORECASE):
            return "apa"
        if re.search(r'10\.1016[/\w\.\-]', text) or re.search(r'elsevier\s+science|sciencedirect', text, re.IGNORECASE):
            return "elsevier"
        if re.search(r'10\.(?:1002|1111)[/\w\.\-]', text) or re.search(r'john\s+wiley|blackwell', text, re.IGNORECASE):
            return "wiley"
        if re.search(r'10\.1007[/\w\.\-]', text) or re.search(r'springer\b', text, re.IGNORECASE):
            return "springer"
        if re.search(r'10\.1109[/\w\.\-]', text) or re.search(r'ieee\b', text, re.IGNORECASE):
            return "ieee"

        return None

    @classmethod
    def get_page_count(cls, pdf_path: str) -> int:
        """Retrieves page count using pdfinfo."""
        try:
            out = subprocess.check_output(
                ['pdfinfo', pdf_path],
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode('utf-8', errors='ignore')
            for line in out.splitlines():
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except Exception:
            pass
        return 0

    @classmethod
    def extract_sample_text(cls, pdf_path: str, max_pages: int = 2) -> str:
        """Extracts text from the first N pages."""
        try:
            out = subprocess.check_output(
                ['pdftotext', '-f', '1', '-l', str(max_pages), pdf_path, '-'],
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode('utf-8', errors='ignore')
            return out
        except Exception:
            return ""

    # -------------------------------------------------------------------------
    # Hierarchical Merging (L1 -> L2 -> L3 -> L4)
    # -------------------------------------------------------------------------
    @classmethod
    def load_hierarchical_config(
        cls,
        pdf_path: Optional[str] = None,
        archetype: Optional[str] = None,
        publisher: Optional[str] = None,
        instance_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Loads and merges configs hierarchically:
        Level 1 (Archetype) -> Level 2 (Publisher) -> Level 3 (Shared Knowledge) -> Level 4 (Instance Profile)
        """
        # Determine archetype if not specified
        if not archetype:
            if pdf_path and os.path.exists(pdf_path):
                archetype = cls.detect_archetype(pdf_path)
            else:
                archetype = "literature"

        # Level 1: Archetype
        merged = cls.load_archetype(archetype)
        if not merged:
            merged = {"archetype": archetype}

        # Level 2: Publisher
        if not publisher and pdf_path and os.path.exists(pdf_path):
            publisher = cls.detect_publisher(pdf_path)

        if publisher:
            pub_data = cls.load_publisher(publisher)
            merged = deep_merge(merged, {"publisher_config": pub_data, "publisher": publisher})
        else:
            merged["publisher"] = None

        # Level 3: Shared Cross-Document Knowledge
        shared_knowledge = cls.load_shared_knowledge()
        merged = deep_merge(merged, shared_knowledge)

        # Level 4: Instance Profile (if directory or file given)
        if instance_dir:
            inst_data = cls.load_instance_profile(instance_dir)
            if inst_data:
                merged = deep_merge(merged, {"instance_profile": inst_data})

        return merged

    # -------------------------------------------------------------------------
    # Knowledge Harvesting & Propagation (Cross-Document Learning)
    # -------------------------------------------------------------------------
    @classmethod
    def harvest_emergent_section(
        cls,
        name: str,
        aliases: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        target_heading_level: int = 2,
        typical_location: str = "end_of_paper",
    ) -> bool:
        """
        Harvests a newly discovered section structure into `config/shared_knowledge/journal_sections.json`.
        Ensures that unexpected structures identified in one document are immediately available
        to all future documents.
        """
        config_dir = cls.get_config_root() / "shared_knowledge"
        file_path = config_dir / "journal_sections.json"
        data = cls.load_json(file_path)
        sections = data.get("emergent_sections", [])

        # Check if already present
        for sec in sections:
            if sec.get("name", "").lower() == name.lower():
                # Merge patterns and aliases
                if aliases:
                    for a in aliases:
                        if a not in sec.get("aliases", []):
                            sec.setdefault("aliases", []).append(a)
                if patterns:
                    for p in patterns:
                        if p not in sec.get("patterns", []):
                            sec.setdefault("patterns", []).append(p)
                cls.save_json(file_path, {"emergent_sections": sections})
                return True

        # Add new emergent section
        new_entry = {
            "name": name,
            "aliases": aliases or [name],
            "patterns": patterns or [f"(?i)^{re.escape(name)}\\b"],
            "target_heading_level": target_heading_level,
            "typical_location": typical_location,
        }
        sections.append(new_entry)
        cls.save_json(file_path, {"emergent_sections": sections})
        logger.info("Harvested new emergent section into shared knowledge: %s", name)
        return True

    @classmethod
    def harvest_symbol_mapping(cls, unicode_char: str, latex_rep: str) -> bool:
        """
        Harvests a newly discovered font/glyph encoding into `config/shared_knowledge/symbol_mappings.json`.
        """
        config_dir = cls.get_config_root() / "shared_knowledge"
        file_path = config_dir / "symbol_mappings.json"
        data = cls.load_json(file_path)
        symbols = data.get("unicode_to_latex", {})

        if symbols.get(unicode_char) == latex_rep:
            return False

        symbols[unicode_char] = latex_rep
        cls.save_json(file_path, {"unicode_to_latex": symbols})
        logger.info("Harvested new symbol mapping into shared knowledge: %s -> %s", unicode_char, latex_rep)
        return True

    @classmethod
    def save_instance_profile(cls, output_dir, profile_data: dict, archetype: str = ""):
        """Saves dynamic instance configuration to the output directory.

        For literature/journal archetypes: writes ``document_profile.json``.
        For textbook archetypes: writes ``book_profile.json`` (legacy name preserved
        for backward compatibility with textbook pipeline components).
        """
        is_literature = archetype.lower() in ("journal", "literature") if archetype else False
        filename = "document_profile.json" if is_literature else "book_profile.json"
        out_path = Path(output_dir) / filename
        cls.save_json(out_path, profile_data)

