"""
Pipelined Producer-Consumer Chapter Processor
============================================
Coordinates concurrent document processing across Apple Silicon M-series architecture:
- Stage 1 (CPU): Parallel PDF parsing, Markdown synthesis, and element cropping via CPU worker pool.
- Stage 2 (GPU/Ollama): Asynchronous semantic audit, verification, and diff proposal via dedicated Metal queue.
- Overlaps CPU and GPU workloads so that Stage 1 processes Chapter N+1 while Stage 2 audits Chapter N.
- Integrates M5 unified memory pressure guards (< 2.0 GB headroom auto-throttles).
"""

from __future__ import annotations

import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Optional

from literature_parser.services.concurrency.m5_worker_pool import (
    M5HardwareProfile,
    get_m5_optimal_workers,
)

logger = logging.getLogger(__name__)


class PipelinedChapterProcessor:
    """Two-stage overlapping pipeline executor for CPU parsing and GPU/Ollama audit."""

    def __init__(
        self,
        max_cpu_workers: Optional[int] = None,
        min_headroom_gb: float = 2.0,
    ):
        """Initializes the PipelinedChapterProcessor.

        Args:
            max_cpu_workers: Maximum parallel workers for CPU Stage 1 (default: M5 optimal workers).
            min_headroom_gb: Minimum available unified memory headroom in GB.
        """
        self.max_cpu_workers = max_cpu_workers or get_m5_optimal_workers()
        self.min_headroom_gb = min_headroom_gb

    def run_pipeline(
        self,
        items: List[Any],
        cpu_task_fn: Callable[[Any], Any],
        gpu_task_fn: Optional[Callable[[Any], Any]] = None,
        desc: str = "Pipelined Execution",
    ) -> List[Any]:
        """Runs the two-stage pipeline overlapping CPU processing and GPU reviewing.

        Args:
            items: List of document/chapter items to process.
            cpu_task_fn: Callable executing CPU-bound Stage 1 (PDF parsing & Markdown generation).
            gpu_task_fn: Optional callable executing GPU-bound Stage 2 (Ollama review & verification).
            desc: Description label for logging.

        Returns:
            List of completed results preserving the original order of items.
        """
        if not items:
            return []

        # If memory is low or single item or no GPU task, run serially or simple
        if not M5HardwareProfile.is_memory_safe(self.min_headroom_gb):
            logger.warning("[%s] Low memory headroom (%.1f GB). Running serially.", desc, M5HardwareProfile.get_available_ram_gb())
            results: List[Any] = []
            for item in items:
                res = cpu_task_fn(item)
                if gpu_task_fn:
                    res = gpu_task_fn(res)
                results.append(res)
            return results

        total_items = len(items)
        results: List[Any] = [None] * total_items
        gpu_queue: queue.Queue[Optional[tuple[int, Any]]] = queue.Queue()
        errors: List[Exception] = []

        # Worker for Stage 2 (GPU Ollama Queue Consumer)
        def _gpu_consumer_worker() -> None:
            while True:
                item_tuple = gpu_queue.get()
                if item_tuple is None:
                    gpu_queue.task_done()
                    break
                idx, intermediate = item_tuple
                try:
                    if gpu_task_fn is not None:
                        final_res = gpu_task_fn(intermediate)
                    else:
                        final_res = intermediate
                    results[idx] = final_res
                except Exception as exc:
                    logger.error("[%s] GPU Stage 2 failed on item %d: %s", desc, idx, exc)
                    errors.append(exc)
                finally:
                    gpu_queue.task_done()

        gpu_thread = threading.Thread(target=_gpu_consumer_worker, daemon=True)
        gpu_thread.start()

        # Producer: CPU Worker Pool
        effective_cpu_workers = min(self.max_cpu_workers, total_items)
        logger.info(
            "[%s] Starting pipeline with %d CPU workers and 1 GPU queue. Total items: %d",
            desc,
            effective_cpu_workers,
            total_items,
        )

        with ThreadPoolExecutor(max_workers=effective_cpu_workers) as executor:
            def _cpu_worker(idx: int, item: Any) -> None:
                try:
                    cpu_res = cpu_task_fn(item)
                    # Push immediately to GPU queue as soon as CPU task finishes
                    gpu_queue.put((idx, cpu_res))
                except Exception as exc:
                    logger.error("[%s] CPU Stage 1 failed on item %d: %s", desc, idx, exc)
                    errors.append(exc)

            futures = [
                executor.submit(_cpu_worker, idx, item)
                for idx, item in enumerate(items)
            ]
            for f in futures:
                f.result()

        # Signal GPU consumer to terminate when all queue items processed
        gpu_queue.put(None)
        gpu_thread.join()

        if errors:
            raise errors[0]

        return results
