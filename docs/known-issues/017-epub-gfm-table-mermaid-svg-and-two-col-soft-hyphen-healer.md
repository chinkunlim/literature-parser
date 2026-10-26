# ISSUE-017：Pure-Python EPUB exporter missing GFM pipe table & Mermaid SVG conversion, plus 2-column P1 header interleaving and U+00AD soft-hyphen artifacts

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-26
- **Agent**：`Antigravity`
- **任務**：`TASK-048`

## 1. 現象

MarkdownToXHTML emitted raw GFM pipe tables and raw Mermaid code in EPUB; DigitalPDFParser forced single-column on top 45% of 2-column front-matter pages; U+00AD soft hyphens and orphan `**` markers remained in Markdown.

- **錯誤訊息**：
  - EPUB XHTML 內出現 `<p>| Term | Term | Term |</p><p>| --- | --- | --- |</p>`（117+ 行未渲染表格）與 `<pre><code>graph LR ...</code></pre>`。
  - 《Biopsychology》雙欄前言（`00-09-Preface.md`）上半頁左右欄交錯：`The illustrations in Edition of ing scientific fields...`，以及 1,398 處軟連字號 `\xad`（`U+00AD`）未清理。
  - 5 本書共 153 行殘留孤立 `**`（如 `**Lisa Y. Flores, PhD,** **`、`<td>Simple correlation ( r )**</td>`）與跨行長標題第二行掉入普通段落。
- **重現步驟**：在不具備外部 `pandoc` 的環境下匯出 5 本教科書的 `.epub` 並以 `PyMuPDF` 逐頁開啟檢查。
- **影響範圍**：`epub_exporter.py`、`digital_pdf.py`、`text_utils.py`、`layout_healer.py`。

## 2. 根本原因

1. `MarkdownToXHTML.to_xhtml_body()` 未實作 GFM 管線表格（`| Col1 | Col2 |`）轉 HTML `<table>` 的解析器，且將 ` ```mermaid ` 區塊當作一般 `<pre><code>` 輸出，而電子書閱讀器不執行 Mermaid JS。
2. `DigitalPDFParser` 在第 1 頁 `top < p1_body_y`（預設 45% 頁面高度）時無條件設定 `is_p1_header_area = True`，覆蓋了 `page_has_two_cols = True`，導致從頁面頂部就開始雙欄排版的章節（如 `Preface`、`Brief Contents`）上半頁被當成單欄橫向拼接。
3. `repair_hyphens()` 與 `clean_typography_artifacts()` 僅處理 ASCII `-`，未處理隱形軟連字號 `U+00AD (\xad)`。
4. `LayoutAutoHealer` 未針對跨 span 粗體切割留下的孤立單數 `**`、HTML `<td>` 內的 `**` 以及帶頁碼的跨行標題續行進行閉環修復。

## 3. 修正或規避方式

1. 於 `epub_exporter.py` 實作 GFM 管線表格轉 `<table><thead><tbody>` 與 `MermaidToSVGConverter`（將 ` ```mermaid ` 繪製為內嵌向量 `<svg>` 概念圖），並修復 HTML 區塊內的行內 Markdown 與詞彙錨點（`Refs: ISSUE-017`）。
2. 於 `digital_pdf.py` 計算實際雙欄起始座標 `two_col_top_y`，避免 `is_p1_header_area` 誤將雙欄區域強制合併為單欄，並放寬跨行標題續行接合（`Refs: ISSUE-017`）。
3. 於 `text_utils.py` 清理並接合 `U+00AD (\xad)` 軟連字號；於 `layout_healer.py` 新增孤立 `**`、HTML `<td>` 粗體與跨行長標題修復（`Refs: ISSUE-017`）。
4. 新增 `epub_visual_auditor.py`（`EpubVisualAuditor`），使用 `PyMuPDF` 將 EPUB 全書每一頁渲染為 PNG 截圖並執行閉環檢查與自動回修（`Refs: ISSUE-017`）。

## 4. 防回歸

- `tests/test_epub_visual_closed_loop.py`：`TestEpubVisualClosedLoop` 涵蓋 GFM 表格轉 XHTML `<table>`、Mermaid 轉 `<svg>`、軟連字號 `\xad` 接合、孤立 `**` 與跨行標題修復，以及 `EpubVisualAuditor` 逐頁 PNG 截圖與閉環修復測試。
