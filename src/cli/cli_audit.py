"""
CLI Format & Quality Audit Command
===================================
Inspects Markdown output against all 8 quality dimensions:
- Structure, title, and authors
- Abstract integrity and placement
- Table notes and caption isolation
- LaTeX formula delimiters and currency protection
- References formatting and unparenthesized years
- Running headers, footers, and orphan page noise
- Optional deep Ollama semantic audit and auto-repair
"""

import json
import sys
from pathlib import Path

from src.cli.common import ROOT
from doc_processor.verification.format_auditor import FormatAuditor
from doc_processor.verification.ollama_verifier import OllamaVerifier


def cmd_audit(args):
    """
    Dedicated format and typography audit command.
    Inspects Markdown output against all 8 quality dimensions.
    Optionally calls Ollama for deep semantic review.
    Optionally applies auto-repair.
    """
    print("\n" + "=" * 65)
    print("📋 [AUDIT] 文獻排版與格式深度稽核 (Format & Quality Audit)")
    print("=" * 65)

    ollama = None
    if getattr(args, "ollama", False):
        print("🤖 啟用 Ollama 本地大模型深度語義與排版核對...")
        from src.guards.ollama_guard import OllamaGuard
        guard = OllamaGuard()
        service = guard.ensure_service_ready(auto_wake=True)
        if service.get("alive"):
            ollama = OllamaVerifier(semantic_model=service.get("selected_model"), auto_start=True)
            print(f"✅ Ollama 模型就緒: {ollama.semantic_model}")
        else:
            print("⚠️ [WARN] Ollama 服務離線，降級為純規則掃描模式。")
            ollama = None

    target = Path(args.target) if hasattr(args, "target") and args.target else None
    audit_all = getattr(args, "all", False)

    md_files = []
    if audit_all or not target:
        lit_dir = ROOT / "data" / "output" / "literature"
        if lit_dir.exists():
            for d in sorted(lit_dir.iterdir()):
                if d.is_dir():
                    candidates = [f for f in d.glob("*.md") if not f.name.endswith(("_Verified.md", "processing_status.md", "audit_report.md"))]
                    md_files.extend(candidates)
    elif target.is_file():
        md_files = [target]
    elif target.is_dir():
        candidates = [f for f in target.glob("*.md") if not f.name.endswith(("_Verified.md", "processing_status.md", "audit_report.md"))]
        if candidates:
            md_files.extend(candidates)
        else:
            for d in sorted(target.iterdir()):
                if d.is_dir():
                    sub_cands = [f for f in d.glob("*.md") if not f.name.endswith(("_Verified.md", "processing_status.md", "audit_report.md"))]
                    md_files.extend(sub_cands)

    if not md_files:
        print(f"🛑 找不到可供稽核的 Markdown 檔案。")
        sys.exit(1)

    print(f"🔍 掃描目標: 共有 {len(md_files)} 篇文獻待稽核\n")

    auditor = FormatAuditor(is_literature=True)
    all_passed = True
    total_errors = 0
    total_warnings = 0

    for idx, md_path in enumerate(md_files, 1):
        doc_dir = md_path.parent
        doc_name = md_path.stem

        if getattr(args, "fix", False):
            with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            repaired_text, rep_count = auditor.auto_repair(content)
            if rep_count > 0:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(repaired_text)
                print(f"[{idx}/{len(md_files)}] 🔧 已自動修復 {rep_count} 處瑕疵: {doc_name}")

        report = auditor.audit_file(md_path, ollama_verifier=ollama)

        # Write reports
        report_md_path = doc_dir / "audit_report.md"
        report_md_path.write_text(report.to_markdown(), encoding="utf-8")
        report_json_path = doc_dir / "audit_report.json"
        report_json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

        status_icon = "✅ [PASS]" if report.passed else "⚠️ [FAIL]"
        print(f"[{idx}/{len(md_files)}] {status_icon} {doc_name[:45]:45s} 得分: {report.score_percent:5.1f}% | 錯: {report.error_count} 警: {report.warning_count}")

        if not report.passed:
            all_passed = False
            total_errors += report.error_count
            total_warnings += report.warning_count
            for iss in report.issues:
                if iss.severity == "ERROR":
                    print(f"    ❌ [{iss.category}] 行 {iss.line_num or '-'}: {iss.message} (片段: {iss.snippet[:40]})")
                elif iss.severity == "WARNING" and len(report.issues) <= 5:
                    print(f"    ⚠️ [{iss.category}] 行 {iss.line_num or '-'}: {iss.message} (片段: {iss.snippet[:40]})")

        if report.ollama_review:
            first_line = report.ollama_review.strip().splitlines()[0] if report.ollama_review.strip() else ""
            print(f"    🤖 [Ollama 診斷摘要]: {first_line[:100]}")

        if report.recipe_recommendations:
            for rec in report.recipe_recommendations[:2]:
                print(f"    💡 [手冊修復建議]: {rec['command']}")

    print("\n" + "=" * 65)
    if all_passed:
        print(f"🎉 稽核大獲全勝！全數 {len(md_files)} 篇文獻排版格式均達到黃金標準！")
    else:
        print(f"⚠️ 稽核完畢，累計發現 {total_errors} 個重大錯誤與 {total_warnings} 個警告。")
        print(f"💡 詳細報告已寫入各文獻目錄之 audit_report.md。")
    print("=" * 65 + "\n")

    if not all_passed and not getattr(args, "no_exit_error", False):
        sys.exit(1)
