# 📜 CHANGELOG.md (專案變更日誌)

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 規範，並以語意化版本進行紀錄。

---

## [Unreleased]
- 待開發：未來的視覺化儀表板 (Dashboard) 介面 (`dashboard/`)。
- 待優化：更多特化期刊排版（如 IEEE、ACM）的雙欄分割微調。

---

## [1.0.0-rc2] - 2026-09-24

### 🌟 新增 (Added)
- **通用開案標準升級至 30 大核心工程鐵律 (`PROJECT_INIT_STANDARD.md`)**：
  - 深度整合 SOLID 物件導向原則、純函數無副作用計算、強型別 Data Contract、防衛性編程與原子性檔案寫入、12-Factor 環境隔離。
  - 整合使用者 6 大操作習慣（全局系統思維、零歷史包袱、高密度摘要先行、秒級測試迴圈、離線主權、一鍵腳手架）。
- **雙層代碼規範架構 (`docs/CODING_RULES.md`)**：
  - 第一部：通用軟體工程基線（所有專案 100% 通用，零污染繼承）。
  - 第二部：本專案專屬領域擴充（Apple Vision OCR、4GB RAM 守衛、Ollama 修復、`literature` 命名）。
- **全生命週期六大黃金時機同步矩陣 (The 6 Golden Triggers)**：
  - 確定性規範開場喚醒、架構異動、規則改進、功能完成、離席暫停與里程碑結案時的文檔、Git 與對話備份動作。
- **專案全自動化八大防線 (The 8 Autonomous Triggers)**：
  - 存檔自動測試門禁、發布全流程門禁、Ollama 背景自動喚醒、硬體受限平滑降級、看門狗來檔自動轉檔、瑕疵自動修復隔離、過期暫存自動清理、環境依賴自動同步。
- **一鍵開案 CLI 指令 (`run.py init-project`)**：
  - 3 秒內自動建立符合 30 大鐵律的完整專案目錄（14 個目錄）、Git 安全鎖、軟硬體守衛、雙層代碼規範、測試與 run.py 總指揮。
- **全會話雙軌自動封存 (`run.py archive-sessions`)**：
  - 自動同步歷史 5 個會話之高密度摘要 (`-summary.md`) 與完整問答紀錄 (`-transcript.md`)。
- **軟硬體一體化看門狗 (`run.py watchdog`)**：
  - 常駐監聽 `data/input/` 目錄，同時稽核 RAM、SSD、電池安全，來檔即自動安全轉檔。

### 🔧 變更 (Changed)
- **領域命名全面標準化**：學術文件命名全面升級為 `literature`（學術文獻），涵蓋期刊、論文、預印本與報告。
- **技能體系升級三層分流**：`.agent/skills/` 確立 `document-processor` (總調度)、`textbook-processor` (書籍子技能)、`literature-processor` (文獻子技能)。
- **單元測試相依性優化**：動態注入 `sys.path`，171 個單元測試在 0.11 秒內全數通過 (100% PASS)。

### 🗑️ 移除與清理 (Removed & Cleaned)
- **根目錄過渡資料夾徹底清除**：移除 `inbox/`、`processed/`、`output/`，資料流嚴格統一於 `data/input/` 與 `data/output/`。
- **根目錄過渡腳本清理歸檔**：移除 `verify_accuracy.py`、`batch_convert.py`、`book_processor.py` 並歸檔至 `scratch/`。
- **過時的根目錄 `skills/` 資料夾徹底移除**：移除 9 月 18 日舊版 `skills/`，確立官方原生 `.agent/skills/` 為唯一單一真理來源。
- **非標 Markdown 檔案歸檔**：`ISSUES.md` 與 `OPTIMIZATION_PROPOSAL.md` 全數規範收納至 `docs/`。

---

## [1.0.0-rc1] - 2026-09-23

### 🌟 新增 (Added)
- **跨 Agent 治理體系**：
  - 新增 `OPERATIONS.md`，提供 30 秒冷啟動與故障排除指南。
  - 新增 `AGENTS.md`，建立意圖路由表、Local Git 規範與決策衝突阻斷協議。
  - 新增 `PROJECT_INIT_STANDARD.md`，提供日後所有新專案通用的開案標準範本。
- **軟硬體與連動守衛層 (`src/guards/`)**：
  - `hardware.py`：即時檢測系統可用 RAM (≥ 4GB 門檻)、電池狀態、SSD 剩餘空間 (≥ 10GB) 與 Apple Silicon MPS 狀態。
  - `ollama_guard.py`：自動探活本地 Ollama 服務、支援後台自動喚醒、檢查模型下載狀態，並提供優雅降級機制。
  - `validator.py`：自動檢查輸入檔案是否符合 JSON 描述，並在輸出異常時自動喚醒 Ollama 進行自我修復除錯。
- **總指揮入口 (`run.py`)**：
  - 封裝 `doctor`、`process`、`save`、`handoff`、`publish`、`test-ollama-auto-trigger` 等一鍵指令。
- **雙軌架構與人機防呆分流 (`data/`)**：
  - 實體劃分 `data/input/books/` 與 `data/input/journals/`，達成「路徑即路由」零判斷成本。
  - 新增 `data/needs_review/` 隔離區，異常段落自動隔離，避免卡死主轉檔管線。
- **Git 物理防護鎖**：
  - 配置 `.git/hooks/pre-push`，預設封鎖所有未經 `ALLOW_PUSH=1` 授權的遠端推送。
- **架構決策紀錄 (ADR)**：
  - 建立 `docs/adr/0001-ollama-hardware-guard-and-auto-verify.md`
  - 建立 `docs/adr/0002-domain-split-book-and-paper.md`

### 🔧 變更 (Changed)
- **Ollama 呼叫機制徹底翻新**：徹底告別過往預設關閉 (`use_ollama=False`) 的假修復問題，全面改由守衛層自動依硬體條件決定啟用與降級。
- **日誌標準化**：統一採用結構化日誌格式（Where + Why + How），日誌集中收錄於 `logs/`。

### 🗑️ 移除 (Removed)
- 清理非本專案所需的 OpenClaw 冗餘規範，集中專案記憶於 `memory/` 與 `docs/`。
