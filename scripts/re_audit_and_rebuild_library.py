"""Full Library Re-Audit and EPUB Rebuild Script.
================================================
Iterates through all 5 textbooks in the library (128 chapters), applies the
latest four structural anchors (TOC skeleton alignment, Glossary domain vocabulary,
Figure/Table sequential continuity, and Pedagogical LO/EOC enclosure), writes
updated audit_report.json and AUDIT.md files, and rebuilds high-fidelity EPUB 3 archives.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from literature_parser.config.logging_setup import setup_logging
from literature_parser.config.settings import load_config
from literature_parser.services.exporter.epub_exporter import EpubExporter
from literature_parser.services.verification.glossary_anchor import GlossaryAnchor
from literature_parser.services.verification.quality_engine import QualityInspectionEngine
from literature_parser.services.verification.toc_alignment_auditor import TocAlignmentAuditor, TocNode

logger = logging.getLogger(__name__)


def re_audit_and_rebuild_book(book_dir: Path, rebuild_epub: bool = True) -> Dict[str, Any]:
    """Re-audits all chapters of a book using latest anchors and rebuilds its EPUB.

    Args:
        book_dir: Absolute path to the book's output directory.
        rebuild_epub: Whether to trigger EPUB 3 rebuilding after chapter audits.

    Returns:
        Summary dictionary with book name, chapter count, average score, and EPUB path.
    """
    book_name = book_dir.name
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        logger.warning("No chapters directory found in %s", book_dir)
        return {"book_name": book_name, "error": "No chapters dir"}

    print(f"\n{'='*75}\n📚 [RE-AUDIT] 開始體檢書籍: {book_name}\n{'='*75}")

    # 1. Parse TOC Skeleton if present in front matter
    toc_skeleton = None
    toc_candidates = list(chapters_dir.glob("00-*-TOC*/*.md")) + list(chapters_dir.glob("*TOC*/*.md"))
    if toc_candidates:
        try:
            toc_text = toc_candidates[0].read_text(encoding="utf-8")
            toc_skeleton = TocAlignmentAuditor.parse_toc_markdown(toc_text)
            print(f"  [✓] 成功載入 TOC 骨架樹: 包含 {len(toc_skeleton.chapters)} 個章節目錄")
        except Exception as err:
            logger.warning("Failed parsing TOC skeleton from %s: %s", toc_candidates[0], err)

    # 2. Extract Glossary terms if present in back matter
    glossary_terms: Dict[str, str] = {}
    glo_candidates = list(chapters_dir.glob("00-*-Glossary*/*.md")) + list(chapters_dir.glob("*Glossary*/*.md"))
    if glo_candidates:
        try:
            glo_text = glo_candidates[0].read_text(encoding="utf-8")
            glossary_terms = GlossaryAnchor.extract_terms(glo_text)
            print(f"  [✓] 成功載入書末詞彙庫: 包含 {len(glossary_terms)} 個專業名詞釋義")
        except Exception as err:
            logger.warning("Failed extracting glossary terms from %s: %s", glo_candidates[0], err)

    # 3. Iterate through all chapters
    chapter_dirs = sorted([d for d in chapters_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])
    total_chapters = len(chapter_dirs)
    chapter_scores: List[float] = []
    total_issues = 0

    engine = QualityInspectionEngine()
    if glossary_terms:
        GlossaryAnchor.inject_domain_vocabulary(engine.lexical_auditor, glossary_terms)

    for idx, ch_dir in enumerate(chapter_dirs, 1):
        md_files = [f for f in ch_dir.glob("*.md") if not f.name.endswith("_Verified.md") and f.name != "AUDIT.md"]
        if not md_files:
            continue

        md_path = md_files[0]
        md_text = md_path.read_text(encoding="utf-8")

        # Find matching chapter sections from TOC skeleton
        expected_sections: Optional[List[TocNode]] = None
        if toc_skeleton:
            for ch_entry in toc_skeleton.chapters:
                # Match by number or normalized title substring
                if ch_entry.chapter_num in ch_dir.name or TocAlignmentAuditor.normalize_title(ch_entry.title) in TocAlignmentAuditor.normalize_title(ch_dir.name):
                    expected_sections = ch_entry.sections
                    break

        # Run multi-tier inspection
        report = engine.inspect(
            markdown_text=md_text,
            doc_name=ch_dir.name,
            file_path=md_path,
            base_dir=ch_dir,
            expected_sections=expected_sections,
        )

        # Save repaired markdown if changes occurred
        if report.repaired_count > 0 and report.repaired_markdown != md_text:
            md_path.write_text(report.repaired_markdown, encoding="utf-8")

        # Export audit_report.json and AUDIT.md
        QualityInspectionEngine.export_report_files(report, ch_dir)

        score = report.scores.overall_score
        chapter_scores.append(score)
        total_issues += len(report.issues)

        status_icon = "✓" if report.passed else "⚠️"
        print(f"  [{idx:02d}/{total_chapters:02d}] {status_icon} {ch_dir.name:<45} ➔ 評分: {score:>5.1f}% (問題: {len(report.issues)}, 修復: {report.repaired_count})")

    avg_score = round(sum(chapter_scores) / len(chapter_scores), 2) if chapter_scores else 0.0
    print(f"\n📊 [{book_name}] 體檢完成: 平均品質評分: {avg_score}% (累計檢測問題: {total_issues})")

    # 4. Rebuild EPUB 3 Archive
    output_epub = None
    if rebuild_epub:
        try:
            print(f"  [📦 EPUB] 正在使用純 Python EPUB 3 引擎重新打包電子書...")
            output_epub = EpubExporter.export_book(book_dir, engine="python")
            print(f"  [🎉 EPUB] 出版級 EPUB 重新編譯完成: {output_epub.name} ({output_epub.stat().st_size / (1024*1024):.1f} MB)")
        except Exception as err:
            logger.error("Failed rebuilding EPUB for %s: %s", book_name, err)
            print(f"  [!] EPUB 重建發生錯誤: {err}")

    return {
        "book_name": book_name,
        "total_chapters": total_chapters,
        "average_score": avg_score,
        "total_issues": total_issues,
        "epub_path": str(output_epub) if output_epub else None,
    }


def main():
    """Main runner executing full library re-audit across all books."""
    setup_logging()
    cfg = load_config()
    books_dir = cfg.data_dir / "output" / "books"
    if not books_dir.exists():
        print(f"[!] Books directory not found: {books_dir}")
        sys.exit(1)

    book_folders = sorted([b for b in books_dir.iterdir() if b.is_dir() and not b.name.startswith(".")])
    print(f"\n{'='*75}\n🚀 啟動全書庫 5 本教科書全量體檢與 EPUB 重建作業 (共 {len(book_folders)} 本書)\n{'='*75}")

    start_all = time.time()
    results = []

    for b in book_folders:
        res = re_audit_and_rebuild_book(b, rebuild_epub=True)
        results.append(res)

    elapsed_all = round(time.time() - start_all, 1)

    print(f"\n{'='*75}\n🎉 全書庫 5 本教科書體檢與 EPUB 重編全部完工 (總耗時: {elapsed_all} 秒)\n{'='*75}")
    print(f"| 書名 | 章節數 | 平均品質分 | 累計檢出問題 | EPUB 狀態 |")
    print(f"|---|---|---|---|---|")
    for r in results:
        epub_stat = "✅ 已更新" if r.get("epub_path") else "❌ 失敗"
        print(f"| {r['book_name'][:35]}... | {r['total_chapters']} | {r['average_score']}% | {r['total_issues']} | {epub_stat} |")


if __name__ == "__main__":
    main()
