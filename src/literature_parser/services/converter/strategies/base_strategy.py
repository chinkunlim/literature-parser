"""
Base Strategy for Conversion Post-Processing
============================================
Defines the abstract interface for domain-specific post-processing
applied to raw Markdown output generated from PDF pages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.converter.models import ConversionOptions, CroppedElement


class PostProcessorStrategy(ABC):
    """Abstract strategy for domain-specific Markdown post-processing."""

    @abstractmethod
    def process(
        self,
        raw_markdown: str,
        profile: DocumentProfile,
        options: ConversionOptions,
        cropped_elements: list[CroppedElement],
        context: Dict[str, Any],
    ) -> str:
        """Processes raw Markdown to inject domain-specific structure.

        Args:
            raw_markdown: Combined multi-page Markdown text.
            profile: DocumentProfile carrying typographic and geometry configs.
            options: ConversionOptions controlling generation parameters.
            cropped_elements: List of cropped figures and tables extracted.
            context: Additional contextual data (e.g. chapter_name, pdf_path).

        Returns:
            Refined and semantically enriched Markdown string.
        """
        pass
