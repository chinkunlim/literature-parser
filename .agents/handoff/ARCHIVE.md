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
