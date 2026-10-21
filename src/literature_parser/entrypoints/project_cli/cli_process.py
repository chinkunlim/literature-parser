"""
CLI Document & Literature Processing
=====================================
Handles document conversion execution and multi-file batch processing:
- _run_process_pipeline: Invokes core pipeline with hardware safeguards
- cmd_process: Processes a single book or literature file
- cmd_batch: Processes a directory of PDF/EPUB files with cool-down guards
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from literature_parser.entrypoints.project_cli.common import ROOT
from literature_parser.adapters.guards.hardware import check_hardware_safety
from literature_parser.services.utils.app_logger import get_diagnostic_logger

logger = get_diagnostic_logger("CommandCenter")


def _run_process_pipeline(
    filepath: Path,
    doc_type: Optional[str] = None,
    ignore_battery: bool = False,
    export_epub: bool = False
) -> bool:
    """Executes the conversion pipeline for a single file. Returns True on success, False on failure."""
    if not filepath.exists():
        print(f"🛑 錯誤：找不到指定的輸入檔案: {filepath}")
        return False

    if not doc_type:
        try:
            rel = filepath.resolve().relative_to(ROOT)
            parts = rel.parts
            if len(parts) >= 3 and parts[0] == "data" and parts[1] == "input":
                subdir = parts[2]
                if subdir in ("literature", "journals", "papers"):
                    doc_type = "literature"
                elif subdir == "books":
                    doc_type = "book"
        except ValueError:
            pass
        if not doc_type:
            parent_lower = filepath.parent.name.lower()
            if parent_lower in ("literature", "journals", "papers"):
                doc_type = "literature"
            else:
                doc_type = "book"
    elif doc_type == "journal":
        doc_type = "literature"

    print(f"\n🚀 啟動處理管線: [{doc_type.upper()}] 檔案: {filepath.name}")

    hw = check_hardware_safety(ignore_battery=ignore_battery)
    if not hw["safe_for_batch_ocr"]:
        print(f"🛑 硬體空間不足拒絕啟動: {'; '.join(hw['reasons'])}")
        return False

    output_base = Path("data/output") / ("books" if doc_type == "book" else "literature")
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"• 輸出目標資料夾: {output_base}")
    print(f"• 呼叫對應領域管線: src/literature_parser.services/pipelines/{'textbook_pipeline' if doc_type == 'book' else 'literature_pipeline'}.py")

    cli_cmd = [
        sys.executable, "-m", "literature_parser.entrypoints.doc_cli", "run",
        "--file", str(filepath),
        "--output-dir", str(output_base),
    ]
    if hw["safe_for_heavy_llm"]:
        cli_cmd.append("--ollama")

    logger.info(f"Executing: {' '.join(cli_cmd)}")
    from literature_parser.config.env import child_process_env
    src_dir = str(ROOT / "src")
    base_env = child_process_env()
    python_path = f"{src_dir}:{base_env['PYTHONPATH']}" if "PYTHONPATH" in base_env else src_dir
    env = child_process_env({"PYTHONPATH": python_path})
    res = subprocess.run(cli_cmd, env=env)
    if res.returncode == 0:
        print(f"\n✅ 處理完成！結果已儲存至 {output_base}")
        if export_epub:
            from literature_parser.services.exporter.epub_exporter import EpubExporter
            doc_name = filepath.stem
            target_out = output_base / doc_name
            try:
                if doc_type == "literature":
                    EpubExporter.export_literature(target_out)
                else:
                    EpubExporter.export_book(target_out)
            except Exception as e:
                logger.error("EPUB export failed for '%s': %s", doc_name, e)
                print(f"  [!] EPUB 匯出失敗: {e}")
        return True
    else:
        print("\n⚠️ 處理過程中遇到警告或錯誤，請檢視 logs/process.log 或 data/needs_review/")
        return False


def cmd_process(args):
    """Processes a single document file."""
    filepath = Path(args.file)
    success = _run_process_pipeline(
        filepath,
        doc_type=args.type,
        ignore_battery=args.ignore_battery,
        export_epub=getattr(args, "epub", False)
    )
    if not success:
        sys.exit(1)


def cmd_epub(args):
    """Exports a markdown file, literature directory, or book directory to EPUB."""
    from literature_parser.services.exporter.epub_exporter import EpubExporter

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"🛑 錯誤：找不到指定的路徑: {target_path}")
        sys.exit(1)

    output_path = Path(args.output) if getattr(args, "output", None) else None
    engine = getattr(args, "engine", "auto")
    chapter = getattr(args, "chapter", None)

    try:
        if target_path.is_file() and target_path.suffix.lower() == ".md":
            res = EpubExporter.export_literature(target_path, output_epub_path=output_path, engine=engine)
        elif target_path.is_dir():
            if (target_path / "chapters").exists():
                res = EpubExporter.export_book(target_path, output_epub_path=output_path, chapter=chapter, engine=engine)
            else:
                res = EpubExporter.export_literature(target_path, output_epub_path=output_path, engine=engine)
        else:
            print(f"🛑 錯誤：無法識別的目標檔案或資料夾: {target_path}")
            sys.exit(1)

        print(f"\n🎉 [EPUB 完成] 電子書產出路徑: {res}")
    except Exception as e:
        logger.error("EPUB export failed: %s", e, exc_info=True)
        print(f"🛑 錯誤：EPUB 匯出失敗: {e}")
        sys.exit(1)


def cmd_batch(args):
    """
    Processes ALL PDF/EPUB files in a given directory, one-by-one, with
    hardware safety checks between each file to prevent system overload.
    """
    input_dir = Path(args.directory)
    if not input_dir.is_dir():
        print(f"🛑 錯誤：目錄不存在: {input_dir}")
        sys.exit(1)

    all_files = sorted(set(
        f for pat in ["*.pdf", "*.epub", "*.PDF", "*.EPUB"]
        for f in input_dir.glob(pat)
    ))

    if not all_files:
        print(f"ℹ️ 目錄內沒有找到 PDF/EPUB 檔案: {input_dir}")
        return

    doc_type = args.type
    if not doc_type:
        parent_name = input_dir.name.lower()
        doc_type = "literature" if parent_name in ("literature", "journals", "papers") else "book"
    elif doc_type == "journal":
        doc_type = "literature"

    print(f"\n{'='*65}")
    print(f"📦 [BATCH] 批次處理: {len(all_files)} 個檔案 ({doc_type.upper()})")
    print(f"{'='*65}\n")

    success, failed, skipped = [], [], []

    for idx, fpath in enumerate(all_files, 1):
        print(f"\n[{idx:02d}/{len(all_files):02d}] 📄 {fpath.name}")

        hw = check_hardware_safety(ignore_battery=getattr(args, "ignore_battery", False))
        if not hw["safe_for_batch_ocr"]:
            reason = "; ".join(hw.get("reasons", []))
            print(f"  ⏸️  硬體資源不足，暫停批次: {reason}")
            skipped.extend(f.name for f in all_files[idx-1:])
            break

        try:
            ok = _run_process_pipeline(
                fpath,
                doc_type=doc_type,
                ignore_battery=getattr(args, "ignore_battery", False),
                export_epub=getattr(args, "epub", False)
            )
            if ok:
                success.append(fpath.name)
            else:
                failed.append(fpath.name)
        except Exception as e:
            logger.error("Batch: unexpected error for '%s': %s", fpath.name, e)
            failed.append(fpath.name)

        if idx < len(all_files):
            time.sleep(1.5)

    print(f"\n{'='*65}")
    print(f"📊 [BATCH 完成] 成功: {len(success)} | 失敗: {len(failed)} | 跳過: {len(skipped)}")
    if failed:
        print(f"  ❌ 失敗清單: {', '.join(failed)}")
    if skipped:
        print(f"  ⏭️  跳過清單: {', '.join(skipped)}")
    print(f"{'='*65}\n")
