"""Unit tests for MCP server tools and safety confirmation guards."""

import json
import unittest
from unittest.mock import patch

from literature_parser.entrypoints.mcp_server import (
    generate_regression_tests,
    list_books,
    list_corrections,
    rebuild_book_epub,
    update_chapter_markdown,
)


class TestMCPServer(unittest.TestCase):
    """Verifies that MCP tools query correctly and require confirmation on write actions."""

    def test_list_books_tool(self):
        """Verifies list_books returns valid JSON string."""
        raw = list_books()
        data = json.loads(raw)
        self.assertIsInstance(data, list)

    def test_update_chapter_requires_confirm(self):
        """Verifies update_chapter_markdown blocks execution when confirm is False."""
        res_raw = update_chapter_markdown(
            book_id="TestBook",
            chapter_id="Ch01",
            new_content="# New text",
            confirm=False,
        )
        data = json.loads(res_raw)
        self.assertIn("error", data)
        self.assertIn("Confirmation required", data["error"])

    def test_rebuild_epub_requires_confirm(self):
        """Verifies rebuild_book_epub blocks execution when confirm is False."""
        res_raw = rebuild_book_epub(book_id="TestBook", confirm=False)
        data = json.loads(res_raw)
        self.assertIn("error", data)
        self.assertIn("Confirmation required", data["error"])

    def test_generate_regression_tests_requires_confirm(self):
        """Verifies generate_regression_tests blocks execution when confirm is False."""
        res_raw = generate_regression_tests(confirm=False)
        data = json.loads(res_raw)
        self.assertIn("error", data)
        self.assertIn("Confirmation required", data["error"])

    def test_list_corrections_tool(self):
        """Verifies list_corrections returns valid JSON string."""
        raw = list_corrections()
        data = json.loads(raw)
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
