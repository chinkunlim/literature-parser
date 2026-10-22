"""
Concurrency & Hardware Optimization Package
===========================================
"""

from .m5_worker_pool import M5HardwareProfile, M5WorkerPool, get_m5_optimal_workers
from .pipelined_processor import PipelinedChapterProcessor

__all__ = [
    "M5HardwareProfile",
    "M5WorkerPool",
    "PipelinedChapterProcessor",
    "get_m5_optimal_workers",
]
