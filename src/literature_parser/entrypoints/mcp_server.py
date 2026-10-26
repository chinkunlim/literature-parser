"""Model Context Protocol (MCP) Server for Literature Parser.

Provides tools for AI assistants (Claude Code, Antigravity, OpenCode, Open WebUI)
to inspect books, retrieve and update chapter content, log human corrections,
trigger EPUB recompilations, and generate automated regression suites.
Write/delete operations strictly enforce the `confirm: bool` safety guard.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from literature_parser.services.core.correction_service import CorrectionService
from literature_parser.services.core.web_data_service import WebDataService

logger = logging.getLogger(__name__)

mcp = MCPServer("literature-parser")
web_service = WebDataService()
correction_service = CorrectionService()


@mcp.tool()
def list_books() -> str:
    """Lists all processed books and documents in the output repository.

    Returns:
        JSON-formatted string listing all books and their chapter counts.
    """
    books = web_service.list_books()
    return json.dumps(books, ensure_ascii=False, indent=2)


@mcp.tool()
def get_book_chapters(book_id: str) -> str:
    """Retrieves list of chapters for a given book.

    Args:
        book_id: Directory name of the book in output/books/.

    Returns:
        JSON-formatted string listing chapters, word counts, and scores.
    """
    chapters = web_service.get_book_chapters(book_id)
    return json.dumps(chapters, ensure_ascii=False, indent=2)


@mcp.tool()
def get_chapter_markdown(book_id: str, chapter_id: str) -> str:
    """Retrieves Markdown source content of a specific chapter.

    Args:
        book_id: Directory name of the book.
        chapter_id: Directory name of the chapter.

    Returns:
        The Markdown text of the chapter.
    """
    data = web_service.get_chapter_markdown(book_id, chapter_id)
    return data["markdown"]


@mcp.tool()
def update_chapter_markdown(
    book_id: str,
    chapter_id: str,
    new_content: str,
    issue_type: str = "general_edit",
    user_notes: str = "",
    rebuild_epub: bool = True,
    confirm: bool = False,
) -> str:
    """Updates a chapter's Markdown content and logs a correction record.

    Modifying chapter files requires explicit confirmation.

    Args:
        book_id: Directory name of the book.
        chapter_id: Directory name of the chapter.
        new_content: Modified Markdown content.
        issue_type: Classification tag (e.g. ocr_typo, heading_level, table_layout).
        user_notes: Explanation of why this correction was made.
        rebuild_epub: Whether to automatically trigger EPUB rebuild.
        confirm: Safety flag. Must be set to True to execute file modifications.

    Returns:
        JSON-formatted string with operation status.
    """
    if not confirm:
        return json.dumps({
            "error": "Confirmation required. Set confirm=True to write changes.",
            "book_id": book_id,
            "chapter_id": chapter_id,
        })

    res = web_service.save_chapter_markdown(
        book_id=book_id,
        chapter_id=chapter_id,
        new_content=new_content,
        issue_type=issue_type,
        user_notes=user_notes,
        rebuild_epub=rebuild_epub,
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def rebuild_book_epub(book_id: str, confirm: bool = False) -> str:
    """Rebuilds the EPUB 3 archive for the specified book.

    Args:
        book_id: Directory name of the book.
        confirm: Safety flag. Must be True to execute recompilation.

    Returns:
        JSON-formatted string with the compiled EPUB path.
    """
    if not confirm:
        return json.dumps({"error": "Confirmation required. Set confirm=True to rebuild EPUB."})

    out_path = web_service.rebuild_book_epub(book_id)
    return json.dumps({"success": True, "output_epub": str(out_path)})


@mcp.tool()
def list_corrections(book_id: Optional[str] = None, issue_type: Optional[str] = None) -> str:
    """Lists recorded human corrections and issue diffs.

    Args:
        book_id: Optional filter by book directory name.
        issue_type: Optional filter by issue category.

    Returns:
        JSON-formatted string listing matching correction records.
    """
    records = correction_service.list_corrections(book_id=book_id, issue_type=issue_type)
    return json.dumps([r.to_dict() for r in records], ensure_ascii=False, indent=2)


@mcp.tool()
def generate_regression_tests(confirm: bool = False) -> str:
    """Generates an automated unit regression test suite from human corrections.

    Args:
        confirm: Safety flag. Must be True to generate the test file.

    Returns:
        JSON-formatted string with generation details.
    """
    if not confirm:
        return json.dumps({"error": "Confirmation required. Set confirm=True to generate test suite."})

    res = correction_service.generate_regression_tests()
    return json.dumps(res, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
