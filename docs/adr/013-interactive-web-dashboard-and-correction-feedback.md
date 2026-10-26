# ADR-013：Interactive Web Studio, Dual-View PDF/EPUB Comparison, and Closed-Loop Correction Feedback

- **狀態**：Accepted
- **日期**：2026-10-26
- **Agent**：`Antigravity`
- **任務**：`TASK-050`

## 1. 背景與問題

轉檔後的書籍與文獻過去僅能透過 CLI 指令 (`run.py dashboard` / `run.py verify`) 產生靜態 HTML 報告或抽樣截圖，使用者在審查時面臨以下痛點：
1. **缺乏直接的動態對比檢視**：無法在同一介面中同時比對原始章節 PDF 頁面與編譯後的 EPUB 渲染排版。
2. **修改與反饋斷層**：使用者發現錯字（OCR 瑕疵）、標題階層誤判或表格跑版時，只能手動進入終端機修改檔案，修改原因與上下文無法被系統記錄。
3. **錯誤重複發生**：人工修正沒有沉澱為測試用例或修復手冊規則，後續模型重新訓練或管線重跑時容易再次出現相同瑕疵。
4. **AI 工具協作受限**：缺乏符合 Rule 13 與 `LOCAL_AI_ENVIRONMENT.md` 的三入口架構（REST API、MCP 工具、Web UI）。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| **方案 A：純靜態 HTML 生成 + 手動 Git Commit** | 不需常駐服務與新相依性。 | 無法實現即時線上編輯、PDF 動態翻頁渲染與閉環回歸測試生成。 |
| **方案 B：重量級 Full-stack (React/Vue + Node + Docker)** | 生態豐富、元件庫多。 | 違背專案原則（禁止 Docker、禁止 npm/npx 複雜建置、耗費主機資源）。 |
| **方案 C（本決策）：FastAPI + 純前端 SPA + 結構化題庫與回歸測試生成器 (CorrectionService)** | 遵循本地離線原則（綁定 127.0.0.1:8767）；純 HTML5/JS 免建置；同一組 services 同時支援 Web UI、REST API 與 MCP 工具；自動閉環生成 unittest/pytest 回歸測試。 | 需新增 `fastapi`, `uvicorn`, `mcp` 等輕量純 Python 相依套件。 |

## 3. 決策與理由

決定採用 **方案 C**，打造完整的互動式 Review Studio：

1. **三入口統一商務層 (Services Layer)**：
   - `WebDataService`：負責書目統計、章節 Markdown 讀寫、即時 PDF 頁面渲染（PyMuPDF 高清流）與背景 EPUB 重編。
   - `CorrectionService`：負責計算 Unified Diff、標註問題 Taxonomy 標籤（`ocr_typo`, `heading_level`, `table_layout`, `missing_image`, `header_footer_leak` 等），寫入 `DATA_DIR/db/corrections.json`。
   - 自動生成回歸測試：提供 `generate_regression_tests()` 將修正資料轉化為可執行的 `tests/test_user_corrections_regression.py`。
2. **多通道入口 (Entrypoints Layer)**：
   - **Web UI** (`web/index.html`, `app.js`, `styles.css`)：現代暗色系 SPA，整合 Dashboard、雙欄 PDF/EPUB 對比編輯器、視覺差異樣本庫與問題歷史。
   - **REST API** (`src/literature_parser/entrypoints/web_app.py`)：FastAPI 路由，嚴格綁定 `127.0.0.1:8767`。
   - **MCP Server** (`src/literature_parser/entrypoints/mcp_server.py`)：提供工具供 Claude Code、Antigravity、OpenCode、Open WebUI 呼叫（寫操作具備 `confirm: bool` 防護）。
   - **CLI 整合**：新增 `uv run literature-parser web` 一鍵啟動指令。

## 4. 影響與代價

- **正面影響**：
  - 使用者能直接在瀏覽器比對 PDF 與 EPUB，並在線上編輯修正後即時背景重打包。
  - 所有問題修正皆具備結構化審計紀錄與 Diff。
  - 人工修正能一鍵沉澱為自動化單元測試，達成防回歸的演算法自愈閉環。
- **代價與後續注意**：
  - 專案相依性加入 `fastapi`, `uvicorn`, `mcp`。
  - 伺服器僅限本機 `127.0.0.1` 存取，嚴禁綁定 `0.0.0.0`。
