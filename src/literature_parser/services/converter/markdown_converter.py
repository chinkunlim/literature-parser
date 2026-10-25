"""
Markdown Conversion Service (MarkdownConversionService)
=======================================================
Pure, thread-safe transformation service converting PDF documents into
structured, high-fidelity Markdown based on canonical DocumentProfile:
- Eliminates global module variable mutations for safe parallel execution.
- Extracts figures and crops tables with equal margin padding and notes.
- Generates dual CSS styling (independent style.css + embedded <style> block).
- Delegates domain-specific semantic enrichment to PostProcessorStrategy.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from literature_parser.domain.profiler.profile_schema import DocumentProfile
from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.config_manager import ConfigManager
from literature_parser.services.converter.element_cropper import ElementCropper
from literature_parser.services.converter.models import (
    ConversionOptions,
    ConversionResult,
    CroppedElement,
)
from literature_parser.services.converter.strategies.base_strategy import PostProcessorStrategy
from literature_parser.services.converter.strategies.book_strategy import BookPostProcessor
from literature_parser.services.converter.strategies.literature_strategy import LiteraturePostProcessor
from literature_parser.services.core.analyzer import PDFAnalyzer
from literature_parser.services.core.image_manager import ImageManager
from literature_parser.services.literature_style import build_literature_css
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser
from literature_parser.services.profiler.chapter_blueprint_scanner import ChapterBlueprintScanner

logger = logging.getLogger(__name__)


class MarkdownConversionService:
    """Core domain service converting PDF files to structured Markdown."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initializes MarkdownConversionService.

        Args:
            config_manager: Optional ConfigManager for hierarchical profile resolution.
        """
        self.config_manager = config_manager or ConfigManager()

    def convert(
        self,
        pdf_path: str | Path,
        profile: Optional[DocumentProfile] = None,
        output_dir: Optional[str | Path] = None,
        strategy: Optional[PostProcessorStrategy] = None,
        options: Optional[ConversionOptions] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversionResult:
        """Converts a PDF file into structured Markdown according to its profile.

        Args:
            pdf_path: Path to the target PDF document.
            profile: Canonical DocumentProfile carrying geometry and style settings.
            output_dir: Directory where images and style.css should be saved.
            strategy: Domain-specific PostProcessorStrategy (Book or Literature).
            options: ConversionOptions controlling TOC, CSS, cropping, and images.
            context: Context dictionary passed to strategy (chapter_name, book_source, etc.).

        Returns:
            ConversionResult containing Markdown content, cropped elements, and metadata.
        """
        start_time = time.time()
        p_path = Path(pdf_path)
        if not p_path.exists():
            raise FileNotFoundError(f"PDF file not found: {p_path}")

        opts = options or ConversionOptions()
        ctx = dict(context or {})

        # 1. Resolve DocumentProfile
        if profile is None:
            doc_dir = p_path.parent
            prof_dict = self.config_manager.get_canonical_profile(doc_dir, doc_type="book")
            prof = DocumentProfile.from_dict(prof_dict)
        else:
            prof = profile

        # Determine mode & document type
        is_scanned = (prof.meta.mode == "scanned")
        is_literature = (prof.meta.doc_type == "literature")

        # 2. Select Strategy if not provided
        if strategy is None:
            active_strategy: PostProcessorStrategy = (
                LiteraturePostProcessor() if is_literature else BookPostProcessor()
            )
        else:
            active_strategy = strategy

        # 3. Determine Output Directory & Images Directory
        out_root = Path(output_dir) if output_dir else p_path.parent
        out_root.mkdir(parents=True, exist_ok=True)
        images_dir = out_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        total_pages = PDFAnalyzer.get_page_count(str(p_path))
        if total_pages <= 0:
            total_pages = 1

        # 3.5. Pass 1: Pre-Conversion Chapter Structural Blueprint Scan (Refs: ADR-011)
        ch_blueprint = None
        try:
            ch_blueprint = ChapterBlueprintScanner.scan_chapter(
                pdf_path=p_path,
                chapter_name=ctx.get("chapter_name") or p_path.stem,
                output_dir=out_root,
                is_scanned=is_scanned,
                specialist_enricher=ctx.get("specialist_enricher"),
            )
            ctx["chapter_blueprint"] = ch_blueprint
        except Exception as bp_err:
            logger.debug("ChapterBlueprintScanner skipped for %s: %s", p_path.name, bp_err)

        # 4. Extract Genuine Raster Figures
        saved_images: List[Dict[str, Any]] = []
        if opts.extract_images:
            try:
                is_cover_doc = bool(opts.is_front_matter and ("cover" in p_path.stem.lower() or "00-01" in p_path.stem.lower()))
                raw_images = ImageManager.extract_pdf_images(str(p_path), is_scanned=is_scanned, is_cover=is_cover_doc)
                if raw_images:
                    for seq, img in enumerate(raw_images, 1):
                        p_num = img.get('page', 1)
                        ext = img.get('ext', 'png')
                        fname = f"{p_num:03d}_{seq:03d}.{ext}"
                        dest = images_dir / fname
                        with open(dest, 'wb') as f_out:
                            f_out.write(img['data'])
                        img_copy = dict(img)
                        img_copy['filename'] = fname
                        saved_images.append(img_copy)
            except Exception as e:
                logger.warning("Raster image extraction failed for %s: %s", p_path.name, e)

        # 5. Extract Standalone Cropped Figures & Tables (with equal margin and notes)
        cropped_elements: List[CroppedElement] = []
        if opts.crop_figures_and_tables and not is_scanned:
            margin_pt = getattr(prof.geometry, "uniform_crop_margin_pt", opts.uniform_crop_margin_pt)
            pw = prof.geometry.page_width
            ph = prof.geometry.page_height

            for p_num in range(1, total_pages + 1):
                try:
                    xml_str = DigitalPDFParser.extract_page_xml(str(p_path), p_num)
                    if xml_str and '<page' in xml_str:
                        start_tag = xml_str.find('<page')
                        end_tag = xml_str.rfind('</page>') + len('</page>')
                        page_elem = ET.fromstring(xml_str[start_tag:end_tag])

                        tbl_crops = ElementCropper.extract_and_crop_page_tables(
                            pdf_path=p_path,
                            page_elem=page_elem,
                            page_num=p_num,
                            pw=pw,
                            ph=ph,
                            images_dir=images_dir,
                            margin_pt=margin_pt,
                        )
                        cropped_elements.extend(tbl_crops)

                        fig_crops = ElementCropper.extract_and_crop_page_figures(
                            pdf_path=p_path,
                            page_elem=page_elem,
                            page_num=p_num,
                            pw=pw,
                            ph=ph,
                            images_dir=images_dir,
                            margin_pt=margin_pt,
                        )
                        cropped_elements.extend(fig_crops)
                except Exception as e:
                    logger.debug("Crop extraction skipped for page %d: %s", p_num, e)

        # 6. Page-by-Page Conversion Loop
        md_parts: List[str] = []
        if not is_scanned:
            DigitalPDFParser.reset_chapter_state()

        with tempfile.TemporaryDirectory() as work_tmp:
            for p in range(1, total_pages + 1):
                p_imgs = [img for img in saved_images if img.get('page') == p]
                if is_scanned:
                    p_md = ScannedPDFParser.parse_page_to_markdown(str(p_path), p, work_tmp)
                else:
                    p_md = DigitalPDFParser.parse_page_to_markdown(str(p_path), p, p_imgs)

                if p_md:
                    md_parts.append(f"<!-- Page {p} -->\n{p_md}")

        raw_md = '\n\n'.join(md_parts).strip()

        # 7. CSS Generation (Dual Output: standalone style.css + embedded <style>)
        prof_dict = prof.to_dict()
        if is_literature:
            css_raw = build_literature_css(prof_dict)
        else:
            css_raw = build_textbook_css(prof_dict)

        # Clean standalone CSS by stripping <style> and </style> tags
        clean_css = re.sub(r'</?style>', '', css_raw).strip()

        if opts.output_standalone_css:
            try:
                css_file = out_root / "style.css"
                css_file.write_text(clean_css + "\n", encoding="utf-8")
            except Exception as e:
                logger.warning("Failed writing standalone style.css to %s: %s", out_root, e)

        # 8. Strategy Semantic Post-Processing
        processed_md = active_strategy.process(
            raw_markdown=raw_md,
            profile=prof,
            options=opts,
            cropped_elements=cropped_elements,
            context=ctx,
        )

        # 9. Embed CSS in Markdown Header if requested
        if opts.embed_css and clean_css:
            style_block = f"<style>\n{clean_css}\n</style>\n\n"
            if not processed_md.startswith("<style>"):
                processed_md = f"{style_block}{processed_md}"

        elapsed_sec = round(time.time() - start_time, 3)
        stats = {
            "elapsed_sec": elapsed_sec,
            "page_count": total_pages,
            "mode": "scanned" if is_scanned else "digital",
            "doc_type": prof.meta.doc_type,
            "images_extracted": len(saved_images),
            "elements_cropped": len(cropped_elements),
        }

        return ConversionResult(
            markdown=processed_md,
            css_content=clean_css,
            images=saved_images,
            cropped_elements=cropped_elements,
            page_count=total_pages,
            metadata={"title": prof.meta.title, "mode": prof.meta.mode},
            stats=stats,
            profile=prof,
        )
