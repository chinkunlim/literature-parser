# ADR-012：Hierarchical publishing-grade TOC resolution with hyperlinked anchors and side-by-side visual diffing

- **狀態**：Accepted
- **日期**：2026-10-26
- **Agent**：`Antigravity`
- **任務**：`TASK-048`

## 1. 背景與問題

既有教科書轉檔流程產生的目錄（TOC）存在以下痛點：
1. **目錄結構雜亂平鋪**：將全書數十個小節平鋪為單層無序列表，遺失了出版級的 `Part / Unit -> Chapter -> Section` 巢狀分類。
2. **缺乏超連結跳轉**：書內目錄（`00-07-TOC`）與側邊欄導航（`nav.xhtml` / `toc.ncx`）未與內文章節和小節標題錨點綁定，讀者無法點擊跳轉至目標內容。
3. **缺乏客觀視覺對比依據**：雖然具備 EPUB 頁面渲染與截圖能力，但缺乏與原書 PDF 原始頁面的並排直觀比對（Side-by-Side Visual Diffing），無法直觀審查目錄、複雜表格、圖片與專欄方塊的排版保真度。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| **方案 A：純依賴 PDF 原生書籤大綱 (Outline)** | 提取快速，依賴既有 Outline 樹狀結構。 | 掃描版 PDF 或書籤混亂的教科書無法正確取得階層；無法精確對齊至轉檔產生的章節 XHTML 檔案與錨點。 |
| **方案 B：純文字 Markdown 連結替換** | 實作簡單，僅產生標準 Markdown 連結清單。 | 無法呈現出版級點線導引（dot leaders）與頁碼對齊；在 EPUB 側邊欄中無法生成巢狀 `<navPoint>`。 |
| **方案 C（本決策）：混合階層對齊引擎 (TOCResolver) + 雙向錨點注入 + 原書並排對比 (Side-by-Side Visual Diff)** | 結合檔案系統與正文 Markdown 結構作為 Ground Truth，融合原書 Part 劃分；支援書內 HTML 點線跳轉與 EPUB 3 多層導航；提供高精並排對比圖供人工與自動審查。 | 需維護標題 slugification 與多層對齊邏輯，並需 PyMuPDF 與 PIL 生成並排圖。 |

## 3. 決策與理由

決定採用 **方案 C**，建立端到端的出版級目錄解析與原書視覺對比引擎：

1. **實作 TOCResolver 階層對齊引擎** (`src/literature_parser/services/core/toc_resolver.py`)：
   - `scan_book_hierarchy`: 自動遍歷全書章節 Markdown，提取 H1 標題、起始頁碼與 H2 子標題，並結合原始目錄中的 Part/Unit 分類聚合章節。
   - `render_in_book_toc_html`: 生成語意化 XHTML 結構，包含 `.toc-part-header`、`.toc-chapter`、`.toc-section`、`.toc-dots`（點線自動填充）與 `.toc-page`。
   - `render_epub_nav_xhtml` 與 `render_epub_ncx`: 輸出多層巢狀 EPUB 3 `<nav epub:type="toc">` 與 EPUB 2 相容的 `toc.ncx`。
2. **自動錨點 ID 注入** (`src/literature_parser/services/exporter/epub_exporter.py`)：
   - 於 `MarkdownToXHTML.to_xhtml_body` 為所有一級與二級標題注入 slugified ID：`<h2 id="slug">`，確保目錄跳轉精確定位。
3. **原書 PDF 與 EPUB 並排視覺對比** (`src/literature_parser/adapters/verification/epub_visual_auditor.py`)：
   - 透過 `visual_compare_epub_with_source_pdf` 自動檢索 `processed-books` 中的原書 PDF。
   - 抽樣代表性頁面（TOC、Table、Figure、Box），使用 PyMuPDF 渲染高解析度 PDF 頁面與 Playwright/PyMuPDF 渲染 EPUB 頁面，調用 `stitch_side_by_side` 加入辨識橫幅後拼接輸出至 `visual_diff_samples/`。
4. **全量 Markdown 檔案同步更新** (`src/literature_parser/services/core/markdown_updater.py`)：
   - 提供離線全量掃描與自愈工具，修復磁碟上所有 chapter Markdown、重新建立全書 `index.md` 與 100% 同步進度表。

## 4. 影響與代價

- **正面影響**：
  - 書內目錄具備點線導引與章節/小節點擊跳轉，EPUB 閱讀器側邊欄目錄具備展開折疊的階層樹。
  - 產出直觀的並排對比圖，使排版與幾何還原度可視覺化驗收。
  - 磁碟上的 Markdown、Obsidian 圖譜索引與 EPUB 電子書保持 100% 雙向同步。
- **代價與後續注意**：
  - 新增 `Pillow>=10.0.0` 相依性於 `pyproject.toml`。
  - 書本主題索引檔案若命名為 `Index.md`，在 macOS 檔案系統需避免覆蓋全書圖譜索引 `index.md`。

## 5. 相關紀錄

- **Known Issues**：`docs/known-issues/018-epub-xml-parsing-corruption-and-tag-interleaving.md`
- **規格書**：`docs/specs/003-epub-exporter.md`
- **測試**：`tests/test_toc_resolver.py`、`tests/test_visual_pdf_epub_diff.py`、`tests/test_markdown_updater.py`
