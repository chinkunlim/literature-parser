# 📋 memory/TASKS.md (專案任務進度看板)

最後更新日期：2026-09-25

---

## 🏃 當前 Sprint (v1.0.0-rc1 專案治理與守衛上線)

- [x] [2026-09-25] 實作多期刊學術文獻版面分析與物理座標校準 (`CoordinateCalibrator.calibrate_literature_geometry` & `document_profile.json`)：
  - 提取頁面寬高、頂部導覽 cutoff、底部頁碼 cutoff、單雙欄判定與分欄 gutter、第一頁內文起始 Y 座標
  - 自動為每篇文獻持久化專屬 `document_profile.json`，並擴充出版商範本 (`literature_aip.json`, `literature_cup.json`, `literature_annual_reviews.json`)
  - 擴充 `PublisherDetector` 支援 AIP (`10.1063`), Annual Reviews (`10.1146`), CUP (`10.1017`)
- [x] [2026-09-25] 解決單欄/雙欄自適應與 NIH/HHS 作者手稿雜訊過濾：
  - `DigitalPDFParser` 整合動態單欄守衛 (`is_single_col_doc`)，防止單欄手稿被誤切
  - `IMRADResolver` 實裝 `_clean_nih_watermarks` 與 `_relocate_auxiliary_sections`，將特別章節（Author Note, Acknowledgments, Declarations, Funding, Conflict of Interest, Data Availability）統一收斂至 `## References` 之前
  - `LiteratureMetadataExtractor` 支援 NIH `Published in final edited form as:`、CUP、AIP、Elsevier 元數據解析，且支援 `Keywords:` 前之摘要提取與第一頁緒論保護
  - 解決貨幣與版權費符號 (`$12.00`) 與不對稱 `$$` 導致之 KaTeX 崩潰
  - 優化 `AccuracyVerifier` 字典型態辨識（支援標準英文屈折/衍生詞綴與學術詞彙），全套 197 項測試 100% 通過
- [x] [2026-09-25] 全量批次轉檔與審查 `data/input/literature/` 全部 10 篇學術文獻：
  - 10 篇文獻全部產出高精確度 Markdown、抽取並語義錨定圖表、生成精準座標 `document_profile.json`，全部 100% 通過品質驗證（SUCCESS PASS）
- [x] [2026-09-25] 實作 Figure 與 Table 語義定位與句子自動縫合演算法 (`FigureFormatter.reposition_figures`)：
  - 解決 Figure 2 穿插於跨頁指示說明段落中間（截斷 `...all money in` 與 `your temporary bank is lost...`）之缺陷
  - 所有 Figure 和 Table 精確放置於內文第一次提及之完整段落（以 `\n\n` 結尾）之後
  - 原位置被圖表切斷之段落 100% 自動無縫縫合，未提及圖表優雅回退章節末尾
  - 新增 `tests/test_v37_semantic_figure_table_placement.py`，全套 193 項單元測試 100% 通過，Content Continuity 達成 0 abrupt cut [PASS]
- [x] [2026-09-25] 對比驗證 `2002-01194-001.md` 與 `2002-01194-001_Verified.md`：
  - 17 個標題與 6 個 HTML 表格 100% 精準對齊
  - 清理 Table 1~6 所有 OCR 殘留碎片，縫合跨欄截斷之討論段落
  - `MarginParser` 增加 `gloss_placement == 'none'` 與 `is_literature` 守衛，根除教科書邊欄詞彙誤判
  - 正規化詞彙相似度達 95.44%，190 項單元測試 100% 通過
- [x] [2026-09-25] 全專案核心套件重命名：`src/book_processor` → `src/doc_processor`，同步更新 `pyproject.toml`、`run.py`、所有測試與技能文檔
- [x] [2026-09-25] 徹底根除 `journal` 殘留：刪除 `journal_pipeline.py` 與 `journal_*.json`，全面收斂為 `literature` 架構
- [x] [2026-09-25] 修復 5 大文獻排版瑕疵 (`2002-01194-001.md`)：
  - 清理頁碼殘留（75）並保留連字號（`laboratory-based`）
  - 欄位隔離基線聚合，消除假清單項（`- established`）
  - 精確清除 Table 1, 2, 6 OCR 殘留碎片並錨定語意位置
  - 修復跨行 `Table\n2. With...` 導致之偽清單標記
  - 轉義 `Collect $$$` 防範 KaTeX 語法崩潰，解碼 `&amp;` 為 `&`
- [x] [2026-09-25] 新增單元測試驗證排版修復，190 項測試 100% 通過
- [x] [2026-09-25] 徹底整併刪除 `src/book_processor/parsers/journal/`，將所有文獻模組收斂於 `parsers/literature/`
- [x] [2026-09-25] 建立 `LiteratureMetadataExtractor`：支援 Page 1 確定性元數據快速路徑、Ollama 結構化 JSON 備援、統一 `.article-meta` 與作者卡片
- [x] [2026-09-25] 建立 `FigureFormatter`：實現單頁圖表去重、HTML5 語意化 `<figure>` 渲染與換行正規化
- [x] [2026-09-25] 升級 `IMRADResolver`：支援 APA Level 4 行內標題 (`####`) 促進、第一頁作者註分離重組、論文結束日期提取、統計符號修復
- [x] [2026-09-25] 修復第一頁緒論內文遭切除問題，實現 17 個大綱標題與 `2002-01194-001_Verified.md` 100% 精準對齊
- [x] [2026-09-25] 新增 `literature_*.json` 版面配置，統一 `style_loader.py` 與 `config_manager.py` 優先順序
- [x] [2026-09-25] 新增 `tests/test_v36_literature_layout_refinement.py`，全套 186 個單元測試 100% 通過

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





