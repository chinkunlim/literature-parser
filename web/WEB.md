# Web 前端與視覺化 Studio (Literature Parser Web Studio)

純 HTML5 + CSS + JavaScript 單頁應用（SPA），不需要外部建置工具（免 npm / vite 打包）。
符合 Anthropic Frontend Design、Vercel Web Design Guidelines 與 Taste Skill Anti-Slop 規範（UI Taste Score: 100/100）。
檔案開頭皆具備規範之用途說明與 JSDoc 註解（`agentctl check` 校驗通過，單檔均 <= 420 行）。

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
   - 支援「進入對比校對」快速跳轉。

2. **🔍 PDF vs EPUB 雙欄對比與即時編輯 (Compare & Edit)**：
   - **左側 PDF 檢視器**：連續垂直滾動饋送 (Continuous Scroll Feed)，支援頁面圖片 IntersectionObserver 懶加載、頁碼直接跳轉輸入框 (`第 [ N ] / Total 頁`)、縮放控制 (`適寬`, `🔍+`, `🔍-`, `↺`)。
   - **中線拖曳調節器**：支援滑鼠拖動調整左右分欄比例 (20% ~ 80%)，支援 `[ 📄 僅 PDF ]` `[ ⚖️ 雙欄 ]` `[ ✏️ 僅編輯 ]` 佈局切換。
   - **雙向同步捲動**：PDF 滾動自動對齊 EPUB 錨點；EPUB 預覽滾動亦自動帶動 PDF 頁碼，支援一鍵開關切換 (`🔗 同步中` / `🔓 獨立滾動`)。
   - **右側排版預覽與編輯器**：
     - `👁️ 即時排版預覽`：暖紙白 (`#FAF8F5`) 出版級渲染，支援 Markdown 表格 (`<table class="epub-table">`)、引述框 (`<blockquote class="epub-blockquote">`)、程式碼區塊、有序/無序清單、頁面分隔錨點標籤。
     - `✏️ Markdown 編輯器`：等寬字體 (`JetBrains Mono`)、即時字數統計、Tab 鍵 2 空格縮排支援、一鍵複製 Markdown 按鈕。
   - **品質瑕疵審查器 (Audit Inspector)**：呈現該章節品質得分、缺陷清單與「定位 ➔」一鍵滾動並高亮問題段落。
   - **問題反饋與重編譯**：點擊「💾 儲存並反饋 (Cmd+S)」，自動計算 Unified Diff 寫入 `DATA_DIR/db/corrections.json` 並在背景觸發 EPUB 3 重新編譯。

3. **側邊欄導航與快速篩選**：
   - 支援 `[ ☰ ]` 一鍵折疊側邊欄（視窗 < 900px 時預設自動收折，狀態由 `localStorage` 持久化記憶）。
   - 提供「🔍 快速篩選章節」即時過濾輸入框，解決多章節教科書翻找不易之痛點。

4. **⌨️ 全域鍵盤快捷鍵體系**：
   - 點擊頂部 `[ ⌨️ 快捷鍵 ]` 或按下 `?` 鍵即可隨時開啟快捷鍵指南視窗：
     - `Cmd + S` / `Ctrl + S`：儲存章節修改並記錄問題反饋
     - `[` / `]`：切換上一章節 / 下一章節
     - `1` / `2` / `3`：切換佈局 (僅 PDF / 雙欄對比 / 僅編輯)
     - `Cmd + 0`：重設 PDF 視角與頁面寬度
     - `+` / `-`：放大 / 縮小 PDF 頁面寬度
     - `?`：開啟 / 關閉快捷鍵視窗
     - `Esc`：關閉任何開啟的彈出對話框

5. **🖼️ 頁對頁視覺圖像對照 (Visual Diff Inspector)**：
   - 瀏覽由 `EpubVisualAuditor` 自動生成的 PDF 原頁與 EPUB 渲染截圖並列樣本 (`visual_diff_samples/`)。

6. **🛠️ 人工修正與反饋資料庫 (Correction Feedback Library)**：
   - 集中檢視所有在 Web Studio 紀錄的人工校驗與修改歷史。
   - 支援「⚡ 生成自動化回歸測試」，一鍵將累積問題轉化為 `tests/test_user_corrections_regression.py`。

## 3. 前端架構與模組劃分

- `web/index.html`：語意化 HTML5 單頁結構，無障礙標籤與模態框。
- `web/styles.css`：設計系統 Tokens、暖紙白調色盤、響應式斷點、Reduced Motion 降級。
- `web/markdown.js`：純前端高效 Markdown 轉 HTML 語意解析器（支援表格、引述、錨點）。
- `web/panzoom.js`：PDF 連續饋送、雙向同步滾動控制器、分欄拖動與側邊欄折疊。
- `web/audit.js`：章節品質得分徽章、缺陷清單與段落高亮定位。
- `web/corrections.js`：問題修正對話框、Diff 比對、反饋列表管理與測試生成。
- `web/app.js`：主應用狀態機、視圖切換、章節過濾、鍵盤快捷鍵調度。

## 4. API 與 MCP 三入口串接

- **RESTful API**：詳見 `http://127.0.0.1:8767/docs`（Swagger UI OpenAPI 規格）。
- **MCP 工具**：提供給 AI Agent（Claude Code、Antigravity、OpenCode、Open WebUI）之 MCP 工具定義於 `src/literature_parser/entrypoints/mcp_server.py`。
