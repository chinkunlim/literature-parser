"""Unit tests for ResilienceGuard and Graceful Degradation Engine."""

import unittest
from literature_parser.adapters.guards.resilience_guard import (
    DegradationRecord,
    ResilienceGuard,
    timeout_guard,
)


class TestResilienceGuard(unittest.TestCase):
    """Verifies non-blocking execution, timeout containment, and graceful degradation."""

    def setUp(self):
        ResilienceGuard.reset_quarantine()

    def test_execute_with_fallback_success(self):
        """Verifies normal execution proceeds cleanly when no errors occur."""
        def _normal_parse():
            return "## Section 1\nClean body prose."

        def _fallback(reason):
            return f"Degraded: {reason}"

        result = ResilienceGuard.execute_with_fallback(
            func=_normal_parse,
            page_num=1,
            fallback_func=_fallback,
            timeout_seconds=5,
        )
        self.assertIn("Clean body prose", result)
        self.assertEqual(len(ResilienceGuard.get_quarantine_records()), 0)

    def test_execute_with_fallback_on_exception(self):
        """Verifies unhandled parser exceptions are caught and fallback is returned."""
        def _buggy_parse():
            raise ZeroDivisionError("Simulated parser catastrophic failure")

        def _fallback(reason):
            return ResilienceGuard.format_degraded_page("Raw text stream", reason, 42)

        result = ResilienceGuard.execute_with_fallback(
            func=_buggy_parse,
            page_num=42,
            fallback_func=_fallback,
            timeout_seconds=5,
            context_name="TestChapter",
        )
        self.assertIn("Needs Review: Unrecognized Layout or Parsing Degradation", result)
        self.assertIn("Raw text stream", result)

        records = ResilienceGuard.get_quarantine_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["page_num"], 42)
        self.assertEqual(records[0]["reason"], "EXCEPTION")

    def test_execute_with_fallback_on_timeout(self):
        """Verifies that infinite loops or freezing code times out safely."""
        import time

        def _infinite_loop():
            # Trigger timeout
            time.sleep(1.5)
            return "Should not finish"

        def _fallback(reason):
            return ResilienceGuard.format_degraded_page("Partial text", reason, 7)

        result = ResilienceGuard.execute_with_fallback(
            func=_infinite_loop,
            page_num=7,
            fallback_func=_fallback,
            timeout_seconds=1,  # 1s hard limit
            context_name="SlowChapter",
        )
        self.assertIn("Needs Review", result)
        self.assertIn("TIMEOUT", result)

        records = ResilienceGuard.get_quarantine_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["page_num"], 7)
        self.assertEqual(records[0]["reason"], "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
