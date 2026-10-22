# 歷史交接歸檔 (Handoff Archive)

### [2026-10-21 04:12 UTC] Initial Bootstrap (by `init_project`)
- **狀態**: 專案已初始化（框架 v3.1.0）。
- **下一步**: 檢視 `.agents/project.toml`，再用 `agentctl task create` 建立第一個任務。

### [2026-10-21 04:12 UTC] 建立任務 `TASK-001`: 遷移批次 1：依賴與設定檔轉換（uv / pnpm / .env.example / Brewfile） (by `system`)
- **狀態**: `open`
- **相關範圍**: `legacy, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-002`: 遷移批次 2：config 層（設定、環境變數讀取） (by `system`)
- **狀態**: `open`
- **相關範圍**: `src/literature_parser/config/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-003`: 遷移批次 3：domain 層（資料模型、純邏輯） (by `system`)
- **狀態**: `open`
- **相關範圍**: `src/literature_parser/domain/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-004`: 遷移批次 4：adapters 層（外部 API、資料庫、檔案 I/O） (by `system`)
- **狀態**: `open`
- **相關範圍**: `src/literature_parser/adapters/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-005`: 遷移批次 5：services 層（業務流程） (by `system`)
- **狀態**: `open`
- **相關範圍**: `src/literature_parser/services/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-006`: 遷移批次 6：entrypoints 層（CLI、HTTP、排程入口） (by `system`)
- **狀態**: `open`
- **相關範圍**: `src/literature_parser/entrypoints/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-007`: 遷移批次 7：web 前端（HTML / CSS / JS） (by `system`)
- **狀態**: `open`
- **相關範圍**: `web/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-008`: 遷移批次 8：測試 (by `system`)
- **狀態**: `open`
- **相關範圍**: `tests/, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-009`: 遷移批次 9：文件（README、規格、決策、已知問題） (by `system`)
- **狀態**: `open`
- **相關範圍**: `docs/PROMPT_TEMPLATES.md, docs/adr/, docs/architecture/ARCHITECTURE.md, docs/known-issues/, docs/specs/, docs/standards/PROJECT_RULES.md, evals/EVALS.md, legacy`

### [2026-10-21 04:12 UTC] 建立任務 `TASK-010`: 遷移批次 10：其他（資料、資源、需人工判斷） (by `system`)
- **狀態**: `open`
- **相關範圍**: `docs/standards/PROJECT_RULES.md, legacy`

### [2026-10-21 16:01 UTC] 認領任務 `TASK-001` (遷移批次 1：依賴與設定檔轉換（uv / pnpm / .env.example / Brewfile）) (by `antigravity`)
- **相關範圍**: `legacy, legacy`

### [2026-10-21 16:02 UTC] 完成任務 `TASK-001` — 遷移批次 1：依賴與設定檔轉換（uv / pnpm / .env.example / Brewfile） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 依賴與設定檔轉換完成，已合併 .env.example 與 pyproject.toml 腳本設定並移除 legacy 舊設定檔

### [2026-10-21 16:02 UTC] 認領任務 `TASK-002` (遷移批次 2：config 層（設定、環境變數讀取）) (by `antigravity`)
- **相關範圍**: `src/literature_parser/config/, legacy`

### [2026-10-21 16:03 UTC] 完成任務 `TASK-002` — 遷移批次 2：config 層（設定、環境變數讀取） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: config 層遷移完成，processor_config.py 與 config_manager.py 正確載入資源，0 critical issues

### [2026-10-21 16:03 UTC] 認領任務 `TASK-003` (遷移批次 3：domain 層（資料模型、純邏輯）) (by `antigravity`)
- **相關範圍**: `src/literature_parser/domain/, legacy`

### [2026-10-21 16:03 UTC] 完成任務 `TASK-003` — 遷移批次 3：domain 層（資料模型、純邏輯） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: domain 層遷移完成，model_advisor.py 搬遷與型別註解通過，0 critical issues

### [2026-10-21 16:03 UTC] 認領任務 `TASK-007` (遷移批次 7：web 前端（HTML / CSS / JS）) (by `antigravity`)
- **相關範圍**: `web/, legacy`

### [2026-10-21 16:04 UTC] 完成任務 `TASK-007` — 遷移批次 7：web 前端（HTML / CSS / JS） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: web 前端遷移完成，dashboard.html 搬遷並加上用途註解，0 critical issues

### [2026-10-21 16:05 UTC] 認領任務 `TASK-008` (遷移批次 8：測試) (by `antigravity`)
- **相關範圍**: `tests/, legacy`

### [2026-10-21 16:05 UTC] 完成任務 `TASK-008` — 遷移批次 8：測試 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 測試層遷移完成，29 個測試檔案完成 import 重寫，240 個測試通過，0 critical issues

### [2026-10-21 16:05 UTC] 認領任務 `TASK-010` (遷移批次 10：其他（資料、資源、需人工判斷）) (by `antigravity`)
- **相關範圍**: `docs/standards/PROJECT_RULES.md, legacy`

### [2026-10-21 16:07 UTC] 完成任務 `TASK-010` — 遷移批次 10：其他（資料、資源、需人工判斷） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 其他批次資源遷移完成，JSON 規範檔、LICENSE、資料隔離與環境變數對照全數完成

### [2026-10-21 16:07 UTC] 認領任務 `TASK-004` (遷移批次 4：adapters 層（外部 API、資料庫、檔案 I/O）) (by `antigravity`)
- **相關範圍**: `src/literature_parser/adapters/, legacy`

### [2026-10-21 16:07 UTC] 完成任務 `TASK-004` — 遷移批次 4：adapters 層（外部 API、資料庫、檔案 I/O） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: adapters 層遷移完成，8 個適配器模組通過靜態檢查與單元測試，0 critical issues

### [2026-10-21 16:07 UTC] 認領任務 `TASK-005` (遷移批次 5：services 層（業務流程）) (by `antigravity`)
- **相關範圍**: `src/literature_parser/services/, legacy`

### [2026-10-21 16:08 UTC] 完成任務 `TASK-005` — 遷移批次 5：services 層（業務流程） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: services 層遷移完成，70 個模組全數通過單元測試與程式碼審查，0 critical issues

### [2026-10-21 16:08 UTC] 認領任務 `TASK-006` (遷移批次 6：entrypoints 層（CLI、HTTP、排程入口）) (by `antigravity`)
- **相關範圍**: `src/literature_parser/entrypoints/, legacy`

### [2026-10-21 16:09 UTC] 完成任務 `TASK-006` — 遷移批次 6：entrypoints 層（CLI、HTTP、排程入口） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: entrypoints 層遷移完成，run.py, doc_cli.py 與 project_cli 系列功能完備且通過 CLI 測試，0 critical issues

### [2026-10-21 16:09 UTC] 認領任務 `TASK-009` (遷移批次 9：文件（README、規格、決策、已知問題）) (by `antigravity`)
- **相關範圍**: `docs/PROMPT_TEMPLATES.md, docs/adr/, docs/architecture/ARCHITECTURE.md, docs/known-issues/, docs/specs/, docs/standards/PROJECT_RULES.md, evals/EVALS.md, legacy`

### [2026-10-21 16:12 UTC] 完成任務 `TASK-009` — 遷移批次 9：文件（README、規格、決策、已知問題） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 文件批次遷移完成，README、ARCHITECTURE、ADR、Known Issues、PROJECT_RULES、SPECS 與歷史對話已全數轉換至標準路徑

### [2026-10-21 17:46 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 驗證所有專案工作流正常運作，清理 repo 內產生的暫存，並確認 240 測試與門禁 100% 通過
- **錯誤與根因**: 1. poppler/pdfinfo 缺失導致頁數解析失敗 → 增加純 Python PDF Page Count 正則 Fallback; 2. image_manager.extract_pdf_images 缺失 pdfimages 時崩潰 → 增加 FileNotFoundError 捕獲與優雅降級; 3. a
- **下一步**: 所有 16 個 CLI 工作流與 240 項單元測試皆已實測通過，後續可依需求串接 FastAPI 或新增解析規則
- **交接備註**: 所有工作流實測完畢，純 Python fallback 與 DATA_DIR 結構健全
- **本機對話紀錄**: `.agents/conversations/2026-10-22-0146-antigravity-summary.md`（只在這台電腦）

### [2026-10-21 17:48 UTC] 建立任務 `TASK-011`: 更新所有 md 檔案與專案文件 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-21 17:48 UTC] 認領任務 `TASK-011` (更新所有 md 檔案與專案文件) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-21 17:52 UTC] 完成任務 `TASK-011` — 更新所有 md 檔案與專案文件 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 全面更新並校準所有專案 Markdown 文件，包含 README、CHANGELOG、SPEC-003/004、ISSUE-003、EVALS、WEB、MIGRATION 及 PROJECT_TREE

### [2026-10-21 17:56 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 全面更新所有專案 Markdown 文件，補齊 SPEC 與 ISSUE，並同步目錄樹與依賴圖
- **錯誤與根因**: 無未解決錯誤。前期 poppler/pdfimages 缺失問題已透過 ISSUE-003 完成文檔沉澱
- **下一步**: 所有 16 個 CLI 工作流、240 項單元測試與全部 Markdown 文件皆已校對最新，後續可依需求串接 API 或擴充解析規則
- **交接備註**: 全量文件與規格更新完成，測試與門禁全部通過
- **本機對話紀錄**: `.agents/conversations/2026-10-22-0156-antigravity-summary.md`（只在這台電腦）

### [2026-10-22 01:51 UTC] 建立任務 `TASK-012`: 輸入目錄結構分流與資料夾連字號命名規範 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 01:51 UTC] 認領任務 `TASK-012` (輸入目錄結構分流與資料夾連字號命名規範) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 01:59 UTC] 完成任務 `TASK-012` — 輸入目錄結構分流與資料夾連字號命名規範 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 完成輸入目錄分流結構（books/digital-pdf/ 與 scanned-pdf/、literature/）與輸出資料夾連字號命名規範

### [2026-10-22 02:20 UTC] 建立任務 `TASK-013`: 統一 profile.json 規格、出版社階層繼承與強型別 Schema (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 02:20 UTC] 認領任務 `TASK-013` (統一 profile.json 規格、出版社階層繼承與強型別 Schema) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 02:29 UTC] 完成任務 `TASK-013` — 統一 profile.json 規格、出版社階層繼承與強型別 Schema (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Unified profile.json schema with DocumentProfile domain model, publisher-first hierarchical inheritance, closed-loop geometry healing, and full backward compatibility.

### [2026-10-22 02:53 UTC] 建立任務 `TASK-014`: Front Matter 獨立切分、全章節 Markdown 轉換與排版細節知識庫 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 02:53 UTC] 認領任務 `TASK-014` (Front Matter 獨立切分、全章節 Markdown 轉換與排版細節知識庫) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 03:01 UTC] 完成任務 `TASK-014` — Front Matter 獨立切分、全章節 Markdown 轉換與排版細節知識庫 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Implemented Front Matter independent PDF splitting, pure Chapter 1 validation, shared knowledge taxonomies (front matter and pedagogical blocks), odd-even asymmetric layout schema, and full sequential Markdown conversion.

### [2026-10-22 03:03 UTC] 建立任務 `TASK-015`: 更新全專案 Markdown 文件：架構、規格、變更日誌與使用說明 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 03:03 UTC] 認領任務 `TASK-015` (更新全專案 Markdown 文件：架構、規格、變更日誌與使用說明) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 03:06 UTC] 完成任務 `TASK-015` — 更新全專案 Markdown 文件：架構、規格、變更日誌與使用說明 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Synchronized all project markdown documentation: README.md, PROJECT_RULES.md, SPECS.md, SPEC-001, SPEC-005, DECISIONS.md, ADR-004, KNOWN_ISSUES.md, ISSUE-004, CHANGELOG.md, and synchronized agent entrypoints.

### [2026-10-22 03:07 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 規劃並實作 Front Matter 獨立切分、純淨 Chapter 1 起始頁校驗、四層級 Profile 與共享知識庫架構，並同步更新全專案 Markdown 文件
- **錯誤與根因**: 第一章書籤起始頁若誤包前言，透過 Pre-flight Profile 的純淨 Chapter 1 校驗自動修正（ISSUE-004）。259 個單元測試全數通過。
- **下一步**: 四層 Profile 與 Front Matter 切分已就緒且文件完備；下一步可接續實測真實大部頭教科書或擴充外部 API / 批次轉檔作業。
- **交接備註**: Front Matter 獨立切分與純淨 Chapter 1 規格及四層 Profile 已全部落地並完成文件同步。
- **本機對話紀錄**: `.agents/conversations/2026-10-22-1107-antigravity-summary.md`（只在這台電腦）

### [2026-10-22 03:36 UTC] 建立任務 `TASK-016`: 實作獨立 MarkdownConversionService 與圖表裁切/CSS 輸出模組 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 03:36 UTC] 認領任務 `TASK-016` (實作獨立 MarkdownConversionService 與圖表裁切/CSS 輸出模組) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 03:44 UTC] 完成任務 `TASK-016` — 實作獨立 MarkdownConversionService 與圖表裁切/CSS 輸出模組 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 實作獨立 MarkdownConversionService、CSS 雙出、Figure/Table 獨立裁切（含 Caption/Notes/等寬 16pt Margin）與 Orchestrator/Pipeline 整合

### [2026-10-22 03:50 UTC] 建立任務 `TASK-017`: 實作三層 Markdown 轉檔檢驗與品質評估體系（排版、詞語、語意） (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 03:50 UTC] 認領任務 `TASK-017` (實作三層 Markdown 轉檔檢驗與品質評估體系（排版、詞語、語意）) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 03:53 UTC] 完成任務 `TASK-017` — 實作三層 Markdown 轉檔檢驗與品質評估體系（排版、詞語、語意） (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 實作三層 Markdown 轉檔檢驗與品質評估體系（排版、詞語、語意）、評分引擎與獨立 CLI 整合

### [2026-10-22 03:55 UTC] 建立任務 `TASK-018`: 更新並同步全專案 Markdown 文件 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 03:55 UTC] 認領任務 `TASK-018` (更新並同步全專案 Markdown 文件) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 03:58 UTC] 完成任務 `TASK-018` — 更新並同步全專案 Markdown 文件 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 更新並同步全專案 Markdown 文件（README, ARCHITECTURE, SPECS, ADR, PROJECT_RULES, CHANGELOG）

### [2026-10-22 03:59 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 實作獨立 MarkdownConversionService、CSS 雙出、圖表獨立裁切（含 Caption/Notes/等寬 16pt Margin）、三層漸進檢驗體系（排版/詞語/語意）與全專案 Markdown 同步
- **錯誤與根因**: 統計檢定數字間空格導致正規化漏配（F ( 2 , 4 0 )）➔ 允許 \d\s+ 數字內空白並於替換時去空格；單一引註遺失門檻過高 ➔ 移除 len > 2 限制只要有未比對引註即發出警告
- **下一步**: 核心轉換與三層檢驗已全部就緒（270 測試通過）；下一步可接續實測大型教科書批次轉檔，或對接本地 AI / Web 視覺化看板
- **交接備註**: 獨立轉換引擎、CSS 雙出、圖表裁切與三層檢驗體系已完整落地，全專案文檔與規格已 100% 同步
- **本機對話紀錄**: `.agents/conversations/2026-10-22-1159-antigravity-summary.md`（只在這台電腦）

### [2026-10-22 07:35 UTC] 建立任務 `TASK-019`: Optimize literature and textbook pipeline for speed and quality (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 07:35 UTC] 認領任務 `TASK-019` (Optimize literature and textbook pipeline for speed and quality) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 07:45 UTC] 完成任務 `TASK-019` — Optimize literature and textbook pipeline for speed and quality (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: (無)

### [2026-10-22 08:09 UTC] 建立任務 `TASK-020`: Implement Marker-style layout framing, paragraph boundary anchoring, and typography colors (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 08:09 UTC] 認領任務 `TASK-020` (Implement Marker-style layout framing, paragraph boundary anchoring, and typography colors) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 08:18 UTC] 完成任務 `TASK-020` — Implement Marker-style layout framing, paragraph boundary anchoring, and typography colors (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Implemented Marker-style layout framing, paragraph boundary anchoring, complex table HTML adaptation, collapsed TOC by default, and Google Fonts with 60-30-10 palette.

### [2026-10-22 08:31 UTC] 建立任務 `TASK-021`: Externalize typography, palette, TOC, layout rules, and quality thresholds into unified config (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 08:31 UTC] 認領任務 `TASK-021` (Externalize typography, palette, TOC, layout rules, and quality thresholds into unified config) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 08:36 UTC] 完成任務 `TASK-021` — Externalize typography, palette, TOC, layout rules, and quality thresholds into unified config (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Externalized typography, palette, layout, TOC, artifacts, tables, learning blocks, navigation, and quality thresholds into config/theme.json with schema and instant re-theme CLI script.

### [2026-10-22 08:37 UTC] 建立任務 `TASK-022`: Update all project documentation and architecture records (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 08:37 UTC] 認領任務 `TASK-022` (Update all project documentation and architecture records) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 08:39 UTC] 完成任務 `TASK-022` — Update all project documentation and architecture records (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Updated and synchronized all project documentation including README.md, ARCHITECTURE.md, DECISIONS.md, ADR-007, and CHANGELOG.md.

### [2026-10-22 08:40 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 全專案流程優化：原生 PyMuPDF 解析、流水線並行、Marker 式版面輪廓與段落首提錨定、8大分區集中外部化設定檔 (config/theme.json)、即時重刷 CLI 與全專案 Markdown 同步更新
- **錯誤與根因**: 表格提取 Regex 容易誤匹配 table class 中的 class 羅馬數字 -> 改用反向否定預查；未引用圖表不應在段落掃描前被提前 flush -> 建立 cited_fig_ids 全文預檢集合確保標題與正文順序正確
- **下一步**: 接續實測大型數位教科書或期刊論文批次轉檔，檢驗新版樣式與即時重刷工具，或對接本地 Web 視覺化看板
- **交接備註**: 全套 297 項測試 100% 通過，排版規則已集中至 config/theme.json，支援一鍵重刷
- **本機對話紀錄**: `.agents/conversations/2026-10-22-1640-antigravity-summary.md`（只在這台電腦）

### [2026-10-22 08:48 UTC] 建立任務 `TASK-023`: 整理 DATA_DIR 之 input 與 output 目錄結構 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 08:48 UTC] 認領任務 `TASK-023` (整理 DATA_DIR 之 input 與 output 目錄結構) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 08:53 UTC] 完成任務 `TASK-023` — 整理 DATA_DIR 之 input 與 output 目錄結構 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 完成 DATA_DIR 之 input 與 output 目錄結構重組（建立 books/literature 之 digital-pdf 與 scanned-pdf 子目錄，全面以連字號 - 重新命名 output 資料夾與文件）

### [2026-10-22 08:54 UTC] 建立任務 `TASK-024`: 更新專案所有 Markdown 文件以反映最新目錄結構與架構規範 (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 08:54 UTC] 認領任務 `TASK-024` (更新專案所有 Markdown 文件以反映最新目錄結構與架構規範) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 08:58 UTC] 完成任務 `TASK-024` — 更新專案所有 Markdown 文件以反映最新目錄結構與架構規範 (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: 更新專案所有 Markdown 文件（README、PROJECT_RULES、ARCHITECTURE、SPECS、EVALS、CHANGELOG、DECISIONS、KNOWN_ISSUES），新增 ADR-008 與 ISSUE-005

### [2026-10-22 08:58 UTC] Session Closeout (結束對話收尾) (by `antigravity`)
- **檢查結果**: 測試與 Code Review Guard 通過
- **目標**: 整理 DATA_DIR 之 input 與 output 目錄結構，修正全域狀態路徑誤判 bug，並更新全專案 Markdown 文件
- **錯誤與根因**: GlobalStateManager 在 sync_from_output_dir 時使用 'literature' in str(status_json) 比對，因專案路徑含 literature-parser 導致所有書籍被誤歸類為論文 -> 根本原因為字串包含判斷過寬 -> 改為 status_json.rela
- **下一步**: 接續實測大型數位教科書或期刊論文批次轉檔，檢驗新版輸入路由與連字號目錄命名
- **交接備註**: DATA_DIR 目錄重整完成，297 項測試全數通過，ADR-008 與 ISSUE-005 已收錄
- **本機對話紀錄**: `.agents/conversations/2026-10-22-1658-antigravity-summary.md`（只在這台電腦）

### [2026-10-22 09:05 UTC] 建立任務 `TASK-025`: Test split and profile pipeline for Research Methods 13th ed (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 09:05 UTC] 認領任務 `TASK-025` (Test split and profile pipeline for Research Methods 13th ed) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 09:19 UTC] 完成任務 `TASK-025` — Test split and profile pipeline for Research Methods 13th ed (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Completed split and profile pipeline integration test with uv and PyMuPDF optimizations

### [2026-10-22 09:22 UTC] 建立任務 `TASK-026`: Test split and profile pipeline for Group Counseling scanned book (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`

### [2026-10-22 09:22 UTC] 認領任務 `TASK-026` (Test split and profile pipeline for Group Counseling scanned book) (by `antigravity`)
- **相關範圍**: `-`
- **接棒自**: `antigravity`

### [2026-10-22 09:24 UTC] 完成任務 `TASK-026` — Test split and profile pipeline for Group Counseling scanned book (by `antigravity`)
- **狀態**: ✅ 已完成 (`done`)
- **完成摘要**: Verified split and profile pipeline on Group Counseling scanned book without outline (22 sections, 500 pages in 0.34s)

### [2026-10-22 09:27 UTC] 建立任務 `TASK-027`: Test Markdown export on a chapter of Research Methods 13th ed (by `antigravity`)
- **狀態**: `in_progress`
- **相關範圍**: `-`
