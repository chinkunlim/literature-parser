"""
Scanned Textbook Neural Layout & OCR Parser
===========================================
High-fidelity neural layout & OCR engine for scanned textbooks using Tesseract 5.5.2 TSV.
Renders pages at 300 DPI, splits multi-column reading order, strips running headers/footers,
and converts mathematical equations to LaTeX.
"""

import os
import re
import csv
import io
import shutil
import subprocess
from pathlib import Path
from book_processor.config import DEFAULT_DPI, FOOTER_NOISE_PATTERNS
from book_processor.utils.text_utils import clean_punctuation_spacing
from book_processor.parsers.math_latex import MathLaTeXConverter
from book_processor.parsers.layout_detector import LayoutDetector


class ScannedPDFParser:
    """Neural OCR & layout parser for scanned PDF textbook pages."""

    @staticmethod
    def get_image_size(img_path: str) -> tuple:
        sips_bin = shutil.which('sips') or '/usr/bin/sips'
        try:
            out = subprocess.check_output(
                [sips_bin, '-g', 'pixelWidth', '-g', 'pixelHeight', img_path],
                stderr=subprocess.DEVNULL,
                timeout=15
            ).decode('utf-8', errors='ignore')
            wm = re.search(r'pixelWidth:\s+(\d+)', out)
            hm = re.search(r'pixelHeight:\s+(\d+)', out)
            if wm and hm:
                return int(wm.group(1)), int(hm.group(1))
        except Exception:
            pass
        return 2200, 2800

    @staticmethod
    def is_running_header(line_words: list, line_text: str, top_ratio: float) -> bool:
        if top_ratio > 0.075:
            return False
        if len(line_words) > 6:
            return False
        clean = line_text.strip()
        if re.match(r'^(?:[ivxlcdm]+|\d+)\s*$', clean, re.I):
            return True
        if re.match(r'^(?:Chapter|Part|Section|Contents)\b', clean, re.I):
            return True
        if clean.isupper() and len(clean) < 40:
            return True
        if re.search(r'(?:CHAPTER|PART|\d{1,3}\s+[A-Z]|COREY|GROUPS|PROCESS)', line_text, re.I):
            return True
        return False

    @staticmethod
    def is_running_footer(line_words: list, line_text: str, top_ratio: float) -> bool:
        if top_ratio < 0.85:
            return False
        clean = line_text.strip()
        for pat in FOOTER_NOISE_PATTERNS:
            if re.search(pat, clean, re.I):
                return True
        if re.match(r'^(?:[ivxlcdm]+|\d+)\s*$', clean, re.I):
            return True
        if re.search(r'(?:[ivxlcdm]+|\d+)\s*/|/\s*(?:[ivxlcdm]+|\d+|contents|index)\b', clean, re.I):
            return True
        if clean.isupper() and len(clean) < 40 and any(k in clean.lower() for k in ('about the authors', 'contents', 'index')):
            return True
        return False

    @classmethod
    def parse_page_to_markdown(cls, pdf_path: str, page_num: int, work_dir: str) -> str:
        """
        Renders page to 300 DPI PNG, performs neural OCR & layout analysis,
        and returns structured Markdown with LaTeX math formulas.
        """
        os.makedirs(work_dir, exist_ok=True)
        page_prefix = os.path.join(work_dir, f'page_{page_num:03d}')
        subprocess.run(
            ['pdftoppm', '-png', '-r', str(DEFAULT_DPI), '-f', str(page_num), '-l', str(page_num), pdf_path, page_prefix],
            check=True, stderr=subprocess.DEVNULL, timeout=90
        )

        png_candidates = [f for f in os.listdir(work_dir) if f.startswith(f'page_{page_num:03d}') and f.endswith('.png')]
        if not png_candidates:
            return ''
        png_path = os.path.join(work_dir, png_candidates[0])
        pw, ph = cls.get_image_size(png_path)

        # Execute Tesseract TSV
        tess_bin = shutil.which('tesseract') or '/opt/homebrew/bin/tesseract' or 'tesseract'
        tsv_proc = subprocess.run(
            [tess_bin, png_path, 'stdout', '--psm', '1', 'tsv'],
            capture_output=True, text=True, check=True, timeout=90
        )
        tsv_text = tsv_proc.stdout

        reader = csv.DictReader(io.StringIO(tsv_text), delimiter='\t')
        words = []
        for r in reader:
            if r['level'] == '5':
                txt = r['text'].strip()
                try:
                    conf = float(r['conf'])
                except ValueError:
                    conf = -1.0
                if txt and conf >= 0:
                    words.append({
                        'text': txt,
                        'conf': conf,
                        'left': int(r['left']),
                        'top': int(r['top']),
                        'width': int(r['width']),
                        'height': int(r['height']),
                        'right': int(r['left']) + int(r['width']),
                        'bottom': int(r['top']) + int(r['height']),
                        'line_num': int(r['line_num']),
                        'par_num': int(r['par_num']),
                        'block_num': int(r['block_num'])
                    })

        raw_lines = {}
        for w in words:
            raw_lines.setdefault((w['block_num'], w['par_num'], w['line_num']), []).append(w)

        # 1. Filter running header and running footer
        filtered_lines = []
        for k in sorted(raw_lines.keys()):
            ws = sorted(raw_lines[k], key=lambda x: x['left'])
            line_txt = ' '.join(x['text'] for x in ws)
            top_ratio = min(x['top'] for x in ws) / ph
            if cls.is_running_header(ws, line_txt, top_ratio):
                continue
            if cls.is_running_footer(ws, line_txt, top_ratio):
                continue
            ws_clean = [x for x in ws if not (x['text'] in (':', '|', '¦') and x['width'] < 10)]
            if ws_clean:
                filtered_lines.append(ws_clean)

        if not filtered_lines:
            return ''

        # 2. Count multi-column split lines (lines with gap >= 80px between adjacent words)
        split_lines_count = 0
        for ws in filtered_lines:
            for i in range(len(ws) - 1):
                gap = ws[i + 1]['left'] - ws[i]['right']
                if gap >= 80:
                    split_lines_count += 1
                    break

        is_multi_col = split_lines_count >= 3

        def lines_to_markdown(lines_list):
            records = []
            for l in lines_list:
                text = ' '.join(x['text'] for x in l)
                text = clean_punctuation_spacing(text)
                avg_h = sum(x['height'] for x in l) / len(l)
                records.append((text, avg_h))

            paras = []
            curr_p = []
            for text, h in records:
                if re.match(r'^(?:CHAPTER|Chapter)\s+\d+', text, re.I):
                    if curr_p:
                        paras.append(' '.join(curr_p))
                        curr_p = []
                    paras.append(f'### {text}')
                elif re.match(r'^[•\-\*°©e]\s*', text):
                    if curr_p:
                        paras.append(' '.join(curr_p))
                        curr_p = []
                    bullet_content = re.sub(r'^[•\-\*°©e\s]+', '', text)
                    paras.append(f'- {bullet_content}')
                elif h > 45 and len(text) < 80 and not text.endswith('.'):
                    if curr_p:
                        paras.append(' '.join(curr_p))
                        curr_p = []
                    paras.append(f'## {text}')
                else:
                    if curr_p and curr_p[-1].endswith('-'):
                        curr_p[-1] = curr_p[-1][:-1] + text
                    else:
                        curr_p.append(text)
            if curr_p:
                paras.append(' '.join(curr_p))
            return paras

        if is_multi_col:
            col_left = []
            col_right = []
            for ws in filtered_lines:
                split_idx = -1
                for i in range(len(ws) - 1):
                    gap = ws[i + 1]['left'] - ws[i]['right']
                    if gap >= 80:
                        split_idx = i
                        break
                if split_idx != -1:
                    lp = ws[:split_idx + 1]
                    rp = ws[split_idx + 1:]
                    if lp:
                        col_left.append(lp)
                    if rp:
                        col_right.append(rp)
                else:
                    cx = (ws[0]['left'] + ws[-1]['right']) / 2
                    if cx < pw * 0.48:
                        col_left.append(ws)
                    elif cx > pw * 0.52:
                        col_right.append(ws)
                    else:
                        col_left.append(ws)
            out_blocks = lines_to_markdown(col_left) + lines_to_markdown(col_right)
        else:
            out_blocks = lines_to_markdown(filtered_lines)

        # Format sidebars / callout boxes
        out_blocks = LayoutDetector.format_callout_boxes(out_blocks)
        # Format tables
        out_blocks = LayoutDetector.detect_and_format_tables(out_blocks)
        # Format figure captions
        out_blocks = LayoutDetector.format_figure_captions(out_blocks)

        md_result = '\n\n'.join(out_blocks).strip()
        # Format squashed lists
        md_result = LayoutDetector.detect_and_format_lists(md_result)
        # Format code blocks
        md_result = LayoutDetector.detect_and_format_code_blocks(md_result)
        # Normalise math notation to LaTeX
        return MathLaTeXConverter.process_text(md_result)

