# 🤖 AGENTS.md (跨 AI Agent 協作通用憲法)

> 適用對象：所有參與本專案的 AI Agents（包含 Antigravity、Claude Code、Codex、Cursor、OpenClaw 等）。
> 所有 Agent 進入專案的第一件事，必須完整閱讀並恪守本憲法。

---

## 一、 意圖 ➔ 指令派發對照表 (Action Dispatch Table)

當使用者提出以下意圖時，**直接呼叫對應指令，嚴禁自己重新發明輪子或改寫底層主邏輯**：

| 使用者意圖 (User Intent) | 應該執行的 CLI 指令 | 說明與約束 |
| :--- | :--- | :--- |
| **環境健檢 / 診斷** | `uv run python run.py doctor` | 檢查 RAM、電池、SSD、Ollama、模型 |
| **轉換書籍** | `uv run python run.py process data/input/books/<filename>` | 自動啟動書籍章節切分與文意縫合 |
| **轉換學術期刊 / 論文** | `uv run python run.py process data/input/journals/<filename>` | 自動啟動雙欄排版、摘要與文獻解析 |
| **驗證 Ollama 自動喚醒** | `uv run python run.py test-ollama-auto-trigger` | 驗證輸入與輸出守衛能否自動喚醒 Ollama |
| **一般進度存檔** | `uv run python run.py save "<commit_message>"` | 先更新文檔時間戳，再本地 commit |
| **使用者說要去上課/中斷** | `uv run python run.py handoff "<reason>"` | 先更新 `memory/HANDOFF.md`，再本地 commit |
| **發布與合併到 main** | `uv run python run.py publish "<release_notes>"` | 本地 Squash 合併，提示手動 push 指令 |

---

## 二、 核心四大鐵律 (Core Directives)

### 1. 🛑 嚴禁未經授權 Push (Zero-Push Rule)
- 本專案預設為 **Local-Only 模式**。
- 所有 AI Agent 嚴禁在終端機執行任何形式的 `git push`（系統已配置 Pre-push Hook 阻斷）。
- 唯有使用者明確要求發布，且附帶 `ALLOW_PUSH=1` 授權時方可進行。

### 2. 📝 提交前強制文檔同步 (Doc-Before-Commit Protocol)
- **嚴禁只 commit 程式碼而遺漏文檔！**
- 每次準備提交代碼前：
  - 若完成功能：先在 `memory/TASKS.md` 勾選並標註日期 `[YYYY-MM-DD]`。
  - 若中斷或交接：先在 `memory/HANDOFF.md` 刷新當前時間戳與下次接手指令。
  - 若更動架構或檔案：先同步更新 `docs/STRUCTURE.md`。

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

---

## 三、 臨時實驗室規範 (Scratchpad Policy)
- 開發或除錯過程中所撰寫的一次性測試腳本、臨時試跑程式，**一律存放在 `scratch/` 目錄下**（例如 `scratch/test_math_regex.py`）。
- **嚴禁** 將臨時腳本隨意散落在根目錄或 `src/` 中。
