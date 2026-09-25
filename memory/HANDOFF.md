# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-25 08:55
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **實裝專屬修復手冊庫 (`FixPlaybook`) 與零容忍防呆門禁 (`QualityInvariantGuard` 避免有錯還報對)**：
  1. **專門修復手冊知識庫 (`src/doc_processor/fixes/playbook.py`)**：
     - 將無法直接通用的特定修復邏輯收錄為 8 大專用修復配方（CUP 側欄清理、Elsevier 粘連參考文獻拆分、無括號年份引用條目重構、建議清單降級、孤立頁碼清理、KaTeX 貨幣轉義、OCR 統計符號修復、NIH 水印過濾）。
     - 提供獨立 CLI 工具：`uv run python run.py fix list`（檢視清單）、`uv run python run.py fix apply <id> <file>`（手動指定修復）、`uv run python run.py fix info <id>`（檢視配方詳情）。
     - 於 `run.py audit` 中實裝「配方智能推薦」與 `--fix` 自動症狀匹配修復，形成自動化閉環。
  2. **零容忍防呆門禁 (`QualityInvariantGuard.verify_hard_invariants`)**：
     - 定義 7 大核心不變量（標題非空、摘要存在、參考文獻獨立、LaTeX 公式閉合、無 OCR 表格洩漏、無孤立頁碼、非空白檔案）。
     - 違背任一項強制判定 FAIL 並標紅，管線嚴格禁止輸出「100% verified」，自動隔離至 `data/needs_review/`，徹底杜絕「有錯還報對」。
  3. **全套測試與文獻稽核 100% 通過**：
     - 新增 `tests/test_v40_fix_playbook_and_invariants.py`，全套 219/219 單元測試 100% 通過。
     - 全量 10 篇學術文獻稽核全數合格，並能智能推薦匹配之手冊修復指令。

#### 2. 目前專案狀態與代碼位置
- 分支：`main`
- 狀態：所有模組、功能、文檔 100% 同步，代碼庫極致整潔，已完整通過全量測試。

#### 3. 下一個 AI 回來接手時的第 1 步指令 (Next Steps)
```bash
# 開場喚醒儀式（自動讀取本卡片與 AGENTS.md 守則）
uv run python run.py agent-init

# 系統軟硬體與環境前置健檢
uv run python run.py doctor

# 檢視全域處理進度快照
uv run python run.py status
```
接手者請直接向使用者簡報目前狀態，並依使用者下一步指令進行處理！

