# Web 前端與視覺化 Studio (Literature Parser Web Studio)

純 HTML5 + CSS + JavaScript 單頁應用（SPA），不需要外部建置工具（免 npm / vite 打包）。
檔案開頭皆具備規範之用途說明與 JSDoc 註解（`agentctl check` 校驗通過）。

## 1. 互動式 Web Studio 啟動方式

執行專案標準 CLI 命令一鍵啟動 FastAPI 後端與 SPA 介面：
```bash
uv run literature-parser web
```
或指定自訂埠號並禁止自動開啟瀏覽器：
```bash
uv run literature-parser web --port 8767 --no-open
```
本機瀏覽器訪問：`http://127.0.0.1:8767`（嚴禁使用 `0.0.0.0` 或直接打外網 IP）。

## 2. 功能架構與視圖說明

1. **📊 儀表板總覽 (Dashboard)**：
   - 即時統計總處理文檔數、完工數、全域章節通過率與累積問題反饋筆數。
   - 包含書籍卡片列表、進度條、狀態徽章與 EPUB 下載按鈕。
   - 支援「開啟雙欄對照」快速跳轉。

2. **🔍 PDF vs EPUB 雙欄對比與即時編輯 (Compare & Edit)**：
   - **左欄**：原書章節 PDF 檢視器，支援即時頁面渲染（PyMuPDF 高清轉譯）、翻頁控制（上一頁/下一頁）與縮放。
   - **右欄**：提供雙頁籤切換：
     - `👁️ 即時排版預覽`：呈現 EPUB 排版效果（支援 Markdown 樣式語意映射）。
     - `✏️ Markdown 編輯器`：直接編輯章節內容。
   - **問題反饋與重編譯**：點擊「💾 儲存修改並記錄問題」，彈出分類標籤選單（OCR 錯字、標題階層、表格排版、圖表遺失、頁首殘留等）與優化備註，儲存時自動計算 Unified Diff 寫入 `DATA_DIR/db/corrections.json` 並在背景觸發 EPUB 3 重新編譯。

3. **🖼️ 頁對頁視覺圖像對照 (Visual Diff Inspector)**：
   - 瀏覽由 `EpubVisualAuditor` 自動生成的 PDF 原頁與 EPUB 渲染截圖並列樣本 (`visual_diff_samples/`)。

4. **🛠️ 人工修正與反饋資料庫 (Correction Feedback Library)**：
   - 集中檢視所有在 Web Studio 紀錄的人工校驗與修改歷史。
   - 支援「⚡ 生成自動化回歸測試」，一鍵將累積問題轉化為 `tests/test_user_corrections_regression.py`，確保日後管線演算法優化時不會重蹈覆轍。

## 3. API 與 MCP 三入口串接

- **RESTful API**：詳見 `http://127.0.0.1:8767/docs`（Swagger UI OpenAPI 規格）。
- **MCP 工具**：提供給 AI Agent（Claude Code、Antigravity、OpenCode、Open WebUI）之 MCP 工具定義於 `src/literature_parser/entrypoints/mcp_server.py`。
