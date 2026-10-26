"""FastAPI Web Application Entrypoint for Book & Literature Processing Dashboard.

Exposes RESTful APIs for querying dashboard metrics, rendering PDF pages on-the-fly,
viewing/editing chapter Markdown, triggering background EPUB recompilation,
logging human corrections, and generating regression tests.
Mounts the static Single Page Application (SPA) located in the `web/` directory.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from literature_parser.config.settings import PROJECT_ROOT, load_config
from literature_parser.services.core.correction_service import CorrectionService
from literature_parser.services.core.web_data_service import WebDataService

logger = logging.getLogger(__name__)

cfg = load_config()
web_service = WebDataService()
correction_service = CorrectionService()

app = FastAPI(
    title="Literature Parser Dashboard & Review Studio",
    description="Local web interface and REST API for comparing PDFs with EPUBs and managing correction feedback.",
    version="1.0.0",
)

# CORS configuration allowing Open WebUI and local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8767",
        "http://localhost:8767",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChapterSaveRequest(BaseModel):
    """Payload for saving modified chapter content and recording user corrections."""

    markdown: str = Field(..., description="Updated Markdown content for the chapter")
    issue_type: str = Field("general_edit", description="Classification tag for the issue")
    user_notes: str = Field("", description="User notes or root cause explanation")
    rebuild_epub: bool = Field(True, description="Whether to rebuild the full EPUB after saving")


class DirectCorrectionRequest(BaseModel):
    """Payload for directly recording a correction without modifying files."""

    book_id: str
    chapter_id: str
    original_text: str
    corrected_text: str
    issue_type: str = "general_edit"
    user_notes: str = ""


@app.get("/api/dashboard", response_model=Dict[str, Any])
def api_get_dashboard() -> Dict[str, Any]:
    """Retrieves aggregated pipeline stats, book progress, and feedback counts.

    Returns:
        Dashboard metrics summary dictionary.
    """
    return web_service.get_dashboard_summary()


@app.get("/api/books")
def api_list_books() -> Dict[str, Any]:
    """Lists all processed books in the output directory.

    Returns:
        Dictionary containing list of book metadata.
    """
    books = web_service.list_books()
    return {"books": books}


@app.get("/api/books/{book_id}/chapters")
def api_get_book_chapters(book_id: str) -> Dict[str, Any]:
    """Retrieves all chapters for a given book.

    Args:
        book_id: Book directory name.

    Returns:
        Dictionary containing chapter items.
    """
    chapters = web_service.get_book_chapters(book_id)
    return {"book_id": book_id, "chapters": chapters}


@app.get("/api/books/{book_id}/chapters/{chapter_id}/markdown")
def api_get_chapter_markdown(book_id: str, chapter_id: str) -> Dict[str, Any]:
    """Retrieves Markdown source text for a specific chapter.

    Args:
        book_id: Book directory name.
        chapter_id: Chapter directory name.

    Returns:
        Dictionary containing markdown text and filename.
    """
    try:
        return web_service.get_chapter_markdown(book_id, chapter_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/api/books/{book_id}/chapters/{chapter_id}/markdown")
def api_save_chapter_markdown(
    book_id: str,
    chapter_id: str,
    payload: ChapterSaveRequest,
) -> Dict[str, Any]:
    """Saves updated Markdown, records correction diff, and triggers EPUB rebuild.

    Args:
        book_id: Book directory name.
        chapter_id: Chapter directory name.
        payload: Save request containing new markdown, issue tag, and notes.

    Returns:
        Status dictionary with correction record ID and EPUB compile status.
    """
    try:
        res = web_service.save_chapter_markdown(
            book_id=book_id,
            chapter_id=chapter_id,
            new_content=payload.markdown,
            issue_type=payload.issue_type,
            user_notes=payload.user_notes,
            rebuild_epub=payload.rebuild_epub,
        )
        return res
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to save chapter markdown: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/books/{book_id}/chapters/{chapter_id}/pdf/meta")
def api_get_chapter_pdf_meta(book_id: str, chapter_id: str) -> Dict[str, Any]:
    """Retrieves total page count and file information for chapter PDF.

    Args:
        book_id: Book directory name.
        chapter_id: Chapter directory name.

    Returns:
        Dictionary with PDF existence and total page count.
    """
    return web_service.get_chapter_pdf_meta(book_id, chapter_id)


@app.get("/api/books/{book_id}/chapters/{chapter_id}/pdf/page/{page_num}")
def api_render_pdf_page(
    book_id: str,
    chapter_id: str,
    page_num: int,
    dpi: int = Query(150, ge=72, le=300),
) -> Response:
    """Renders a single PDF page into PNG format on the fly.

    Args:
        book_id: Book directory name.
        chapter_id: Chapter directory name.
        page_num: 1-based page number.
        dpi: Render DPI resolution (default 150).

    Returns:
        PNG image streaming response.
    """
    try:
        png_bytes, total_pages = web_service.render_pdf_page(
            book_id=book_id,
            chapter_id=chapter_id,
            page_index=page_num - 1,
            dpi=dpi,
        )
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"X-Total-Pages": str(total_pages)},
        )
    except (FileNotFoundError, IndexError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get("/api/books/{book_id}/visual-diffs")
def api_get_visual_diffs(book_id: str) -> Dict[str, Any]:
    """Retrieves list of visual diff comparison samples.

    Args:
        book_id: Book directory name.

    Returns:
        Dictionary with list of available comparison samples.
    """
    samples = web_service.get_visual_diff_samples(book_id)
    return {"book_id": book_id, "samples": samples}


@app.get("/api/books/{book_id}/visual-diffs/{file_name}")
def api_get_visual_diff_image(book_id: str, file_name: str) -> FileResponse:
    """Serves a visual diff sample PNG image.

    Args:
        book_id: Book directory name.
        file_name: PNG filename.

    Returns:
        FileResponse serving the image.
    """
    img_path = web_service.books_dir / book_id / "visual_diff_samples" / file_name
    if not img_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(img_path, media_type="image/png")


@app.get("/api/books/{book_id}/epub-pages/{file_name}")
def api_get_epub_page_image(book_id: str, file_name: str) -> FileResponse:
    """Serves an EPUB rendered page PNG image.

    Args:
        book_id: Book directory name.
        file_name: PNG filename.

    Returns:
        FileResponse serving the image.
    """
    img_path = web_service.books_dir / book_id / "epub_pages" / file_name
    if not img_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(img_path, media_type="image/png")


@app.get("/api/books/{book_id}/epub/file")
def api_get_epub_file(book_id: str) -> FileResponse:
    """Downloads or streams the compiled EPUB 3 archive.

    Args:
        book_id: Book directory name.

    Returns:
        FileResponse with the .epub file.
    """
    book_dir = web_service.books_dir / book_id
    epubs = list(book_dir.glob("*.epub"))
    if not epubs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EPUB file not found")
    return FileResponse(
        epubs[0],
        media_type="application/epub+zip",
        filename=epubs[0].name,
    )


@app.post("/api/books/{book_id}/rebuild-epub")
def api_rebuild_epub(book_id: str) -> Dict[str, Any]:
    """Manually triggers recompilation of the book's EPUB 3 archive.

    Args:
        book_id: Book directory name.

    Returns:
        Dictionary with compilation status and output path.
    """
    try:
        out_path = web_service.rebuild_book_epub(book_id)
        return {"success": True, "output_epub": str(out_path)}
    except Exception as e:
        logger.error("Failed to rebuild EPUB: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/corrections")
def api_list_corrections(
    book_id: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Lists recorded user corrections and issue diffs.

    Args:
        book_id: Optional book filter.
        issue_type: Optional category filter.

    Returns:
        Dictionary with list of correction records.
    """
    records = correction_service.list_corrections(book_id=book_id, issue_type=issue_type)
    return {"corrections": [r.to_dict() for r in records]}


@app.post("/api/corrections")
def api_record_correction(payload: DirectCorrectionRequest) -> Dict[str, Any]:
    """Directly records a correction item.

    Args:
        payload: DirectCorrectionRequest parameters.

    Returns:
        Dictionary with created correction record.
    """
    rec = correction_service.record_correction(
        book_id=payload.book_id,
        chapter_id=payload.chapter_id,
        original_text=payload.original_text,
        corrected_text=payload.corrected_text,
        issue_type=payload.issue_type,
        user_notes=payload.user_notes,
    )
    return {"success": True, "correction": rec.to_dict()}


@app.delete("/api/corrections/{record_id}")
def api_delete_correction(record_id: str) -> Dict[str, Any]:
    """Deletes a correction record by ID.

    Args:
        record_id: UUID of record to delete.

    Returns:
        Status dictionary.
    """
    deleted = correction_service.delete_correction(record_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return {"success": True, "id": record_id}


@app.post("/api/corrections/generate-tests")
def api_generate_regression_tests() -> Dict[str, Any]:
    """Generates automated unit tests from recorded human corrections.

    Returns:
        Generation statistics and destination test file path.
    """
    return correction_service.generate_regression_tests()


# Mount Static Files from web/
web_static_dir = PROJECT_ROOT / "web"
if web_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def serve_index() -> HTMLResponse:
        """Serves the main single page application HTML.

        Returns:
            HTMLResponse containing web/index.html content.
        """
        index_file = web_static_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Literature Parser Web Dashboard</h1><p>Index file not found.</p>")
