"""
Style Loader
============
Loads the global STYLE dict (optionally informed by global_profile.json) and
merges per-book settings from ``book_profile.json`` and/or ``book_style_override.py``
located in the book's output directory.

Usage:
    from literature_parser.services.style_loader import load_style
    style = load_style(book_output_dir="/path/to/output/My Book")
"""

import importlib.util
import json
import logging
from copy import deepcopy
from pathlib import Path

from literature_parser.services.book_style import STYLE as _DEFAULT_STYLE

logger = logging.getLogger(__name__)


def load_style(book_output_dir: str = None) -> dict:
    """
    Returns the active style dict for a given book.

    1. Starts with the global default STYLE.
    2. Merges global_profile.json if present.
    3. If `book_output_dir` is provided:
       a. Loads and merges book_profile.json.
       b. Loads and merges book_style_override.py.

    Args:
        book_output_dir: Path to the book's output directory.

    Returns:
        dict: Merged style configuration.
    """
    style = deepcopy(_DEFAULT_STYLE)

    # 1. Load global_profile.json if available
    global_profile_path = Path(__file__).parent / "profiles" / "global_profile.json"
    if global_profile_path.exists():
        try:
            with open(global_profile_path, "r", encoding="utf-8") as f:
                gp = json.load(f)
                if "learning_objectives" in gp:
                    lo = gp["learning_objectives"]
                    if lo.get("style") == "bullet_list":
                        style["lo_use_blockquote"] = lo.get("use_blockquote", False)
                        style["lo_emoji"] = lo.get("emoji", "🎯")
                        style["lo_number_format"] = lo.get("number_format", "**{num}**")
                        style["lo_colon_after_number"] = lo.get("colon_after_number", False)
                if "study_questions" in gp:
                    sq = gp["study_questions"]
                    style["study_question_callout"] = sq.get("callout", "[!TIP]")
                if "margin_glossary" in gp:
                    mg = gp["margin_glossary"]
                    style["gloss_placement"] = mg.get("placement", "chapter_end")
                    style["gloss_section_title"] = mg.get("section_title", "### Chapter Key Terms & Flashcards")
                if "tables" in gp:
                    tb = gp["tables"]
                    style["table_heading_style"] = tb.get("heading_style", "bold-label")
                    style["table_merged_rows_strategy"] = tb.get("merged_rows_strategy", "html_colspan")
                if "typography" in gp:
                    tp = gp["typography"]
                    style["css_justify_body"] = tp.get("css_justify_body", True)
                    style["css_heading_align"] = tp.get("css_heading_align", "left")
                    style["css_blockquote_align"] = tp.get("css_blockquote_align", "left")
                    style["arrow_symbol"] = tp.get("arrow_symbol", "$\\rightarrow$")
        except Exception as exc:
            logger.warning("Could not read global_profile.json: %s", exc)

    if not book_output_dir:
        return style

    book_path = Path(book_output_dir)

    # 2. Check book_profile.json
    book_profile_path = book_path / "book_profile.json"
    if book_profile_path.exists():
        try:
            with open(book_profile_path, "r", encoding="utf-8") as f:
                bp = json.load(f)

                # If publisher is declared or fingerprinted, merge publisher template first
                pub = bp.get("publisher", "").lower()
                if "pearson" in pub:
                    pub_path = profiles_dir / "publisher_pearson.json"
                elif "cengage" in pub:
                    pub_path = profiles_dir / "publisher_cengage.json"
                elif any(k in pub for k in ("apa", "american psychological", "experimental psychology")):
                    pub_path = profiles_dir / "literature_apa.json" if (profiles_dir / "literature_apa.json").exists() else profiles_dir / "journal_apa.json"
                elif any(k in pub for k in ("elsevier", "sciencedirect", "academic press")):
                    pub_path = profiles_dir / "literature_elsevier.json" if (profiles_dir / "literature_elsevier.json").exists() else profiles_dir / "journal_elsevier.json"
                elif any(k in pub for k in ("wiley", "blackwell")):
                    pub_path = profiles_dir / "literature_wiley.json" if (profiles_dir / "literature_wiley.json").exists() else profiles_dir / "journal_wiley.json"
                elif any(k in pub for k in ("springer", "nature", "psychonomic")):
                    pub_path = profiles_dir / "literature_springer.json" if (profiles_dir / "literature_springer.json").exists() else profiles_dir / "journal_springer.json"
                elif any(k in pub for k in ("sage", "association for psychological science", "psychological science")):
                    pub_path = profiles_dir / "literature_sage.json" if (profiles_dir / "literature_sage.json").exists() else profiles_dir / "journal_sage.json"
                else:
                    pub_path = None

                if pub_path and pub_path.exists():
                    try:
                        with open(pub_path, "r", encoding="utf-8") as pf:
                            pub_data = json.load(pf)
                            if "special_blocks" in pub_data:
                                style.update(pub_data["special_blocks"])
                            if "is_journal" in pub_data:
                                style["is_journal"] = pub_data["is_journal"]
                            if "column_roles" in pub_data:
                                style["column_roles"] = pub_data["column_roles"]
                            logger.info("Inherited publisher profile: %s", pub_path.name)
                    except Exception as pe:
                        logger.debug("Failed loading publisher profile: %s", pe)

                style["book_profile"] = bp
                # Apply direct style keys from book_profile.json
                for k in ("gloss_placement", "gloss_format", "gloss_section_title",
                          "lo_use_bullets", "table_html_semantic", "dialogue_html_semantic",
                          "table_heading_style"):
                    if k in bp:
                        style[k] = bp[k]

                # Apply special blocks / section rules
                if "special_blocks" in bp:
                    sb = bp["special_blocks"]
                    for k in ("gloss_placement", "gloss_format", "eoc_heading_patterns", "lo_use_bullets"):
                        if k in sb:
                            style[k] = sb[k]
                if "section_rules" in bp:
                    style["section_rules"] = bp["section_rules"]
        except Exception as exc:
            logger.warning("Could not read book_profile.json at %s: %s", book_profile_path, exc)


    # 3. Check book_style_override.py
    override_path = book_path / "book_style_override.py"
    if override_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("book_style_override", str(override_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            override = getattr(module, "STYLE_OVERRIDE", None)
            if isinstance(override, dict):
                style.update(override)
                logger.info("Loaded per-book style override from: %s", override_path)
        except Exception as exc:
            logger.warning("Could not load book_style_override.py at '%s': %s", override_path, exc)

    return style
