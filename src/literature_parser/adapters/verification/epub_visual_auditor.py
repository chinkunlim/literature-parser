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
from typing import Any, Dict, List

from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.services.exporter.epub_exporter import EpubExporter
from literature_parser.services.utils.text_utils import (
    clean_typography_artifacts,
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
                md_files.extend(
                    sorted(
                        f
                        for f in c_dir.glob("*.md")
                        if not f.name.endswith(("_Verified.md", "_report.md"))
                    )
                )
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
                for c_md in c_dir.glob("*.md"):
                    if not c_md.name.endswith(("_Verified.md", "_report.md")):
                        mirror_target = md_mirror_dir / c_md.name
                        if mirror_target.exists():
                            mirror_target.write_text(
                                c_md.read_text(encoding="utf-8"), encoding="utf-8"
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
