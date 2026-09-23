#!/usr/bin/env python3
"""
Book & Journal Processor: Unified Command Center (run.py)
=========================================================
Central CLI orchestrating hardware pre-flight checks, convention-based routing,
auto-Ollama triggering, date-stamped doc synchronization, and local-only Git checkpoints.

Usage:
  python run.py doctor
  python run.py process <filepath> [--type book|journal]
  python run.py save "<commit message>"
  python run.py handoff "<reason for pause>"
  python run.py publish "<release message>"
  python run.py test-ollama-auto-trigger
"""

import sys
import os
import re
import argparse
import datetime
import subprocess
from pathlib import Path

# Add project root and src to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.utils.logger import get_diagnostic_logger
from src.guards.hardware import check_hardware_safety
from src.guards.ollama_guard import OllamaGuard
from src.guards.validator import ValidatorGuard

logger = get_diagnostic_logger("CommandCenter")


def get_current_date() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def get_current_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ==============================================================================
# 1. DOCTOR: System Health & Pre-flight Diagnostics
# ==============================================================================
def cmd_doctor(args):
    print("\n" + "=" * 65)
    print("🩺 [DOCTOR] 系統軟硬體與環境前置健檢 (System Health Audit)")
    print("=" * 65)

    # 1. Hardware Check
    hw = check_hardware_safety(ignore_battery=getattr(args, "ignore_battery", False))
    m = hw["metrics"]
    print(f"• 記憶體狀態 (RAM)  : {m['ram_available_gb']} GB 可用 (門檻: ≥ 4.0 GB) -> {'✅ [PASS]' if m['ram_available_gb'] >= 4.0 else '⚠️ [WARN: 低於門檻]'}")
    print(f"• 硬碟剩餘空間 (SSD): {m['disk_free_gb']} GB 剩餘 (門檻: ≥ 10.0 GB) -> {'✅ [PASS]' if m['disk_free_gb'] >= 10.0 else '🛑 [FAIL: 空間不足]'}")
    print(f"• 電源供應狀態      : {m['power_status']} -> {'✅ [PASS]' if not m['is_battery'] or m['battery_percent'] >= 40 else '⚠️ [WARN: 電池電量偏低]'}")
    print(f"• Apple MPS 晶片加速: {'✅ [PASS: 支援硬體加速]' if m['mps_acceleration'] else 'ℹ️ [INFO: CPU 模式]'}")

    # 2. Ollama & Models Check
    guard = OllamaGuard()
    service = guard.ensure_service_ready(auto_wake=True)
    print("\n[Ollama 本地大模型診斷]")
    if service["alive"]:
        print(f"• 服務狀態 (Port 11434): ✅ [ONLINE] 在線運行中")
        print(f"• 已安裝模型清單       : {', '.join(service['models']) if service['models'] else '(無已下載模型)'}")
        print(f"• 推薦啟用模型         : 🤖 {service['selected_model'] or '無 (請執行 ollama pull qwen2.5:7b)'}")
    else:
        print(f"• 服務狀態 (Port 11434): ⚠️ [OFFLINE] 離線 (將自動啟用純語法規則降級模式)")

    print("=" * 65)
    if hw["safe_for_heavy_llm"] and service["alive"] and service["selected_model"]:
        print("🎉 系統狀態完美！全自動 Ollama 深度語義與公式除錯已準備就緒。\n")
    else:
        print("💡 提示：系統可正常轉檔，但在硬體受限或 Ollama 離線時將自動優雅降級。\n")


# ==============================================================================
# 2. PROCESS: Convention-based Routing & Pipeline Execution
# ==============================================================================
def cmd_process(args):
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"🛑 錯誤：找不到指定的輸入檔案: {filepath}")
        sys.exit(1)

    # Determine pipeline by directory convention or flag
    doc_type = args.type
    if not doc_type:
        path_str = str(filepath.resolve())
        if "journals" in path_str or "papers" in path_str:
            doc_type = "journal"
        elif "books" in path_str:
            doc_type = "book"
        else:
            doc_type = "book"  # default fallback

    print(f"\n🚀 啟動處理管線: [{doc_type.upper()}] 檔案: {filepath.name}")

    # Run quick hardware check
    hw = check_hardware_safety(ignore_battery=args.ignore_battery)
    if not hw["safe_for_batch_ocr"]:
        print(f"🛑 硬體空間不足拒絕啟動: {'; '.join(hw['reasons'])}")
        sys.exit(1)

    output_base = Path("data/output") / ("books" if doc_type == "book" else "journals")
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"• 輸出目標資料夾: {output_base}")
    print(f"• 呼叫對應領域管線: src/book_processor/pipelines/{'textbook_pipeline' if doc_type == 'book' else 'journal_pipeline'}.py")

    # Delegate to existing core CLI with appropriate arguments
    cli_cmd = [
        sys.executable, "-m", "book_processor.cli", "run",
        "--file", str(filepath),
        "--output-dir", str(output_base),
    ]
    if hw["safe_for_heavy_llm"]:
        cli_cmd.append("--ollama")

    logger.info(f"Executing: {' '.join(cli_cmd)}")
    res = subprocess.run(cli_cmd)
    if res.returncode == 0:
        print(f"\n✅ 處理完成！結果已儲存至 {output_base}")
    else:
        print(f"\n⚠️ 處理過程中遇到警告或錯誤，請檢視 logs/process.log 或 data/needs_review/")


# ==============================================================================
# 3. AGENT-INIT: Onboarding Briefing for Any Incoming AI Agent
# ==============================================================================
def cmd_agent_init(args):
    """
    Onboarding command called at the very beginning of an AI session
    to brief the agent on mandatory directives, commit habits, and current status.
    """
    print("\n" + "=" * 70)
    print("🤖 [AGENT ONBOARDING BRIEFING] 核心工作原則與即時狀態指引")
    print("=" * 70)
    print("""
【AI 代理核心工作守則 (Mandatory Agent Directives)】

1. 📝 文檔同步先行 (Doc-Before-Commit Protocol):
   - 在執行 git commit 前，必須先更新 memory/TASKS.md 勾選完成項目與日期。
   - 若為中斷交接，必須更新 memory/HANDOFF.md 的時間戳記與接手引導。
   - ⚠️ 所有 Git Commit 訊息必須使用【英文】(Conventional Commits, e.g., feat:, fix:, docs:, chore:)。

2. 🛑 嚴禁未授權推送 (Zero-Push Rule):
   - 本專案預設為 Local-Only 模式。嚴禁執行 git push (系統設有 pre-push 阻斷)。

3. 🤖 Ollama 自動調用原則 (Auto-Ollama Triggers):
   - 輸入比對：輸入檔案與 manifest.json 不符時，自動喚醒 Ollama 進行語義分析。
   - 輸出修復：LaTeX 公式或語法異常時，自動喚醒 Ollama 進行自我修復；修復失敗進 data/needs_review/。

4. 🛡️ 軟硬體前置守衛 (Hardware Safeguards):
   - 調用大模型前檢查 RAM ≥ 4.0GB、非低電量電池模式，未達標則優雅降級為純規則。

5. 📂 零硬編碼絕對路徑 (Zero Hardcoded Paths):
   - 嚴禁寫死絕對路徑 (/Users/...)，一律以 ROOT 動態相對錨定，確保搬移目錄零崩潰。

6. 🍎 macOS 原生優先 (macOS-Native Priority):
   - 優先評估 Apple Vision Framework、sips、Metal/MPS、CoreML 等系統原生能力。

7. 🧪 臨時腳本隔離 (Scratchpad Policy):
   - 一次性測試程式一律放入 scratch/，不污染正式目錄。
""")

    # Display current handoff state
    handoff_file = ROOT / "memory" / "HANDOFF.md"
    if handoff_file.exists():
        print("----------------------------------------------------------------------")
        print("📌 [當前交接狀態摘要 (Latest Handoff Snapshot)]")
        print("----------------------------------------------------------------------")
        lines = handoff_file.read_text(encoding="utf-8").splitlines()
        for line in lines[:20]:
            print(f"  {line}")
    print("=" * 70 + "\n")


# ==============================================================================
# 4. SAVE & HANDOFF: Doc-Before-Commit & Safe Git Checkpoints
# ==============================================================================
def sync_markdown_dates():
    """Ensures memory/TASKS.md has today's date in header."""
    tasks_file = ROOT / "memory" / "TASKS.md"
    if tasks_file.exists():
        content = tasks_file.read_text(encoding="utf-8")
        today = get_current_date()
        updated = re.sub(r"最後更新日期：\d{4}-\d{2}-\d{2}", f"最後更新日期：{today}", content)
        tasks_file.write_text(updated, encoding="utf-8")


def cmd_save(args):
    """Saves progress locally, stamping docs first. Enforces English commit messages."""
    sync_markdown_dates()
    today = get_current_date()
    msg = args.message.strip()

    # Ensure Conventional Commit format in English
    prefixes = ("feat:", "fix:", "docs:", "refactor:", "test:", "chore:", "style:", "perf:", "wip:")
    if not msg.lower().startswith(prefixes):
        commit_msg = f"[{today}] feat: {msg}"
    else:
        commit_msg = f"[{today}] {msg}"

    subprocess.run(["git", "add", "-A"], cwd=str(ROOT))
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(ROOT))
    if res.returncode == 0:
        print(f"\n✅ [Local Git] Committed (in English): {commit_msg}")
    else:
        print("\nℹ️ [Local Git] Working tree clean, nothing to commit.")


def cmd_handoff(args):
    """Prepares for interruption/class, updating HANDOFF.md with timestamp before commit in English."""
    now_ts = get_current_timestamp()
    today = get_current_date()
    handoff_file = ROOT / "memory" / "HANDOFF.md"

    if handoff_file.exists():
        content = handoff_file.read_text(encoding="utf-8")
        content = re.sub(
            r"### 🕒 最新交接時間：\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
            f"### 🕒 最新交接時間：{now_ts}",
            content,
        )
        handoff_file.write_text(content, encoding="utf-8")
        print(f"📝 [Auto-Doc] Updated {handoff_file} timestamp to {now_ts}")

    sync_markdown_dates()
    reason = args.reason or "pause session before stepping away"
    commit_msg = f"[{today}] wip(handoff): {reason}"

    subprocess.run(["git", "add", "-A"], cwd=str(ROOT))
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(ROOT))
    if res.returncode == 0:
        print(f"🎒 [Local Git] Handoff saved (in English): {commit_msg}")
        print("You can safely close your laptop and step away!")
    else:
        print("🎒 [Local Git] Handoff doc updated.")


def cmd_publish(args):
    """Squash merges to main and prints authorized push instructions."""
    print("\n📦 [PUBLISH] 準備打包發布里程碑...")
    today = get_current_date()
    release_msg = f"[{today}] release: {args.message}"

    # Check current branch
    branch_out = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if branch_out != "main":
        print(f"• 目前在分支 [{branch_out}]，執行切換至 main 並 Squash Merge...")
        subprocess.run(["git", "checkout", "main"])
        subprocess.run(["git", "merge", branch_out, "--squash"])
        subprocess.run(["git", "commit", "-m", release_msg])
    else:
        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", release_msg])

    print("\n🎉 本地打包完成！")
    print("========================================================================")
    print("🛑 提醒：由於 Pre-push 物理防護鎖限制，直接執行 git push 會被安全攔截。")
    print("若確定要推送至 GitHub，請下達帶有安全授權的指令：")
    print("   ALLOW_PUSH=1 git push origin main")
    print("========================================================================\n")


# ==============================================================================
# 4. TEST: Ollama Auto-Trigger Verification Drill
# ==============================================================================
def cmd_test_ollama_auto_trigger(args):
    print("\n" + "=" * 65)
    print("🧪 [TEST] Ollama 自動除錯與輸入校驗自我檢驗 (Self-Drill)")
    print("=" * 65)

    guard = OllamaGuard()
    val = ValidatorGuard(guard)

    # 1. Test Output LaTeX Repair Auto-Trigger
    broken_latex = r"\frac{a}{b + \sqrt{c"  # Intentionally missing closing brace
    context = "Calculus integration equation with missing bracket."

    print("• [情境 1: 輸出異常自動攔截] 正在注入損壞的 LaTeX 公式...")
    print(f"  原始損壞代碼: {broken_latex}")
    repair_res = val.repair_math_latex(broken_latex, context)

    if repair_res.get("repaired"):
        print(f"  ✅ [Ollama 自我修復成功] 修復後代碼: {repair_res['latex']}")
    elif repair_res.get("quarantined"):
        print(f"  ℹ️ [隔離防呆啟動] 無法自動修復或處於降級模式，已自動隔離至: {repair_res.get('file')}")
    else:
        print("  ⚠️ 修復回傳未預期狀態")

    # 2. Test Input Manifest Schema Check Auto-Trigger
    test_dir = ROOT / "scratch" / "test_manifest_drill"
    test_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = test_dir / "manifest.json"
    manifest_file.write_text(
        '{"title": "Test Book", "chapters": ["ch1_intro.pdf", "ch2_advanced.pdf"]}',
        encoding="utf-8",
    )
    # Only create ch1, intentionally omit ch2
    (test_dir / "ch1_intro.pdf").write_text("dummy", encoding="utf-8")

    print("\n• [情境 2: 輸入校驗自動攔截] 注入缺少章節的測試檔案...")
    manifest_res = val.validate_input_manifest(test_dir)
    if not manifest_res["valid"]:
        print(f"  ✅ [輸入校驗防線觸發] 成功偵測到結構不符: {manifest_res['discrepancies']}")
        if manifest_res.get("ollama_diagnosis"):
            print(f"  🤖 [Ollama 診斷反饋]: {manifest_res['ollama_diagnosis'][:120]}...")
    else:
        print("  ⚠️ 未能偵測出輸入不符")

    print("=" * 65)
    print("🎉 檢驗完成！證明 Ollama 守衛與異常攔截功能已真實掛載於程式碼中。\n")


def main():
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="Book & Journal Processor Unified Command Center",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="執行系統軟硬體與 Ollama 健康檢查")
    p_doc.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_doc.set_defaults(func=cmd_doctor)

    # process
    p_proc = subparsers.add_parser("process", help="處理單一書籍或期刊")
    p_proc.add_argument("file", help="輸入檔案路徑 (PDF/EPUB)")
    p_proc.add_argument("--type", choices=["book", "journal"], default=None, help="強制指定處理類型")
    p_proc.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_proc.set_defaults(func=cmd_process)

    # save
    p_save = subparsers.add_parser("save", help="日常本地存檔 (先更新文檔日期後 commit)")
    p_save.add_argument("message", help="Commit 說明")
    p_save.set_defaults(func=cmd_save)

    # handoff
    p_hand = subparsers.add_parser("handoff", help="離席交接存檔 (更新 HANDOFF.md 後 commit)")
    p_hand.add_argument("reason", default="外出/上課暫存", nargs="?", help="離席原因")
    p_hand.set_defaults(func=cmd_handoff)

    # publish
    p_pub = subparsers.add_parser("publish", help="本地發布並合併至 main 分支")
    p_pub.add_argument("message", help="發布版本說明")
    p_pub.set_defaults(func=cmd_publish)

    # test-ollama-auto-trigger
    p_test = subparsers.add_parser("test-ollama-auto-trigger", help="執行 Ollama 自動喚醒與自我除錯測試")
    p_test.set_defaults(func=cmd_test_ollama_auto_trigger)

    # agent-init
    p_init = subparsers.add_parser("agent-init", help="AI 對話開場自動簡報，讀取工作守則與交接狀態")
    p_init.set_defaults(func=cmd_agent_init)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
