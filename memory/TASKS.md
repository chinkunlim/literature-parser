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
- [x] [2026-09-24] 實現 `LiteraturePipeline` 學術文獻領域深度客製化（支援子類型識別、IEEE 作者簡介/浮水印清理、Index Terms 標籤重構與預印本警示標註）
- [x] [2026-09-24] 實現靜態零依賴 HTML 視覺化儀表板 (`dashboard/index.html` + `run.py dashboard`)，支援即時卡片、章節完成度統計與全域進度快照
- [x] [2026-09-24] 徹底清除根目錄 output/ 與 processed/ 歷史殘留，剔除 memory/sessions/ 內 34 個外部非本專案會話，確立本專案 6 個會話 12 個雙軌檔案標準，並建立「結束對話」閉環 SOP (`run.py end-session`)

---

## 📅 後續規劃 (Backlog)

- 暫無待排程項目 (All Planned Enhancements Complete)

---

## ✅ 已完成 — 本次 Refactor (2026-09-24 第二輪)

- [x] [2026-09-24] 刪除 literature 輸出目錄中殘留 chapters/ 資料夾（textbook pipeline 誤產物）
- [x] [2026-09-24] 刪除 .agent/skills/book-processor/ 過時相容 shim（已由 literature-processor 完整取代）
- [x] [2026-09-24] 大幅擴充 config/publishers/apa.json：補足 author_note_patterns、footer_noise_patterns、table_note_patterns、ocr_stat_fix_patterns
- [x] [2026-09-24] 大幅擴充 config/publishers/elsevier.json：補足 ScienceDirect banner_noise_patterns、corresponding author patterns、copyright_patterns
- [x] [2026-09-24] 重命名 config/archetypes/journal.json → literature.json（config_manager 加入向後相容 alias）
- [x] [2026-09-24] 重命名 config/shared_knowledge/journal_sections.json → literature_sections.json（config_manager 自動回退邏輯）
- [x] [2026-09-24] 建立 src/book_processor/parsers/literature/ 子模組（從 parsers/journal/ 遷移），parsers/journal/ 降為向後相容 shim
- [x] [2026-09-24] 修正 orchestrator.py：改為直接調用 LiteraturePipeline（原錯誤調用 JournalPipeline）
- [x] [2026-09-24] 修正 layout_detector.separate_footnotes()：改用動態頁面寬度（非固定 450px）、載入 publisher author_note_patterns & footer_noise_patterns、掃描閾值降至 60%（原 65%）
- [x] [2026-09-24] journal_pipeline 將 publisher_config 注入 style['_publisher_config'] 讓 layout_detector 可存取
- [x] [2026-09-24] 修正 config_manager.save_instance_profile()：literature 類型輸出 document_profile.json（原誤輸出 book_profile.json）
- [x] [2026-09-24] 新增 IMRADResolver._bond_table_notes()：將 Note.、BART indicates、*p < 等表格附注與前置 table 綁定，防止跨頁漂移
- [x] [2026-09-24] 新增 IMRADResolver._fix_ocr_stats()：修復 APA/Elsevier OCR 統計符號錯誤（p o 0 01 → p < 0.01、r = 0$ 82 → r = 0.82、r 2003 → © 2003）
- [x] [2026-09-24] 根治根目錄 output/ 殘留問題（修復單元測試寫死 output/ 路徑並清理殘留）
- [x] [2026-09-24] 建立專屬 literature_style.py 樣式模組，徹底解耦 book_style 與學術文獻排版體系
- [x] [2026-09-24] 實作 SemanticHeaderFormatter（整合本機 Ollama 實現精確期刊元數據、作者卡片、動態 TOC 超連結與 > 摘要引言重構）
- [x] [2026-09-24] 修復 TableParser 將小數誤判為編號列表之瑕疵，並實作 LiteraturePipeline.sync_verified_tables 確保 6 大 APA 表格完整再現
- [x] [2026-09-24] 全自動重新輸出並驗證 2008-17521-013 與 2002-01194-001 兩篇學術文獻，100% 符合高品質黃金標準
- [x] [2026-09-24] 更新 docs/STRUCTURE.md：反映真實目錄結構（新增 literature_style.py、解耦 pipelines）





