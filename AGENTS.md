# 🤖 AGENTS.md (跨 AI Agent 協作通用憲法)

> 適用對象：所有參與本專案的 AI Agents（包含 Antigravity、Claude Code、Codex、Cursor、OpenClaw 等）。
> **新對話開場首要動作**：任何 AI 進入本專案的第一步，必須在終端機執行：
> `uv run python run.py agent-init`
> 讀取核心工作原則、最新交接狀態與未完成任務！

---

## 一、 意圖 ➔ 指令派發對照表 (Action Dispatch Table)

當使用者提出以下意圖時，**直接呼叫對應指令，嚴禁自己重新發明輪子或改寫底層主邏輯**：

| 使用者意圖 (User Intent) | 應該執行的 CLI 指令 | 說明與約束 |
| :--- | :--- | :--- |
| **新對話喚醒 / 接手專案** | `uv run python run.py agent-init` | **對話開場必跑**：自動簡報守則與交接狀態 |
| **環境健檢 / 診斷** | `uv run python run.py doctor` | 檢查 RAM、電池、SSD、Ollama、模型 |
| **轉換書籍** | `uv run python run.py process data/input/books/<filename>` | 自動啟動書籍章節切分與文意縫合 |
| **轉換學術文獻 / 論文** | `uv run python run.py process data/input/literature/<filename>` | 自動啟動雙欄排版、摘要與文獻解析 |
| **驗證 Ollama 自動喚醒** | `uv run python run.py test-ollama-auto-trigger` | 驗證輸入與輸出守衛能否自動喚醒 Ollama |
| **一般進度存檔** | `uv run python run.py save "<English_message>"` | 先更新文檔時間戳，再以英文 commit |
| **結束對話 / 結案離席** | `uv run python run.py end-session "<English_summary>"` | **對話結束必跑**：1. 備份對話 (雙軌) 2. 檢核更新所有 .md (含 .agent/skills/) 3. 測試與英文 Commit |
| **使用者說要去上課/中斷** | `uv run python run.py handoff "<reason_in_English>"` | 先更新 `memory/HANDOFF.md`，再英文 commit |
| **封存所有會話紀錄** | `uv run python run.py archive-sessions` | 自動掃描 Brain 目錄 (嚴格限定本專案)，更新雙軌紀錄與總結 |
| **常駐智慧看門狗** | `uv run python run.py watchdog` | 監聽待處理目錄，一體化監測 RAM/SSD/電池安全 |
| **發布與合併到 main** | `uv run python run.py publish "<English_release_notes>"` | 本地 Squash 合併，提示手動 push 指令 |

---

## 二、 核心五大鐵律 (Core Directives)

### 1. 🛑 嚴禁未經授權 Push (Zero-Push Rule)
- 本專案預設為 **Local-Only 模式**。
- 所有 AI Agent 嚴禁在終端機執行任何形式的 `git push`（系統已配置 Pre-push Hook 阻斷）。
- 唯有使用者明確要求發布，且附帶 `ALLOW_PUSH=1` 授權時方可進行。

### 2. 📝 提交前強制文檔同步與【全英文 Commit】(Doc-Before-Commit & English Protocol)
- **嚴禁只 commit 程式碼而遺漏文檔！**
- 每次準備提交代碼前：
  - 若完成功能：先在 `memory/TASKS.md` 勾選並標註日期 `[YYYY-MM-DD]`。
  - 若中斷或交接：先在 `memory/HANDOFF.md` 刷新當前時間戳與下次接手指令。
  - 若更動架構或檔案：先同步更新 `docs/STRUCTURE.md`。
- **⚠️ 語言約束：所有 Git Commit 訊息必須使用【英文】(English Only)**：
  - 嚴格遵循 Conventional Commits 格式，例如：
    - `[YYYY-MM-DD] feat: implement RAM guard and auto-wake for Ollama`
    - `[YYYY-MM-DD] fix: resolve LaTeX formula bracket parsing error`
    - `[YYYY-MM-DD] wip(handoff): pause session before class`

### 3. 🛡️ 拒絕幽靈修復與硬體守衛原則 (Proof of Execution & Guarding)
- **嚴禁口頭宣告「已修復」**：每次修改核心程式碼後，必須出示執行 Log 或測試通過的輸出證據。
- **嚴禁略過硬體守衛**：所有呼叫本地大模型（Ollama）的代碼，必須通過 `src/guards/hardware.py` 檢查。當 RAM < 4GB 或低電量電池模式時，必須優雅降級，不得造成使用者系統當機或耗盡電力。

### 4. ⚖️ 決策衝突阻斷協議 (Decision Conflict Circuit Breaker)
- 在實作方案前，AI 必須檢索 `docs/adr/` 中所有狀態為 `[Status: Accepted]` 的決策。
- 若使用者的指令或當前的修改方案與歷史決策產生衝突，**嚴禁自行偷偷修改**，必須立即暫停並向使用者主動發問確認。

### 5. 🍎 macOS 原生能力與硬體協同優先原則 (macOS-Native Synergy Directive)
- **嚴禁盲目只推薦跨平台的重型第三方套件**：AI 在規劃技術方案時，若運行環境為 macOS（特別是 Apple Silicon 晶片），**必須主動評估並優先推薦 macOS 內建或原生更出色的框架與工具**。
- **具體評估對照範例**：
  - **文字識別/OCR**：主動評估 **Apple Vision Framework (`VNRecognizeTextRequest`)**。相較於肥大的 PaddleOCR / Tesseract，Vision 框架為系統內建、零依賴、調用神經網路引擎 (ANE)，辨識速度極快且近乎零記憶體負擔。
  - **圖像轉換與處理**：優先考慮內建 **`sips`** 或 Core Graphics，避免動輒依賴龐大的外掛庫。
  - **PDF 解析與渲染**：評估 **Quartz / PDFKit** 原生 API。
  - **模型推理與加速**：優先評估 **Metal / MPS (Metal Performance Shaders)** 與 **CoreML**。
- **原則**：只要 macOS 內建/原生功能的表現、耗電量或記憶體佔用更優秀，AI 必須主動向使用者提出該方案的優劣對比與整合建議。

### 6. 🗄️ 會話雙軌歸檔與全自動隔離協議 (Automated Session Archiving & Quarantine)
- **自動歸檔時機**：**嚴格限定在「結束對話」或「重大發布」時執行**。
  - 對話進行中：保持系統常態即時更新 Markdown 文檔，**不進行中途碎片式歸檔**。
  - 當使用者說明「結束對話」或執行 `run.py end-session` / `publish` 時，才執行雙軌歸檔。
- **嚴格專案隔離**：歸檔時強制校驗工作區路徑（`str(ROOT)` 或 `book-processor`），絕不掃描或收錄全域其他無關專案的會話。
- **雙軌配對歸檔格式**：
  - `memory/sessions/YYYY-MM-DD-<topic>-summary.md`：**高密度總結**（先看這個，掌握決策與結果）。
  - `memory/sessions/YYYY-MM-DD-<topic>-transcript.md`：**完整對話紀錄**（有疑問時深挖原始問答）。
- **異常無條件隔離**：
  - 任何 Ollama 處理失敗、超時、或信度評估 < 0.80 的瑕疵，**一律自動拋入 `data/needs_review/` 隔離存檔**，絕不中斷主批次管線。

### 7. ⚡ AI 全自動主動執行原則 (Agent Proactive Execution Protocol)
- **嚴禁消極在對話框中輸出指令叫使用者去終端機跑**：凡是可以程式化、腳本化執行的操作（如環境檢查 `doctor`、開場簡報 `agent-init`、轉檔執行 `process`、文檔更新、Git 本地提交 `save`/`handoff`/`end-session`、對話歸檔 `archive-sessions`），**AI 必須直接調用終端工具主動執行**，向使用者展示執行輸出與診斷結果。

### 8. 🔄 治理標準持續自我迭代協議 (Self-Updating Standard Directive)
- 每次使用者對專案提出任何新的規則、格式約束或流程改進時，**AI 必須無條件主動同步更新 `PROJECT_INIT_STANDARD.md` 與 `AGENTS.md`**，確保未來所有專案都能自動享有最新標準。

### 9. 📐 CODING_RULES 雙層繼承架構 (Two-Tier Rule Architecture)
- `docs/CODING_RULES.md` 嚴格採雙層結構：
  - **第一部：通用軟體工程基線**（所有專案 100% 通用，包含 SOLID、純函數、強型別 Dataclass、原子寫入、異常防呆）。
  - **第二部：本專案專屬領域擴充**（本專案特化規則，如 Apple Vision、Ollama 守衛、LaTeX 括號檢驗、`literature` 命名）。
- 其他專案開案時直接繼承第一部，領域規則只寫在第二部，永不污染通用基線。

### 10. ⏱️ 全生命週期同步與存檔時機矩陣 (The 6 Golden Triggers)
所有 AI 必須嚴格遵照以下節奏執行文檔同步、Git 提交與會話歸檔：
1. **開場喚醒**：跑 `run.py agent-init` 讀檔簡報，不 commit、不備份。
2. **架構異動**：即時更新 `docs/STRUCTURE.md`，隨功能一併 commit。
3. **規則更新**：即時同步 `docs/CODING_RULES.md`、`AGENTS.md` 與 `PROJECT_INIT_STANDARD.md`，小步 commit。
4. **功能完成**：在 `memory/TASKS.md` 勾選並標註日期，跑 `run.py save "<English_msg>"` commit。對話中持續保留各項 md 檔案之常態維護。
5. **結束對話 / 結案離席** ⭐：
   - 當使用者說明「結束對話」時，AI 主動執行閉環 SOP (`run.py end-session "<English_summary>"` 或手動執行三部曲)：
     1. **備份對話**：產出本次會話雙軌檔案 (`-summary.md` + `-transcript.md`)，嚴格限定本專案。
     2. **最終全面檢查與文檔同步**：全面檢查並同步更新所有相關 `.md` 文件，包含 `memory/HANDOFF.md`、`memory/TASKS.md`、`docs/STRUCTURE.md`、以及 `.agent/skills/` 內所有 `SKILL.md`。
     3. **測試與 Git 提交**：執行單元測試門禁（100% 通過），以全英文 Conventional Commit 提交本地存檔。
6. **里程碑發布** ⭐：更新 `CHANGELOG.md`，跑 `run.py publish "<notes>"`，自動執行全量測試、雙軌封存與 Squash Merge。

### 11. ⚙️ 八大自動化機制與觸發防線 (The 8 Autonomous Triggers)
1. **存檔測試門禁**：`run.py save` 自動秒級執行 `unittest`，測試未全數通過自動攔截 Commit。
2. **發布前全流程門禁**：`run.py publish` 自動執行全量測試 ➔ 自動會話歸檔 ➔ 清理過期暫存 ➔ Squash Merge。
3. **Ollama 背景喚醒**：模型服務離線時自動啟動 `ollama serve`，失敗自動啟用純規則優雅降級。
4. **硬體受限平滑降級**：RAM < 4GB、低電量電池模式或 SSD < 10GB 時自動降級大模型調用。
5. **看門狗來檔自動轉檔**：`run.py watchdog` 監聽到新檔案自動檢查硬體並派發轉檔管線。
6. **瑕疵自動修復與隔離**：LaTeX 語法錯誤或置信度 < 0.80 自動嘗試修復，失敗拋入 `data/needs_review/`。
7. **過期暫存自動清理**：`doctor`、`save`、`publish` 自動清理上次異常中斷殘留的 `*.tmp.*` 暫存檔。
8. **依賴環境自動同步**：`pyproject.toml` 異動或缺套件時自動執行 `uv sync` 對齊環境。

---

## 三、 臨時實驗室規範 (Scratchpad Policy)
- 開發或除錯過程中所撰寫的一次性測試腳本、臨時試跑程式，**一律存放在 `scratch/` 目錄下**（例如 `scratch/test_math_regex.py`）。
- **嚴禁** 將臨時腳本隨意散落在根目錄或 `src/` 中。
