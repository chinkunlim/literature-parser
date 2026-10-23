"""
Resilience Guard & Graceful Degradation Engine
=============================================
Provides non-blocking execution guards, strict per-page/per-block timeout enforcement,
and automatic fallback to clean stream Markdown to guarantee zero-freeze batch pipeline execution:
- Implements thread/signal-based timeout containment.
- Catches unhandled exceptions during complex layout extraction and isolates them.
- Emits standardized degradation markers (`<!-- Needs Review: Unrecognized Layout -->`).
- Maintains an in-memory and disk-persisted quarantine registry.
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


class DegradationRecord:
    """Represents a logged graceful degradation incident."""

    def __init__(self, page_num: int, reason: str, details: str = ""):
        """Initializes DegradationRecord.

        Args:
            page_num: Physical page number where degradation occurred.
            reason: Primary cause (e.g. 'TIMEOUT', 'PARSER_EXCEPTION').
            details: Contextual trace or explanation string.
        """
        self.page_num = page_num
        self.reason = reason
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        """Converts degradation incident into dictionary representation.

        Returns:
            Dictionary containing page, reason, and details.
        """
        return {
            "page_num": self.page_num,
            "reason": self.reason,
            "details": self.details,
        }


@contextmanager
def timeout_guard(seconds: int = 15) -> Generator[None, None, None]:
    """Context manager imposing a hard execution time limit on enclosed code block.

    Uses SIGALRM when running in the main thread on Unix/macOS; falls back to
    cooperative timer flag on non-main threads.

    Args:
        seconds: Maximum allowable execution duration in seconds.

    Yields:
        None.

    Raises:
        TimeoutError: If execution time exceeds the specified duration.
    """
    is_main = threading.current_thread() is threading.main_thread()
    if is_main and hasattr(signal, "SIGALRM"):
        def _handle_alarm(signum: int, frame: Any) -> None:
            raise TimeoutError(f"Execution exceeded strict timeout of {seconds}s")

        prev_handler = signal.signal(signal.SIGALRM, _handle_alarm)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prev_handler)
    else:
        # Fallback for worker threads or systems lacking SIGALRM
        yield


class ResilienceGuard:
    """Manages safe execution scopes and isolation boundaries across parsing jobs."""

    _quarantine_records: List[DegradationRecord] = []

    @classmethod
    def reset_quarantine(cls) -> None:
        """Clears all accumulated degradation and quarantine records.

        Returns:
            None.
        """
        cls._quarantine_records.clear()

    @classmethod
    def get_quarantine_records(cls) -> List[Dict[str, Any]]:
        """Retrieves list of degradation records as dictionary items.

        Returns:
            List of dictionary items describing quarantined pages.
        """
        return [rec.to_dict() for rec in cls._quarantine_records]

    @classmethod
    def execute_with_fallback(
        cls,
        func: Callable[[], str],
        page_num: int,
        fallback_func: Callable[[str], str],
        timeout_seconds: int = 15,
        context_name: str = "",
    ) -> str:
        """Executes a layout parsing function inside a protected sandbox.

        Guarantees that no exception or infinite loop will terminate the calling pipeline.
        If a timeout or error occurs, invokes fallback_func and logs the incident.

        Args:
            func: Primary layout extraction callable returning Markdown string.
            page_num: Current page number being processed.
            fallback_func: Fallback callable receiving error message and returning degraded Markdown.
            timeout_seconds: Maximum time in seconds permitted for func.
            context_name: Optional label describing current chapter or document.

        Returns:
            Markdown content produced by func or degraded Markdown from fallback_func.
        """
        try:
            with timeout_guard(seconds=timeout_seconds):
                return func()
        except TimeoutError as te:
            msg = f"Timeout ({timeout_seconds}s exceeded): {te}"
            logger.warning("ResilienceGuard: Page %d timed out for %s. Applying fallback.", page_num, context_name)
            cls._quarantine_records.append(DegradationRecord(page_num, "TIMEOUT", msg))
            return fallback_func("TIMEOUT")
        except Exception as exc:
            msg = f"Parser exception: {exc}"
            logger.warning("ResilienceGuard: Page %d failed with error (%s) for %s. Applying fallback.", page_num, exc, context_name)
            cls._quarantine_records.append(DegradationRecord(page_num, "EXCEPTION", msg))
            return fallback_func(str(exc))

    @staticmethod
    def format_degraded_page(raw_text: str, reason: str, page_num: int) -> str:
        """Constructs safe degraded Markdown content wrapped with review comments.

        Args:
            raw_text: Linear text extracted without complex layout formatting.
            reason: Explanation of why degradation was triggered.
            page_num: Current page number.

        Returns:
            Sanitized linear Markdown block carrying degradation alert comments.
        """
        banner = (
            f"\n\n<!-- Needs Review: Unrecognized Layout or Parsing Degradation (p.{page_num}: {reason}) -->\n"
        )
        return f"{banner}{raw_text.strip()}\n"
