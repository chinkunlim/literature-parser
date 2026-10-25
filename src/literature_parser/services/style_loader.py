"""
Style & Unified Theme Loader
============================
Loads the global configuration and theme from ``config/theme.json``, informed by
eight unified divisions (typography, palette, layout, artifacts, tables, learning_blocks,
navigation, quality), and merges per-book settings from ``theme.json``, ``book_profile.json``,
or ``book_style_override.py`` located in the book's output directory.

Usage:
    from literature_parser.services.style_loader import load_style, load_theme
    theme = load_theme(book_output_dir="/path/to/output/My Book")
    style = load_style(book_output_dir="/path/to/output/My Book")
"""

from __future__ import annotations

import importlib.util
import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from literature_parser.services.book_style import STYLE as _DEFAULT_STYLE

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_THEME_PATH = PROJECT_ROOT / "config" / "theme.json"

_FALLBACK_THEME: Dict[str, Any] = {
    "typography": {
        "google_fonts_url": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap",
        "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang TC', 'Noto Sans TC', sans-serif",
        "font_serif": "'Merriweather', 'Source Serif Pro', 'Georgia', 'Noto Serif TC', serif",
        "font_mono": "'JetBrains Mono', 'Fira Code', 'Menlo', monospace",
        "body_font_family": "var(--font-sans)",
        "headings_font_family": "var(--font-serif)",
        "code_font_family": "var(--font-mono)",
        "base_font_size": "16px",
        "line_height": "1.75",
        "css_justify_body": True,
        "css_heading_align": "left",
        "css_blockquote_align": "left",
        "embed_css": True,
        "output_standalone_css": True,
    },
    "palette": {
        "color_text_main": "#1f2937",
        "color_text_muted": "#4b5563",
        "primary_theme_color": "#842959",
        "category_bg_color": "#f7f0f4",
        "card_bg_color": "#faf7f9",
        "color_blue": "#2563eb",
        "color_emerald": "#059669",
        "color_amber": "#d97706",
        "color_rose": "#e11d48",
        "highlight_bg": "#fef08a",
        "term_tag_bg": "#fef3c7",
        "term_tag_color": "#92400e",
        "table_border_color": "#d1d5db",
        "table_header_bg": "#f3f4f6",
    },
    "layout": {
        "generate_toc": True,
        "toc_mode": "close",
        "toc_title": "📑 Table of Contents",
        "toc_depth": 3,
        "toc_min_headings": 2,
        "prepend_chapter_title_if_missing": True,
        "front_matter_independent_split": True,
    },
    "artifacts": {
        "figure_render_mode": "html_figure",
        "figure_max_width_px": 650,
        "figure_uniform_pad_pt": 13.0,
        "figure_caption_italic": True,
        "orphan_flush_position": "section_end",
        "sub_figure_normalization": True,
        "extract_dpi": 300,
        "coverage_threshold": 0.80,
    },
    "tables": {
        "table_html_semantic": True,
        "table_heading_style": "bold-label",
        "table_numbered_style": "ordered-list",
        "table_bullet_style": "bullet-list",
    },
    "learning_blocks": {
        "lo_emoji": "🎯",
        "lo_use_bullets": False,
        "lo_show_label": False,
        "lo_number_format": "**{num}**",
        "lo_colon_after_number": False,
        "gloss_placement": "chapter_end",
        "gloss_format": "anki",
        "gloss_section_title": "## 🗂️ Chapter Key Terms & Active Recall",
        "gloss_emoji": "📖",
        "gloss_separator": "—",
        "gloss_backlink": True,
        "study_question_callout": "[!TIP]",
        "dialogue_html_semantic": True,
        "critical_incident_html_semantic": True,
    },
    "navigation": {
        "generate_obsidian_index": True,
        "inject_chapter_navigation": True,
        "navigation_style": "arrows",
    },
    "quality": {
        "verification_pass_threshold": 85.0,
        "enable_safe_autofix": True,
        "enable_ollama_deep_dive": True,
        "max_heading_chars_for_h3": 120,
        "min_dictionary_coverage": 0.90,
    },
}


def _deep_merge_dict(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges source dict into target dict.

    Args:
        target: Destination dictionary to merge into.
        source: Overriding dictionary.

    Returns:
        Dict[str, Any]: Merged dictionary.
    """
    for key, val in source.items():
        if isinstance(val, dict) and key in target and isinstance(target[key], dict):
            _deep_merge_dict(target[key], val)
        else:
            target[key] = deepcopy(val)
    return target


def load_theme(book_output_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Loads unified 8-division theme configuration from config/theme.json.

    Merges global defaults with optional per-book theme.json.

    Args:
        book_output_dir: Optional path to the book's output directory.

    Returns:
        Dict[str, Any]: Consolidated 8-division theme dictionary.
    """
    theme = deepcopy(_FALLBACK_THEME)

    # 1. Load global config/theme.json if present
    if CONFIG_THEME_PATH.exists():
        try:
            with open(CONFIG_THEME_PATH, "r", encoding="utf-8") as f:
                global_data = json.load(f)
                _deep_merge_dict(theme, global_data)
        except Exception as exc:
            logger.warning("Could not read %s: %s", CONFIG_THEME_PATH, exc)

    if not book_output_dir:
        return theme

    # 2. Check per-book theme.json
    book_path = Path(book_output_dir)
    book_theme_path = book_path / "theme.json"
    if book_theme_path.exists():
        try:
            with open(book_theme_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
                _deep_merge_dict(theme, book_data)
                logger.info("Loaded per-book theme override: %s", book_theme_path)
        except Exception as exc:
            logger.warning("Could not load %s: %s", book_theme_path, exc)

    return theme


def load_style(book_output_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Returns the active style dict for a given book.

    1. Starts with the global default STYLE.
    2. Overlays load_theme() 8-division settings.
    3. Merges global_profile.json if present.
    4. If `book_output_dir` is provided:
       a. Loads and merges book_profile.json.
       b. Loads and merges book_style_override.py.

    Args:
        book_output_dir: Optional path to the book's output directory.

    Returns:
        Dict[str, Any]: Merged flat and structured style configuration.
    """
    style = deepcopy(_DEFAULT_STYLE)
    theme = load_theme(book_output_dir)

    # Overlay theme divisions into style as structured keys
    for division_key, division_val in theme.items():
        style[division_key] = deepcopy(division_val)
        # Also flatten into style for backward compatibility
        if isinstance(division_val, dict):
            for sub_key, sub_val in division_val.items():
                style[sub_key] = deepcopy(sub_val)

    # 1. Load global_profile.json if available
    profiles_dir = Path(__file__).resolve().parent / "profiles"
    global_profile_path = profiles_dir / "global_profile.json"
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

    # 2. Check profile.json / book_profile.json
    cand_canon = book_path / "profile.json"
    cand_legacy = book_path / "book_profile.json"
    book_profile_path = cand_canon if cand_canon.exists() else cand_legacy
    if book_profile_path.exists():
        try:
            with open(book_profile_path, "r", encoding="utf-8") as f:
                bp = json.load(f)

                # If publisher is declared or fingerprinted, merge publisher template first
                pub = (bp.get("publisher") or "").lower()
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

                # Apply special blocks / section rules (preserve default EOC patterns via union, Refs: ISSUE-016)
                if "special_blocks" in bp:
                    sb = bp["special_blocks"]
                    for k in ("gloss_placement", "gloss_format", "lo_use_bullets"):
                        if k in sb:
                            style[k] = sb[k]
                    if "eoc_heading_patterns" in sb and isinstance(sb["eoc_heading_patterns"], list):
                        existing_eoc = list(style.get("eoc_heading_patterns", []))
                        for pat in sb["eoc_heading_patterns"]:
                            if pat not in existing_eoc:
                                existing_eoc.append(pat)
                        style["eoc_heading_patterns"] = existing_eoc
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
