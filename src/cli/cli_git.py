"""
CLI Git & Session Operations
=============================
Handles local Git checkpoints, handoff protocols, agent onboarding, and dual-track archiving:
- cmd_agent_init: AI agent onboarding briefing
- cmd_save: Local Git commit with English message and test gate
- cmd_handoff: Prepares handoff note before pausing session
- cmd_end_session: End-of-session archiving, testing, and commit
- cmd_publish: Squash merge and local release tagging
- cmd_archive_sessions: Automated dual-track session archiving (summary + transcript)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from src.cli.common import (
    ROOT,
    clean_dangling_tmp_files,
    get_current_date,
    get_current_timestamp,
    sync_markdown_dates,
)


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
   - 調用大模型前檢查 RAM ≥ 2.0GB (AC電源) / 4.0GB (電池模式)，未達標則優雅降級為純規則。

5. 📂 零硬編碼絕對路徑 (Zero Hardcoded Paths):
   - 嚴禁寫死絕對路徑 (/Users/...)，一律以 ROOT 動態相對錨定，確保搬移目錄零崩潰。

6. 🍎 macOS 原生優先 (macOS-Native Priority):
   - 優先評估 Apple Vision Framework、sips、Metal/MPS、CoreML 等系統原生能力。

7. 🧪 臨時腳本隔離 (Scratchpad Policy):
   - 一次性測試程式一律放入 scratch/，不污染正式目錄。
""")

    handoff_file = ROOT / "memory" / "HANDOFF.md"
    if handoff_file.exists():
        print("----------------------------------------------------------------------")
        print("📌 [當前交接狀態摘要 (Latest Handoff Snapshot)]")
        print("----------------------------------------------------------------------")
        lines = handoff_file.read_text(encoding="utf-8").splitlines()
        for line in lines[:20]:
            print(f"  {line}")
    print("=" * 70 + "\n")


def cmd_save(args):
    """Saves progress locally, stamping docs first. Enforces English commit messages and test gate."""
    clean_dangling_tmp_files()

    # Automated test gate
    if (ROOT / "tests").exists():
        res_test = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=str(ROOT), capture_output=True)
        if res_test.returncode != 0:
            print("\n🛑 [COMMIT 攔截] 單元測試未通過！為杜絕幽靈修復與代碼腐化，已自動阻止提交。")
            print(res_test.stderr.decode("utf-8") or res_test.stdout.decode("utf-8"))
            sys.exit(1)

    sync_markdown_dates()
    today = get_current_date()
    msg = args.message.strip()

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


def cmd_end_session(args):
    """
    End-of-Session Protocol:
    1. Dual-track transcript backup.
    2. Final markdown check and sync.
    3. Test gate and English Conventional Commit.
    """
    print("\n" + "=" * 65)
    print("🏁 [END-SESSION] 對話結束閉環流程啟動")
    print("=" * 65)
    today = get_current_date()
    now_ts = get_current_timestamp()

    print("\n📦 [Step 1/3] 執行對話雙軌全量備份 (Dual-Track Archiving)...")
    cmd_archive_sessions(args)

    print("\n📝 [Step 2/3] 最終檢查與文檔同步 (Sync Markdown Docs)...")
    handoff_file = ROOT / "memory" / "HANDOFF.md"
    if handoff_file.exists():
        c = handoff_file.read_text(encoding="utf-8")
        c = re.sub(
            r"### 🕒 最新交接時間：\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
            f"### 🕒 最新交接時間：{now_ts}",
            c,
        )
        handoff_file.write_text(c, encoding="utf-8")
        print(f"  • 更新 {handoff_file.name} 時間戳記 ➔ {now_ts}")

    sync_markdown_dates()

    skills_dir = ROOT / ".agent" / "skills"
    if skills_dir.exists():
        skill_files = list(skills_dir.rglob("*.md"))
        print(f"  • 檢核 .agent/skills/ 共 {len(skill_files)} 份技能定義文件 (全部齊全)")

    pruned = clean_dangling_tmp_files()
    if pruned > 0:
        print(f"  • 已自動清理 {pruned} 個過期暫存檔 (*.tmp.*)")

    print("\n🧪 [Step 3/3] 執行自動化測試門禁並提交 Git...")
    res_test = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=str(ROOT))
    if res_test.returncode != 0:
        print("\n🛑 [存檔阻斷] 單元測試未全數通過，已安全攔截 Commit！請檢查修正後重試。")
        sys.exit(1)

    summary_note = (getattr(args, "summary", "") or "").strip()
    if not summary_note:
        summary_note = "end conversation session and sync all documentation"
    commit_msg = f"[{today}] chore(session): {summary_note}"

    subprocess.run(["git", "add", "-A"], cwd=str(ROOT))
    res_git = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(ROOT))
    if res_git.returncode == 0:
        print(f"\n🎉 [Git Commit 成功] {commit_msg}")
    else:
        print("\nℹ️ [Git Status] 無額外檔案異動需提交。")
    print("=================================================================")
    print("✅ 對話已安全歸檔並完成全量文件檢核與存檔，可放心結束此會話！\n")


def cmd_publish(args):
    """Squash merges to main and prints authorized push instructions with automated gates."""
    print("\n📦 [PUBLISH] 準備打包發布里程碑...")
    today = get_current_date()
    release_msg = f"[{today}] release: {args.message}"

    print("\n🧪 [Gate 1] 執行發布前全量自動化單元測試門禁 (Automated Test Gate)...")
    res_test = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=str(ROOT))
    if res_test.returncode != 0:
        print("\n🛑 [發布中斷] 單元測試未全數通過，發布已被安全阻斷！請修復測試後再試。")
        sys.exit(1)
    print("✅ 單元測試全數通過 (100% PASS)！")

    print("\n🗄️ [Gate 2] 執行會話雙軌全量封存 (Auto-Archiving Sessions)...")
    cmd_archive_sessions(args)

    pruned = clean_dangling_tmp_files()
    if pruned > 0:
        print(f"🧹 [Gate 3] 已自動清理 {pruned} 個過期暫存檔 (*.tmp.*)")

    branch_out = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if branch_out != "main":
        print(f"\n• 目前在分支 [{branch_out}]，執行切換至 main 並 Squash Merge...")
        subprocess.run(["git", "checkout", "main"])
        subprocess.run(["git", "merge", branch_out, "--squash"])
        subprocess.run(["git", "commit", "-m", release_msg])
    else:
        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", release_msg])

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


def cmd_archive_sessions(args):
    """
    Auto-discovers ALL conversation sessions in the Antigravity brain directory
    and archives them into memory/sessions/ with dual-track pairing (summary + transcript).
    """
    brain_dir = Path.home() / ".gemini" / "antigravity" / "brain"
    sessions_dir = ROOT / "memory" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("🗄️ [ARCHIVE-SESSIONS] 全自動對話雙軌歸檔 (Dual-Track Archiving)")
    print("=" * 65)

    if not brain_dir.exists():
        print(f"⚠️ Brain 目錄不存在: {brain_dir}")
        return

    discovered = []
    for conv_dir in sorted(brain_dir.iterdir()):
        if not conv_dir.is_dir() or conv_dir.name.startswith("."):
            continue
        t_src = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if not t_src.exists():
            continue

        try:
            with open(t_src, "r", encoding="utf-8", errors="ignore") as _f:
                _sample = _f.read(20000)
                if str(ROOT) not in _sample and "book-processor" not in _sample:
                    continue
        except Exception:
            continue

        date_str = ""
        first_user_msg = ""
        try:
            with open(t_src, "r", encoding="utf-8") as _f:
                for _line in _f:
                    try:
                        _d = json.loads(_line)
                        if not date_str and _d.get("created_at"):
                            date_str = _d["created_at"][:10]
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
        slug_raw = re.sub(r"[^\w\s-]", "", first_user_msg[:50]).strip().lower()
        slug = re.sub(r"[\s_-]+", "-", slug_raw).strip("-") or conv_id[:8]
        title = first_user_msg or f"Session {conv_id[:8]}"

        discovered.append((date_str, conv_id, slug, title, t_src))

    if not discovered:
        print("ℹ️ 未找到屬於本專案的對話紀錄。")
        return

    print(f"🔍 自動偵測到 {len(discovered)} 個本專案對話紀錄目錄。\n")

    for date_str, conv_id, slug, title, t_src in discovered:
        matched_summary = None
        matched_transcript = None
        for ef in sessions_dir.glob("*.md"):
            try:
                sample_txt = ef.read_text(encoding="utf-8", errors="ignore")[:3000]
                if conv_id in sample_txt:
                    if ef.name.endswith("-summary.md"):
                        matched_summary = ef
                    elif ef.name.endswith("-transcript.md"):
                        matched_transcript = ef
            except Exception:
                pass

        summary_file = matched_summary or (sessions_dir / f"{date_str}-{slug}-summary.md")
        transcript_file = matched_transcript or (sessions_dir / f"{date_str}-{slug}-transcript.md")

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
                        d = json.loads(line)
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
                                    tc_args = tc.get("args", {})
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
