"""
Scanned Textbook Neural Layout & OCR Parser
===========================================
High-fidelity neural layout & OCR engine for scanned textbooks using Tesseract 5.5.2 TSV.
Renders pages at 300 DPI, splits multi-column reading order, strips running headers/footers,
and converts mathematical equations to LaTeX.
"""

import csv
import io
import logging
import os
import re
import shutil
import subprocess
from typing import Any

from literature_parser.config.processor_config import DEFAULT_DPI, FOOTER_NOISE_PATTERNS
from literature_parser.services.parsers.layout_detector import LayoutDetector
from literature_parser.services.parsers.math_latex import MathLaTeXConverter
from literature_parser.services.utils.text_utils import clean_punctuation_spacing

logger = logging.getLogger(__name__)


class ScannedPDFParser:
    """Neural OCR & layout parser for scanned PDF textbook pages."""

    @staticmethod
    def get_image_size(img_path: str) -> tuple[int, int]:
        """Reads the pixel width and height of an image using macOS sips.

        Args:
            img_path: File path to the image to inspect.

        Returns:
            Tuple of (width, height) in pixels; defaults to (2200, 2800) on error.
        """
        sips_bin = shutil.which("sips") or "/usr/bin/sips"
        try:
            out = subprocess.check_output(
                [sips_bin, "-g", "pixelWidth", "-g", "pixelHeight", img_path],
                stderr=subprocess.DEVNULL,
                timeout=15,
            ).decode("utf-8", errors="ignore")
            wm = re.search(r"pixelWidth:\s+(\d+)", out)
            hm = re.search(r"pixelHeight:\s+(\d+)", out)
            if wm and hm:
                return int(wm.group(1)), int(hm.group(1))
        except Exception:
            logger.debug("Failed to read image size via sips for %s", img_path, exc_info=True)
        return 2200, 2800

    @staticmethod
    def is_running_header(line_words: list[dict[str, Any]], line_text: str, top_ratio: float) -> bool:
        """Determines whether an OCR line at the top of a page is a running header.

        Args:
            line_words: List of word bounding-box dictionaries in the line.
            line_text: Concatenated text of the line.
            top_ratio: Vertical position of the line normalized by page height (0.0 to 1.0).

        Returns:
            True if the line matches running header heuristics, False otherwise.
        """
        if top_ratio > 0.075:
            return False
        if len(line_words) > 6:
            return False
        clean = line_text.strip()
        if re.match(r"^(?:[ivxlcdm]+|\d+)\s*$", clean, re.IGNORECASE):
            return True
        if re.match(r"^(?:Chapter|Part|Section|Contents)\b", clean, re.IGNORECASE):
            return True
        if clean.isupper() and len(clean) < 40:
            return True
        return bool(re.search(r"(?:CHAPTER|PART|\d{1,3}\s+[A-Z]|COREY|GROUPS|PROCESS)", line_text, re.IGNORECASE))

    @staticmethod
    def is_running_footer(line_words: list[dict[str, Any]], line_text: str, top_ratio: float) -> bool:
        """Determines whether an OCR line near the bottom of a page is a running footer.

        Args:
            line_words: List of word bounding-box dictionaries in the line.
            line_text: Concatenated text of the line.
            top_ratio: Vertical position of the line normalized by page height (0.0 to 1.0).

        Returns:
            True if the line matches running footer heuristics, False otherwise.
        """
        if top_ratio < 0.85:
            return False
        clean = line_text.strip()
        for pat in FOOTER_NOISE_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return True
        if re.match(r"^(?:[ivxlcdm]+|\d+)\s*$", clean, re.IGNORECASE):
            return True
        if re.search(r"(?:[ivxlcdm]+|\d+)\s*/|/\s*(?:[ivxlcdm]+|\d+|contents|index)\b", clean, re.IGNORECASE):
            return True
        return bool(
            clean.isupper()
            and len(clean) < 40
            and any(k in clean.lower() for k in ("about the authors", "contents", "index"))
        )

    @staticmethod
    def _extract_ocr_words(tsv_text: str) -> list[dict[str, Any]]:
        """Parses Tesseract TSV output into word dictionaries with bounding box coordinates.

        Args:
            tsv_text: Raw TSV string produced by Tesseract OCR.

        Returns:
            List of word dictionaries with coordinates and confidence scores.
        """
        reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
        words: list[dict[str, Any]] = []
        for r in reader:
            if r["level"] != "5":
                continue
            txt = r["text"].strip()
            try:
                conf = float(r["conf"])
            except ValueError:
                conf = -1.0
            if txt and conf >= 0:
                words.append(
                    {
                        "text": txt,
                        "conf": conf,
                        "left": int(r["left"]),
                        "top": int(r["top"]),
                        "width": int(r["width"]),
                        "height": int(r["height"]),
                        "right": int(r["left"]) + int(r["width"]),
                        "bottom": int(r["top"]) + int(r["height"]),
                        "line_num": int(r["line_num"]),
                        "par_num": int(r["par_num"]),
                        "block_num": int(r["block_num"]),
                    }
                )
        return words

    @classmethod
    def _filter_ocr_lines(cls, words: list[dict[str, Any]], ph: int) -> list[list[dict[str, Any]]]:
        """Groups OCR words into lines and filters out running headers, footers, and margin noise.

        Args:
            words: List of OCR word dictionaries.
            ph: Page height in pixels.

        Returns:
            Filtered list of lines, where each line is a list of word dictionaries.
        """
        raw_lines: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
        for w in words:
            raw_lines.setdefault((w["block_num"], w["par_num"], w["line_num"]), []).append(w)

        filtered_lines: list[list[dict[str, Any]]] = []
        for k in sorted(raw_lines.keys()):
            ws = sorted(raw_lines[k], key=lambda x: int(x["left"]))
            line_txt = " ".join(str(x["text"]) for x in ws)
            top_ratio = min(int(x["top"]) for x in ws) / ph
            if cls.is_running_header(ws, line_txt, top_ratio):
                continue
            if cls.is_running_footer(ws, line_txt, top_ratio):
                continue
            ws_clean = [x for x in ws if not (x["text"] in (":", "|", "¦") and int(x["width"]) < 10)]
            if ws_clean:
                filtered_lines.append(ws_clean)
        return filtered_lines

    @staticmethod
    def _lines_to_markdown(lines_list: list[list[dict[str, Any]]]) -> list[str]:
        """Converts grouped OCR word lines into Markdown paragraph and heading blocks.

        Args:
            lines_list: List of OCR word lines in reading order.

        Returns:
            List of formatted Markdown paragraph strings.
        """
        records: list[tuple[str, float]] = []
        for line in lines_list:
            text = " ".join(str(x["text"]) for x in line)
            text = clean_punctuation_spacing(text)
            avg_h = sum(int(x["height"]) for x in line) / len(line)
            records.append((text, avg_h))

        paras: list[str] = []
        curr_p: list[str] = []
        for text, h in records:
            if re.match(r"^(?:CHAPTER|Chapter)\s+\d+", text, re.IGNORECASE):
                if curr_p:
                    paras.append(" ".join(curr_p))
                    curr_p = []
                paras.append(f"### {text}")
            elif re.match(r"^[•\-\*°©e]\s*", text):
                if curr_p:
                    paras.append(" ".join(curr_p))
                    curr_p = []
                bullet_content = re.sub(r"^[•\-\*°©e\s]+", "", text)
                paras.append(f"- {bullet_content}")
            elif h > 45 and len(text) < 80 and not text.endswith("."):
                if curr_p:
                    paras.append(" ".join(curr_p))
                    curr_p = []
                paras.append(f"## {text}")
            else:
                if curr_p and curr_p[-1].endswith("-"):
                    curr_p[-1] = curr_p[-1][:-1] + text
                else:
                    curr_p.append(text)
        if curr_p:
            paras.append(" ".join(curr_p))
        return paras

    @staticmethod
    def _split_multi_column_lines(
        filtered_lines: list[list[dict[str, Any]]],
        pw: int,
    ) -> tuple[list[list[dict[str, Any]]], list[list[dict[str, Any]]]]:
        """Partitions OCR lines into left and right columns based on horizontal word gaps.

        Args:
            filtered_lines: Filtered list of OCR word lines.
            pw: Page width in pixels.

        Returns:
            Tuple of (left_column_lines, right_column_lines).
        """
        col_left: list[list[dict[str, Any]]] = []
        col_right: list[list[dict[str, Any]]] = []
        for ws in filtered_lines:
            split_idx = -1
            for i in range(len(ws) - 1):
                gap = int(ws[i + 1]["left"]) - int(ws[i]["right"])
                if gap >= 80:
                    split_idx = i
                    break
            if split_idx != -1:
                lp = ws[: split_idx + 1]
                rp = ws[split_idx + 1 :]
                if lp:
                    col_left.append(lp)
                if rp:
                    col_right.append(rp)
            else:
                cx = (int(ws[0]["left"]) + int(ws[-1]["right"])) / 2
                if cx < pw * 0.48:
                    col_left.append(ws)
                elif cx > pw * 0.52:
                    col_right.append(ws)
                else:
                    col_left.append(ws)
        return col_left, col_right

    @classmethod
    def parse_page_to_markdown(cls, pdf_path: str, page_num: int, work_dir: str) -> str:
        """Renders page to 300 DPI PNG, performs neural OCR & layout analysis, and returns Markdown.

        Args:
            pdf_path: Path to the source PDF file.
            page_num: 1-based page number to render and OCR.
            work_dir: Temporary working directory for rendered page images.

        Returns:
            Structured Markdown string with LaTeX math formulas for the page.
        """
        os.makedirs(work_dir, exist_ok=True)
        page_prefix = os.path.join(work_dir, f"page_{page_num:03d}")
        logger.debug("Rendering scanned PDF page %d with pdftoppm", page_num)
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(DEFAULT_DPI), "-f", str(page_num), "-l", str(page_num), pdf_path, page_prefix],
            check=True,
            stderr=subprocess.DEVNULL,
            timeout=90,
        )

        png_candidates = [
            f for f in os.listdir(work_dir) if f.startswith(f"page_{page_num:03d}") and f.endswith(".png")
        ]
        if not png_candidates:
            return ""
        png_path = os.path.join(work_dir, png_candidates[0])
        pw, ph = cls.get_image_size(png_path)

        # Execute Tesseract TSV
        tess_bin = shutil.which("tesseract") or "/opt/homebrew/bin/tesseract" or "tesseract"
        tsv_proc = subprocess.run(
            [tess_bin, png_path, "stdout", "--psm", "1", "tsv"],
            capture_output=True,
            text=True,
            check=True,
            timeout=90,
        )
        words = cls._extract_ocr_words(tsv_proc.stdout)
        filtered_lines = cls._filter_ocr_lines(words, ph)
        if not filtered_lines:
            return ""

        # Count multi-column split lines (lines with gap >= 80px between adjacent words)
        split_lines_count = sum(
            1
            for ws in filtered_lines
            if any(int(ws[i + 1]["left"]) - int(ws[i]["right"]) >= 80 for i in range(len(ws) - 1))
        )
        if split_lines_count >= 3:
            col_left, col_right = cls._split_multi_column_lines(filtered_lines, pw)
            out_blocks = cls._lines_to_markdown(col_left) + cls._lines_to_markdown(col_right)
        else:
            out_blocks = cls._lines_to_markdown(filtered_lines)

        out_blocks = LayoutDetector.format_callout_boxes(out_blocks)
        out_blocks = LayoutDetector.detect_and_format_tables(out_blocks)
        out_blocks = LayoutDetector.format_figure_captions(out_blocks)

        md_result = "\n\n".join(out_blocks).strip()
        md_result = LayoutDetector.detect_and_format_lists(md_result)
        md_result = LayoutDetector.detect_and_format_code_blocks(md_result)
        return MathLaTeXConverter.process_text(md_result)

    # Backward-compatible alias
    process_scanned_page = parse_page_to_markdown
