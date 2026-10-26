"""Service layer providing data access, rendering, and EPUB operations for web and MCP interfaces.

Handles document discovery, chapter reading/writing, PDF page rendering via PyMuPDF,
visual diff sample queries, and automated EPUB rebuild triggers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from literature_parser.config.settings import load_config
from literature_parser.services.core.correction_service import CorrectionService
from literature_parser.services.core.global_state import GlobalStateManager

logger = logging.getLogger(__name__)


class WebDataService:
    """Provides document query, PDF rendering, and chapter modification services."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initializes WebDataService with config paths.

        Args:
            data_dir: Optional root data folder. Defaults to config `data_dir`.
        """
        cfg = load_config()
        self._data_dir = Path(data_dir) if data_dir else cfg.data_dir
        self._output_dir = self._data_dir / "output"
        self._books_dir = self._output_dir / "books"
        self._correction_svc = CorrectionService(db_path=self._data_dir / "db" / "corrections.json")

    @property
    def books_dir(self) -> Path:
        """Returns the books output directory.

        Returns:
            Path to `<data_dir>/output/books`.
        """
        return self._books_dir

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Calculates and aggregates global status, progress rates, and correction metrics.

        Returns:
            Dictionary containing metrics, book cards, and feedback counts.
        """
        gsm = GlobalStateManager()
        state = gsm.get_all()
        books_data = state.get("books", {})

        if not books_data and self._books_dir.exists():
            gsm.sync_from_output_dir()
            state = gsm.get_all()
            books_data = state.get("books", {})

        total_docs = len(books_data)
        completed_docs = 0
        total_chapters = 0
        verified_chapters = 0
        failed_chapters = 0

        book_summaries: List[Dict[str, Any]] = []

        for title, info in sorted(books_data.items()):
            status = info.get("status", "PENDING")
            if status == "COMPLETE":
                completed_docs += 1
            ch_total = info.get("total_chapters", 0)
            ch_ver = info.get("verified", 0)
            ch_fail = info.get("failed", 0)

            total_chapters += ch_total
            verified_chapters += ch_ver
            failed_chapters += ch_fail

            book_dir = self._books_dir / title
            epub_files = list(book_dir.glob("*.epub")) if book_dir.exists() else []
            has_epub = len(epub_files) > 0
            epub_size = epub_files[0].stat().st_size if has_epub else 0

            book_summaries.append({
                "id": title,
                "title": title,
                "doc_type": info.get("doc_type", "book"),
                "status": status,
                "progress_pct": info.get("progress_pct", 0),
                "total_chapters": ch_total,
                "verified": ch_ver,
                "failed": ch_fail,
                "last_updated": info.get("last_updated", ""),
                "has_epub": has_epub,
                "epub_size_bytes": epub_size,
            })

        overall_pct = int(round((verified_chapters / total_chapters) * 100)) if total_chapters > 0 else 0
        corrections = self._correction_svc.list_corrections()

        return {
            "total_docs": total_docs,
            "completed_docs": completed_docs,
            "total_chapters": total_chapters,
            "verified_chapters": verified_chapters,
            "failed_chapters": failed_chapters,
            "overall_pct": overall_pct,
            "total_corrections": len(corrections),
            "last_updated": state.get("last_updated", ""),
            "books": book_summaries,
        }

    def list_books(self) -> List[Dict[str, Any]]:
        """Lists all books present in output directory with structural metadata.

        Returns:
            List of book descriptor dictionaries.
        """
        if not self._books_dir.exists():
            return []

        results: List[Dict[str, Any]] = []
        for p in sorted(self._books_dir.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                chapters_dir = p / "chapters"
                ch_count = len([c for c in chapters_dir.iterdir() if c.is_dir()]) if chapters_dir.exists() else 0
                epubs = list(p.glob("*.epub"))
                results.append({
                    "id": p.name,
                    "title": p.name,
                    "chapters_count": ch_count,
                    "has_epub": len(epubs) > 0,
                    "epub_name": epubs[0].name if epubs else None,
                })
        return results

    def get_book_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        """Returns the sorted list of chapters for a specific book.

        Args:
            book_id: Directory name of the book.

        Returns:
            List of chapter descriptor dictionaries.
        """
        chapters_dir = self._books_dir / book_id / "chapters"
        if not chapters_dir.exists():
            return []

        chapters: List[Dict[str, Any]] = []
        for ch in sorted(chapters_dir.iterdir()):
            if ch.is_dir() and not ch.name.startswith("."):
                md_files = list(ch.glob("*.md"))
                pdf_files = list(ch.glob("*.pdf"))
                audit_files = list(ch.glob("*_audit.json"))

                word_count = 0
                if md_files:
                    try:
                        word_count = len(md_files[0].read_text(encoding="utf-8").split())
                    except Exception:
                        pass

                audit_score = 100
                if audit_files:
                    try:
                        aud = json.loads(audit_files[0].read_text(encoding="utf-8"))
                        audit_score = aud.get("score", aud.get("final_score", 100))
                    except Exception:
                        pass

                chapters.append({
                    "id": ch.name,
                    "title": ch.name,
                    "has_markdown": len(md_files) > 0,
                    "has_pdf": len(pdf_files) > 0,
                    "word_count": word_count,
                    "audit_score": audit_score,
                })
        return chapters

    def get_chapter_markdown(self, book_id: str, chapter_id: str) -> Dict[str, Any]:
        """Reads and returns the Markdown content of a specific chapter.

        Args:
            book_id: Book directory name.
            chapter_id: Chapter directory name.

        Returns:
            Dictionary containing markdown string and metadata.

        Raises:
            FileNotFoundError: If the chapter or markdown file is missing.
        """
        ch_dir = self._books_dir / book_id / "chapters" / chapter_id
        if not ch_dir.exists():
            raise FileNotFoundError(f"Chapter directory not found: {ch_dir}")

        md_files = list(ch_dir.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"No Markdown file found in chapter: {ch_dir}")

        md_path = md_files[0]
        content = md_path.read_text(encoding="utf-8")
        return {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "file_name": md_path.name,
            "markdown": content,
        }

    def save_chapter_markdown(
        self,
        book_id: str,
        chapter_id: str,
        new_content: str,
        issue_type: str = "general_edit",
        user_notes: str = "",
        rebuild_epub: bool = True,
    ) -> Dict[str, Any]:
        """Saves edited Markdown, logs correction diff, and optionally rebuilds EPUB.

        Args:
            book_id: Book directory name.
            chapter_id: Chapter directory name.
            new_content: Modified Markdown text to overwrite existing chapter file.
            issue_type: Classification tag for the issue.
            user_notes: User notes explaining the modification.
            rebuild_epub: Whether to automatically trigger EPUB rebuilding.

        Returns:
            Dictionary with operation status and created correction record details.
        """
        ch_dir = self._books_dir / book_id / "chapters" / chapter_id
        if not ch_dir.exists():
            raise FileNotFoundError(f"Chapter directory not found: {ch_dir}")

        md_files = list(ch_dir.glob("*.md"))
        if not md_files:
            target_md = ch_dir / f"{chapter_id}.md"
            original_content = ""
        else:
            target_md = md_files[0]
            original_content = target_md.read_text(encoding="utf-8")

        # Save the updated Markdown content
        target_md.write_text(new_content, encoding="utf-8")
        logger.info("Saved updated chapter markdown at %s", target_md)

        # Record human correction feedback
        record = self._correction_svc.record_correction(
            book_id=book_id,
            chapter_id=chapter_id,
            original_text=original_content,
            corrected_text=new_content,
            issue_type=issue_type,
            user_notes=user_notes,
        )

        epub_status = "skipped"
        if rebuild_epub:
            try:
                self.rebuild_book_epub(book_id)
                epub_status = "rebuilt"
            except Exception as e:
                logger.error("Failed to rebuild EPUB for %s: %s", book_id, e)
                epub_status = f"failed: {e}"

        return {
            "success": True,
            "correction_id": record.id,
            "issue_type": record.issue_type,
            "epub_status": epub_status,
        }

    def rebuild_book_epub(self, book_id: str) -> Path:
        """Triggers full EPUB recompilation for the specified book.

        Args:
            book_id: Book directory name.

        Returns:
            Path to the compiled `.epub` archive.

        Raises:
            FileNotFoundError: If the book directory does not exist.
        """
        book_dir = self._books_dir / book_id
        if not book_dir.exists():
            raise FileNotFoundError(f"Book directory not found: {book_dir}")

        from literature_parser.services.exporter.epub_exporter import EpubExporter
        output_epub = EpubExporter.export_book(book_dir)
        logger.info("Successfully rebuilt EPUB at %s", output_epub)
        return output_epub

    def render_pdf_page(
        self,
        book_id: str,
        chapter_id: str,
        page_index: int,
        dpi: int = 150,
    ) -> Tuple[bytes, int]:
        """Renders a specific page of the chapter or book PDF as PNG image bytes.

        Args:
            book_id: Book directory name.
            chapter_id: Chapter directory name.
            page_index: 0-based page index.
            dpi: Resolution for rendering (default 150 DPI).

        Returns:
            Tuple of (PNG image bytes, total page count).

        Raises:
            FileNotFoundError: If no PDF is found for the chapter or book.
            IndexError: If page_index is out of bounds.
        """
        ch_dir = self._books_dir / book_id / "chapters" / chapter_id
        pdf_path: Optional[Path] = None

        if ch_dir.exists():
            ch_pdfs = list(ch_dir.glob("*.pdf"))
            if ch_pdfs:
                pdf_path = ch_pdfs[0]

        if pdf_path is None or not pdf_path.exists():
            # Fallback to processed input books directory
            processed_dir = self._data_dir / "input" / "processed" / "processed-books"
            if processed_dir.exists():
                for p in processed_dir.glob("*.pdf"):
                    clean_name = p.stem.replace(" ", "-").replace(",", "").replace("--", "-")
                    if book_id.startswith(clean_name[:20]):
                        pdf_path = p
                        break

        if pdf_path is None or not pdf_path.exists():
            raise FileNotFoundError(f"No PDF found for {book_id}/{chapter_id}")

        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        if page_index < 0 or page_index >= total_pages:
            doc.close()
            raise IndexError(f"Page index {page_index} out of bounds (total pages: {total_pages})")

        page = doc[page_index]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        doc.close()

        return png_bytes, total_pages

    def get_chapter_pdf_meta(self, book_id: str, chapter_id: str) -> Dict[str, Any]:
        """Retrieves page count and file existence metadata for a chapter PDF.

        Args:
            book_id: Book directory name.
            chapter_id: Chapter directory name.

        Returns:
            Metadata dictionary containing page count and PDF path info.
        """
        ch_dir = self._books_dir / book_id / "chapters" / chapter_id
        if not ch_dir.exists():
            return {"has_pdf": False, "total_pages": 0}

        ch_pdfs = list(ch_dir.glob("*.pdf"))
        if not ch_pdfs:
            return {"has_pdf": False, "total_pages": 0}

        pdf_path = ch_pdfs[0]
        try:
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            doc.close()
            return {"has_pdf": True, "total_pages": total_pages, "file_name": pdf_path.name}
        except Exception as e:
            logger.warning("Failed to inspect PDF %s: %s", pdf_path, e)
            return {"has_pdf": False, "total_pages": 0, "error": str(e)}

    def get_visual_diff_samples(self, book_id: str) -> List[Dict[str, Any]]:
        """Retrieves visual comparison samples and rendered EPUB pages for a book.

        Args:
            book_id: Book directory name.

        Returns:
            List of visual diff sample descriptors.
        """
        book_dir = self._books_dir / book_id
        diff_dir = book_dir / "visual_diff_samples"
        samples: List[Dict[str, Any]] = []

        if diff_dir.exists():
            for p in sorted(diff_dir.glob("*.png")):
                samples.append({
                    "id": p.stem,
                    "title": p.name,
                    "file_name": p.name,
                    "type": "stitched_comparison",
                    "url": f"/api/books/{book_id}/visual-diffs/{p.name}",
                })

        epub_pages_dir = book_dir / "epub_pages"
        if epub_pages_dir.exists():
            for ep in sorted(epub_pages_dir.glob("*.png"))[:30]:  # sample up to 30 pages
                samples.append({
                    "id": ep.stem,
                    "title": f"EPUB Rendered {ep.stem}",
                    "file_name": ep.name,
                    "type": "epub_rendered_page",
                    "url": f"/api/books/{book_id}/epub-pages/{ep.name}",
                })

        return samples
