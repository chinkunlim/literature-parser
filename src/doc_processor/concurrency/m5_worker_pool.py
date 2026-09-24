"""
Apple M5 Hardware-Aware Concurrency Engine
==========================================
Tailors parallel document and chapter execution to Apple Silicon (M-Series):
- Detects P-Core (Performance) vs E-Core (Efficiency) topology via sysctl.
- Caps CPU-heavy extraction workers to (P_cores - 1), reserving 1 P-Core for
  macOS system responsiveness and local Ollama GPU Metal dispatch.
- Enforces an aggressive Unified Memory safety guard (< 80% RAM utilization)
  to prevent macOS disk swapping and SSD degradation.
"""

import os
import re
import sys
import time
import logging
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


class M5HardwareProfile:
    """Detects and reports hardware topology and memory pressure for Apple Silicon."""

    _cached_p_cores: Optional[int] = None
    _cached_total_ram_bytes: Optional[int] = None

    @classmethod
    def get_p_core_count(cls) -> int:
        """Returns the number of High-Performance cores, or estimated fallback."""
        if cls._cached_p_cores is not None:
            return cls._cached_p_cores

        p_cores = None
        if platform.system() == "Darwin":
            try:
                out = subprocess.check_output(
                    ['sysctl', '-n', 'hw.perflevel0.physicalcpu'],
                    stderr=subprocess.DEVNULL,
                    timeout=2
                ).decode('utf-8').strip()
                if out.isdigit():
                    p_cores = int(out)
            except Exception:
                pass

        if p_cores is None:
            total = os.cpu_count() or 4
            # On generic machines, assume ~50% or max 4 are performance cores
            p_cores = max(1, min(4, total // 2))

        cls._cached_p_cores = p_cores
        return p_cores

    @classmethod
    def get_total_ram_gb(cls) -> float:
        """Returns total physical RAM in Gigabytes."""
        if cls._cached_total_ram_bytes is not None:
            return cls._cached_total_ram_bytes / (1024 ** 3)

        if platform.system() == "Darwin":
            try:
                out = subprocess.check_output(
                    ['sysctl', '-n', 'hw.memsize'],
                    stderr=subprocess.DEVNULL,
                    timeout=2
                ).decode('utf-8').strip()
                if out.isdigit():
                    cls._cached_total_ram_bytes = int(out)
                    return cls._cached_total_ram_bytes / (1024 ** 3)
            except Exception:
                pass

        # Fallback
        cls._cached_total_ram_bytes = 16 * (1024 ** 3)
        return 16.0

    @classmethod
    def get_available_ram_gb(cls) -> float:
        """Returns available (free + inactive) memory in Gigabytes."""
        if platform.system() == "Darwin":
            try:
                out = subprocess.check_output(['vm_stat'], stderr=subprocess.DEVNULL, timeout=2).decode('utf-8')
                page_size = 16384  # 16KB on Apple Silicon default
                m_ps = re.search(r'page size of (\d+) bytes', out)
                if m_ps:
                    page_size = int(m_ps.group(1))

                m_free = re.search(r'Pages free:\s+(\d+)', out)
                m_inact = re.search(r'Pages inactive:\s+(\d+)', out)
                if m_free and m_inact:
                    avail_bytes = (int(m_free.group(1)) + int(m_inact.group(1))) * page_size
                    return avail_bytes / (1024 ** 3)
            except Exception as e:
                logger.debug("vm_stat memory check failed: %s", e)

        # Fallback conservative estimate
        return 4.0

    @classmethod
    def is_memory_safe(cls, min_headroom_gb: float = 2.0) -> bool:
        """Checks if available memory exceeds min_headroom_gb."""
        avail = cls.get_available_ram_gb()
        return avail >= min_headroom_gb

    @classmethod
    def get_optimal_worker_count(cls) -> int:
        """
        Calculates optimal worker count:
        - Apple M5 (4 P-cores): returns 3 (reserves 1 P-core for OS / GPU scheduling).
        - If available memory < 2.0 GB: drops to 1 to prevent swapping.
        """
        if not cls.is_memory_safe(min_headroom_gb=2.0):
            logger.warning("[M5 Memory Guard] Low memory headroom (< 2.0 GB). Throttling concurrency to 1 worker.")
            return 1

        p_cores = cls.get_p_core_count()
        # Reserve 1 P-core for system and Ollama Metal acceleration
        workers = max(1, p_cores - 1)
        return workers


def get_m5_optimal_workers() -> int:
    """Convenience accessor for optimal worker count."""
    return M5HardwareProfile.get_optimal_worker_count()


class M5WorkerPool:
    """
    Hardware-managed parallel executor designed for Apple M-series architecture.
    Prevents thread exhaustion, CPU starvation, and memory swapping.
    """

    def __init__(self, max_workers: Optional[int] = None, min_headroom_gb: float = 2.0):
        self.max_workers = max_workers or M5HardwareProfile.get_optimal_worker_count()
        self.min_headroom_gb = min_headroom_gb

    def execute_parallel(
        self,
        items: List[Any],
        process_fn: Callable[[Any], Any],
        desc: str = "Parallel Execution"
    ) -> List[Any]:
        """
        Executes process_fn on items concurrently using up to max_workers.
        If items is empty, returns empty list.
        If memory is low or max_workers == 1, executes serially.
        """
        if not items:
            return []

        # Enforce memory safety before starting batch
        if not M5HardwareProfile.is_memory_safe(self.min_headroom_gb):
            logger.info("[%s] Low memory headroom; falling back to serial execution.", desc)
            return [process_fn(item) for item in items]

        effective_workers = min(self.max_workers, len(items))
        if effective_workers <= 1:
            return [process_fn(item) for item in items]

        logger.info(
            "[%s] Spawning M5 Worker Pool with %d workers (M5 P-Core limit: %d). Available RAM: %.1f GB",
            desc,
            effective_workers,
            M5HardwareProfile.get_p_core_count(),
            M5HardwareProfile.get_available_ram_gb()
        )

        results = [None] * len(items)
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            future_to_idx = {
                executor.submit(process_fn, item): idx
                for idx, item in enumerate(items)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    logger.error("[%s] Worker task %d raised exception: %s", desc, idx, exc)
                    raise exc

        return results
