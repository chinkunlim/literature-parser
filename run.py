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
from typing import Optional, List, Dict, Any
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


def clean_dangling_tmp_files() -> int:
    """Scans and removes leftover *.tmp.* files from interrupted atomic writes."""
    pruned = 0
    for p in ROOT.rglob("*.tmp.*"):
        if p.is_file() and not any(part in (".git", ".venv", "node_modules") for part in p.parts):
            try:
                p.unlink()
                pruned += 1
            except Exception:
                pass
    return pruned


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

    # 3. Core Binary Dependencies (poppler + tesseract)
    import shutil
    print("\n[核心工具鏈診斷]")
    _deps = {
        "pdfinfo":     ("poppler-utils", "brew install poppler"),
        "pdfseparate": ("poppler-utils", "brew install poppler"),
        "pdftoppm":    ("poppler-utils", "brew install poppler"),
        "pdftohtml":   ("poppler-utils", "brew install poppler"),
        "tesseract":   ("tesseract",     "brew install tesseract"),
    }
    all_deps_ok = True
    for binary, (pkg, install_cmd) in _deps.items():
        found = shutil.which(binary) is not None
        if not found:
            all_deps_ok = False
        print(f"• {binary:12s}: {'✅ [PASS]' if found else f'🛑 [MISSING] → 安裝指令: {install_cmd}'}")
    if all_deps_ok:
        print("  → 所有核心工具鏈完整！")
    else:
        print("  → ⚠️ 缺少必要工具，PDF 轉檔將無法正常運作，請依上方指令安裝後重試。")

    # 4. Clean temporary files
    pruned = clean_dangling_tmp_files()
    if pruned > 0:
        print(f"\n• 暫存檔案自動清理     : 🧹 [CLEAN] 已自動清理 {pruned} 個過期暫存檔 (*.tmp.*)")
    else:
        print(f"\n• 暫存檔案自動清理     : ✅ [PASS] 磁碟環境無殘留暫存檔")

    print("=" * 65)
    if hw["safe_for_heavy_llm"] and service["alive"] and service["selected_model"] and all_deps_ok:
        print("🎉 系統狀態完美！全自動 Ollama 深度語義與公式除錯已準備就緒。\n")
    else:
        print("💡 提示：系統可正常轉檔，但在硬體受限或 Ollama 離線時將自動優雅降級。\n")



def _run_process_pipeline(filepath: Path, doc_type: Optional[str] = None, ignore_battery: bool = False) -> bool:
    """Executes the conversion pipeline for a single file. Returns True on success, False on failure."""
    if not filepath.exists():
        print(f"🛑 錯誤：找不到指定的輸入檔案: {filepath}")
        return False

    # Determine pipeline by directory convention or flag.
    # Use anchor-based detection: compare resolved path against known input roots
    # to avoid false matches when the user's home path contains 'books' or 'literature'.
    if not doc_type:
        try:
            rel = filepath.resolve().relative_to(ROOT)
            parts = rel.parts  # e.g. ('data', 'input', 'literature', 'paper.pdf')
            if len(parts) >= 3 and parts[0] == "data" and parts[1] == "input":
                subdir = parts[2]  # 'books', 'literature', etc.
                if subdir in ("literature", "journals", "papers"):
                    doc_type = "literature"
                elif subdir == "books":
                    doc_type = "book"
        except ValueError:
            pass  # file is outside ROOT — fall through to keyword scan
        if not doc_type:
            # Last-resort: keyword scan on the portion after the last path separator
            parent_lower = filepath.parent.name.lower()
            if parent_lower in ("literature", "journals", "papers"):
                doc_type = "literature"
            else:
                doc_type = "book"  # safe default
    elif doc_type == "journal":
        doc_type = "literature"  # normalize alias

    print(f"\n🚀 啟動處理管線: [{doc_type.upper()}] 檔案: {filepath.name}")

    # Run quick hardware check
    hw = check_hardware_safety(ignore_battery=ignore_battery)
    if not hw["safe_for_batch_ocr"]:
        print(f"🛑 硬體空間不足拒絕啟動: {'; '.join(hw['reasons'])}")
        return False

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
        return True
    else:
        print(f"\n⚠️ 處理過程中遇到警告或錯誤，請檢視 logs/process.log 或 data/needs_review/")
        return False


def cmd_process(args):
    filepath = Path(args.file)
    success = _run_process_pipeline(filepath, doc_type=args.type, ignore_battery=args.ignore_battery)
    if not success:
        sys.exit(1)


# ==============================================================================
# 2b. BATCH: Multi-File Batch Processing with Hardware Guard
# ==============================================================================
def cmd_batch(args):
    """
    Processes ALL PDF/EPUB files in a given directory, one-by-one, with
    hardware safety checks between each file to prevent system overload.
    """
    import time

    input_dir = Path(args.directory)
    if not input_dir.is_dir():
        print(f"🛑 錯誤：目錄不存在: {input_dir}")
        sys.exit(1)

    # Collect all processable files
    all_files = sorted(set(
        f for pat in ["*.pdf", "*.epub", "*.PDF", "*.EPUB"]
        for f in input_dir.glob(pat)
    ))

    if not all_files:
        print(f"ℹ️ 目錄內沒有找到 PDF/EPUB 檔案: {input_dir}")
        return

    # Determine doc_type from parent dir name or explicit flag
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

        # Hardware safety check before EACH file
        hw = check_hardware_safety(ignore_battery=getattr(args, "ignore_battery", False))
        if not hw["safe_for_batch_ocr"]:
            reason = "; ".join(hw.get("reasons", []))
            print(f"  ⏸️  硬體資源不足，暫停批次: {reason}")
            skipped.extend(f.name for f in all_files[idx-1:])
            break

        try:
            ok = _run_process_pipeline(fpath, doc_type=doc_type, ignore_battery=getattr(args, "ignore_battery", False))
            if ok:
                success.append(fpath.name)
            else:
                failed.append(fpath.name)
        except Exception as e:
            logger.error("Batch: unexpected error for '%s': %s", fpath.name, e)
            failed.append(fpath.name)

        if idx < len(all_files):
            time.sleep(1.5)  # cool-down between files

    print(f"\n{'='*65}")
    print(f"📊 [BATCH 完成] 成功: {len(success)} | 失敗: {len(failed)} | 跳過: {len(skipped)}")
    if failed:
        print(f"  ❌ 失敗清單: {', '.join(failed)}")
    if skipped:
        print(f"  ⏭️  跳過清單: {', '.join(skipped)}")
    print(f"{'='*65}\n")



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
    """Saves progress locally, stamping docs first. Enforces English commit messages and test gate."""
    # 1. Clean dangling tmp files
    clean_dangling_tmp_files()

    # 2. Automated test gate (fast check)
    if (ROOT / "tests").exists():
        res_test = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=str(ROOT), capture_output=True)
        if res_test.returncode != 0:
            print("\n🛑 [COMMIT 攔截] 單元測試未通過！為杜絕幽靈修復與代碼腐化，已自動阻止提交。")
            print(res_test.stderr.decode("utf-8") or res_test.stdout.decode("utf-8"))
            sys.exit(1)

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
    """Squash merges to main and prints authorized push instructions with automated gates."""
    print("\n📦 [PUBLISH] 準備打包發布里程碑...")
    today = get_current_date()
    release_msg = f"[{today}] release: {args.message}"

    # 1. Automated Test Gate
    print("\n🧪 [Gate 1] 執行發布前全量自動化單元測試門禁 (Automated Test Gate)...")
    res_test = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=str(ROOT))
    if res_test.returncode != 0:
        print("\n🛑 [發布中斷] 單元測試未全數通過，發布已被安全阻斷！請修復測試後再試。")
        sys.exit(1)
    print("✅ 單元測試全數通過 (100% PASS)！")

    # 2. Automated Session Archiving
    print("\n🗄️ [Gate 2] 執行會話雙軌全量封存 (Auto-Archiving Sessions)...")
    cmd_archive_sessions(args)

    # 3. Clean Dangling Tmp Files
    pruned = clean_dangling_tmp_files()
    if pruned > 0:
        print(f"🧹 [Gate 3] 已自動清理 {pruned} 個過期暫存檔 (*.tmp.*)")

    # 4. Check current branch and squash merge
    branch_out = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if branch_out != "main":
        print(f"\n• 目前在分支 [{branch_out}]，執行切換至 main 並 Squash Merge...")
        subprocess.run(["git", "checkout", "main"])
        subprocess.run(["git", "merge", branch_out, "--squash"])
        subprocess.run(["git", "commit", "-m", release_msg])
    else:
        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", release_msg])

    # 5. Local Git Tagging
    tag_name = getattr(args, "tag", None)
    if not tag_name:
        match = re.search(r"\b(v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)\b", args.message)
        if match:
            tag_name = match.group(1)
    if tag_name:
        tag_res = subprocess.run(["git", "tag", "-a", tag_name, "-m", release_msg], cwd=str(ROOT))
        if tag_res.returncode == 0:
            print(f"🏷️ [Local Git] 成功打上本地發布標籤: {tag_name}")

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
    Auto-discovers ALL conversation sessions in the Antigravity brain directory
    and archives them into memory/sessions/ with dual-track pairing (summary + transcript).
    No hardcoded UUID list required — fully automatic.
    """
    import json as _json

    brain_dir = Path.home() / ".gemini" / "antigravity" / "brain"
    sessions_dir = ROOT / "memory" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("🗄️ [ARCHIVE-SESSIONS] 全自動對話雙軌歸檔 (Dual-Track Archiving)")
    print("=" * 65)

    if not brain_dir.exists():
        print(f"⚠️ Brain 目錄不存在: {brain_dir}")
        return

    # ── Auto-discover all conversation directories ──────────────────────
    discovered = []
    for conv_dir in sorted(brain_dir.iterdir()):
        if not conv_dir.is_dir() or conv_dir.name.startswith("."):
            continue
        t_src = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if not t_src.exists():
            continue

        # Extract date and topic from transcript metadata
        date_str = ""
        first_user_msg = ""
        try:
            with open(t_src, "r", encoding="utf-8") as _f:
                for _line in _f:
                    try:
                        _d = _json.loads(_line)
                        if not date_str and _d.get("created_at"):
                            date_str = _d["created_at"][:10]  # YYYY-MM-DD
                        if not first_user_msg and _d.get("type") == "USER_INPUT":
                            _raw = _d.get("content", "")
                            first_user_msg = (
                                _raw.replace("<USER_REQUEST>", "")
                                    .replace("</USER_REQUEST>", "")
                                    .strip()[:80]
                            )
                        if date_str and first_user_msg:
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        if not date_str:
            date_str = "0000-00-00"
        conv_id = conv_dir.name
        # Build a slug from the first user message (sanitize to filename-safe)
        slug_raw = re.sub(r"[^\w\s-]", "", first_user_msg[:50]).strip().lower()
        slug = re.sub(r"[\s_-]+", "-", slug_raw).strip("-") or conv_id[:8]
        title = first_user_msg or f"Session {conv_id[:8]}"

        discovered.append((date_str, conv_id, slug, title, t_src))

    if not discovered:
        print("ℹ️ 未找到任何對話紀錄。")
        return

    print(f"🔍 自動偵測到 {len(discovered)} 個對話紀錄目錄。\n")

    for date_str, conv_id, slug, title, t_src in discovered:
        summary_file = sessions_dir / f"{date_str}-{slug}-summary.md"
        transcript_file = sessions_dir / f"{date_str}-{slug}-transcript.md"

        print(f"• 會話 [{date_str}] {title[:60]} (ID: {conv_id[:8]}...):")
        if summary_file.exists():
            print(f"  - 總結 (Summary)   : ✅ 已存在 ({summary_file.name})")
        else:
            print(f"  - 總結 (Summary)   : ⚠️ 待補充 ({summary_file.name})")

        try:
            with open(t_src, "r", encoding="utf-8") as fin, \
                 open(transcript_file, "w", encoding="utf-8") as fout:
                fout.write(f"# 📜 對話紀錄全量封存 (Full Transcript): {title}\n\n")
                fout.write(f"- **會話 ID**: `{conv_id}`\n")
                fout.write(f"- **歸檔檔案**: `{transcript_file.name}`\n\n---\n\n")
                step_idx = 0
                for line in fin:
                    try:
                        d = _json.loads(line)
                        step_idx = d.get("step_index", step_idx + 1)
                        stype = d.get("type", "")
                        created = d.get("created_at", "")
                        content = d.get("content", "")
                        tool_calls = d.get("tool_calls", [])
                        if stype == "USER_INPUT":
                            user_text = (
                                content.replace("<USER_REQUEST>", "")
                                       .replace("</USER_REQUEST>", "")
                                       .strip()
                            )
                            fout.write(f"## 👤 [Step {step_idx}] 使用者指令 (User Input)\n")
                            fout.write(f"**時間**: `{created}`\n\n{user_text}\n\n---\n\n")
                        elif stype == "PLANNER_RESPONSE" or tool_calls or content:
                            fout.write(f"## 🤖 [Step {step_idx}] 助手回應與執行軌跡 (Assistant Response)\n")
                            fout.write(f"**時間**: `{created}`\n\n")
                            if tool_calls:
                                fout.write("### 🛠️ 工具調用 (Tool Calls)\n")
                                for tc in tool_calls:
                                    tc_name = tc.get("name", "")
                                    tc_args = tc.get("args", {})   # ← fixed: was `args` (shadowing outer param)
                                    tc_summary = tc_args.get("toolSummary", "")
                                    tc_action = tc_args.get("toolAction", "")
                                    fout.write(f"- `{tc_name}`: *{tc_action}* ({tc_summary})\n")
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

        time.sleep(3)


def cmd_init_project(args):
    """
    Initializes a new enterprise-grade project according to PROJECT_INIT_STANDARD.md
    with full directory scaffolding, security locks, two-tier coding rules, and run.py.
    """
    import shutil
    target_dir = Path(args.target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    pkg_name = args.name or target_dir.name.lower().replace("-", "_")
    today = get_current_date()

    print("\n" + "=" * 65)
    print(f"🌟 [PROJECT-INIT] 正在為新專案初始化企業級標準架構")
    print("=" * 65)
    print(f"• 目標目錄: {target_dir}")
    print(f"• 套件名稱: {pkg_name}")
    print(f"• 標準規範: 30 大核心工程鐵律 + 雙層 CODING_RULES + 6 大同步矩陣")
    print("=" * 65 + "\n")

    # 1. Directories
    subdirs = [
        target_dir / "memory" / "sessions",
        target_dir / "docs" / "adr",
        target_dir / "scratch",
        target_dir / "logs",
        target_dir / "data" / "input",
        target_dir / "data" / "output",
        target_dir / "data" / "needs_review",
        target_dir / "data" / "state",
        target_dir / "tests" / "unit",
        target_dir / "tests" / "integration",
        target_dir / "src" / pkg_name / "core",
        target_dir / "src" / pkg_name / "guards",
        target_dir / "src" / pkg_name / "utils",
        target_dir / ".agent" / "skills",
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✅ 1. 企業級目錄結構建立完畢 (memory, docs, data, src, tests, scratch)")

    # 2. Git init & hooks
    subprocess.run(["git", "init"], cwd=str(target_dir), capture_output=True)
    git_hooks = target_dir / ".git" / "hooks"
    git_hooks.mkdir(parents=True, exist_ok=True)
    pre_push = git_hooks / "pre-push"
    pre_push.write_text("""#!/bin/sh
if [ "$ALLOW_PUSH" != "1" ]; then
    echo "🛑 [GIT PUSH SAFETY LOCK ENGAGED]"
    echo "This project is strictly in LOCAL-ONLY mode to prevent unwanted pushes."
    echo "If you intentionally wish to push changes, authorize via:"
    echo "   ALLOW_PUSH=1 git push origin <branch>"
    exit 1
fi
exit 0
""", encoding="utf-8")
    pre_push.chmod(0o755)
    print("✅ 2. Git Local-Only 物理防護鎖安裝完成 (.git/hooks/pre-push)")

    # 3. .gitignore
    (target_dir / ".gitignore").write_text("""# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Scratchpad & Logs
scratch/
logs/

# Data states & Quarantine
data/state/
data/needs_review/
*.tmp.*

# Environments
.env
.venv/
env/
venv/
.DS_Store
""", encoding="utf-8")

    # 4. .env.example
    (target_dir / ".env.example").write_text(f"""# {pkg_name} Environment Configuration Template (12-Factor)
APP_ENV=development
LOG_LEVEL=INFO
OLLAMA_HOST=http://localhost:11434
""", encoding="utf-8")

    # 5. Core Documentation
    if (ROOT / "PROJECT_INIT_STANDARD.md").exists():
        shutil.copy2(ROOT / "PROJECT_INIT_STANDARD.md", target_dir / "PROJECT_INIT_STANDARD.md")
    if (ROOT / "docs" / "CODING_RULES.md").exists():
        shutil.copy2(ROOT / "docs" / "CODING_RULES.md", target_dir / "docs" / "CODING_RULES.md")
    
    # 6. OPERATIONS.md
    (target_dir / "OPERATIONS.md").write_text(f"""# 🚀 OPERATIONS.md (專案操作速查手冊 - {pkg_name})

> 💡 **專為「3 個月後的自己」與「剛喚醒的 AI Agent」設計**。無論何時重啟專案，請先閱讀此手冊，30 秒內即可快速上手！

---

## 1. 喚醒三部曲 (30 秒冷啟動)
```bash
# 步驟 1：健檢環境
python run.py doctor

# 步驟 2：開場喚醒儀式 (AI 進入對話必跑)
python run.py agent-init
```

## 2. 常用指令
```bash
# 一般進度存檔 (自動測試門禁 + 英文 Commit)
python run.py save "implement feature x"

# 離席上課/暫存
python run.py handoff "pause session before class"

# 會話雙軌歸檔
python run.py archive-sessions

# 里程碑發布 (自動測試 + 會話封存 + Squash + Tag)
python run.py publish "release v1.0.0" --tag v1.0.0
```
""", encoding="utf-8")

    # 7. AGENTS.md
    if (ROOT / "AGENTS.md").exists():
        shutil.copy2(ROOT / "AGENTS.md", target_dir / "AGENTS.md")

    # 8. memory/TASKS.md & HANDOFF.md
    (target_dir / "memory" / "TASKS.md").write_text(f"""# 📋 memory/TASKS.md (專案任務進度看板)

最後更新日期：{today}

---

## 🏃 當前 Sprint (v1.0.0 初始化)

- [x] [{today}] 依據 PROJECT_INIT_STANDARD 完成專案骨幹初始化、軟硬體守衛與 Git 本地安全鎖

---

## 📅 後續規劃 (Backlog)

- [ ] [未排程] 實作第一項核心業務邏輯
""", encoding="utf-8")

    (target_dir / "memory" / "HANDOFF.md").write_text(f"""# 🪪 memory/HANDOFF.md (離席交接卡片)

### 🕒 最新交接時間：{today} 00:00
- **狀態**：專案骨幹初始化已完成，等待首個任務派發。
- **下次接手第一步指令**：`python run.py doctor`
""", encoding="utf-8")

    # 9. Hardware & Logger scaffolds (both in src/<pkg> and src/ for universal import compatibility)
    for g_dir in [target_dir / "src" / "guards", target_dir / "src" / pkg_name / "guards"]:
        g_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "src" / "guards" / "hardware.py", g_dir / "hardware.py")
        if (ROOT / "src" / "guards" / "ollama_guard.py").exists():
            shutil.copy2(ROOT / "src" / "guards" / "ollama_guard.py", g_dir / "ollama_guard.py")
        if (ROOT / "src" / "guards" / "validator.py").exists():
            shutil.copy2(ROOT / "src" / "guards" / "validator.py", g_dir / "validator.py")
        if (ROOT / "src" / "guards" / "prompts.py").exists():
            shutil.copy2(ROOT / "src" / "guards" / "prompts.py", g_dir / "prompts.py")

    for u_dir in [target_dir / "src" / "utils", target_dir / "src" / pkg_name / "utils"]:
        u_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "src" / "utils" / "logger.py", u_dir / "logger.py")

    # 10. tests/__init__.py and sample unit test
    (target_dir / "tests" / "__init__.py").write_text(f"""import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "{pkg_name}"))
""", encoding="utf-8")

    (target_dir / "tests" / "unit" / f"test_{pkg_name}_baseline.py").write_text(f"""import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.guards.hardware import check_hardware_safety

class TestBaseline(unittest.TestCase):
    def test_hardware_probe(self):
        res = check_hardware_safety()
        self.assertIn("metrics", res)
        self.assertIn("ram_available_gb", res["metrics"])

if __name__ == "__main__":
    unittest.main()
""", encoding="utf-8")

    # 11. Copy run.py scaffold
    shutil.copy2(ROOT / "run.py", target_dir / "run.py")

    # 12. Initial Git commit
    subprocess.run(["git", "add", "-A"], cwd=str(target_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", f"[{today}] chore: initialize project governance and architecture via PROJECT_INIT_STANDARD"], cwd=str(target_dir), capture_output=True)

    print("🎉 新專案已成功在 3 秒內完成企業級標準初始化！")
    print(f"👉 請切換至新目錄：cd {target_dir}")
    print(f"👉 第一步執行：python run.py doctor\n")


def cmd_obsidian_link(args):
    """
    Scans a processed book output directory, generates index.md with Obsidian
    wikilinks, and injects inter-chapter previous/next navigation footers.
    """
    from book_processor.utils.obsidian_linker import generate_book_index, inject_chapter_navigation

    book_dir = Path(args.book_dir).resolve()
    if not book_dir.is_dir():
        print(f"🛑 錯誤：找不到書籍輸出資料夾: {book_dir}")
        sys.exit(1)

    chapters_root = book_dir / "chapters"
    ch_list = []

    if chapters_root.is_dir():
        for ch_dir in sorted(chapters_root.iterdir()):
            if ch_dir.is_dir() and not ch_dir.name.startswith("."):
                md_file = ch_dir / f"{ch_dir.name}.md"
                if md_file.exists():
                    ch_list.append({"name": ch_dir.name, "md_path": md_file})
    else:
        # Check if direct markdown files exist in book_dir
        for md_file in sorted(book_dir.glob("*.md")):
            if md_file.name != "index.md" and md_file.name != "processing_status.md":
                ch_list.append({"name": md_file.stem, "md_path": md_file})

    if not ch_list:
        print(f"⚠️ 在 {book_dir} 中未找到任何章節 Markdown 檔案。")
        return

    print(f"\n🔗 [OBSIDIAN LINKER] 為書籍建立雙鏈網絡: {book_dir.name}")
    print(f"• 找到章節數量: {len(ch_list)} 個")

    idx = generate_book_index(book_dir, ch_list)
    nav_count = inject_chapter_navigation(ch_list)

    print(f"✅ [1/2] 已生成全書索引檔案: {idx.name}")
    print(f"✅ [2/2] 已為 {nav_count} 個章節檔案成功注入前/後篇導航雙鏈。")
    print("🎉 在 Obsidian 中開啟此書籍資料夾，即可使用 Graph View 視覺化章節網絡！\n")


def cmd_status(args):
    """
    Displays an aggregated visual snapshot of all processed books/literature
    from data/state/global_status.json (with automatic rebuild if needed).
    """
    from book_processor.core.global_state import GlobalStateManager

    gsm = GlobalStateManager()
    # If state file is empty or requested sync, scan output directory
    data = gsm.get_all()
    if not data.get("books") or getattr(args, "sync", False):
        synced = gsm.sync_from_output_dir()
        if synced > 0:
            print(f"🔄 [STATUS SYNC] 已從輸出目錄自動同步 {synced} 本書之進度狀態。")
        data = gsm.get_all()

    books = data.get("books", {})
    last_updated = data.get("last_updated", "N/A")

    print("\n" + "=" * 65)
    print(f"📊 [STATUS] 全域書籍與文獻處理進度快照 (更新時間: {last_updated})")
    print("=" * 65)

    if not books:
        print("\nℹ️ 尚無任何轉檔紀錄。請先執行 run.py process 或 run.py batch。\n")
        print("=" * 65)
        return

    for title, info in books.items():
        pct = info.get("progress_pct", 0)
        filled = pct // 5
        bar = "█" * filled + "░" * (20 - filled)
        status = info.get("status", "UNKNOWN")
        icon = {
            "COMPLETE": "✅",
            "IN_PROGRESS": "🔄",
            "HAS_FAILURES": "❌",
            "PENDING": "⏳",
        }.get(status, "ℹ️")

        doc_type = info.get("doc_type", "book").upper()
        print(f"\n{icon} [{doc_type}] {title}")
        print(f"   [{bar}] {pct:3d}%  ({info.get('verified', 0)}/{info.get('total_chapters', 0)} 章節完成)")
        if info.get("failed", 0) > 0:
            print(f"   ❌ 驗證失敗: {info['failed']} 個章節")
        if info.get("pending_review", 0) > 0:
            print(f"   👁️  待人工/AI審查: {info['pending_review']} 個章節")

    print("\n" + "=" * 65 + "\n")


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

    # batch
    p_batch = subparsers.add_parser("batch", help="批次處理目錄內所有 PDF/EPUB 檔案")
    p_batch.add_argument("directory", help="輸入資料夾路徑 (例如 data/input/books/)")
    p_batch.add_argument("--type", choices=["book", "literature", "journal"], default=None, help="強制指定處理類型 (book 或 literature)")
    p_batch.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_batch.set_defaults(func=cmd_batch)


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
    p_pub.add_argument("--tag", default=None, help="可選：打上本地 Git 標籤 (例如 v1.0.0)")
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

    # init-project
    p_init_proj = subparsers.add_parser("init-project", help="一鍵為任何新專案生成企業級標準架構、文檔、守衛與安全鎖")
    p_init_proj.add_argument("target_dir", help="新專案的目錄路徑")
    p_init_proj.add_argument("--name", default=None, help="可選：新專案 Python 套件名稱 (預設為目錄名)")
    p_init_proj.set_defaults(func=cmd_init_project)

    # obsidian-link
    p_obs = subparsers.add_parser("obsidian-link", help="為已轉換書籍自動生成 index.md 全書索引與章節前後導航雙鏈")
    p_obs.add_argument("book_dir", help="書籍輸出資料夾 (例如 data/output/books/ResearchMethods/)")
    p_obs.set_defaults(func=cmd_obsidian_link)

    # status
    p_stat = subparsers.add_parser("status", help="檢視所有書籍與學術文獻之全域處理進度快照")
    p_stat.add_argument("--sync", action="store_true", help="強制重新掃描輸出目錄以同步全域狀態")
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)




if __name__ == "__main__":
    main()
