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
