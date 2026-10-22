"""Chapter PDF-to-Markdown conversion helpers for the orchestrator pipeline.

Handles per-book geometry calibration, style configuration, image extraction,
page-level parsing, heading/TOC normalization, flashcard generation, auto-healing,
and local AI review annotation.
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier
from literature_parser.services.book_style import build_textbook_css
from literature_parser.services.core.image_manager import ImageManager
from literature_parser.services.core.invariants import QualityInvariantGuard
from literature_parser.services.core.learner import GlobalLearner
from literature_parser.services.parsers import digital_pdf as _digital_pdf_mod
from literature_parser.services.parsers.digital_pdf import DigitalPDFParser
from literature_parser.services.parsers.layout_detector import (
    generate_markdown_toc,
    set_style as _ld_set_style,
)
from literature_parser.services.parsers.scanned_pdf import ScannedPDFParser
from literature_parser.services.profiler.coordinate_calibrator import CoordinateCalibrator
from literature_parser.services.profiler.special_block_scanner import SpecialBlockScanner
from literature_parser.services.style_loader import load_style
from literature_parser.services.utils.anki_exporter import AnkiExporter
from literature_parser.services.utils.text_utils import stitch_cross_page_continuity
from literature_parser.adapters.verification.layout_healer import LayoutAutoHealer
from literature_parser.adapters.verification.review_manager import ReviewManager

logger = logging.getLogger(__name__)


def calibrate_book_profile_if_missing(
    book_dir: Path, ch_pdf: Path, is_journal_doc: bool
) -> None:
    """Auto-calibrate book geometry and scan special blocks if book_profile.json is missing.

    Args:
        book_dir: Root output directory for the book.
        ch_pdf: Path to the current chapter PDF file.
        is_journal_doc: Whether the document is classified as a journal article.

    Returns:
        None.
    """
    cand_canon = book_dir / "profile.json"
    cand_legacy = book_dir / "book_profile.json"
    if cand_canon.exists() or cand_legacy.exists():
        return
    try:
        CoordinateCalibrator.calibrate_and_save_profile(book_dir, ch_pdf)
        if is_journal_doc:
            target_profile = cand_canon if cand_canon.exists() else cand_legacy
            _mark_profile_as_journal(target_profile)
        scanner = SpecialBlockScanner(book_dir)
        scanner.scan_and_update([ch_pdf], max_pages_per_chapter=10)
    except Exception as exc:
        logger.debug("Automatic book calibration skipped: %s", exc)


def _mark_profile_as_journal(book_profile_path: Path) -> None:
    """Set the is_journal flag in an existing book_profile.json file.

    Args:
        book_profile_path: Path to the book_profile.json file.

    Returns:
        None.
    """
    try:
        with open(book_profile_path, encoding="utf-8") as f_prof:
            prof_data = json.load(f_prof)
        prof_data["is_journal"] = True
        with open(book_profile_path, "w", encoding="utf-8") as f_prof:
            json.dump(prof_data, f_prof, indent=2)
        # Also sync mirror profile.json / book_profile.json
        mirror_name = "profile.json" if book_profile_path.name != "profile.json" else "book_profile.json"
        mirror_path = book_profile_path.parent / mirror_name
        with open(mirror_path, "w", encoding="utf-8") as f_prof:
            json.dump(prof_data, f_prof, indent=2)
    except Exception as exc:
        logger.debug("Failed updating is_journal in profile: %s", exc)


def configure_chapter_style(book_dir: Path, is_journal_doc: bool) -> dict[str, Any]:
    """Load per-book style configuration and apply it to layout and PDF parser modules.

    Args:
        book_dir: Root output directory for the book.
        is_journal_doc: Whether the document is classified as a journal article.

    Returns:
        Merged style configuration dictionary for the chapter.
    """
    style: dict[str, Any] = load_style(str(book_dir))
    if is_journal_doc:
        style["is_journal_article"] = True
        style["generate_toc"] = False
        style["gloss_placement"] = "none"
        style["prepend_chapter_title_if_missing"] = False
    _ld_set_style(style)
    _digital_pdf_mod._STYLE = style
    return style


def extract_and_save_chapter_images(
    ch_pdf: Path, ch_images_dir: Path, is_scanned: bool
) -> list[dict[str, Any]]:
    """Extract genuine figures and photos from a chapter PDF and write them to disk.

    Args:
        ch_pdf: Path to the chapter PDF file.
        ch_images_dir: Destination directory for extracted image files.
        is_scanned: Whether the chapter PDF is a scanned document.

    Returns:
        List of extracted image metadata dictionaries with populated filenames.
    """
    raw_images: list[dict[str, Any]] = ImageManager.extract_pdf_images(
        str(ch_pdf), is_scanned=is_scanned
    )
    saved_images: list[dict[str, Any]] = []
    if raw_images:
        os.makedirs(ch_images_dir, exist_ok=True)
        for seq, img in enumerate(raw_images, 1):
            page_num = img["page"]
            ext = img["ext"]
            fname = f"{page_num:03d}_{seq:03d}.{ext}"
            dest = ch_images_dir / fname
            with open(dest, "wb") as f_out:
                f_out.write(img["data"])
            img["filename"] = fname
            saved_images.append(img)
    logger.info("Genuine figures/photos extracted for %s: %d", ch_pdf.stem, len(saved_images))
    return saved_images


def parse_chapter_pages(
    ch_pdf: Path,
    total_pages: int,
    is_scanned: bool,
    saved_images: list[dict[str, Any]],
) -> str:
    """Parse all pages of a chapter PDF into combined raw Markdown text.

    Args:
        ch_pdf: Path to the chapter PDF file.
        total_pages: Total number of pages in the chapter PDF.
        is_scanned: Whether to use the scanned OCR parser instead of vector XML parser.
        saved_images: Extracted image metadata entries for page matching.

    Returns:
        Combined Markdown string across all pages of the chapter.
    """
    md_parts: list[str] = []
    if not is_scanned:
        DigitalPDFParser.reset_chapter_state()
    with tempfile.TemporaryDirectory() as work_tmp:
        for page_num in range(1, total_pages + 1):
            p_imgs = [img for img in saved_images if img["page"] == page_num]
            if is_scanned:
                p_md = ScannedPDFParser.parse_page_to_markdown(
                    str(ch_pdf), page_num, work_tmp
                )
            else:
                p_md = DigitalPDFParser.parse_page_to_markdown(
                    str(ch_pdf), page_num, p_imgs
                )
            if p_md:
                md_parts.append(f"<!-- Page {page_num} -->\n{p_md}")
    return "\n\n".join(md_parts).strip()


def postprocess_chapter_headings_and_toc(
    full_md: str, ch_name: str, is_journal_doc: bool, style: dict[str, Any]
) -> str:
    """Normalize top-level chapter headings, inject TOC if enabled, and stitch cross-page text.

    Args:
        full_md: Raw combined Markdown content for the chapter.
        ch_name: Stem name of the chapter.
        is_journal_doc: Whether the document is classified as a journal article.
        style: Active book style configuration dictionary.

    Returns:
        Post-processed Markdown string with normalized headings, TOC, and stitched pages.
    """
    if is_journal_doc:
        full_md = _promote_journal_title(full_md)
    elif style.get("prepend_chapter_title_if_missing", True):
        has_title = re.search(
            r"^\s*#+\s*(?:PART|CHAPTER|\d+|Introduction)", full_md, re.IGNORECASE
        ) or re.search(r"^\s*<!--.*?-->\s*#+\s*", full_md, re.IGNORECASE)
        if not has_title:
            full_md = f"# {ch_name}\n\n{full_md}"

    toc_mode = style.get("toc_mode", "open")
    if not is_journal_doc and style.get("generate_toc", True) and toc_mode != "none":
        toc_block = generate_markdown_toc(full_md, toc_mode=toc_mode)
        if toc_block and "<summary>📑 <b>Table of Contents</b>" not in full_md:
            m_h1 = re.search(r"^(#[^\n]+\n+)", full_md)
            if m_h1:
                full_md = full_md[: m_h1.end()] + toc_block + "\n\n" + full_md[m_h1.end() :]
            else:
                full_md = toc_block + "\n\n" + full_md

    return stitch_cross_page_continuity(full_md)


def _promote_journal_title(full_md: str) -> str:
    """Promote the first H3 heading to H1 in journal articles lacking an H1 title.

    Args:
        full_md: Markdown content of the journal article.

    Returns:
        Markdown string with the main article title promoted to H1 if applicable.
    """
    if re.search(r"^\s*#\s+[^\n]+", full_md):
        return full_md
    m_first_h = re.search(r"###\s+([^\n]+)(?:\n+###\s+([^\n]+))?", full_md)
    if not m_first_h:
        return full_md
    t1 = m_first_h.group(1).strip()
    t2 = m_first_h.group(2).strip() if m_first_h.group(2) else ""
    combined_title = f"{t1} {t2}".strip()
    return full_md[: m_first_h.start()] + f"# {combined_title}" + full_md[m_first_h.end() :]


def _build_bullet_flashcards(ch_gloss: list[dict[str, Any]]) -> list[str]:
    """Build bullet-list key term lines for chapter-end glossary output.

    Args:
        ch_gloss: List of glossary term dictionaries collected from the chapter.

    Returns:
        List of formatted Markdown lines for bullet glossary display.
    """
    fc_lines = ["## 📖 Chapter Key Terms", ""]
    for item in ch_gloss:
        term = item["term"]
        definition = (item.get("definition") or "").strip()
        pg = item.get("page")
        pg_str = f" *(p. {pg})*" if pg else ""
        if definition:
            fc_lines.append(f"- **{term}**{pg_str}: {definition}")
        else:
            fc_lines.append(f"- **{term}**{pg_str}")
    fc_lines.append("")
    return fc_lines


def _build_details_flashcards(ch_gloss: list[dict[str, Any]]) -> list[str]:
    """Build collapsible HTML details flashcards for active-recall key terms.

    Args:
        ch_gloss: List of glossary term dictionaries collected from the chapter.

    Returns:
        List of formatted Markdown/HTML lines for interactive flashcards.
    """
    fc_lines = [
        "## 🗂️ Chapter Key Terms & Active Recall",
        "",
        "> 💡 **Learning tip:** Try to recall the definition of each term *before* clicking to reveal it.",
        "> This active retrieval practice strengthens long-term memory far more than re-reading.",
        "",
    ]
    for item in ch_gloss:
        term = item["term"]
        definition = (item.get("definition") or "").strip()
        pg = item.get("page")
        pg_str = f" *(p. {pg})*" if pg else ""
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", term.lower()).strip("-")
        fc_lines.append(f'<details id="flashcard-{slug}">')
        fc_lines.append(f"<summary>📇 <b>{term}</b>{pg_str}</summary>")
        fc_lines.append("")
        if definition:
            fc_lines.append(f"> **Definition:** {definition}")
        else:
            loc = f"on p. {pg}" if pg else "in the chapter"
            fc_lines.append(f"> *This term appears in bold {loc}.*")
            fc_lines.append(
                "> *Write your own definition from context, then re-read that passage to check.*"
            )
        fc_lines.extend(["", "</details>", ""])
    return fc_lines


def append_chapter_flashcards(
    full_md: str, is_scanned: bool, style: dict[str, Any]
) -> str:
    """Append chapter-end flashcards or key-term bullets when configured in style.

    Args:
        full_md: Chapter Markdown content prior to glossary injection.
        is_scanned: Whether the chapter was processed in scanned OCR mode.
        style: Active book style configuration dictionary.

    Returns:
        Markdown string with chapter-end glossary flashcards inserted if applicable.
    """
    if is_scanned or style.get("gloss_placement") != "chapter_end":
        return full_md
    ch_gloss: list[dict[str, Any]] = DigitalPDFParser.get_chapter_all_terms()
    if not ch_gloss:
        return full_md

    if style.get("gloss_format") == "bullet":
        fc_lines = _build_bullet_flashcards(ch_gloss)
    else:
        fc_lines = _build_details_flashcards(ch_gloss)

    fc_text = "\n".join(fc_lines)
    m_eoc = re.search(
        r'(?:<a id="key-terms-and-concepts"></a>|###\s*Key Terms and Concepts)',
        full_md,
    )
    if m_eoc:
        pos = m_eoc.start()
        return full_md[:pos] + fc_text + "\n\n" + full_md[pos:]
    return full_md + "\n\n" + fc_text


def apply_healers_to_markdown(
    full_md: str, ch_pdf: Path, is_journal_doc: bool, use_ollama: bool
) -> str:
    """Pre-apply learned global fixes and run layout auto-healing on chapter Markdown.

    Args:
        full_md: Chapter Markdown content including CSS header.
        ch_pdf: Path to the chapter PDF file.
        is_journal_doc: Whether the document is classified as a journal article.
        use_ollama: Whether Ollama vision/LLM healing is enabled.

    Returns:
        Healed Markdown string ready for syntax verification.
    """
    doc_archetype = "journal" if is_journal_doc else "textbook"
    try:
        full_md, pre_fixes = GlobalLearner.apply_known_fixes(
            full_md, archetype=doc_archetype
        )
        if pre_fixes:
            logger.info(
                "Pre-applied %d known fix rule(s) from global memory for %s.",
                len(pre_fixes),
                ch_pdf.stem,
            )
    except Exception as gl_err:
        logger.debug("GlobalLearner pre-application skipped: %s", gl_err)

    ch_dir = ch_pdf.parent
    full_md, fixes = LayoutAutoHealer.audit_and_heal_chapter(
        full_md,
        str(ch_pdf),
        str(ch_dir),
        images_dir=ch_dir / "images",
        use_ollama_vision=use_ollama,
    )
    if fixes:
        logger.info(
            "LayoutAutoHealer applied %d correction(s) on %s", len(fixes), ch_pdf.stem
        )
    return full_md


def write_chapter_outputs(
    full_md: str, ch_pdf: Path, is_scanned: bool, style: dict[str, Any]
) -> Path:
    """Inject CSS, validate syntax invariants, write chapter Markdown, and export Anki TSV.

    Args:
        full_md: Chapter Markdown content to validate and write.
        ch_pdf: Path to the chapter PDF file.
        is_scanned: Whether the chapter was processed in scanned OCR mode.
        style: Active book style configuration dictionary.

    Returns:
        Path to the written chapter Markdown file.
    """
    if "<style>" not in full_md:
        full_md = build_textbook_css(style) + full_md

    ch_dir = ch_pdf.parent
    ch_name = ch_pdf.stem
    QualityInvariantGuard.check_markdown_syntax(full_md, str(ch_dir))

    md_file = ch_dir / f"{ch_name}.md"
    with open(md_file, "w", encoding="utf-8") as f_out:
        f_out.write(full_md + "\n")
    logger.info("Markdown generated: %s", md_file.name)

    if not is_scanned and style.get("gloss_placement") == "chapter_end":
        all_terms = DigitalPDFParser.get_chapter_all_terms()
        if all_terms:
            anki_path = ch_dir / f"{ch_name}_flashcards.tsv"
            count = AnkiExporter.export_chapter_flashcards_to_tsv(
                all_terms, anki_path, chapter_name=ch_name
            )
            if count > 0:
                logger.info("Exported %d Anki flashcard(s) to %s", count, anki_path.name)
    return md_file


def run_ollama_ai_review(
    full_md: str, md_file: Path, use_ollama: bool, ollama_model: str
) -> None:
    """Request local AI review proposals via Ollama and annotate the chapter Markdown.

    Args:
        full_md: Generated chapter Markdown text to audit.
        md_file: Path to the chapter Markdown file on disk.
        use_ollama: Whether Ollama AI review is enabled.
        ollama_model: Name of the Ollama healer/reviewer model.

    Returns:
        None.
    """
    if not use_ollama:
        return
    ollama = (
        OllamaVerifier(healer_model=ollama_model)
        if ollama_model
        else OllamaVerifier()
    )
    if not ollama.is_available:
        return
    logger.info("Requesting local AI audit & diff suggestions from %s", ollama_model)
    proposals = ollama.audit_and_propose_fixes(full_md)
    if proposals:
        annotated_md, applied = OllamaVerifier.apply_review_annotations(
            full_md, proposals
        )
        with open(md_file, "w", encoding="utf-8") as f_out:
            f_out.write(annotated_md + "\n")
        ReviewManager.save_review_manifest(str(md_file.parent), applied)
        logger.info(
            "Saved %d AI review proposed correction(s) in %s",
            len(applied),
            md_file.parent,
        )
