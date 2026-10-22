"""
Dual-Engine High-Performance PDF Document Engine
===============================================
Encapsulates native PyMuPDF (fitz) extraction with transparent Poppler CLI fallback:
- Loads PDF document once into memory, eliminating repeated subprocess spawning.
- Provides text spans, font metrics, bounding boxes, vector lines, and high-res image crops.
- Supports context manager protocol (__enter__ / __exit__) for safe resource disposal.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pymupdf  # type: ignore
    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False


class PDFDocumentEngine:
    """Unified PDF parser and rendering engine with native PyMuPDF and Poppler fallback."""

    def __init__(self, pdf_path: str | Path, force_fallback: bool = False):
        """Initializes the PDFDocumentEngine.

        Args:
            pdf_path: Path to the PDF file.
            force_fallback: If True, bypasses PyMuPDF to use external CLI utilities.
        """
        self.pdf_path = Path(pdf_path).resolve()
        self.force_fallback = force_fallback
        self._doc: Optional[Any] = None
        self.is_native_active = False

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF document not found: {self.pdf_path}")

        if _HAS_PYMUPDF and not self.force_fallback:
            try:
                self._doc = pymupdf.open(str(self.pdf_path))
                self.is_native_active = True
            except Exception as e:
                logger.warning("Failed to open PDF with PyMuPDF, falling back to CLI: %s", e)
                self._doc = None
                self.is_native_active = False

    def __enter__(self) -> PDFDocumentEngine:
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit point to close native document handle."""
        self.close()

    def close(self) -> None:
        """Closes native PDF document handle if opened."""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

    def get_page_count(self) -> int:
        """Returns the total number of pages in the PDF.

        Returns:
            Total page count as integer.
        """
        if self.is_native_active and self._doc is not None:
            return len(self._doc)

        from literature_parser.adapters.utils.system import get_pdf_page_count
        return get_pdf_page_count(self.pdf_path)

    def extract_page_data(self, page_num: int) -> Dict[str, Any]:
        """Extracts text, structured spans, and dimensions for a single 1-based page.

        Args:
            page_num: 1-based page index.

        Returns:
            Dictionary containing 'text', 'spans', 'width', and 'height'.
        """
        if self.is_native_active and self._doc is not None:
            idx = page_num - 1
            if 0 <= idx < len(self._doc):
                page = self._doc[idx]
                rect = page.rect
                page_dict = page.get_text("dict")
                spans: List[Dict[str, Any]] = []
                full_text_parts: List[str] = []

                for block in page_dict.get("blocks", []):
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            line_text: List[str] = []
                            for span in line.get("spans", []):
                                s_text = span.get("text", "")
                                if s_text:
                                    line_text.append(s_text)
                                    spans.append({
                                        "text": s_text,
                                        "bbox": span.get("bbox", (0, 0, 0, 0)),
                                        "size": span.get("size", 10.0),
                                        "font": span.get("font", ""),
                                        "flags": span.get("flags", 0),
                                    })
                            if line_text:
                                full_text_parts.append(" ".join(line_text))

                return {
                    "text": "\n".join(full_text_parts),
                    "spans": spans,
                    "width": rect.width,
                    "height": rect.height,
                }

        # Fallback to pdftotext
        from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
        text = DigitalPDFParser.extract_page_text(str(self.pdf_path), page_num)
        return {
            "text": text,
            "spans": [],
            "width": 612.0,
            "height": 792.0,
        }

    def get_drawings(self, page_num: int) -> List[Dict[str, Any]]:
        """Extracts vector drawings (lines, rectangles) for a 1-based page.

        Args:
            page_num: 1-based page index.

        Returns:
            List of drawing dicts containing bounding geometry and coordinates.
        """
        if self.is_native_active and self._doc is not None:
            idx = page_num - 1
            if 0 <= idx < len(self._doc):
                page = self._doc[idx]
                drawings: List[Dict[str, Any]] = []
                try:
                    raw_drawings = page.get_drawings()
                    for d in raw_drawings:
                        items = d.get("items", [])
                        for item in items:
                            if item[0] == "l":  # Line
                                p1, p2 = item[1], item[2]
                                drawings.append({
                                    "type": "line",
                                    "start": (p1.x, p1.y),
                                    "end": (p2.x, p2.y),
                                    "rect": d.get("rect", (p1.x, p1.y, p2.x, p2.y)),
                                    "width": d.get("width", 1.0),
                                })
                            elif item[0] == "re":  # Rect
                                r = item[1]
                                drawings.append({
                                    "type": "rect",
                                    "rect": (r.x0, r.y0, r.x1, r.y1),
                                    "width": d.get("width", 1.0),
                                })
                except Exception as e:
                    logger.debug("Failed getting drawings for page %d: %s", page_num, e)
                return drawings

        return []

    def render_cropped_image(
        self,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        output_path: str | Path,
        dpi: int = 150,
    ) -> bool:
        """Renders and saves a specific bounding box on a page as a high-resolution image.

        Args:
            page_num: 1-based page index.
            bbox: Tuple of (x0, y0, x1, y1) in points.
            output_path: Destination file path for the cropped PNG image.
            dpi: Dots per inch for rendering resolution (default: 150).

        Returns:
            True if image rendering succeeded, False otherwise.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if self.is_native_active and self._doc is not None:
            idx = page_num - 1
            if 0 <= idx < len(self._doc):
                try:
                    page = self._doc[idx]
                    x0, y0, x1, y1 = bbox
                    # Clamp to page boundaries
                    rect = page.rect
                    clip_rect = pymupdf.Rect(
                        max(0.0, min(float(x0), rect.width)),
                        max(0.0, min(float(y0), rect.height)),
                        max(0.0, min(float(x1), rect.width)),
                        max(0.0, min(float(y1), rect.height)),
                    )
                    if clip_rect.width <= 1.0 or clip_rect.height <= 1.0:
                        return False

                    zoom = dpi / 72.0
                    matrix = pymupdf.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=matrix, clip=clip_rect, alpha=False)
                    pix.save(str(out_p))
                    return True
                except Exception as e:
                    logger.warning("PyMuPDF crop rendering failed on page %d: %s", page_num, e)

        # Fallback to ElementCropper CLI implementation if poppler installed
        from literature_parser.services.converter.element_cropper import ElementCropper
        return ElementCropper.crop_pdf_region(
            pdf_path=self.pdf_path,
            page_num=page_num,
            bbox=bbox,
            output_image_path=out_p,
            dpi=dpi,
        )
