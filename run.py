#!/usr/bin/env python3
"""
Book & Journal Processor: Unified Command Center (run.py)
=========================================================
Central CLI orchestrating hardware pre-flight checks, convention-based routing,
auto-Ollama triggering, date-stamped doc synchronization, and local-only Git checkpoints.

Modularized architecture delegating command implementations to `src.cli.*`.

Usage:
  uv run python run.py doctor
  uv run python run.py process <filepath> [--type book|journal]
  uv run python run.py batch <directory> [--type book|journal]
  uv run python run.py audit <path> [--ollama] [--fix]
  uv run python run.py fix [list|apply|info|review|test|promote|reject|synthesize]
  uv run python run.py save "<commit message>"
  uv run python run.py handoff "<reason for pause>"
  uv run python run.py end-session "<summary>"
  uv run python run.py publish "<release message>"
  uv run python run.py test-ollama-auto-trigger
  uv run python run.py agent-init
  uv run python run.py archive-sessions
  uv run python run.py watchdog [--once]
  uv run python run.py init-project <target_dir>
  uv run python run.py obsidian-link <book_dir>
  uv run python run.py status [--sync]
  uv run python run.py dashboard [--no-open]
"""

import argparse
import sys
from pathlib import Path

# Add project root and src to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Re-export all CLI functions for direct API / script compatibility
from src.cli import (
    cmd_agent_init,
    cmd_archive_sessions,
    cmd_audit,
    cmd_batch,
    cmd_dashboard,
    cmd_doctor,
    cmd_end_session,
    cmd_fix,
    cmd_handoff,
    cmd_init_project,
    cmd_obsidian_link,
    cmd_process,
    cmd_publish,
    cmd_save,
    cmd_status,
    cmd_test_ollama_auto_trigger,
    cmd_watchdog,
)


def main():
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="Book & Journal Processor Unified Command Center",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. fix
    p_fix = subparsers.add_parser("fix", help="專案修復手冊工具 (list / apply / info / review / test / promote / reject / synthesize)")
    p_fix_sub = p_fix.add_subparsers(dest="fix_action", required=False)

    p_fix_list = p_fix_sub.add_parser("list", help="列出所有可用的修復配方與症狀")
    p_fix_list.set_defaults(func=cmd_fix)

    p_fix_apply = p_fix_sub.add_parser("apply", help="對目標檔案套用特定修復配方")
    p_fix_apply.add_argument("recipe_id", help="配方唯一識別碼 (例如 clean_orphan_page_numbers)")
    p_fix_apply.add_argument("target", help="目標 Markdown 檔案路徑")
    p_fix_apply.set_defaults(func=cmd_fix)

    p_fix_info = p_fix_sub.add_parser("info", help="查看特定修復配方詳細資訊")
    p_fix_info.add_argument("recipe_id", help="配方唯一識別碼")
    p_fix_info.set_defaults(func=cmd_fix)

    p_fix_review = p_fix_sub.add_parser("review", help="檢閱所有待審核的 Ollama 生成修復配方")
    p_fix_review.set_defaults(func=cmd_fix)

    p_fix_test = p_fix_sub.add_parser("test", help="執行待審核配方的單元測試與沙盒試跑")
    p_fix_test.add_argument("recipe_id", help="待審核配方 ID")
    p_fix_test.set_defaults(func=cmd_fix)

    p_fix_promote = p_fix_sub.add_parser("promote", help="批准並將待審核配方升級整合進正式 Playbook")
    p_fix_promote.add_argument("recipe_id", help="待審核配方 ID")
    p_fix_promote.set_defaults(func=cmd_fix)

    p_fix_reject = p_fix_sub.add_parser("reject", help="駁回並刪除待審核配方")
    p_fix_reject.add_argument("recipe_id", help="待審核配方 ID")
    p_fix_reject.set_defaults(func=cmd_fix)

    p_fix_synth = p_fix_sub.add_parser("synthesize", help="調用 Ollama 針對特定瑕疵自動撰寫 Python 修復程式並隔離暫存")
    p_fix_synth.add_argument("target", help="目標瑕疵檔案路徑")
    p_fix_synth.add_argument("issue", help="問題描述 (例如 '去除特定殘留字串')")
    p_fix_synth.add_argument("--id-hint", default=None, help="可選：建議的配方 ID")
    p_fix_synth.set_defaults(func=cmd_fix)

    p_fix.set_defaults(func=cmd_fix)

    # 2. audit
    p_audit = subparsers.add_parser("audit", help="執行文獻排版格式詳細稽核 (支援 --ollama 與 --fix)")
    p_audit.add_argument("target", nargs="?", default=None, help="目標 Markdown 檔案或資料夾路徑")
    p_audit.add_argument("--all", action="store_true", help="稽核 data/output/literature/ 下全部文獻")
    p_audit.add_argument("--ollama", action="store_true", help="啟用本地 Ollama 深度語義診斷")
    p_audit.add_argument("--fix", action="store_true", help="自動修復高置信度排版語法瑕疵")
    p_audit.add_argument("--no-exit-error", action="store_true", help="即使發現瑕疵亦不退出非 0 返回碼")
    p_audit.set_defaults(func=cmd_audit)

    # 3. doctor
    p_doc = subparsers.add_parser("doctor", help="執行系統軟硬體與 Ollama 健康檢查")
    p_doc.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_doc.set_defaults(func=cmd_doctor)

    # 4. process
    p_proc = subparsers.add_parser("process", help="處理單一書籍或學術文獻")
    p_proc.add_argument("file", help="輸入檔案路徑 (PDF/EPUB)")
    p_proc.add_argument("--type", choices=["book", "literature", "journal"], default=None, help="強制指定處理類型 (book 或 literature)")
    p_proc.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_proc.set_defaults(func=cmd_process)

    # 5. batch
    p_batch = subparsers.add_parser("batch", help="批次處理目錄內所有 PDF/EPUB 檔案")
    p_batch.add_argument("directory", help="輸入資料夾路徑 (例如 data/input/books/)")
    p_batch.add_argument("--type", choices=["book", "literature", "journal"], default=None, help="強制指定處理類型 (book 或 literature)")
    p_batch.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_batch.set_defaults(func=cmd_batch)

    # 6. save
    p_save = subparsers.add_parser("save", help="日常本地存檔 (先更新文檔日期後 commit)")
    p_save.add_argument("message", help="Commit 說明")
    p_save.set_defaults(func=cmd_save)

    # 7. handoff
    p_hand = subparsers.add_parser("handoff", help="離席交接存檔 (更新 HANDOFF.md 後 commit)")
    p_hand.add_argument("reason", default="外出/上課暫存", nargs="?", help="離席原因")
    p_hand.set_defaults(func=cmd_handoff)

    # 8. end-session
    p_end = subparsers.add_parser("end-session", help="對話結束閉環 (1. 歸檔對話 2. 最終檢查更新所有 md 3. 測試與 Git Commit)")
    p_end.add_argument("summary", nargs="?", default="", help="可選：本次會話核心總結說明")
    p_end.set_defaults(func=cmd_end_session)

    # 9. publish
    p_pub = subparsers.add_parser("publish", help="本地發布並合併至 main 分支")
    p_pub.add_argument("message", help="發布版本說明")
    p_pub.add_argument("--tag", default=None, help="可選：打上本地 Git 標籤 (例如 v1.0.0)")
    p_pub.set_defaults(func=cmd_publish)

    # 10. test-ollama-auto-trigger
    p_test = subparsers.add_parser("test-ollama-auto-trigger", help="執行 Ollama 自動喚醒與自我除錯測試")
    p_test.set_defaults(func=cmd_test_ollama_auto_trigger)

    # 11. agent-init
    p_init = subparsers.add_parser("agent-init", help="AI 對話開場自動簡報，讀取工作守則與交接狀態")
    p_init.set_defaults(func=cmd_agent_init)

    # 12. archive-sessions
    p_arch = subparsers.add_parser("archive-sessions", help="自動掃描並更新所有歷史對話之雙軌歸檔 (Summary + Transcript)")
    p_arch.set_defaults(func=cmd_archive_sessions)

    # 13. watchdog
    p_watch = subparsers.add_parser("watchdog", help="啟動軟硬體一體化看門狗，監控目錄檔案並確保硬體安全")
    p_watch.add_argument("--once", action="store_true", help="僅執行一次巡檢後離開")
    p_watch.add_argument("--ignore-battery", action="store_true", help="忽略電池電量限制")
    p_watch.set_defaults(func=cmd_watchdog)

    # 14. init-project
    p_init_proj = subparsers.add_parser("init-project", help="一鍵為任何新專案生成企業級標準架構、文檔、守衛與安全鎖")
    p_init_proj.add_argument("target_dir", help="新專案的目錄路徑")
    p_init_proj.add_argument("--name", default=None, help="可選：新專案 Python 套件名稱 (預設為目錄名)")
    p_init_proj.set_defaults(func=cmd_init_project)

    # 15. obsidian-link
    p_obs = subparsers.add_parser("obsidian-link", help="為已轉換書籍自動生成 index.md 全書索引與章節前後導航雙鏈")
    p_obs.add_argument("book_dir", help="書籍輸出資料夾 (例如 data/output/books/ResearchMethods/)")
    p_obs.set_defaults(func=cmd_obsidian_link)

    # 16. status
    p_stat = subparsers.add_parser("status", help="檢視所有書籍與學術文獻之全域處理進度快照")
    p_stat.add_argument("--sync", action="store_true", help="強制重新掃描輸出目錄以同步全域狀態")
    p_stat.set_defaults(func=cmd_status)

    # 17. dashboard
    p_dash = subparsers.add_parser("dashboard", help="生成靜態 HTML 視覺化儀表板並於瀏覽器中檢視進度")
    p_dash.add_argument("--no-open", action="store_true", help="僅生成檔案，不自動開啟瀏覽器")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
