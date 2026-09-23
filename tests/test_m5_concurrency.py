"""
Tests for Apple M5 Hardware-Aware Concurrency Engine
====================================================
"""

import unittest
from unittest.mock import patch
from book_processor.concurrency.m5_worker_pool import (
    M5HardwareProfile,
    M5WorkerPool,
    get_m5_optimal_workers
)


class TestM5Concurrency(unittest.TestCase):

    def test_p_core_detection(self):
        """Verify P-Core detection returns a positive integer."""
        p_cores = M5HardwareProfile.get_p_core_count()
        self.assertIsInstance(p_cores, int)
        self.assertGreaterEqual(p_cores, 1)

    def test_total_ram_gb(self):
        """Verify total RAM is positive and within realistic workstation range."""
        ram_gb = M5HardwareProfile.get_total_ram_gb()
        self.assertIsInstance(ram_gb, float)
        self.assertGreaterEqual(ram_gb, 4.0)

    def test_available_ram_gb(self):
        """Verify available RAM is positive."""
        avail_gb = M5HardwareProfile.get_available_ram_gb()
        self.assertIsInstance(avail_gb, float)
        self.assertGreaterEqual(avail_gb, 0.0)

    def test_optimal_worker_count(self):
        """Verify optimal worker count leaves 1 core free and respects M5 3-worker limit."""
        workers = get_m5_optimal_workers()
        self.assertGreaterEqual(workers, 1)
        # On a 4 P-core machine, workers should be 3
        if M5HardwareProfile.get_p_core_count() == 4 and M5HardwareProfile.is_memory_safe():
            self.assertEqual(workers, 3)

    def test_worker_pool_execution_order(self):
        """Verify M5WorkerPool parallel execution preserves task ordering."""
        pool = M5WorkerPool(max_workers=3)
        items = [1, 2, 3, 4, 5]
        results = pool.execute_parallel(items, lambda x: x * 2, desc="Test Task")
        self.assertEqual(results, [2, 4, 6, 8, 10])

    def test_worker_pool_empty_items(self):
        """Verify empty items list returns empty list."""
        pool = M5WorkerPool(max_workers=3)
        results = pool.execute_parallel([], lambda x: x)
        self.assertEqual(results, [])

    @patch.object(M5HardwareProfile, 'is_memory_safe', return_value=False)
    def test_worker_pool_low_memory_serial_fallback(self, mock_mem):
        """Verify pool falls back to serial execution when memory headroom is low."""
        pool = M5WorkerPool(max_workers=4)
        items = ['a', 'b', 'c']
        results = pool.execute_parallel(items, lambda s: s.upper(), desc="Low Mem Task")
        self.assertEqual(results, ['A', 'B', 'C'])


if __name__ == '__main__':
    unittest.main()
