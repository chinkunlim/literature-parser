# 📜 CHANGELOG.md (專案變更日誌)

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 規範，並以語意化版本進行紀錄。

---

## [Unreleased]
- 待開發：未來的視覺化儀表板 (Dashboard) 介面 (`dashboard/`)。
- 待優化：更多特化期刊排版（如 IEEE、ACM）的雙欄分割微調。

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
