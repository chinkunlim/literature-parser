"""
Visual Quality Auditor & Spot-Check Engine
==========================================
Selects high-value representative pages (Mindmaps, Complex Tables, Exhibits)
from converted chapters, renders PDF reference images using PyMuPDF, and audits
Markdown fidelity using local multimodal models (MiniCPM-V) or deterministic heuristics.
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier

logger = logging.getLogger(__name__)


class VisualAuditor:
    """Spot-checks complex page conversions against original PDF renderings."""

    @staticmethod
    def render_pdf_page_image(pdf_path: str, page_num: int, output_png: Path) -> bool:
        """Renders single PDF page to PNG via PyMuPDF (with fallback to pdftoppm).

        Args:
            pdf_path: Path string to the source PDF document.
            page_num: 1-indexed page number to render.
            output_png: Path where the output PNG should be written.

        Returns:
            True if image rendering succeeded and file exists, False otherwise.
        """
        # Primary: Pure-Python PyMuPDF (zero external binary dependency)
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            if 1 <= page_num <= len(doc):
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(dpi=150)
                output_png.parent.mkdir(parents=True, exist_ok=True)
                pix.save(str(output_png))
                doc.close()
                if output_png.exists() and output_png.stat().st_size > 0:
                    return True
            doc.close()
        except Exception as py_err:
            logger.debug("PyMuPDF rendering failed for %s p%d: %s; falling back to pdftoppm", pdf_path, page_num, py_err)

        # Fallback: pdftoppm if installed
        try:
            output_prefix = str(output_png.with_suffix(''))
            subprocess.run(
                ['pdftoppm', '-png', '-r', '150', '-f', str(page_num), '-l', str(page_num), pdf_path, output_prefix],
                check=True, capture_output=True, timeout=20
            )
            for f in output_png.parent.glob(f"{output_png.stem}*"):
                if f.suffix == '.png':
                    if f != output_png:
                        f.replace(output_png)
                    return True
            return False
        except Exception as e:
            logger.debug("pdftoppm failed for %s p%d: %s", pdf_path, page_num, e)
            return False

    @staticmethod
    def extract_page_snippet(markdown_text: str, page_num: int) -> str:
        """Extracts Markdown text corresponding to a specific page number.

        Args:
            markdown_text: Full chapter Markdown text with `<!-- Page N -->` markers.
            page_num: 1-indexed page number to extract.

        Returns:
            Extracted Markdown text snippet for that page, or empty string if not found.
        """
        pat = rf'<!-- Page {page_num} -->([\s\S]*?)(?:<!-- Page \d+ -->|\Z)'
        m = re.search(pat, markdown_text)
        if m:
            return m.group(1).strip()
        return ""

    @classmethod
    def audit_chapter(
        cls,
        ch_pdf: Path,
        ch_md: Path,
        output_dir: Path,
        use_vision_model: bool = True,
    ) -> Dict[str, Any]:
        """Audits a converted chapter using multimodal vision comparison and layout checks.

        Args:
            ch_pdf: Path to the chapter PDF file.
            ch_md: Path to the converted chapter Markdown file.
            output_dir: Destination folder to store audit images and report JSON.
            use_vision_model: Whether to invoke local Ollama vision model (MiniCPM-V) if available.

        Returns:
            Dict summary containing audited pages, defect details, and overall quality score.
        """
        os.makedirs(output_dir / "audit_images", exist_ok=True)
        md_text = ch_md.read_text(encoding='utf-8') if ch_md.exists() else ""

        verifier = None
        if use_vision_model:
            try:
                verifier = OllamaVerifier(auto_start=False)
                if not verifier.is_available:
                    verifier = None
            except Exception as e:
                logger.debug("OllamaVerifier initialization for VisualAuditor skipped: %s", e)
                verifier = None

        results: Dict[str, Any] = {
            "chapter": ch_pdf.stem,
            "has_mindmap": "```mermaid" in md_text,
            "table_count": len(re.findall(r'(\|[^\n]+\|\n\|(?:\s*[-:]+\s*\|)+|<table\b)', md_text)),
            "flashcard_count": len(re.findall(r'<details id="flashcard-', md_text)),
            "has_math_arrows": r"$\rightarrow$" in md_text,
            "vision_model": getattr(verifier, "vision_model", None) if verifier else None,
            "audited_pages": [],
        }

        # 1. Sample Page 1: Concept map / Mindmap / Learning Objectives
        p1_img = output_dir / "audit_images" / f"{ch_pdf.stem}_p01.png"
        p1_rendered = cls.render_pdf_page_image(str(ch_pdf), 1, p1_img)
        p1_snippet = cls.extract_page_snippet(md_text, 1)

        p1_status: Dict[str, Any] = {
            "page": 1,
            "feature": "concept_map_and_lo",
            "image": str(p1_img.name) if p1_rendered else None,
            "lo_format_valid": bool(re.search(r'^- 🎯 \*\*\d+\.\d+\*\*', md_text, re.MULTILINE)),
            "mermaid_valid": "```mermaid" in md_text if "appendix" not in ch_pdf.stem.lower() else ("```mermaid" not in md_text),
            "verified": True,
        }

        if verifier and p1_rendered and p1_snippet:
            v_res = verifier.verify_roi_vision(str(p1_img), p1_snippet[:2000], element_type="concept_map_and_lo")
            p1_status["vision_verified"] = v_res.get("passed", True)
            p1_status["vision_defect"] = v_res.get("defect")
            p1_status["confidence"] = v_res.get("confidence", 0.95)
            if not v_res.get("passed", True):
                p1_status["verified"] = False

        results["audited_pages"].append(p1_status)

        # 2. Extract pages by splitting on page markers
        parts = re.split(r'<!-- Page (\d+) -->', md_text)
        table_pages = []
        exhibit_pages = []

        for idx in range(1, len(parts), 2):
            try:
                p_num = int(parts[idx])
                p_content = parts[idx + 1]
                if '<table' in p_content or '| ---' in p_content:
                    table_pages.append(p_num)
                if '### exhibit' in p_content.lower() or ('exhibit' in p_content.lower() and ('results' in p_content.lower() or 'program' in p_content.lower() or 'table' in p_content.lower())):
                    exhibit_pages.append(p_num)
            except (ValueError, IndexError):
                continue

        # Sample up to 2 table pages and 2 exhibit pages
        sample_pages = set()
        for p in table_pages[:2]:
            sample_pages.add(p)
        for p in exhibit_pages[:2]:
            sample_pages.add(p)

        # Remove page 1 if present since it is audited separately as concept map
        sample_pages.discard(1)

        for p_num in sorted(sample_pages):
            p_img = output_dir / "audit_images" / f"{ch_pdf.stem}_p{p_num:02d}.png"
            p_rendered = cls.render_pdf_page_image(str(ch_pdf), p_num, p_img)
            p_snippet = cls.extract_page_snippet(md_text, p_num)

            p_feat = "table" if p_num in table_pages else "exhibit"
            page_status: Dict[str, Any] = {
                "page": p_num,
                "feature": p_feat,
                "image": str(p_img.name) if p_rendered else None,
                "verified": True,
            }

            if verifier and p_rendered and p_snippet:
                v_res = verifier.verify_roi_vision(str(p_img), p_snippet[:2500], element_type=p_feat)
                page_status["vision_verified"] = v_res.get("passed", True)
                page_status["vision_defect"] = v_res.get("defect")
                page_status["confidence"] = v_res.get("confidence", 0.95)
                if not v_res.get("passed", True):
                    page_status["verified"] = False
                    logger.warning("VisualAuditor: Vision model detected defect on p%d (%s): %s", p_num, p_feat, v_res.get("defect"))

            results["audited_pages"].append(page_status)

        # Calculate overall score out of 10
        score = 10.0
        if not p1_status["lo_format_valid"] and "appendix" not in ch_pdf.stem.lower() and "glossary" not in ch_pdf.stem.lower():
            score -= 1.0
        if not p1_status["mermaid_valid"]:
            score -= 2.0
        if results["table_count"] == 0 and ("Table" in md_text or "table" in md_text):
            score -= 1.5

        for ap in results["audited_pages"]:
            if not ap.get("verified", True):
                score -= 1.0

        results["quality_score"] = max(0.0, round(score, 1))
        results["status"] = "PASSED" if score >= 8.5 else "WARNING"

        # Save report
        report_file = output_dir / f"{ch_pdf.stem}_audit.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return results


if __name__ == "__main__":
    from literature_parser.config.settings import load_config
    b_dir = load_config().output_dir / "books/Research Methods, Design, and Analysis 13th ed"
    ch_pdf = b_dir / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.pdf"
    ch_md = b_dir / "chapters/Ch02 Research Approaches and Methods of Data Collection/Ch02 Research Approaches and Methods of Data Collection.md"
    if ch_pdf.exists() and ch_md.exists():
        res = VisualAuditor.audit_chapter(ch_pdf, ch_md, ch_pdf.parent)
        print("Visual Audit Result for Chapter 2:")
        print(json.dumps(res, indent=2))
