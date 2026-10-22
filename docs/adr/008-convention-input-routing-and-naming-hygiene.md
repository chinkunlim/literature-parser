# ADR-008：輸入目錄約定分流路由與產出目錄連字號命名衛生規範

- **狀態**：Accepted
- **日期**：2026-10-22
- **Agent**：`antigravity`
- **任務**：`TASK-012`, `TASK-023`

## 1. 背景與問題

文檔解析管線在初期主要仰賴「啟發式探測（Heuristic Detection）」：
1. 輸入 PDF 時透過抽樣頁面之文字長度或呼叫 `pdfimages` 抽樣探測是否為掃描版（Scanned PDF）。然而，部分出版商製作之 PDF 含有隱形透明 OCR 文字層或少量首頁向量文字，導致慢速掃描版誤走數位向量管線（產生大量殘破亂碼），或數位原生版被誤判為掃描版而浪費大量算力呼叫神經 OCR。
2. 產出目錄與章節路徑直接採用原始書名或檔案名，帶有大量空格、底線 `_`、逗號與特殊符號（例如 `Research Methods, Design, and Analysis 13th ed`），在跨平台（macOS、Linux、Windows）、URL 鏈結、Obsidian 圖譜引用與 Docker 容器掛載時容易產生編碼逸出與轉義瑕疵。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| A. 全自動啟發式內容探測 | 使用者無需關心檔案存放資料夾 | 抽樣探測耗時，透明文字層或圖文混排容易誤判；輸出路徑混亂 |
| B. CLI 強制參數指定（`--scanned` / `--digital`） | 精準控制單次轉換行為 | 批次處理整個目錄或 Watchdog 監控自動觸發時無法自動化 |
| C. (Selected) **約定優於配置（Convention over Configuration）分流 ＋ 產出全面連字號 `-` 衛生** | 1. `input/books/digital-pdf/` 與 `scanned-pdf/` 物理路徑即為最高優先級設定，確定性 100%<br>2. 產出目錄全面使用 `sanitize_filename` 將底線、空格與特殊符號統一為連字號 `-`<br>3. 仍保留根目錄自動抽樣探測作為透明向下相容備援 | 需要維護標準的 `DATA_DIR` 子目錄結構 |

## 3. 決策與理由

採納 **方案 C**：
1. **輸入端約定路由**：
   - `DATA_DIR/input/books/digital-pdf/`：直接標定為數位教科書，強制執行原生向量提取，禁用神經視覺 OCR。
   - `DATA_DIR/input/books/scanned-pdf/`：直接標定為掃描版教科書，直接調用 Apple Vision Framework 神經 OCR 識別。
   - `DATA_DIR/input/literature/digital-pdf/` 與 `scanned-pdf/`：學術文獻分流（預設走雙欄中縫重組與 IMRAD 管線）。
   - 保留未分流檔案時的抽樣自動探測作為相容備援。
2. **輸出端連字號衛生**：
   - 產出書籍與論文資料夾一律禁用底線 `_` 與空格，統一透過 `sanitize_filename()` 轉換為連字號 `-`（例如 `output/books/Research-Methods-Design-and-Analysis-13th-ed/`）。
   - 章節目錄與檔案統一遵循 `Ch01-Title`、`Appendix-A-Title` 格式。

## 4. 影響與代價

- **正面影響**：
  - 徹底消除了輸入端因檔案透明 OCR 層而產生的誤判與算力浪費。
  - 輸出資料夾在終端機操作、腳本處理、網頁服務與 Obsidian 雙鏈導航中呈現高度一致性與跨平台相容性。
- **代價與後續維護**：
  - 既有 `DATA_DIR` 需執行一次性目錄結構重組遷移（由 `TASK-023` 完成）。
  - 全域狀態管理器 `GlobalStateManager` 需配合同步路徑鍵值。
