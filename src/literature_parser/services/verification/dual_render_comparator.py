"""
Dual-Render Comparator & Tri-Vision Cross-Auditor
=================================================
Performs ultra-dense side-by-side visual and layout comparison between rendered
EPUB pages and original source PDF pages using:
1. Native Apple Vision OCR (pixel-exact geometry & keyword recall)
2. MiniCPM-V (layout artifacts, drop shadows, torn columns)
3. Llama 3.2 Vision (deep multimodal structural & semantic inspection)
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from literature_parser.services.verification.apple_vision_auditor import AppleVisionAuditor
from literature_parser.services.verification.epub_visual_auditor import (
    EpubVisualAuditor,
    PageAuditResult,
)

logger = logging.getLogger(__name__)


class DualRenderComparator:
    """Manages high-resolution page rendering and tri-engine cross-verification."""

    def __init__(
        self,
        apple_vision: Optional[AppleVisionAuditor] = None,
        minicpm_auditor: Optional[EpubVisualAuditor] = None,
        llama_auditor: Optional[EpubVisualAuditor] = None,
        dpi: int = 150,
    ) -> None:
        """Initializes the dual-render comparator.

        Args:
            apple_vision: Configured AppleVisionAuditor instance.
            minicpm_auditor: EpubVisualAuditor instance configured for MiniCPM-V.
            llama_auditor: EpubVisualAuditor instance configured for Llama 3.2 Vision.
            dpi: Rendering resolution DPI.
        """
        self.apple_vision = apple_vision or AppleVisionAuditor()
        self.minicpm_auditor = minicpm_auditor or EpubVisualAuditor(vision_model="minicpm-v:latest")
        self.llama_auditor = llama_auditor or EpubVisualAuditor(vision_model="llama3.2-vision:11b")
        self.dpi = dpi

    def render_pdf_pages(self, pdf_path: Path | str, output_dir: Path | str) -> List[Path]:
        """Renders every page of a PDF document to high-resolution PNG images.

        Args:
            pdf_path: Path to source PDF file.
            output_dir: Directory where rendered PNG images are stored.

        Returns:
            Sorted list of generated PNG file paths.
        """
        p_path = Path(pdf_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        if not p_path.exists():
            return []

        try:
            import pymupdf  # type: ignore
        except ImportError:
            logger.warning("PyMuPDF unavailable for rendering PDF pages %s", p_path)
            return []

        rendered_paths: List[Path] = []
        try:
            doc = pymupdf.open(str(p_path))
            for idx in range(len(doc)):
                page = doc[idx]
                pix = page.get_pixmap(dpi=self.dpi)
                out_file = out_d / f"pdf_page_{idx + 1:03d}.png"
                pix.save(str(out_file))
                rendered_paths.append(out_file)
            doc.close()
        except Exception as err:
            logger.warning("Failed rendering PDF %s: %s", p_path.name, err)

        return rendered_paths

    def find_chapter_epub_page_range(
        self,
        epub_doc: Any,
        chapter_name: str,
    ) -> Tuple[int, int]:
        """Determines the 0-indexed start and end page of a chapter inside an EPUB.

        Args:
            epub_doc: Open PyMuPDF document instance of the EPUB.
            chapter_name: Chapter directory name or stem (e.g. 'Ch01-Introduction...').

        Returns:
            Tuple of (start_page_idx, end_page_idx) inclusive.
        """
        total_epub_pages = len(epub_doc)
        try:
            toc = epub_doc.get_toc() or []
        except Exception:
            return (0, min(10, total_epub_pages - 1))

        # 1. Try matching chapter number (e.g. Ch01 -> Chapter 1)
        ch_num_match = re.search(r"ch0*(\d+)", chapter_name.lower())
        if ch_num_match:
            target_num = int(ch_num_match.group(1))
            for idx, item in enumerate(toc):
                title = str(item[1]).lower()
                num_m = re.search(r"chapter\s*0*(\d+)", title)
                if num_m and int(num_m.group(1)) == target_num:
                    start_p = max(0, int(item[2]) - 1)
                    end_p = total_epub_pages - 1
                    for next_item in toc[idx + 1:]:
                        if int(next_item[2]) > int(item[2]):
                            end_p = int(next_item[2]) - 2
                            break
                    return (start_p, max(start_p, min(total_epub_pages - 1, end_p)))

        # 2. Try keyword matching from TOC titles
        clean_ch = re.sub(r"[^a-z0-9]+", " ", chapter_name.lower()).strip()
        words = [w for w in clean_ch.split() if len(w) > 3 and w not in ("chapter", "part", "section")]

        for idx, item in enumerate(toc):
            t_clean = re.sub(r"[^a-z0-9]+", " ", str(item[1]).lower())
            if any(w in t_clean for w in words):
                start_p = max(0, int(item[2]) - 1)
                end_p = total_epub_pages - 1
                for next_item in toc[idx + 1:]:
                    if int(next_item[2]) > int(item[2]):
                        end_p = int(next_item[2]) - 2
                        break
                return (start_p, max(start_p, min(total_epub_pages - 1, end_p)))

        # Fallback for short/front-matter chapters without TOC entry: 0 to 1
        return (0, min(2, total_epub_pages - 1))

    def render_epub_pages(self, epub_path: Path | str, output_dir: Path | str) -> List[Path]:
        """Renders every page of an EPUB document to high-resolution PNG images.

        Args:
            epub_path: Path to target EPUB file.
            output_dir: Directory where rendered PNG images are stored.

        Returns:
            Sorted list of generated PNG file paths.
        """
        e_path = Path(epub_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        if not e_path.exists():
            return []

        try:
            import pymupdf  # type: ignore
        except ImportError:
            logger.warning("PyMuPDF unavailable for rendering EPUB pages %s", e_path)
            return []

        rendered_paths: List[Path] = []
        try:
            doc = pymupdf.open(str(e_path))
            for idx in range(len(doc)):
                page = doc[idx]
                pix = page.get_pixmap(dpi=self.dpi)
                out_file = out_d / f"epub_page_{idx + 1:04d}.png"
                pix.save(str(out_file))
                rendered_paths.append(out_file)
            doc.close()
        except Exception as err:
            logger.warning("Failed rendering EPUB %s: %s", e_path.name, err)

        return rendered_paths

    def render_epub_chapter_pages(
        self,
        epub_path: Path | str,
        chapter_name: str,
        output_dir: Path | str,
    ) -> List[Path]:
        """Renders only the pages belonging to a specific chapter from an EPUB document.

        Args:
            epub_path: Path to target EPUB file.
            chapter_name: Identifier for the chapter.
            output_dir: Directory where rendered PNG images are stored.

        Returns:
            List of generated PNG file paths for that chapter.
        """
        e_path = Path(epub_path)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        if not e_path.exists():
            return []

        try:
            import pymupdf  # type: ignore
        except ImportError:
            logger.warning("PyMuPDF unavailable for rendering EPUB %s", e_path)
            return []

        rendered_paths: List[Path] = []
        try:
            doc = pymupdf.open(str(e_path))
            start_p, end_p = self.find_chapter_epub_page_range(doc, chapter_name)
            for p_idx in range(start_p, end_p + 1):
                page = doc[p_idx]
                pix = page.get_pixmap(dpi=self.dpi)
                out_file = out_d / f"epub_page_{p_idx + 1:04d}.png"
                pix.save(str(out_file))
                rendered_paths.append(out_file)
            doc.close()
        except Exception as err:
            logger.warning("Failed rendering EPUB chapter %s from %s: %s", chapter_name, e_path.name, err)

        return rendered_paths

    def cross_audit_chapter(
        self,
        chapter_name: str,
        pdf_path: Path | str,
        epub_path: Path | str,
        eval_dir: Path | str,
        sample_stride: int = 1,
    ) -> Dict[str, Any]:
        """Runs side-by-side Tri-Vision audit comparing PDF pages and EPUB pages.

        Args:
            chapter_name: Identifier for the chapter.
            pdf_path: Path to source chapter PDF.
            epub_path: Path to exported EPUB.
            eval_dir: Directory to store images and audit records.
            sample_stride: Step stride across pages (1 = full dense scan of every page).

        Returns:
            Dictionary containing audit summary, tri-engine scores, and defect list.
        """
        ch_eval_d = Path(eval_dir) / chapter_name
        pdf_img_d = ch_eval_d / "pdf_pages"
        epub_img_d = ch_eval_d / "epub_pages"

        pdf_pages = self.render_pdf_pages(pdf_path, pdf_img_d)
        epub_pages = self.render_epub_chapter_pages(epub_path, chapter_name, epub_img_d)

        page_records: List[Dict[str, Any]] = []
        total_coverage: float = 0.0
        inspected_count = 0
        defects_detected: List[Dict[str, Any]] = []

        if not pdf_pages or not epub_pages:
            return {
                "chapter_name": chapter_name,
                "passed": False,
                "total_pdf_pages": len(pdf_pages),
                "total_epub_pages": len(epub_pages),
                "inspected_pages": 0,
                "average_content_coverage": 0.0,
                "defect_count": 1,
                "defects": [{"page_index": 0, "defects": ["Missing rendered PDF or EPUB pages"]}],
                "page_records": [],
            }

        expansion_ratio = max(1.0, len(epub_pages) / len(pdf_pages))

        # Full or sampled stride over PDF pages
        target_pdf_indices = range(0, len(pdf_pages), max(1, sample_stride))

        for pdf_idx in target_pdf_indices:
            pdf_img = pdf_pages[pdf_idx]
            # Map PDF page to EPUB window
            epub_win_start = int(pdf_idx * expansion_ratio)
            epub_win_end = min(len(epub_pages), int((pdf_idx + 1) * expansion_ratio) + 1)
            target_epub_pages = epub_pages[epub_win_start:epub_win_end] or [epub_pages[min(pdf_idx, len(epub_pages) - 1)]]

            inspected_count += 1

            # Engine 1: Apple Vision Native OCR coverage check
            # Extract PDF OCR text
            pdf_ocr = self.apple_vision.extract_page_ocr(pdf_img)
            pdf_text = pdf_ocr.get("full_text", "").lower()
            pdf_words = [
                w for w in re.findall(r"\b[a-z]{4,}\b", pdf_text)
                if w not in ("chapter", "figure", "table", "page", "section", "isbn")
            ]

            # Aggregate EPUB window OCR text
            epub_window_texts = []
            mini_ratings = []
            llama_ratings = []
            page_defects = []

            # 1. OCR Extraction across reflowed EPUB window pages
            for e_img in target_epub_pages:
                e_ocr = self.apple_vision.extract_page_ocr(e_img)
                epub_window_texts.append(e_ocr.get("full_text", "").lower())

            # 2. Engine 2 & 3: Visual inspection on primary representative page
            primary_e_img = target_epub_pages[0]
            mini_res = self.minicpm_auditor.audit_page_with_ollama(primary_e_img, pdf_idx)
            mini_ratings.append(mini_res.rating)
            if mini_res.has_defects and mini_res.defect_description:
                page_defects.append(f"MiniCPM-V [{primary_e_img.name}]: {mini_res.defect_description}")

            if not self.llama_auditor._model_failed:
                llama_res = self.llama_auditor.audit_page_with_ollama(primary_e_img, pdf_idx)
                llama_ratings.append(llama_res.rating)
                if llama_res.has_defects and llama_res.defect_description:
                    page_defects.append(f"Llama-Vision [{primary_e_img.name}]: {llama_res.defect_description}")

            combined_epub_words = set(re.findall(r"\b[a-z]{4,}\b", " ".join(epub_window_texts)))
            if pdf_words:
                matched = [w for w in pdf_words if w in combined_epub_words]
                cov_rate = round(len(matched) / len(pdf_words) * 100.0, 2)
            else:
                cov_rate = 100.0

            total_coverage += cov_rate

            if cov_rate < 70.0 and len(pdf_words) >= 15:
                missing_sample = [w for w in pdf_words if w not in combined_epub_words][:8]
                page_defects.append(f"Low content recall: {cov_rate}% (Missing keywords: {missing_sample})")

            avg_mini = round(sum(mini_ratings) / max(1, len(mini_ratings)), 1)
            avg_llama = round(sum(llama_ratings) / max(1, len(llama_ratings)), 1)

            if page_defects:
                defects_detected.append({
                    "pdf_page_index": pdf_idx + 1,
                    "defects": page_defects,
                    "pdf_image": str(pdf_img),
                    "epub_images": [str(p) for p in target_epub_pages],
                })

            page_records.append({
                "pdf_page": pdf_idx + 1,
                "coverage_rate": cov_rate,
                "minicpm_rating": avg_mini,
                "llama_rating": avg_llama,
                "defects": page_defects,
            })

        avg_cov = round(total_coverage / max(1, inspected_count), 2)
        overall_passed = (len(defects_detected) == 0) and (avg_cov >= 75.0)

        return {
            "chapter_name": chapter_name,
            "passed": overall_passed,
            "total_pdf_pages": len(pdf_pages),
            "total_epub_pages": len(epub_pages),
            "inspected_pages": inspected_count,
            "average_content_coverage": avg_cov,
            "defect_count": len(defects_detected),
            "defects": defects_detected,
            "page_records": page_records,
        }
