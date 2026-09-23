# 📋 memory/TASKS.md (專案任務進度看板)

最後更新日期：2026-09-24

---

## 🏃 當前 Sprint (v1.0.0-rc1 專案治理與守衛上線)

- [x] [2026-09-23] 梳理專案核心需求與淘汰 OpenClaw 冗餘檔案
- [x] [2026-09-23] 設計跨 Agent 協同規範 (`AGENTS.md`) 與冷啟動手冊 (`OPERATIONS.md`)
- [x] [2026-09-23] 建立雙軌實體資料夾與隔離防呆區 (`data/input/`, `data/output/`, `data/needs_review/`)
- [x] [2026-09-23] 撰寫軟硬體守衛模組 (`src/guards/hardware.py` - RAM/電池/SSD/MPS)
- [x] [2026-09-23] 撰寫 Ollama 自動喚醒、模型檢查與優雅降級守衛 (`src/guards/ollama_guard.py`)
- [x] [2026-09-23] 撰寫輸入 JSON 驗證與輸出異常自動除錯攔截器 (`src/guards/validator.py`)
- [x] [2026-09-23] 實作命令總入口 `run.py` (支援 doctor、process、save、handoff 等)
- [x] [2026-09-23] 安裝 Git 物理防手滑鎖 (`.git/hooks/pre-push`)
- [x] [2026-09-23] 建立通用新專案開案範本 (`PROJECT_INIT_STANDARD.md`)
- [x] [2026-09-23] 將歷史全對話脈絡濃縮歸檔至 `memory/sessions/`
- [x] [2026-09-24] 強化低信度自動隔離與對話工作階段雙軌歸檔 (`data/needs_review/`, `memory/sessions/`)
- [x] [2026-09-24] 補齊專案歷史 5 個對話之雙軌歸檔與全自動會話封存指令 (archive-sessions)
- [x] [2026-09-24] 徹底物理遷移並刪除根目錄過渡資料夾 (`inbox/`, `processed/`, `output/`)
- [x] [2026-09-24] 將學術期刊全面標準化升級為學術文獻 (`journal` -> `literature`)
- [x] [2026-09-24] 建立三層技能體系 (`.agent/skills/`: `document-processor`, `textbook-processor`, `literature-processor`)
- [x] [2026-09-24] 將 AI 主動執行、文獻命名、乾淨根目錄與自更新協議永久寫入 `PROJECT_INIT_STANDARD.md`
- [x] [2026-09-24] 徹底移除根目錄過渡腳本 (`verify_accuracy.py`, `batch_convert.py`, `book_processor.py`) 並優化單元測試相依路徑
- [x] [2026-09-24] 實現軟硬體一體化智慧看門狗 (`run.py watchdog`)，歸檔 `ISSUES.md` 與 `OPTIMIZATION_PROPOSAL.md` 至 `docs/`，並將第 14、15 條鐵律寫入標準
- [x] [2026-09-24] 將開案前置軟硬體基線探針 (鐵律 16) 與開案標配看門狗 (鐵律 17) 寫入 `PROJECT_INIT_STANDARD.md`

---

## 📅 後續規劃 (Backlog)

- [ ] [未排程] 實作 `dashboard/` 視覺化儀表板（讀取 `data/state/status.json`）
- [ ] [未排程] 新增專門適配 IEEE / ACM 雙欄論文的進階版面範本
- [ ] [未排程] 優化長篇書籍跨章節概念雙鏈自動關聯 (Obsidian Graph 支援)
