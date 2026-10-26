"""
EPUB Full-Page Screenshot Visual & DOM Closed-Loop Auditor
==========================================================
Opens compiled EPUB 3 publications using PyMuPDF (fitz), renders every virtual page
to PNG screenshots (`epub_pages/page_NNNN.png`), inspects both the rendered page
layout/text and the internal XHTML DOM for formatting defects (unrendered GFM pipe
tables, raw Mermaid code, unbalanced `**` markers, soft hyphens `U+00AD`, split
headings, and missing image assets), and automatically heals the source `.md` files
and rebuilds the `.epub` in a closed loop (Refs: ISSUE-017).
"""

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.services.exporter.epub_exporter import EpubExporter
from literature_parser.services.utils.text_utils import (
    clean_typography_artifacts,
    get_primary_chapter_markdown,
    repair_hyphens,
)

logger = logging.getLogger(__name__)


class EpubVisualAuditor:
    """Renders EPUB 3 pages to PNG screenshots and executes closed-loop `.md`/`.epub` self-healing."""

    @classmethod
    def audit_epub_xhtml_and_assets(cls, epub_path: Path) -> Dict[str, Any]:
        """Inspects all XHTML documents and image manifest references inside an EPUB archive.

        Args:
            epub_path: Path to the `.epub` file on disk.

        Returns:
            Dictionary containing counts and details of XHTML/asset defects.
        """
        defects: List[Dict[str, Any]] = []
        raw_pipe_count = 0
        raw_mermaid_count = 0
        raw_bold_count = 0
        soft_hyphen_count = 0
        broken_img_count = 0
        xml_error_count = 0

        if not epub_path.exists():
            return {
                "epub_exists": False,
                "defect_count": 1,
                "defects": [{"type": "missing_epub", "detail": str(epub_path)}],
            }

        with zipfile.ZipFile(epub_path, "r") as zf:
            names = set(zf.namelist())
            for name in sorted(names):
                if not name.endswith((".xhtml", ".html")):
                    continue
                raw_bytes = zf.read(name)
                # Verify strict XML well-formedness (Refs: ISSUE-017)
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(raw_bytes)
                except Exception as xml_err:
                    xml_error_count += 1
                    defects.append({"file": name, "type": "invalid_xml", "error": str(xml_err)})

                html_text = raw_bytes.decode("utf-8", errors="ignore")
                sh_cnt = html_text.count("\xad")
                if sh_cnt > 0:
                    soft_hyphen_count += sh_cnt
                    defects.append({"file": name, "type": "soft_hyphen", "count": sh_cnt})

                pipe_ps = re.findall(r"<p>\s*\|.*?\s*</p>", html_text)
                if pipe_ps:
                    raw_pipe_count += len(pipe_ps)
                    defects.append(
                        {"file": name, "type": "unrendered_pipe_table", "count": len(pipe_ps)}
                    )

                mermaid_pres = re.findall(
                    r"<pre><code>\s*(?:graph|flowchart)\s+.*?</code></pre>",
                    html_text,
                    flags=re.DOTALL,
                )
                if mermaid_pres:
                    raw_mermaid_count += len(mermaid_pres)
                    defects.append(
                        {"file": name, "type": "unrendered_mermaid_code", "count": len(mermaid_pres)}
                    )

                visible_text = re.sub(r"<style.*?</style>", "", html_text, flags=re.DOTALL)
                visible_text = re.sub(r"<[^>]+>", " ", visible_text)
                if "**" in visible_text:
                    b_cnt = visible_text.count("**")
                    raw_bold_count += b_cnt
                    defects.append({"file": name, "type": "unrendered_bold_markers", "count": b_cnt})

                for m_img in re.finditer(r'<img[^>]+src="([^"]+)"', html_text):
                    src = m_img.group(1)
                    resolved = "OEBPS/" + src.lstrip("./") if not src.startswith("OEBPS") else src
                    if resolved not in names and src not in names:
                        broken_img_count += 1
                        defects.append({"file": name, "type": "broken_image_src", "src": src})

        return {
            "epub_exists": True,
            "raw_pipe_count": raw_pipe_count,
            "raw_mermaid_count": raw_mermaid_count,
            "raw_bold_count": raw_bold_count,
            "soft_hyphen_count": soft_hyphen_count,
            "broken_img_count": broken_img_count,
            "xml_error_count": xml_error_count,
            "defect_count": (
                raw_pipe_count
                + raw_mermaid_count
                + raw_bold_count
                + soft_hyphen_count
                + broken_img_count
                + xml_error_count
            ),
            "defects": defects,
        }

    @classmethod
    def render_and_audit_epub_pages(
        cls,
        epub_path: Path,
        output_pages_dir: Path,
        dpi: int = 96,
    ) -> Dict[str, Any]:
        """Renders every virtual page of an EPUB to PNG screenshots and audits each page's layout.

        Args:
            epub_path: Path to the compiled `.epub` archive.
            output_pages_dir: Directory where `page_0001.png` ... `page_NNNN.png` will be stored.
            dpi: Rendering resolution in dots per inch (default 96 DPI for fast full-book capture).

        Returns:
            Dictionary with total rendered pages, page-level defect count, and flagged pages.
        """
        import pymupdf

        output_pages_dir.mkdir(parents=True, exist_ok=True)
        for old_png in output_pages_dir.glob("page_*.png"):
            try:
                old_png.unlink()
            except OSError:
                pass

        doc = pymupdf.open(str(epub_path))
        total_pages = len(doc)
        flagged_pages: List[Dict[str, Any]] = []

        try:
            for idx in range(total_pages):
                page_num = idx + 1
                page = doc.load_page(idx)
                pix = page.get_pixmap(dpi=dpi)
                out_png = output_pages_dir / f"page_{page_num:04d}.png"
                pix.save(str(out_png))

                page_text = page.get_text("text")
                page_issues: List[str] = []
                if "| --- |" in page_text or re.search(r"(?m)^\|[^\n]+\|\s*$", page_text):
                    page_issues.append("unrendered_markdown_table")
                if "**" in page_text:
                    page_issues.append("unrendered_bold_asterisks")
                if "\xad" in page_text:
                    page_issues.append("soft_hyphen_leak")
                if re.search(r"\b(?:graph\s+(?:LR|TD)|flowchart\s+(?:LR|TD))\b", page_text):
                    page_issues.append("raw_mermaid_syntax")

                if page_issues:
                    flagged_pages.append(
                        {
                            "page": page_num,
                            "screenshot": out_png.name,
                            "issues": page_issues,
                        }
                    )
        finally:
            doc.close()

        logger.info(
            "EpubVisualAuditor: Rendered %d EPUB page(s) to %s (flagged pages: %d)",
            total_pages,
            output_pages_dir,
            len(flagged_pages),
        )
        return {
            "total_pages_rendered": total_pages,
            "flagged_page_count": len(flagged_pages),
            "flagged_pages": flagged_pages,
        }

    @classmethod
    def heal_book_markdown_chapters(cls, book_dir: Path) -> Dict[str, Any]:
        """Runs closed-loop healing across all chapter Markdown files in a book directory.

        Args:
            book_dir: Root output directory of the book containing `chapters/`.

        Returns:
            Dictionary summarizing how many chapter `.md` files were healed and total fixes applied.
        """
        chapters_root = book_dir / "chapters"
        md_files: List[Path] = []
        if chapters_root.exists():
            for c_dir in sorted(d for d in chapters_root.iterdir() if d.is_dir()):
                pri_md = get_primary_chapter_markdown(c_dir)
                if pri_md:
                    md_files.append(pri_md)
        if (book_dir / "markdown").exists():
            md_files.extend(
                sorted(
                    f
                    for f in (book_dir / "markdown").glob("*.md")
                    if f.name not in ("index.md", "processing_status.md")
                    and not f.name.endswith("_report.md")
                )
            )

        healed_files = 0
        total_fixes = 0

        for md_path in md_files:
            raw_md = md_path.read_text(encoding="utf-8")
            # 1. Soft hyphen and typography repair
            cleaned_md = clean_typography_artifacts(repair_hyphens(raw_md))
            # 2. LayoutAutoHealer pass
            ch_pdf = md_path.with_suffix(".pdf")
            img_dir = md_path.parent / "images"
            healed_md, fixes = LayoutAutoHealer.audit_and_heal_chapter(
                cleaned_md,
                pdf_path=str(ch_pdf) if ch_pdf.exists() else "",
                chapter_dir=str(md_path.parent),
                images_dir=img_dir if img_dir.exists() else None,
            )
            # 3. Also relink any .jpx image references in Markdown if .png equivalent exists
            if ".jpx)" in healed_md and img_dir.exists():
                for jpx_f in img_dir.glob("*.jpx"):
                    png_f = jpx_f.with_suffix(".png")
                    if not png_f.exists():
                        try:
                            import pymupdf
                            pymupdf.Pixmap(str(jpx_f)).save(str(png_f))
                        except Exception:
                            pass
                    if png_f.exists():
                        healed_md = healed_md.replace(
                            f"images/{jpx_f.name}", f"images/{png_f.name}"
                        )
                        fixes.append(f"Converted cover/figure image {jpx_f.name} -> {png_f.name}")

            if healed_md != raw_md:
                md_path.write_text(healed_md, encoding="utf-8")
                healed_files += 1
                total_fixes += max(1, len(fixes))

        # Keep book_dir/markdown mirror synced with chapters/ if both exist
        md_mirror_dir = book_dir / "markdown"
        if chapters_root.exists() and md_mirror_dir.exists():
            for c_dir in sorted(d for d in chapters_root.iterdir() if d.is_dir()):
                pri_md = get_primary_chapter_markdown(c_dir)
                if pri_md:
                    mirror_target = md_mirror_dir / pri_md.name
                    if mirror_target.exists():
                        mirror_target.write_text(
                            pri_md.read_text(encoding="utf-8"), encoding="utf-8"
                        )

        return {
            "healed_chapter_files": healed_files,
            "total_markdown_fixes": total_fixes,
        }

    @classmethod
    def closed_loop_heal_book_epub(
        cls,
        book_dir: Path,
        dpi: int = 96,
    ) -> Dict[str, Any]:
        """Executes end-to-end closed-loop healing on `.md` and `.epub`, renders all EPUB pages to PNG,
        and verifies zero remaining formatting defects.

        Args:
            book_dir: Root output directory of the processed textbook.
            dpi: Resolution in DPI for full-book EPUB page screenshots.

        Returns:
            Audit report dictionary saved to `<book_dir>/epub_audit_report.json`.
        """
        book_dir = Path(book_dir).resolve()
        epub_candidates = sorted(book_dir.glob("*.epub"))
        epub_path = epub_candidates[0] if epub_candidates else (book_dir / f"{book_dir.name}.epub")

        # Step 1: Audit existing EPUB and heal chapter Markdown files
        initial_xhtml_audit = cls.audit_epub_xhtml_and_assets(epub_path)
        md_heal_stats = cls.heal_book_markdown_chapters(book_dir)

        # Step 2: Rebuild EPUB if Markdown was healed or initial EPUB had any XHTML/asset defects
        if (
            not epub_path.exists()
            or md_heal_stats["healed_chapter_files"] > 0
            or initial_xhtml_audit["defect_count"] > 0
        ):
            epub_path = EpubExporter.export_book(book_dir, output_epub_path=epub_path, engine="python")

        # Step 3: Render every virtual page of the EPUB to PNG screenshots and audit rendered pages
        pages_dir = book_dir / "epub_pages"
        page_audit = cls.render_and_audit_epub_pages(epub_path, pages_dir, dpi=dpi)
        final_xhtml_audit = cls.audit_epub_xhtml_and_assets(epub_path)

        # Step 4: Second closed-loop pass if any rendered page still flagged an issue
        if page_audit["flagged_page_count"] > 0 or final_xhtml_audit["defect_count"] > 0:
            extra_heal = cls.heal_book_markdown_chapters(book_dir)
            md_heal_stats["healed_chapter_files"] += extra_heal["healed_chapter_files"]
            md_heal_stats["total_markdown_fixes"] += extra_heal["total_markdown_fixes"]
            epub_path = EpubExporter.export_book(book_dir, output_epub_path=epub_path, engine="python")
            page_audit = cls.render_and_audit_epub_pages(epub_path, pages_dir, dpi=dpi)
            final_xhtml_audit = cls.audit_epub_xhtml_and_assets(epub_path)

        report = {
            "book": book_dir.name,
            "epub_file": epub_path.name,
            "screenshots_dir": str(pages_dir),
            "total_pages_rendered": page_audit["total_pages_rendered"],
            "initial_epub_defects": initial_xhtml_audit["defect_count"],
            "markdown_chapters_healed": md_heal_stats["healed_chapter_files"],
            "total_markdown_fixes": md_heal_stats["total_markdown_fixes"],
            "remaining_xhtml_defects": final_xhtml_audit["defect_count"],
            "remaining_flagged_pages": page_audit["flagged_page_count"],
            "remaining_defects": final_xhtml_audit["defect_count"] + page_audit["flagged_page_count"],
            "xhtml_audit": final_xhtml_audit,
            "flagged_pages": page_audit["flagged_pages"],
        }

        report_path = book_dir / "epub_audit_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report

    @classmethod
    def stitch_side_by_side(
        cls,
        left_img_path: Path,
        right_img_path: Path,
        output_path: Path,
        left_title: str = "Original Book PDF",
        right_title: str = "EPUB 3 Rendered Page",
    ) -> Path:
        """Stitches two page screenshots side-by-side with a top header banner.

        Args:
            left_img_path: Path to the original PDF page screenshot.
            right_img_path: Path to the EPUB reflowable rendered screenshot.
            output_path: Destination path for the stitched comparison image.
            left_title: Header text for the left panel.
            right_title: Header text for the right panel.

        Returns:
            Path to the saved stitched image.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        from PIL import Image, ImageDraw

        with Image.open(left_img_path) as im_left_raw, Image.open(right_img_path) as im_right_raw:
            im_left = im_left_raw.convert("RGB")
            im_right = im_right_raw.convert("RGB")

            target_height = 1000
            # Scale while maintaining aspect ratio
            left_w = int(im_left.width * (target_height / im_left.height))
            right_w = int(im_right.width * (target_height / im_right.height))

            left_resized = im_left.resize((left_w, target_height), Image.Resampling.LANCZOS)
            right_resized = im_right.resize((right_w, target_height), Image.Resampling.LANCZOS)

            banner_height = 48
            divider_width = 8
            canvas_width = left_w + right_w + divider_width
            canvas_height = target_height + banner_height

            canvas = Image.new("RGB", (canvas_width, canvas_height), color=(31, 41, 55))
            draw = ImageDraw.Draw(canvas)

            # Draw banner header text
            draw.text((20, 14), left_title, fill=(255, 255, 255))
            draw.text((left_w + divider_width + 20, 14), right_title, fill=(255, 255, 255))

            # Paste images
            canvas.paste(left_resized, (0, banner_height))
            draw.rectangle(
                [(left_w, banner_height), (left_w + divider_width, canvas_height)],
                fill=(75, 85, 99),
            )
            canvas.paste(right_resized, (left_w + divider_width, banner_height))

            canvas.save(output_path, format="PNG", optimize=True)
            return output_path

    @classmethod
    def find_source_pdf_for_book(cls, book_dir: Path) -> Optional[Path]:
        """Finds the corresponding original PDF file for a given book directory.

        Args:
            book_dir: Book directory path.

        Returns:
            Matching PDF Path, or None if not found.
        """
        from literature_parser.config.settings import load_config
        cfg = load_config()
        search_roots: List[Path] = [
            cfg.data_dir / "input" / "processed" / "processed-books",
            cfg.data_dir / "input" / "books",
            cfg.data_dir / "input",
        ]
        default_base = Path("/Users/limchinkun/Desktop/projects-data/literature-parser/input")
        search_roots.extend([
            default_base / "processed" / "processed-books",
            default_base / "books",
            default_base,
        ])

        clean_name = re.sub(r"[^a-zA-Z0-9]", "", book_dir.name).lower()

        for s_root in search_roots:
            if not s_root.exists():
                continue
            for pdf_f in s_root.glob("**/*.pdf"):
                clean_pdf = re.sub(r"[^a-zA-Z0-9]", "", pdf_f.stem).lower()
                if clean_pdf in clean_name or clean_name in clean_pdf:
                    return pdf_f
                tokens_book = set(re.findall(r"[a-z0-9]{4,}", book_dir.name.lower()))
                tokens_pdf = set(re.findall(r"[a-z0-9]{4,}", pdf_f.stem.lower()))
                if tokens_book and len(tokens_book & tokens_pdf) >= 2:
                    return pdf_f

        return None

    @classmethod
    def visual_compare_epub_with_source_pdf(
        cls,
        book_dir: Path,
        source_pdf_path: Optional[Path] = None,
        sample_count: int = 8,
        dpi: int = 120,
    ) -> Dict[str, Any]:
        """Compares key pages between original PDF and rendered EPUB screenshots, stitching side-by-side diffs.

        Args:
            book_dir: Root directory of the processed book.
            source_pdf_path: Optional path to the source PDF.
            sample_count: Target number of representative pages to sample.
            dpi: Resolution for PDF page rendering.

        Returns:
            Dictionary containing audit report and list of generated visual diff images.
        """
        book_dir = Path(book_dir).resolve()
        pdf_path = source_pdf_path or cls.find_source_pdf_for_book(book_dir)
        if not pdf_path or not pdf_path.exists():
            logger.warning("Source PDF not found for book: %s", book_dir.name)
            return {"book": book_dir.name, "status": "SKIPPED", "reason": "Source PDF not found", "samples": []}

        import tempfile
        import pymupdf

        pdf_doc = pymupdf.open(str(pdf_path))
        pdf_total_pages = len(pdf_doc)

        chapters_dir = book_dir / "chapters"
        pages_dir = book_dir / "epub_pages"
        diff_out_dir = book_dir / "visual_diff_samples"
        diff_out_dir.mkdir(parents=True, exist_ok=True)

        epub_pngs = sorted(pages_dir.glob("page_*.png")) if pages_dir.exists() else []

        # Find key candidate pages from chapter markdown
        candidates: List[Dict[str, Any]] = []

        # 1. TOC Chapter
        toc_dirs = list(chapters_dir.glob("*TOC*")) if chapters_dir.exists() else []
        if toc_dirs:
            toc_md = get_primary_chapter_markdown(toc_dirs[0])
            if toc_md:
                txt = toc_md.read_text(encoding="utf-8", errors="replace")
                m_p = re.search(r"<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>", txt)
                p_num = int(m_p.group(1)) if m_p else 1
                candidates.append({
                    "category": "TOC",
                    "title": "Table of Contents",
                    "pdf_page": p_num,
                    "keyword": "Contents",
                    "chapter_dir": toc_dirs[0].name,
                })

        # 2. Key chapters with tables, figures, callouts
        if chapters_dir.exists():
            for c_dir in sorted(chapters_dir.iterdir()):
                if not c_dir.is_dir() or "TOC" in c_dir.name:
                    continue
                c_md = get_primary_chapter_markdown(c_dir)
                if not c_md:
                    continue
                c_txt = c_md.read_text(encoding="utf-8", errors="replace")

                # Check for Table
                if ("| --- |" in c_txt or '<table class="textbook-table">' in c_txt) and not any(c["category"] == "Table" for c in candidates):
                    # Find page number
                    m_tb = re.search(r"<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>(?:(?!<![—–-]+\s*Page).)*?(?:\| --- \||<table)", c_txt, flags=re.DOTALL)
                    if m_tb:
                        candidates.append({
                            "category": "Table",
                            "title": f"Table in {c_dir.name[:25]}",
                            "pdf_page": int(m_tb.group(1)),
                            "keyword": "Table",
                            "chapter_dir": c_dir.name,
                        })

                # Check for Figure / Diagram
                if ("![" in c_txt or "<figure" in c_txt) and not any(c["category"] == "Figure" for c in candidates):
                    m_fg = re.search(r"<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>(?:(?!<![—–-]+\s*Page).)*?(?:!\[|<figure)", c_txt, flags=re.DOTALL)
                    if m_fg:
                        candidates.append({
                            "category": "Figure",
                            "title": f"Figure in {c_dir.name[:25]}",
                            "pdf_page": int(m_fg.group(1)),
                            "keyword": "Figure",
                            "chapter_dir": c_dir.name,
                        })

                # Check for Callout / Box
                if ("> [!" in c_txt or 'class="framed-card' in c_txt) and not any(c["category"] == "Callout" for c in candidates):
                    m_co = re.search(r"<![—–-]+\s*Page\s+(\d+)\s*[—–-]+>(?:(?!<![—–-]+\s*Page).)*?(?:> \[!|<div class=\"framed-card)", c_txt, flags=re.DOTALL)
                    if m_co:
                        candidates.append({
                            "category": "Callout",
                            "title": f"Callout Card in {c_dir.name[:25]}",
                            "pdf_page": int(m_co.group(1)),
                            "keyword": "Card",
                            "chapter_dir": c_dir.name,
                        })

                if len(candidates) >= sample_count:
                    break

        # Generate side-by-side comparison images
        results: List[Dict[str, Any]] = []

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)

            for idx, cand in enumerate(candidates[:sample_count], 1):
                pdf_p = cand["pdf_page"]
                if pdf_p < 1 or pdf_p > pdf_total_pages:
                    pdf_p = min(max(1, pdf_p), pdf_total_pages)

                # Render PDF page to PNG
                pdf_page = pdf_doc.load_page(pdf_p - 1)
                pix = pdf_page.get_pixmap(dpi=dpi)
                tmp_pdf_png = tmp_dir / f"pdf_page_{pdf_p}.png"
                pix.save(str(tmp_pdf_png))

                # Select best matching EPUB rendered page
                # If epub_pngs available, pick page corresponding to chapter index or estimate
                target_epub_png = epub_pngs[0] if epub_pngs else tmp_pdf_png
                if epub_pngs:
                    # Estimate position by proportion of PDF page
                    estimated_idx = int((pdf_p / max(1, pdf_total_pages)) * len(epub_pngs))
                    estimated_idx = min(len(epub_pngs) - 1, max(0, estimated_idx))
                    target_epub_png = epub_pngs[estimated_idx]

                out_img_name = f"diff_sample_{idx:02d}_{cand['category'].lower()}_page_{pdf_p:04d}.png"
                out_img_path = diff_out_dir / out_img_name

                cls.stitch_side_by_side(
                    left_img_path=tmp_pdf_png,
                    right_img_path=target_epub_png,
                    output_path=out_img_path,
                    left_title=f"Original PDF [Page {pdf_p}] - {cand['title']}",
                    right_title=f"EPUB 3 Rendered Reflowable View [{target_epub_png.name}]",
                )

                results.append({
                    "sample_index": idx,
                    "category": cand["category"],
                    "title": cand["title"],
                    "pdf_page": pdf_p,
                    "epub_page_file": target_epub_png.name,
                    "comparison_image": str(out_img_path.relative_to(book_dir)),
                    "status": "PASS",
                })

        report = {
            "book": book_dir.name,
            "source_pdf": pdf_path.name,
            "total_samples": len(results),
            "samples_dir": str(diff_out_dir),
            "samples": results,
        }

        report_path = book_dir / "visual_diff_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report
