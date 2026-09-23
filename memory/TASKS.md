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

---

## 📅 後續規劃 (Backlog)

- [ ] [未排程] 實作 `dashboard/` 視覺化儀表板（讀取 `data/state/status.json`）
- [ ] [未排程] 新增專門適配 IEEE / ACM 雙欄論文的進階版面範本
- [ ] [未排程] 優化長篇書籍跨章節概念雙鏈自動關聯 (Obsidian Graph 支援)
