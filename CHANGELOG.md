# Changelog

All notable changes to **literature-parser** are documented here
(format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions: [SemVer](https://semver.org/)).

## [Unreleased]

### Added
- docs(adr): record ADR-008 on convention-based input routing and hyphen-delimited naming hygiene (TASK-023) (by `@antigravity`)
- docs(known-issues): record ISSUE-005 on global state path substring matching causing doc_type misattribution (TASK-023) (by `@antigravity`)
- docs(adr): record ADR-007 on unified theme and pipeline configuration (TASK-021) (by `@antigravity`)
- docs(specs): add SPEC-007 on theme, typography, and pipeline configuration (TASK-021) (by `@antigravity`)
- docs(adr): record ADR-006 on PyMuPDF dual-engine parsing and pipelined CPU-GPU concurrency (TASK-019) (by `@antigravity`)
- docs(adr): record ADR-005 on modular conversion service, dual CSS, and three-tier quality verification (by `@antigravity`)
- docs(specs): add SPEC-006 on independent MarkdownConversionService and quality verification system (by `@antigravity`)
- docs(adr): record ADR-004 on hierarchical profile inheritance, front matter isolation, and pure chapter 1 (by `@antigravity`)
- docs(specs): add SPEC-005 on unified DocumentProfile schema, shared knowledge taxonomies, and front matter classification (by `@antigravity`)
- docs(known-issues): document ISSUE-004 on Chapter 1 bookmark misattribution on page 1 and front matter pollution (by `@antigravity`)
- docs(specs): add SPEC-003 (EPUB 3 Exporter) and SPEC-004 (Fix Playbook & Recipe Synthesizer) specifications (by `@antigravity`)
- docs(known-issues): document ISSUE-003 on external PDF tools fallback and graceful degradation (by `@antigravity`)
- feat(pipeline): implement convention-based input segregation and hyphen-delimited naming (TASK-012) (by `@antigravity`)
- feat(profiler): implement DocumentProfile schema, publisher-first inheritance, and unified profile.json (TASK-013) (by `@antigravity`)
- feat(profiler): implement front matter splitting, pure chapter 1, and layout taxonomy (TASK-014) (by `@antigravity`)
- feat(shared-knowledge): add front_matter_taxonomy.json and pedagogical_blocks.json repositories (by `@antigravity`)
- feat: implement modular MarkdownConversionService, CSS dual output, and figure/table cropping with equal margins (TASK-016) (by `@antigravity`)
- feat: implement three-tier quality verification system across layout, lexical, and semantic dimensions (TASK-017) (by `@antigravity`)
- feat: optimize pipeline with native PyMuPDF engine, pipelined concurrency, and math/layout quality enhancements (TASK-019) (by `@antigravity`)
- feat: implement Marker-style layout framing, paragraph boundary anchoring, and typography colors (TASK-020) (by `@antigravity`)
- feat: externalize typography, palette, layout rules, and quality thresholds into unified config/theme.json (TASK-021) (by `@antigravity`)
- feat(analyzer): add PyMuPDF memory fallback for outline-free scanned books and generalize test runner (TASK-026) (by `@antigravity`)
- feat(converter): optimize image extraction fallback for vector chapters and verify Ch01 Markdown export (TASK-027) (by `@antigravity`)
- feat(orchestrator): support comma-separated chapter filtering and fix outline hierarchy tree (TASK-029) (by `@antigravity`)
- feat(verifier): integrate MiniCPM-V visual audit, PyMuPDF page rendering, and numerical-invariance surgical table healing (TASK-033) (by `@antigravity`)
- feat(profiler): persist chapter audits and visual defects into book profile, and enhance Cengage cross-book filters (TASK-034) (by `@antigravity`)

### Changed
- docs(migration): mark all migration acceptance criteria as completed (by `@antigravity`)
- docs(evals,web,readme): update eval commands, dashboard guide, CLI command references, and offline test instructions (by `@antigravity`)
- refactor(migration): complete legacy codebase migration to structured layout (by `@antigravity`)
- refactor(data): reorganize DATA_DIR input and output directory structures with convention routing and hyphen hygiene (by `@antigravity`)

### Fixed
- fix(config): standardize DATA_DIR hierarchy and route all data paths through AppConfig (by `@antigravity`)
- fix(verification): refine layout auditor TOC scope and adapt cli_audit for book chapters (TASK-028) (by `@antigravity`)
- fix(parser): eliminate runaway blockquotes, isolate H4 headings, suppress duplicate table images, and enhance Ollama multi-window verification (TASK-030) (by `@antigravity`)
- fix(parser): resolve cross-column baseline fragment split, multiline LO continuations, duplicate chapter slug heading, and study questions callout list spacing (TASK-031) (by `@antigravity`)
- fix(parser): resolve exhibit column splits, table 15.4 grid row capture, margin glossary baseline clustering, and currency escaping (TASK-032) (by `@antigravity`)
- fix(engine): unify PDF engine to PyMuPDF, strip style in verifier, and repair cross-page bold stitching (TASK-036) (by `@antigravity`)
- fix(layout): define left_b bounds in fallback branch of vector figure parser (TASK-037) (by `@antigravity`)
- fix(parser): resolve bullet e-truncation, 573x716 watermark, and TOC banner false-positive (TASK-038) (by `@antigravity`)
- fix(parser): unwrap single-root outline, exempt ANOVA matrices, and clean decorative noise (TASK-039) (by `@antigravity`)
- fix(verifier): exempt back-matter heading density, skip blockquotes in sentence checks, and fix running footer dead code (TASK-039) (by `@antigravity`)

### Documentation
- docs: update and synchronize all project markdown documentation (by `@antigravity`)
- docs: synchronize all project markdown documentation (TASK-015) (by `@antigravity`)
- docs: synchronize all project markdown documentation for conversion and verification systems (TASK-018) (by `@antigravity`)
- docs: update and synchronize all project markdown documentation, ADR-007, and architecture (TASK-022) (by `@antigravity`)
- docs: synchronize all project markdown documentation for input/output convention routing, ADR-008, and ISSUE-005 (by `@antigravity`)

### Testing
- test(workflows): verify all CLI workflows, fix pathing and pure-python fallbacks (by `@antigravity`)
- test: add split and profile integration test with PyMuPDF in-memory optimization for Research Methods 13th ed (TASK-025) (by `@antigravity`)
- test: run batch audit runner across all input books without code change (TASK-035) (by `@antigravity`)

### Chore
- chore(project): update project tooling and config (TASK-001, TASK-009, TASK-010, TASK-011) (by `@antigravity`)

## [0.1.0] - 2026-10-21
### Added
- Initial project scaffold (framework v3.1.0).

## [3.2.0] - 2026-10-08

### 🌟 架構對齊與合規審計 (Structure Alignment & Compliance)
- **全面對齊 `02_PROJECT_ALIGN_CHECK_GUIDE.md` 標準架構**：
  - 根目錄導入自動化合規審計工具 `audit_project.py`，並於 `Makefile` 新增 `audit` 門禁指令。
  - 完成歷史對話全量回溯、脫敏切分與雙軌摘要補齊（`conversations/raw/` 與 `conversations/summaries/` 涵蓋 001~009，100% 脫敏存證）。
  - 全面豐富治理與技術文檔實質內容：`docs/CONTEXT.md`、`docs/DEPLOYMENT.md`、`docs/PROMPT_TEMPLATES.md`、`docs/TOOLS.md`、`evals/README.md`、`.github/CONTRIBUTING.md` 與 `.github/SECURITY.md`。
  - 憲法與引導文件參照收斂：全面替換歷史 `docs/STRUCTURE.md` 與 `OPERATIONS.md` 引用為 `docs/ARCHITECTURE.md` 與 `WORKFLOW_GUIDE.md`。
  - 修正腳手架命令 `run.py init-project` 之生成模板，確保新開案直接符合最新標準。

---

## [3.1.0] - 2026-09-24

### 🌟 新增 (Added)
- **Springer 與 IEEE 出版商版面範本 (`config/publishers/springer.json`, `ieee.json`)**：
  - 補齊 DOI 識別（`10.1007`, `10.1109`）、雙欄屬性標記、頁眉/頁尾浮水印與授權雜訊過濾規則。
- **目錄級批次轉檔 CLI 指令 (`run.py batch <dir>`)**：
  - 一鍵遞迴探索目錄內所有 PDF/EPUB 檔案，逐檔執行硬體守衛巡檢（RAM/SSD/電池）與冷卻防護。
- **Obsidian 雙鏈與全書索引生成器 (`obsidian_linker.py` + `run.py obsidian-link`)**：
  - 自動生成全書目錄索引 `index.md`，並在章節尾部注入前後篇導航雙鏈，原生適配 Obsidian Graph View 知識圖譜。
- **全域進度狀態中心化管理器 (`GlobalStateManager` + `run.py status`)**：
  - 原子化維護 `data/state/global_status.json`，提供終端機進度條視覺化儀表，支援單篇原子文獻與多章節書籍。
- **`LiteraturePipeline` 學術文獻領域深度客製化**：
  - 實作子類型自動偵測（journal、ieee、dissertation、preprint）。
  - 自動剔除 IEEE 論文結尾的作者簡介（Author Biography）與授權宣告雜訊。
  - 將 IEEE/ACM Index Terms 標題重構為現代化 Obsidian 呼號標籤區塊，並為預印本自動標註警告提示。
- **靜態零依賴 HTML 視覺化儀表板 (`dashboard/index.html` + `run.py dashboard`)**：
  - 生成現代暗色主題 HTML 看板，即時匯總所有文獻與書籍完成度、驗證率與審查狀態，自動調用瀏覽器檢視。
- **自動化測試體系擴充至 179 項**：
  - 新增 `test_v33_obsidian_linker.py`、`test_v34_global_state.py`、`test_v35_literature_pipeline.py`，全量測試 100% 通過。

### 🐞 修復 (Fixed)
- **修復 `ScannedPDFParser` 內部方法名稱呼叫不匹配**：
  - 修復 `AttributeError: type object 'ScannedPDFParser' has no attribute 'process_scanned_page'`，補齊向後相容別名並修正呼叫端，徹底打通掃描版書籍神經 OCR 管線。
- **修復全域進度統計對單篇學術文獻的映射支援**：
  - 讓 `GlobalStateManager` 在輸出目錄自動掃描時，能正確將單篇原子論文映射為 100% 完工指標。

### 📦 實體交付 (Deliverables)
- 3 篇學術文獻（APA、Elsevier 雙欄）全量重新輸出完工。
- 4 本電子書（包含 30MB 與 55MB 掃描版教科書）全數完成 OCR 轉換並注入 Obsidian 雙鏈與索引。

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
