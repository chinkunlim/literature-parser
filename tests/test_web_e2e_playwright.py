"""
test_web_e2e_playwright.py - End-to-end browser automation tests via Playwright.

Verifies:
1. Sidebar collapse and re-expansion preserve layout coordinates (no negative offset, no offscreen drift).
2. The hamburger toggle button remains accessible at the left edge when collapsed.
3. localStorage persists sidebar collapse state across page reloads.
4. Small screens (< 900px) auto-collapse the sidebar on initial clean load.
5. Comparison view, layout modes (PDF only, split, editor only), and synchronized scroll controls.
"""

import socket
import threading
import time
import unittest
from typing import Any, Optional

import uvicorn
from playwright.sync_api import sync_playwright

from literature_parser.entrypoints.web_app import app


def _find_free_port() -> int:
    """Finds an unused TCP port on localhost.

    Returns:
        Available TCP port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _is_server_listening(host: str, port: int) -> bool:
    """Checks whether a TCP port is currently accepting connections.

    Args:
        host: Target host IP string.
        port: Target TCP port number.

    Returns:
        True if connection succeeded, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


class TestWebE2EPlaywright(unittest.TestCase):
    """Playwright E2E browser test suite for Web Studio."""

    server_thread: Optional[threading.Thread] = None
    server_port: int = 8767
    base_url: str = "http://127.0.0.1:8767"
    server_started_by_test: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        """Starts a background Uvicorn server if not already running on port 8767.

        Returns:
            None
        """
        if not _is_server_listening("127.0.0.1", 8767):
            cls.server_port = _find_free_port()
            cls.base_url = f"http://127.0.0.1:{cls.server_port}"
            config = uvicorn.Config(app=app, host="127.0.0.1", port=cls.server_port, log_level="warning")
            server = uvicorn.Server(config=config)
            cls.server_thread = threading.Thread(target=server.run, daemon=True)
            cls.server_thread.start()
            cls.server_started_by_test = True

            # Wait for server startup
            for _ in range(30):
                if _is_server_listening("127.0.0.1", cls.server_port):
                    break
                time.sleep(0.1)

    def test_sidebar_collapse_and_expand_geometry(self) -> None:
        """Verifies that collapsing the sidebar smoothly shifts it off-screen without displacing main viewport."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(self.base_url)
            page.wait_for_selector("#btn-sidebar-toggle")

            # 1. Initial State (1280x800)
            sb = page.locator("#sidebar").bounding_box()
            vp = page.locator("#main-viewport").bounding_box()
            btn = page.locator("#btn-sidebar-toggle").bounding_box()

            self.assertIsNotNone(sb)
            self.assertIsNotNone(vp)
            self.assertIsNotNone(btn)
            assert sb and vp and btn

            self.assertEqual(sb["x"], 0, "Sidebar should start at x=0")
            self.assertAlmostEqual(vp["x"], sb["width"], delta=2, msg="Viewport x should match sidebar width")
            self.assertAlmostEqual(vp["width"], 1280 - sb["width"], delta=2, msg="Viewport width should fill remainder")

            # 2. Click toggle button to collapse
            page.click("#btn-sidebar-toggle")
            time.sleep(0.35)

            sb_c = page.locator("#sidebar").bounding_box()
            vp_c = page.locator("#main-viewport").bounding_box()
            btn_c = page.locator("#btn-sidebar-toggle").bounding_box()

            self.assertIsNotNone(sb_c)
            self.assertIsNotNone(vp_c)
            self.assertIsNotNone(btn_c)
            assert sb_c and vp_c and btn_c

            self.assertLessEqual(sb_c["x"], -280, "Collapsed sidebar must slide off-screen to left")
            self.assertEqual(vp_c["x"], 0, "Collapsed viewport x must be exactly 0 (no negative shift)")
            self.assertEqual(vp_c["width"], 1280, "Collapsed viewport must expand to full window width (1280px)")
            self.assertGreaterEqual(btn_c["x"], 10, "Hamburger button must stay within visible left edge")
            self.assertLessEqual(btn_c["x"], 30, "Hamburger button must not wander into screen body")

            # 3. Click toggle button again to re-expand
            page.click("#btn-sidebar-toggle")
            time.sleep(0.35)

            sb_e = page.locator("#sidebar").bounding_box()
            vp_e = page.locator("#main-viewport").bounding_box()
            assert sb_e and vp_e

            self.assertEqual(sb_e["x"], 0, "Re-expanded sidebar must return to x=0")
            self.assertAlmostEqual(vp_e["x"], sb_e["width"], delta=2, msg="Re-expanded viewport x must restore")

            browser.close()

    def test_sidebar_local_storage_persistence(self) -> None:
        """Verifies that sidebar collapsed state is persisted in localStorage and restored across reloads."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(self.base_url)
            page.wait_for_selector("#btn-sidebar-toggle")

            # Collapse sidebar
            page.click("#btn-sidebar-toggle")
            time.sleep(0.35)

            storage_val = page.evaluate("localStorage.getItem('literature_parser_sidebar_collapsed')")
            self.assertEqual(storage_val, "1", "Collapse state should be saved as '1' in localStorage")

            # Reload page
            page.reload()
            page.wait_for_selector("#btn-sidebar-toggle")
            time.sleep(0.2)

            vp_after_reload = page.locator("#main-viewport").bounding_box()
            self.assertIsNotNone(vp_after_reload)
            assert vp_after_reload
            self.assertEqual(vp_after_reload["x"], 0, "Sidebar should remain collapsed after page reload")
            self.assertEqual(vp_after_reload["width"], 1280)

            # Re-expand sidebar
            page.click("#btn-sidebar-toggle")
            time.sleep(0.35)
            storage_val_expanded = page.evaluate("localStorage.getItem('literature_parser_sidebar_collapsed')")
            self.assertEqual(storage_val_expanded, "0", "Expanded state should be saved as '0' in localStorage")

            browser.close()

    def test_small_screen_auto_collapse_on_initial_load(self) -> None:
        """Verifies that small screens (< 900px wide) default to auto-collapsing the sidebar."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 840, "height": 600})
            page.goto(self.base_url)
            # Ensure clean localStorage state
            page.evaluate("localStorage.clear()")
            page.reload()
            page.wait_for_selector("#btn-sidebar-toggle")
            time.sleep(0.35)

            sb_small = page.locator("#sidebar").bounding_box()
            vp_small = page.locator("#main-viewport").bounding_box()
            self.assertIsNotNone(sb_small)
            self.assertIsNotNone(vp_small)
            assert sb_small and vp_small

            self.assertLessEqual(sb_small["x"], -280, "Sidebar should automatically collapse on screen < 900px")
            self.assertEqual(vp_small["x"], 0, "Small screen viewport should start at x=0")
            self.assertEqual(vp_small["width"], 840, "Small screen viewport should fill 840px width")

            browser.close()

    def test_comparison_view_and_layout_switchers(self) -> None:
        """Verifies switching to compare view, testing layout modes and sync scroll toggle button."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(self.base_url)
            page.wait_for_selector('.nav-item[data-view="compare"]')

            # 1. Switch to compare view
            page.click('.nav-item[data-view="compare"]')
            time.sleep(0.2)

            ws = page.locator("#split-workspace").bounding_box()
            pane_pdf = page.locator("#pane-pdf").bounding_box()
            pane_ed = page.locator("#pane-editor").bounding_box()

            self.assertIsNotNone(ws)
            self.assertIsNotNone(pane_pdf)
            self.assertIsNotNone(pane_ed)
            assert ws and pane_pdf and pane_ed

            self.assertGreater(pane_pdf["width"], 100)
            self.assertGreater(pane_ed["width"], 100)

            # 2. Test Layout Switcher (PDF Only)
            page.click("#btn-layout-pdf")
            time.sleep(0.15)
            pane_pdf_only = page.locator("#pane-pdf").bounding_box()
            assert pane_pdf_only
            self.assertGreaterEqual(pane_pdf_only["width"], ws["width"] - 10)

            # 3. Test Layout Switcher (Editor Only)
            page.click("#btn-layout-editor")
            time.sleep(0.15)
            pane_ed_only = page.locator("#pane-editor").bounding_box()
            assert pane_ed_only
            self.assertGreaterEqual(pane_ed_only["width"], ws["width"] - 10)

            # 4. Restore Split
            page.click("#btn-layout-split")
            time.sleep(0.15)

            # 5. Test Sync Scroll Toggle Button
            sync_btn = page.locator("#btn-toggle-sync")
            self.assertIn("🔗 同步中", sync_btn.text_content() or "")
            page.click("#btn-toggle-sync")
            self.assertIn("🔓 獨立滾動", sync_btn.text_content() or "")
            page.click("#btn-toggle-sync")
            self.assertIn("🔗 同步中", sync_btn.text_content() or "")

            browser.close()


if __name__ == "__main__":
    unittest.main()
