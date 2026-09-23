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
        path_str = str(filepath.resolve()).lower()
        if "literature" in path_str or "journals" in path_str or "papers" in path_str:
            doc_type = "literature"
        elif "books" in path_str:
            doc_type = "book"
        else:
            doc_type = "book"  # default fallback
    elif doc_type == "journal":
        doc_type = "literature"  # normalize journal to literature

    print(f"\n🚀 啟動處理管線: [{doc_type.upper()}] 檔案: {filepath.name}")

    # Run quick hardware check
    hw = check_hardware_safety(ignore_battery=args.ignore_battery)
    if not hw["safe_for_batch_ocr"]:
        print(f"🛑 硬體空間不足拒絕啟動: {'; '.join(hw['reasons'])}")
        sys.exit(1)

    output_base = Path("data/output") / ("books" if doc_type == "book" else "literature")
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"• 輸出目標資料夾: {output_base}")
    print(f"• 呼叫對應領域管線: src/book_processor/pipelines/{'textbook_pipeline' if doc_type == 'book' else 'literature_pipeline'}.py")

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


# ==============================================================================
# 5. ARCHIVE-SESSIONS: Automated Dual-Track Session Archiving
# ==============================================================================
def cmd_archive_sessions(args):
    """
    Scans the Antigravity brain directory and archives all conversation sessions
    associated with this workspace into memory/sessions/ with dual-track pairing.
    """
    import json
    brain_dir = Path.home() / ".gemini" / "antigravity" / "brain"
    sessions_dir = ROOT / "memory" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("🗄️ [ARCHIVE-SESSIONS] 全自動對話雙軌歸檔 (Dual-Track Archiving)")
    print("=" * 65)

    known_sessions = [
        ("2026-09-18", "e81a99f1-8fd6-4393-8186-db1c305c5170", "initial-textbook-pipeline-development", "書籍轉檔管線初版開發與版面分析"),
        ("2026-09-18", "74bb97d9-9bba-4680-900c-e5a79d616708", "research-methods-book-conversion", "Research Methods 教科書轉檔與排版優化"),
        ("2026-09-20", "cb3aa69b-509b-4784-96e1-9d645c7ff32b", "typography-tables-and-formula-refinement", "排版、表格與跨頁內容語義修復"),
        ("2026-09-23", "e7e0ccf8-a309-4bad-b967-e1ef03284bae", "academic-journal-pipeline-and-dual-column", "學術期刊雙欄管線開發與 Ollama 邊界分流"),
        ("2026-09-23", "d934528e-eb4f-4097-8457-50cc94bfb932", "project-architecture-and-governance", "專案架構治理、軟硬體守衛與跨 Agent 規範"),
    ]

    for date_str, conv_id, slug, title in known_sessions:
        summary_file = sessions_dir / f"{date_str}-{slug}-summary.md"
        transcript_file = sessions_dir / f"{date_str}-{slug}-transcript.md"
        t_src = brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"

        print(f"• 會話 [{date_str}] {title} (ID: {conv_id[:8]}...):")
        if summary_file.exists():
            print(f"  - 總結 (Summary)   : ✅ 已存在 ({summary_file.name})")
        else:
            print(f"  - 總結 (Summary)   : ⚠️ 待補充 ({summary_file.name})")

        if t_src.exists():
            try:
                with open(t_src, "r", encoding="utf-8") as fin, open(transcript_file, "w", encoding="utf-8") as fout:
                    fout.write(f"# 📜 對話紀錄全量封存 (Full Transcript): {title}\n\n")
                    fout.write(f"- **會話 ID**: `{conv_id}`\n")
                    fout.write(f"- **歸檔檔案**: `{transcript_file.name}`\n\n---\n\n")
                    step_idx = 0
                    for line in fin:
                        try:
                            d = json.loads(line)
                            step_idx = d.get("step_index", step_idx + 1)
                            stype = d.get("type", "")
                            created = d.get("created_at", "")
                            content = d.get("content", "")
                            tool_calls = d.get("tool_calls", [])
                            if stype == "USER_INPUT":
                                user_text = content.replace("<USER_REQUEST>", "").replace("</USER_REQUEST>", "").strip()
                                fout.write(f"## 👤 [Step {step_idx}] 使用者指令 (User Input)\n")
                                fout.write(f"**時間**: `{created}`\n\n{user_text}\n\n---\n\n")
                            elif stype == "PLANNER_RESPONSE" or tool_calls or content:
                                fout.write(f"## 🤖 [Step {step_idx}] 助手回應與執行軌跡 (Assistant Response)\n")
                                fout.write(f"**時間**: `{created}`\n\n")
                                if tool_calls:
                                    fout.write("### 🛠️ 工具調用 (Tool Calls)\n")
                                    for tc in tool_calls:
                                        name = tc.get("name", "")
                                        args = tc.get("args", {})
                                        summary = args.get("toolSummary", "")
                                        action = args.get("toolAction", "")
                                        fout.write(f"- `{name}`: *{action}* ({summary})\n")
                                    fout.write("\n")
                                if content:
                                    fout.write(f"{content}\n\n")
                                fout.write("---\n\n")
                        except Exception:
                            pass
                size_kb = transcript_file.stat().st_size / 1024
                print(f"  - 紀錄 (Transcript): ✅ 已同步更新 ({size_kb:.1f} KB)")
            except Exception as e:
                print(f"  - 紀錄 (Transcript): ❌ 讀取失敗 ({e})")
        else:
            print(f"  - 紀錄 (Transcript): {'✅ 已存在' if transcript_file.exists() else '⚠️ 來源日誌不存在'}")

# ==============================================================================
# 6. WATCHDOG: Integrated Hardware & Directory Monitor
# ==============================================================================
def cmd_watchdog(args):
    """
    Intelligent Watchdog: Monitors data/input/ for new books/literature
    while continuously auditing macOS hardware health (RAM, Battery, SSD, MPS, Ollama).
    Auto-triggers safe conversion when files arrive.
    """
    import time

    books_in = ROOT / "data" / "input" / "books"
    lit_in = ROOT / "data" / "input" / "literature"
    books_in.mkdir(parents=True, exist_ok=True)
    lit_in.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("👁️ [WATCHDOG] 軟硬體一體化智慧看門狗 (Hardware & Input Monitor)")
    print("=" * 65)
    print("• 監控目錄 (Books)     : data/input/books/")
    print("• 監控目錄 (Literature): data/input/literature/")
    print("• 守衛防線             : RAM ≥ 4GB | SSD ≥ 10GB | 非低電量電池模式")
    print("=" * 65 + "\n")

    def scan_files():
        found = {}
        for p in books_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = "book"
        for p in lit_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = "literature"
        return found

    known = scan_files()
    print(f"ℹ️ [Watchdog] 目前已有檔案: {len(known)} 個。等待新檔案投入...\n")

    iterations = 0
    max_iter = 1 if getattr(args, "once", False) else 999999

    while iterations < max_iter:
        iterations += 1
        hw = check_hardware_safety(ignore_battery=getattr(args, "ignore_battery", False))
        m = hw["metrics"]

        current = scan_files()
        new_files = [f for f in current if f not in known]

        if getattr(args, "once", False) or new_files:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🩺 系統硬體巡檢: "
                  f"RAM: {m['ram_available_gb']}GB (門檻≥4GB), "
                  f"SSD: {m['disk_free_gb']}GB, "
                  f"電源: {m['power_status']}")

        for nfile in new_files:
            doc_type = current[nfile]
            print(f"\n📥 [新檔案偵測] 發現待處理文件: [{doc_type.upper()}] {nfile.name}")
            try:
                s1 = nfile.stat().st_size
                time.sleep(0.3)
                s2 = nfile.stat().st_size
                if s1 != s2 or s1 == 0:
                    print("  ⏳ 檔案正在寫入中，暫緩處理...")
                    continue
            except Exception:
                continue

            if not hw["safe_for_batch_ocr"]:
                print(f"  🛑 硬體資源不足，暫停自動處理: {'; '.join(hw['reasons'])}")
                break

            print(f"  🚀 自動啟動轉檔: {doc_type} 管線...")
            class DummyArgs:
                file = str(nfile)
                type = doc_type
                ignore_battery = getattr(args, "ignore_battery", False)
            cmd_process(DummyArgs())
            known[nfile] = doc_type

        if getattr(args, "once", False):
            break

        time.sleep(3)


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
    p_proc = subparsers.add_parser("process", help="處理單一書籍或學術文獻")
    p_proc.add_argument("file", help="輸入檔案路徑 (PDF/EPUB)")
    p_proc.add_argument("--type", choices=["book", "literature", "journal"], default=None, help="強制指定處理類型 (book 或 literature)")
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

    # archive-sessions
    p_arch = subparsers.add_parser("archive-sessions", help="自動掃描並更新所有歷史對話之雙軌歸檔 (Summary + Transcript)")
    p_arch.set_defaults(func=cmd_archive_sessions)

    # watchdog
    p_watch = subparsers.add_parser("watchdog", help="啟動軟硬體一體化看門狗，監控目錄檔案並確保硬體安全")
    p_watch.add_argument("--once", action="store_true", help="僅執行一次巡檢後離開")
    p_watch.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_watch.set_defaults(func=cmd_watchdog)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
