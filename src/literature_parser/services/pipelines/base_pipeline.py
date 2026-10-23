"""
Abstract Base Pipeline
======================
Defines the standard lifecycle interface for all document archetype pipelines.
"""

import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from literature_parser.services.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """Abstract base class for archetype-specific conversion pipelines."""

    def __init__(
        self,
        output_dir: str = "./output",
        processed_dir: str = "./processed",
        use_ollama: bool = True,
        ollama_model: str = "qwen2.5:7b",
    ):
        self.output_dir = Path(output_dir)
        self.processed_dir = Path(processed_dir)
        self.use_ollama = use_ollama
        self.ollama_model = ollama_model
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def process(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """
        Executes the end-to-end conversion pipeline for the specific archetype.
        Returns a dictionary containing processing results and status.
        """

    def archive_source(self, source_path: str, doc_type: str = "literature"):
        """Moves fully processed and verified source file to appropriate processed directory.

        Args:
            source_path: Path to the original document file.
            doc_type: Document archetype ('book' or 'literature').

        Returns:
            None.
        """
        p = Path(source_path)
        from literature_parser.config.settings import load_config as _load_cfg
        app_cfg = _load_cfg()

        is_lit = (doc_type in ("literature", "journal")) or ("literature" in str(p).lower())
        dest_dir = app_cfg.processed_literature_dir if is_lit else app_cfg.processed_books_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / p.name
        try:
            shutil.move(str(p), str(dest_file))
            print(f"\n[📦 ARCHIVE] Document verified! Source moved to: {dest_file}\n")
        except Exception as e:
            logger.warning("Could not move source to %s: %s", dest_file, e)

    def load_pipeline_config(self, pdf_path: str, archetype: str) -> Dict[str, Any]:
        """Loads 4-tier hierarchical configuration for the document."""
        return ConfigManager.load_hierarchical_config(
            pdf_path=pdf_path,
            archetype=archetype,
        )
