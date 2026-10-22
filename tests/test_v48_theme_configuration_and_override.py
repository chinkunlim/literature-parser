"""
Unit Tests for Unified Theme, Pipeline Configuration & Instant Re-theming
========================================================================
Validates:
1. Default loading of config/theme.json with 8 unified divisions.
2. Hierarchical override (global default + per-book theme.json).
3. Dynamic TOC generation honoring toc_mode, toc_depth, and toc_title.
4. Dynamic CSS generation for textbook and literature based on theme palette and typography.
5. Instant re-theme script (apply_theme.py) for fast in-place styling refresh.
"""

import json
import tempfile
import unittest
from pathlib import Path

from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.literature_style import build_literature_css
from literature_parser.services.parsers.layout_detector import generate_markdown_toc
from literature_parser.services.style_loader import load_style, load_theme


class TestThemeConfigurationAndOverride(unittest.TestCase):
    """Verifies externalized configuration, inheritance, and dynamic styling."""

    def test_load_default_theme_has_eight_divisions(self):
        """Ensures load_theme() returns all 8 structured divisions with valid defaults."""
        theme = load_theme()
        self.assertIn("typography", theme)
        self.assertIn("palette", theme)
        self.assertIn("layout", theme)
        self.assertIn("artifacts", theme)
        self.assertIn("tables", theme)
        self.assertIn("learning_blocks", theme)
        self.assertIn("navigation", theme)
        self.assertIn("quality", theme)

        # Check key typography & palette values
        self.assertIn("Inter", theme["typography"]["font_sans"])
        self.assertEqual(theme["palette"]["primary_theme_color"], "#842959")
        self.assertEqual(theme["layout"]["toc_mode"], "close")
        self.assertEqual(theme["layout"]["toc_depth"], 3)
        self.assertEqual(theme["artifacts"]["figure_max_width_px"], 650)
        self.assertEqual(theme["quality"]["verification_pass_threshold"], 85.0)

    def test_per_book_theme_override(self):
        """Verifies that a book directory with its own theme.json overrides specific keys while preserving others."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            book_dir = Path(tmp_dir) / "My Customized Book"
            book_dir.mkdir(parents=True)

            custom_override = {
                "palette": {
                    "primary_theme_color": "#1e3a8a",  # Classic Navy Blue
                    "card_bg_color": "#f0fdf4"
                },
                "layout": {
                    "toc_mode": "open",
                    "toc_depth": 2
                }
            }
            (book_dir / "theme.json").write_text(json.dumps(custom_override), encoding="utf-8")

            merged = load_theme(book_output_dir=str(book_dir))

            # Overridden values
            self.assertEqual(merged["palette"]["primary_theme_color"], "#1e3a8a")
            self.assertEqual(merged["palette"]["card_bg_color"], "#f0fdf4")
            self.assertEqual(merged["layout"]["toc_mode"], "open")
            self.assertEqual(merged["layout"]["toc_depth"], 2)

            # Preserved inherited values
            self.assertIn("Inter", merged["typography"]["font_sans"])
            self.assertEqual(merged["palette"]["color_blue"], "#2563eb")
            self.assertEqual(merged["artifacts"]["figure_max_width_px"], 650)
            self.assertEqual(merged["quality"]["verification_pass_threshold"], 85.0)

    def test_backward_compatibility_with_load_style(self):
        """Verifies load_style() returns flat backward-compatible keys alongside nested divisions."""
        style = load_style()
        self.assertEqual(style.get("primary_theme_color"), "#842959")
        self.assertEqual(style.get("toc_mode"), "close")
        self.assertEqual(style.get("figure_uniform_pad_pt"), 13.0)
        self.assertIn("typography", style)

    def test_dynamic_toc_depth_and_title(self):
        """Ensures generate_markdown_toc respects toc_depth and custom toc_title."""
        md = (
            "## 1. Introduction\n\n"
            "Intro text.\n\n"
            "### 1.1 Background\n\n"
            "Background text.\n\n"
            "#### 1.1.1 Deep Detail\n\n"
            "Deep detail text.\n\n"
            "## 2. Methodology\n\n"
            "Method text."
        )

        # 1. Depth = 2 (Only H2)
        toc_h2_only = generate_markdown_toc(md, toc_mode="close", toc_depth=2, toc_title="📑 本章目錄")
        self.assertIn("<summary>📑 <b>本章目錄</b></summary>", toc_h2_only)
        self.assertIn("Introduction", toc_h2_only)
        self.assertIn("Methodology", toc_h2_only)
        self.assertNotIn("Background", toc_h2_only)
        self.assertNotIn("Deep Detail", toc_h2_only)

        # 2. Depth = 3 (H2 + H3)
        toc_h3 = generate_markdown_toc(md, toc_mode="close", toc_depth=3)
        self.assertIn("Introduction", toc_h3)
        self.assertIn("Background", toc_h3)
        self.assertNotIn("Deep Detail", toc_h3)

        # 3. Depth = 4 (H2 + H3 + H4)
        toc_h4 = generate_markdown_toc(md, toc_mode="open", toc_depth=4)
        self.assertTrue(toc_h4.startswith("<details open>"))
        self.assertIn("Introduction", toc_h4)
        self.assertIn("Background", toc_h4)
        self.assertIn("Deep Detail", toc_h4)

    def test_dynamic_css_generation_with_custom_theme(self):
        """Verifies build_textbook_css and build_literature_css reflect custom theme colors and typography."""
        custom_style = {
            "typography": {
                "google_fonts_url": "https://fonts.googleapis.com/css2?family=Roboto&display=swap",
                "font_sans": "'Roboto', sans-serif",
                "font_serif": "'Georgia', serif",
                "base_font_size": "17px",
                "line_height": "1.8",
                "css_justify_body": True,
                "css_heading_align": "center"
            },
            "palette": {
                "primary_theme_color": "#0d9488",  # Teal 600
                "card_bg_color": "#f0fdfa",
                "color_blue": "#0284c7"
            }
        }

        css = build_textbook_css(custom_style)
        self.assertIn("family=Roboto", css)
        self.assertIn("--font-sans: 'Roboto', sans-serif;", css)
        self.assertIn("text-align: center;", css)  # heading align

        lit_css = build_literature_css(custom_style)
        self.assertIn("family=Roboto", lit_css)
        self.assertIn("--font-sans: 'Roboto', sans-serif;", lit_css)

    def test_apply_theme_utility(self):
        """Verifies that apply_theme in-place replaces <style> blocks and updates style.css."""
        from scripts.apply_theme import apply_theme_to_directory

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            sample_md = out_dir / "Chapter_01.md"
            sample_md.write_text(
                "# Chapter 1\n\n"
                "<style>\n  /* Old CSS */\n  :root { --color-primary: #old; }\n</style>\n\n"
                "<details>\n<summary>📑 <b>Table of Contents</b></summary>\n\n- [Old Intro](#old-intro)\n\n</details>\n\n"
                "## 1. New Introduction\n\nHello world.\n\n### 1.1 Sub Intro\n\nDetail.",
                encoding="utf-8"
            )

            # Write book-level custom theme
            custom_theme = {
                "palette": {
                    "primary_theme_color": "#c026d3"  # Fuchsia
                },
                "layout": {
                    "toc_mode": "open",
                    "toc_title": "📑 快速目錄"
                }
            }
            (out_dir / "theme.json").write_text(json.dumps(custom_theme), encoding="utf-8")

            # Execute re-theming
            success_count = apply_theme_to_directory(out_dir)
            self.assertEqual(success_count, 1)

            # Verify updated markdown
            updated_md = sample_md.read_text(encoding="utf-8")
            self.assertNotIn("#old", updated_md)
            self.assertIn("<details open>", updated_md)
            self.assertIn("📑 <b>快速目錄</b>", updated_md)
            self.assertIn("New Introduction", updated_md)
            self.assertIn("Sub Intro", updated_md)

            # Verify standalone style.css was generated
            style_css = out_dir / "style.css"
            self.assertTrue(style_css.exists())
            self.assertIn("Inter", style_css.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
