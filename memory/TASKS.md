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
- [x] [2026-09-24] 升級 `PROJECT_INIT_STANDARD.md` 至 22 大核心鐵律與企業級目錄骨幹，深度擴充 `docs/CODING_RULES.md` 納入 SOLID 原則、純函數與原子 I/O 規範
- [x] [2026-09-24] 確立 CODING_RULES 雙層繼承架構（通用基線+領域擴充）與六大黃金時機同步矩陣（同步MD/Git/對話歸檔），同步升級標準至 24 大鐵律
- [x] [2026-09-24] 確立八大自動化機制與確定性觸發防線 (The 8 Autonomous Triggers)，在 run.py 實裝存檔測試門禁、發布自動全流程與暫存自動清理，並同步規範至 PROJECT_INIT_STANDARD 與 AGENTS
- [x] [2026-09-24] 確立 Git、對話記憶 (Sessions) 與核心文檔 (Markdown) 全生命週期自動化管理管線規範，並升級 run.py publish 支援本地自動打標籤 (Git Tagging)
- [x] [2026-09-24] 深度分析使用者 6 大操作習慣並整合至 PROJECT_INIT_STANDARD（升級至 30 大工程鐵律），並實作 run.py init-project 達成 3 秒全自動企業級一鍵開案腳手架
- [x] [2026-09-24] 新增 Springer 與 IEEE 出版商版面範本與雜訊過濾規則 (`config/publishers/springer.json`, `config/publishers/ieee.json`)
- [x] [2026-09-24] 實現目錄級全自動批次轉檔指令 (`run.py batch <dir>`)，具備逐檔硬體巡檢保護與冷卻防護機制
- [x] [2026-09-24] 實現 Obsidian 雙鏈與全書索引生成器 (`obsidian_linker.py` + `run.py obsidian-link`)，自動注入章節前後導航並支援 Graph View
- [x] [2026-09-24] 實現全域進度狀態中心化管理 (`GlobalStateManager` + `run.py status`)，原子化維護 `data/state/global_status.json` 並支援輸出目錄自動狀態重建

---

## 📅 後續規劃 (Backlog)

- [ ] [未排程] 實作 `dashboard/` 視覺化儀表板（讀取 `data/state/global_status.json`）
- [ ] [未排程] `LiteraturePipeline` 領域客製化（支援論文子類型判斷與 IEEE 特殊版面過濾）



