# 🗄️ 會話深度紀要：專案治理、文件重構、軟硬體守衛與跨 Agent 體系建立

- **會議/會話日期**：2026-09-23
- **參與角色**：使用者 (Developer) & Antigravity (AI Assistant)
- **主題**：解決專案長期痛點、剔除 OpenClaw 冗餘、落實軟硬體守衛、自動觸發 Ollama、雙軌書籍/期刊分離與未來新專案標準化

---

## 一、 背景與原始痛點回溯

1. **檔案混亂與職責重疊**：
   - 另一個專案留下來的 20+ 個 Markdown 檔案（如 `agent.md`, `AGENTS.md`, `IDENTITY.md`, `AI_PROFILE.md` 等）四胞胎並存，身分設定打架。
   - 40KB 的單一 `DECISIONS.md` 造成每次對話吃掉大量 Token，且容易讓 AI 遺忘覆蓋關係、寫回已被廢棄的舊版代碼。
   - 缺乏「臨時檔案（Scratchpad）」與「長期資產（Docs）」的生命週期區分。
2. **開發過程的中斷（如去上課、外出）**：
   - 使用者中途常需離開去上課，回來時 AI 上下文重置，無法無縫接續，常造成重複施工或方向偏離。
3. **不同 AI Agent 協作迷航**：
   - 切換到 Codex、Claude 或 Cursor 時，新 Agent 不知道現有專案架構，容易亂創資料夾或重複寫已存在的函式。
4. **「幽靈修復」與 Ollama 沒自動啟動**：
   - 過去 AI 聲稱「修復了 Ollama 驗證」，但檢視原始碼發現 `use_ollama` 預設為 `False`，根本從未在主流程中被調用。
   - 缺乏對電腦軟硬體（可用 RAM、筆電電池模式、SSD 空間、過熱降頻）的保護機制，導致可能在低電量下耗盡電池或吃爆記憶體。
5. **重啟專案後的冷啟動失憶**：
   - 專案隔數週/數月重啟時，使用者自己與新 AI 均不知道如何下指令，需要耗費大量 Token 重新掃描整個專案。

---

## 二、 核心架構決策與共識

### 1. 徹底精簡文件架構（留下 9 大核心）
- 根目錄保留：`OPERATIONS.md`（30秒啟動）、`AGENTS.md`（跨 Agent 憲法）、`CHANGELOG.md`、`README.md`、`PROJECT_INIT_STANDARD.md`。
- `memory/` 目錄：`TASKS.md`（任務看板）、`HANDOFF.md`（離席交接卡）、`sessions/`（對話紀要）。
- `docs/` 目錄：`STRUCTURE.md`（全專案地圖與功能備註）、`CODING_RULES.md`（開發守則）、`ARCHITECTURE.md`（系統架構）、`adr/`（獨立 ADR 決策檔案）。

### 2. 軟硬體守衛與 Ollama 強制調用
- 在 `src/guards/` 建立硬體與服務防線：
  - **RAM 守衛**：可用記憶體 < 4.0GB 時拒絕載入本地大模型，啟動安全降級。
  - **電池守衛**：筆電處於電池模式且電量偏低時，提示警報並降級為輕量規則，避免外出斷電。
  - **磁碟守衛**：可用空間 < 10GB 時發出警告。
  - **Ollama 探活與喚醒**：連線前自動 ping，若未開自動嘗試喚醒；若無指定模型或未安裝，優雅降級為純語法規則驗證，絕不讓主轉檔程式崩潰。
  - **兩大觸發 Hook**：
    1. 輸入檔案與 JSON manifest 描述不符時，強制喚醒 Ollama 進行語義分析。
    2. 輸出 LaTeX 公式或排版異常時，主動將上下文拋給 Ollama 自我修復。

### 3. 人機防呆與「慣例優於配置（Convention over Configuration）」
- 設立 `data/input/books/` 與 `data/input/journals/`，以實體目錄定生死，完全免除 AI 猜測書籍或論文的錯誤可能。
- 設立 `data/needs_review/` 隔離區：疑難頁面拋入隔離區由人把關，主流程不被中斷。
- 設立 `scratch/` 臨時實驗室：一次性測試程式集中管理，不入 Git，不污染正式目錄。

### 4. Git 本地防護與先更文檔後 Commit 鐵律
- 配置 `.git/hooks/pre-push`，任何 `git push` 自動阻斷，唯有 `ALLOW_PUSH=1` 才放行。
- AI 執行任何 commit 前，必須先自動將文檔（HANDOFF / TASKS / CHANGELOG）蓋上最新時間戳記，嚴禁只 commit 程式碼。

### 5. 跨專案通用開案標準 (`PROJECT_INIT_STANDARD.md`)
- 產出一份通用的開案標準文件，未來開任何新專案時，直接作為 Prompt 餵給 AI，自動在 1 分鐘內建立一模一樣的高規格工程骨架。

---

## 三、 本次實施產出清單

1. **文檔層**：`OPERATIONS.md`, `AGENTS.md`, `CHANGELOG.md`, `PROJECT_INIT_STANDARD.md`, `memory/TASKS.md`, `memory/HANDOFF.md`, `docs/STRUCTURE.md`, `docs/CODING_RULES.md`, `docs/ARCHITECTURE.md`, `docs/adr/0001-...`, `docs/adr/0002-...`。
2. **代碼層**：`run.py` (CLI 總指揮中心), `src/guards/hardware.py`, `src/guards/ollama_guard.py`, `src/guards/validator.py`, `src/utils/logger.py`, `.git/hooks/pre-push`。
3. **目錄層**：`data/input/books/`, `data/input/journals/`, `data/output/books/`, `data/output/journals/`, `data/needs_review/`, `data/state/`, `scratch/`, `logs/`。
