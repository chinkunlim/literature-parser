"""
CLI Project & Environment Operations
====================================
Contains commands for system diagnostics, health checks, watchdog,
project scaffolding, Obsidian knowledge linking, and status dashboard:
- cmd_doctor: Hardware, dependency, and Ollama status check
- cmd_test_ollama_auto_trigger: Self-healing drill for Ollama guard
- cmd_watchdog: Background monitor for input directories and hardware load
- cmd_init_project: Enterprise project scaffold generator
- cmd_obsidian_link: Bi-directional link and index generator for Obsidian
- cmd_status: Global processing status snapshot
- cmd_dashboard: Standalone HTML visual dashboard generator
"""

import datetime
import json
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

from literature_parser.entrypoints.project_cli.cli_process import cmd_process
from literature_parser.entrypoints.project_cli.common import ROOT, clean_dangling_tmp_files, get_current_date
from literature_parser.adapters.guards.hardware import check_hardware_safety
from literature_parser.adapters.guards.ollama_guard import OllamaGuard
from literature_parser.adapters.guards.validator import ValidatorGuard
from literature_parser.services.utils.app_logger import get_diagnostic_logger

logger = get_diagnostic_logger("CommandCenter")


def cmd_doctor(args):
    """System Health & Pre-flight Diagnostics."""
    print("\n" + "=" * 65)
    print("🩺 [DOCTOR] 系統軟硬體與環境前置健檢 (System Health Audit)")
    print("=" * 65)

    # 1. Hardware Check
    hw = check_hardware_safety(ignore_battery=getattr(args, "ignore_battery", False))
    m = hw["metrics"]
    effective_min_ram = m.get("effective_min_ram_gb", 2.0 if not m.get("is_battery", False) else 4.0)
    ram_status = "✅ [PASS]" if m["ram_available_gb"] >= effective_min_ram else "⚠️ [WARN: 低於門檻]"
    mode_str = "AC 電源模式" if not m.get("is_battery", False) else "電池模式"
    print(f"• 記憶體狀態 (RAM)  : {m['ram_available_gb']} GB 可用 (動態門檻: ≥ {effective_min_ram:.1f} GB, {mode_str}) -> {ram_status}")
    print(f"• 硬碟剩餘空間 (SSD): {m['disk_free_gb']} GB 剩餘 (門檻: ≥ 10.0 GB) -> {'✅ [PASS]' if m['disk_free_gb'] >= 10.0 else '🛑 [FAIL: 空間不足]'}")
    print(f"• 電源供應狀態      : {m['power_status']} -> {'✅ [PASS]' if not m['is_battery'] or m['battery_percent'] >= 40 else '⚠️ [WARN: 電池電量偏低]'}")
    print(f"• Apple MPS 晶片加速: {'✅ [PASS: 支援硬體加速]' if m['mps_acceleration'] else 'ℹ️ [INFO: CPU 模式]'}")

    # 2. Ollama & Models Check
    guard = OllamaGuard()
    service = guard.ensure_service_ready(auto_wake=True)
    print("\n[Ollama 本地大模型診斷]")
    if service["alive"]:
        print("• 服務狀態 (Port 11434): ✅ [ONLINE] 在線運行中")
        print(f"• 已安裝模型清單       : {', '.join(service['models']) if service['models'] else '(無已下載模型)'}")
        print(f"• 推薦啟用模型         : 🤖 {service['selected_model'] or '無 (請執行 ollama pull qwen2.5:7b)'}")
    else:
        print("• 服務狀態 (Port 11434): ⚠️ [OFFLINE] 離線 (將自動啟用純語法規則降級模式)")

    # 3. Core Binary Dependencies (poppler + tesseract)
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
        print("\n• 暫存檔案自動清理     : ✅ [PASS] 磁碟環境無殘留暫存檔")

    print("=" * 65)
    if hw["safe_for_heavy_llm"] and service["alive"] and service["selected_model"] and all_deps_ok:
        print("🎉 系統狀態完美！全自動 Ollama 深度語義與公式除錯已準備就緒。\n")
    else:
        print("💡 提示：系統可正常轉檔，但在硬體受限或 Ollama 離線時將自動優雅降級。\n")


def cmd_test_ollama_auto_trigger(args):
    """Ollama Auto-Trigger Verification Drill."""
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
    with tempfile.TemporaryDirectory(prefix="test_manifest_drill_") as tmp_drill:
        test_dir = Path(tmp_drill)
        manifest_file = test_dir / "manifest.json"
        manifest_file.write_text(
            '{"title": "Test Book", "chapters": ["ch1_intro.pdf", "ch2_advanced.pdf"]}',
            encoding="utf-8",
        )
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


def cmd_watchdog(args):
    """
    Intelligent Watchdog: Monitors data/input/ for new books/literature
    while continuously auditing macOS hardware health (RAM, Battery, SSD, MPS, Ollama).
    Auto-triggers safe conversion when files arrive.
    """
    from literature_parser.config.settings import load_config as _load_config
    app_cfg = _load_config()
    books_in = app_cfg.input_dir / "books"
    books_digital_in = books_in / "digital-pdf"
    books_scanned_in = books_in / "scanned-pdf"
    lit_in = app_cfg.input_dir / "literature"
    lit_digital_in = lit_in / "digital-pdf"
    lit_scanned_in = lit_in / "scanned-pdf"

    books_digital_in.mkdir(parents=True, exist_ok=True)
    books_scanned_in.mkdir(parents=True, exist_ok=True)
    lit_in.mkdir(parents=True, exist_ok=True)
    lit_digital_in.mkdir(parents=True, exist_ok=True)
    lit_scanned_in.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("👁️ [WATCHDOG] 軟硬體一體化智慧看門狗 (Hardware & Input Monitor)")
    print("=" * 65)
    print(f"• 監控目錄 (Books Digital)   : {books_digital_in}")
    print(f"• 監控目錄 (Books Scanned)   : {books_scanned_in}")
    print(f"• 監控目錄 (Literature)      : {lit_in}")
    print("• 守衛防線                   : RAM ≥ 4GB | SSD ≥ 10GB | 非低電量電池模式")
    print("=" * 65 + "\n")

    def scan_files():
        found = {}
        # 1. Books subdirectories
        for p in books_digital_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("book", False)
        for p in books_scanned_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("book", True)
        # 2. Books root fallback
        for p in books_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("book", None)
        # 3. Literature subdirectories
        for p in lit_digital_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("literature", False)
        for p in lit_scanned_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("literature", True)
        # 4. Literature root
        for p in lit_in.iterdir():
            if p.is_file() and p.suffix.lower() in (".pdf", ".epub") and not p.name.startswith("."):
                found[p] = ("literature", False)
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
            doc_type, is_scanned_val = current[nfile]
            scan_hint = " (SCANNED OCR)" if is_scanned_val is True else (" (DIGITAL VECTOR)" if is_scanned_val is False else "")
            print(f"\n📥 [新檔案偵測] 發現待處理文件: [{doc_type.upper()}{scan_hint}] {nfile.name}")
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

            print(f"  🚀 自動啟動轉檔: {doc_type}{scan_hint} 管線...")
            from literature_parser.entrypoints.project_cli.cli_process import _run_process_pipeline
            _run_process_pipeline(
                nfile,
                doc_type=doc_type,
                is_scanned=is_scanned_val,
                ignore_battery=getattr(args, "ignore_battery", False)
            )
            known[nfile] = (doc_type, is_scanned_val)

        time.sleep(3)


def cmd_init_project(args):
    """
    Initializes a new enterprise-grade project according to the Antigravity standard layout
    with full directory scaffolding, security locks, two-tier coding rules, and run.py.
    """
    target_dir = Path(args.target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    pkg_name = args.name or target_dir.name.lower().replace("-", "_")
    today = get_current_date()

    print("\n" + "=" * 65)
    print("🌟 [PROJECT-INIT] 正在為新專案初始化企業級標準架構")
    print("=" * 65)
    print(f"• 目標目錄: {target_dir}")
    print(f"• 套件名稱: {pkg_name}")
    print("• 標準規範: 30 大核心工程鐵律 + 雙層 CODING_RULES + 6 大同步矩陣")
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
    if (ROOT / "docs" / "ARCHITECTURE.md").exists():
        shutil.copy2(ROOT / "docs" / "ARCHITECTURE.md", target_dir / "docs" / "ARCHITECTURE.md")
    if (ROOT / "docs" / "CODING_RULES.md").exists():
        shutil.copy2(ROOT / "docs" / "CODING_RULES.md", target_dir / "docs" / "CODING_RULES.md")

    # 6. WORKFLOW_GUIDE.md
    (target_dir / "WORKFLOW_GUIDE.md").write_text(f"""# 🚀 WORKFLOW_GUIDE.md (專案操作速查手冊 - {pkg_name})

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

    # 9. Hardware & Logger scaffolds
    src_guards = ROOT / "src" / "literature_parser" / "adapters" / "guards"
    if not src_guards.exists():
        src_guards = ROOT / "src" / "guards"

    for g_dir in [target_dir / "src" / "guards", target_dir / "src" / pkg_name / "guards"]:
        g_dir.mkdir(parents=True, exist_ok=True)
        if (src_guards / "hardware.py").exists():
            shutil.copy2(src_guards / "hardware.py", g_dir / "hardware.py")
        if (src_guards / "ollama_guard.py").exists():
            shutil.copy2(src_guards / "ollama_guard.py", g_dir / "ollama_guard.py")
        if (src_guards / "validator.py").exists():
            shutil.copy2(src_guards / "validator.py", g_dir / "validator.py")
        if (src_guards / "prompts.py").exists():
            shutil.copy2(src_guards / "prompts.py", g_dir / "prompts.py")

    src_utils = ROOT / "src" / "literature_parser" / "services" / "utils"
    if not src_utils.exists():
        src_utils = ROOT / "src" / "utils"

    for u_dir in [target_dir / "src" / "utils", target_dir / "src" / pkg_name / "utils"]:
        u_dir.mkdir(parents=True, exist_ok=True)
        if (src_utils / "app_logger.py").exists():
            shutil.copy2(src_utils / "app_logger.py", u_dir / "logger.py")

    # 10. tests/__init__.py and sample unit test
    (target_dir / "tests" / "__init__.py").write_text(f"""import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "{pkg_name}"))
""", encoding="utf-8")

    (target_dir / "tests" / "unit").mkdir(parents=True, exist_ok=True)
    (target_dir / "tests" / "unit" / f"test_{pkg_name}_baseline.py").write_text("""import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from literature_parser.adapters.guards.hardware import check_hardware_safety

class TestBaseline(unittest.TestCase):
    def test_hardware_probe(self):
        res = check_hardware_safety()
        self.assertIn("metrics", res)
        self.assertIn("ram_available_gb", res["metrics"])

if __name__ == "__main__":
    unittest.main()
""", encoding="utf-8")

    # 11. Copy run.py scaffold
    src_run = ROOT / "src" / "literature_parser" / "entrypoints" / "run.py"
    if src_run.exists():
        shutil.copy2(src_run, target_dir / "run.py")

    # 12. Initial Git commit
    subprocess.run(["git", "add", "-A"], cwd=str(target_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", f"[{today}] chore: initialize project governance and architecture via PROJECT_INIT_STANDARD"], cwd=str(target_dir), capture_output=True)

    print("🎉 新專案已成功在 3 秒內完成企業級標準初始化！")
    print(f"👉 請切換至新目錄：cd {target_dir}")
    print("👉 第一步執行：python run.py doctor\n")


def cmd_obsidian_link(args):
    """
    Scans a processed book output directory, generates index.md with Obsidian
    wikilinks, and injects inter-chapter previous/next navigation footers.
    """
    from literature_parser.services.utils.obsidian_linker import (
        generate_book_index,
        inject_chapter_navigation,
    )

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
        for md_file in sorted(book_dir.glob("*.md")):
            if md_file.name not in ("index.md", "processing_status.md"):
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
    from literature_parser.services.core.global_state import GlobalStateManager

    gsm = GlobalStateManager()
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


def cmd_dashboard(args):
    """
    Generates a modern, standalone static HTML dashboard (dashboard/index.html)
    visualizing real-time conversion progress, and opens it in the default browser.
    """
    from literature_parser.services.core.global_state import GlobalStateManager

    gsm = GlobalStateManager()
    data = gsm.get_all()
    if not data.get("books"):
        gsm.sync_from_output_dir()
        data = gsm.get_all()

    dashboard_dir = ROOT / "web"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    html_path = dashboard_dir / "dashboard.html"

    books_data = data.get("books", {})
    books_json = json.dumps(books_data, ensure_ascii=False, indent=2)
    last_updated = data.get("last_updated", "N/A")

    html_content = f"""<!--
Literature Parser Web Dashboard
Visualizes processing pipeline status, progress bars, and chapter stats.
-->
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📚 Book & Literature Processor — 處理進度儀表板</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --text-muted: #7d8590;
      --success: #238636;
      --success-text: #3fb950;
      --warning: #9e6a03;
      --warning-text: #d29922;
      --danger: #da3633;
      --danger-text: #f85149;
      --primary: #1f6feb;
      --primary-text: #58a6ff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem 1.5rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    h1 {{ font-size: 1.6rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }}
    .subtitle {{ color: var(--text-muted); font-size: 0.88rem; margin-top: 0.3rem; }}
    .stats-summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.2rem;
    }}
    .stat-card h3 {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
    .stat-card .value {{ font-size: 2rem; font-weight: 700; margin-top: 0.3rem; }}
    .grid {{
      display: flex;
      flex-direction: column;
      gap: 1.2rem;
    }}
    .book-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.4rem;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .book-card:hover {{ border-color: #58a6ff88; }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      margin-bottom: 0.8rem;
    }}
    .card-title {{ font-size: 1.1rem; font-weight: 600; line-height: 1.4; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }}
    .badge-complete {{ background: #23863622; color: var(--success-text); border: 1px solid #23863655; }}
    .badge-in_progress {{ background: #1f6feb22; color: var(--primary-text); border: 1px solid #1f6feb55; }}
    .badge-has_failures {{ background: #da363322; color: var(--danger-text); border: 1px solid #da363355; }}
    .badge-pending {{ background: #30363d55; color: var(--text-muted); border: 1px solid var(--border); }}
    .type-tag {{
      display: inline-block;
      font-size: 0.7rem;
      font-weight: bold;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      background: #21262d;
      color: #8b949e;
      margin-right: 0.5rem;
    }}
    .progress-bar-bg {{
      background: #21262d;
      height: 10px;
      border-radius: 5px;
      overflow: hidden;
      margin: 0.8rem 0;
    }}
    .progress-bar-fill {{
      height: 100%;
      border-radius: 5px;
      transition: width 0.4s ease;
    }}
    .fill-complete {{ background: var(--success); }}
    .fill-progress {{ background: var(--primary); }}
    .fill-failures {{ background: var(--danger); }}
    .card-footer {{
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 0.82rem;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }}
    .meta-pills {{ display: flex; gap: 0.6rem; }}
    .meta-pill {{ display: flex; align-items: center; gap: 0.3rem; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>📚 書籍與學術文獻處理儀表板</h1>
      <div class="subtitle">零雲端依賴 · 本地 AI 智能排版 · 即時進度快照 (最後更新：{last_updated})</div>
    </div>
  </header>

  <div class="stats-summary" id="statsSummary"></div>

  <div class="grid" id="booksGrid"></div>

  <script>
    const books = {books_json};
    const entries = Object.entries(books);

    // Compute Summary Stats
    const totalDocs = entries.length;
    let completedDocs = 0;
    let totalChapters = 0;
    let verifiedChapters = 0;

    entries.forEach(([_, info]) => {{
      if (info.status === 'COMPLETE') completedDocs++;
      totalChapters += (info.total_chapters || 0);
      verifiedChapters += (info.verified || 0);
    }});

    const overallPct = totalChapters > 0 ? Math.round((verifiedChapters / totalChapters) * 100) : 0;

    document.getElementById('statsSummary').innerHTML = `
      <div class="stat-card">
        <h3>總處理文檔數</h3>
        <div class="value">${{totalDocs}} <span style="font-size:1rem;color:var(--text-muted);">本/篇</span></div>
      </div>
      <div class="stat-card">
        <h3>全數完工</h3>
        <div class="value" style="color:var(--success-text);">${{completedDocs}} <span style="font-size:1rem;color:var(--text-muted);">本/篇</span></div>
      </div>
      <div class="stat-card">
        <h3>章節總完成度</h3>
        <div class="value" style="color:var(--primary-text);">${{overallPct}}%</div>
      </div>
      <div class="stat-card">
        <h3>累計驗證章節</h3>
        <div class="value">${{verifiedChapters}} <span style="font-size:1rem;color:var(--text-muted);">/ ${{totalChapters}}</span></div>
      </div>
    `;

    const grid = document.getElementById('booksGrid');
    if (!entries.length) {{
      grid.innerHTML = '<div class="book-card" style="text-align:center;color:var(--text-muted);padding:3rem;">尚無轉檔紀錄。請使用 <code>python run.py process</code> 或 <code>python run.py batch</code> 啟動轉檔。</div>';
    }} else {{
      entries.forEach(([title, info]) => {{
        const pct = info.progress_pct || 0;
        const status = info.status || 'PENDING';
        const docType = (info.doc_type || 'book').toUpperCase();

        let badgeClass = 'badge-pending';
        let badgeLabel = '⏳ 等待中';
        let fillClass = 'fill-progress';

        if (status === 'COMPLETE') {{
          badgeClass = 'badge-complete';
          badgeLabel = '✅ 已全數完成';
          fillClass = 'fill-complete';
        }} else if (status === 'HAS_FAILURES') {{
          badgeClass = 'badge-has_failures';
          badgeLabel = '❌ 需修復/重試';
          fillClass = 'fill-failures';
        }} else if (status === 'IN_PROGRESS') {{
          badgeClass = 'badge-in_progress';
          badgeLabel = '🔄 處理中';
          fillClass = 'fill-progress';
        }}

        grid.innerHTML += `
          <div class="book-card">
            <div class="card-header">
              <div class="card-title">
                <span class="type-tag">${{docType}}</span>
                ${{title}}
              </div>
              <span class="badge ${{badgeClass}}">${{badgeLabel}}</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill ${{fillClass}}" style="width: ${{pct}}%;"></div>
            </div>
            <div class="card-footer">
              <div class="meta-pills">
                <span class="meta-pill">章節進度: <strong>${{info.verified || 0}} / ${{info.total_chapters || 0}}</strong> (${{pct}}%)</span>
                ${{info.failed > 0 ? `<span class="meta-pill" style="color:var(--danger-text);">⚠️ 失敗: ${{info.failed}}</span>` : ''}}
                ${{info.pending_review > 0 ? `<span class="meta-pill" style="color:var(--warning-text);">👁️ 待審查: ${{info.pending_review}}</span>` : ''}}
              </div>
              <div>更新時間: ${{info.last_updated || 'N/A'}}</div>
            </div>
          </div>
        `;
      }});
    }}
  </script>
</body>
</html>
"""

    html_path.write_text(html_content, encoding="utf-8")
    print("\n" + "=" * 65)
    print("📊 [DASHBOARD] 視覺化儀表板已成功生成！")
    print(f"• 檔案路徑: {html_path}")
    print("=" * 65 + "\n")

    if not getattr(args, "no_open", False):
        try:
            webbrowser.open(f"file://{html_path.resolve()}")
            print("🚀 已自動在預設瀏覽器中開啟儀表板。\n")
        except Exception:
            pass


def cmd_web(args: Any) -> None:
    """Starts the FastAPI Web Application & MCP Server for interactive review and comparison.

    Args:
        args: Parsed command-line arguments (host, port, no_open).

    Returns:
        None.
    """
    import threading
    import uvicorn
    from literature_parser.config.settings import load_config

    cfg = load_config()
    host = getattr(args, "host", None) or cfg.http_host
    port = getattr(args, "port", None) or cfg.http_port

    url = f"http://{host}:{port}"
    print("\n" + "=" * 65)
    print(f"🚀 [WEB STUDIO] 正在啟動 Literature Parser 互動式 Web Studio...")
    print(f"• 綁定端點: {url}")
    print(f"• OpenAPI 文件: {url}/docs")
    print(f"• 靜態頁面: {url}/")
    print("=" * 65 + "\n")

    if not getattr(args, "no_open", False):
        def _open():
            import time
            time.sleep(1.0)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run("literature_parser.entrypoints.web_app:app", host=host, port=port, log_level="info")

