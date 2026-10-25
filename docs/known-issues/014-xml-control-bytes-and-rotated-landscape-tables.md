# ISSUE-014：Unescaped XML control bytes (\x02) and 90-degree rotated landscape tables drop or scramble PDF pages

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-25
- **Agent**：`antigravity`
- **任務**：`TASK-045`

## 1. 現象

Custom vector symbol fonts emit raw ASCII control bytes (0x02) that crash ET.fromstring and silently drop 88 pages across Biopsychology and Research Methods; 90-degree rotated pages (dir=(0,-1)) scramble landscape tables like Career Counseling Table 2-1.

- **錯誤訊息**：`xml.etree.ElementTree.ParseError: not well-formed (invalid token): line X, column Y`
- **重現步驟**：對含有自訂向量字型（如 `HelveticaLTCom-Roman`）的 PDF 頁面（例如 *Biopsychology* Ch06 p.26 或 *Research Methods* Ch09 p.17）呼叫 `DigitalPDFParser.extract_page_xml` 並以 `ET.fromstring` 解析。
- **影響範圍**：*Biopsychology* 共 60 頁、*Research Methods* 共 28 頁（合計 88 頁）因 XML 解析失敗而被靜默略過；*Career Counseling* Ch02 p.10 橫向旋轉表格（`Table 2-1`）因未轉換 90 度旋轉座標而完全錯亂。

## 2. 根本原因

1. `html.escape()` 只轉義 `&`, `<`, `>`, `"`, `'`，不會移除 XML 1.0 非法控制字元（`0x00–0x08`, `0x0B`, `0x0C`, `0x0E–0x1F`, `0x7F`）。當 PDF 內嵌特殊字型 glyph 對應到 `0x02` 等控制碼時，`ET.fromstring` 直接拋出 `ParseError`，且外層 `except ET.ParseError: return ""` 靜默吞掉整頁。
2. 當整頁大多數文字行屬於逆時針 90 度旋轉（`line['dir'] == (0.0, -1.0)`）的橫向表格頁時，原始 `(x0, y0)` 座標會將橫列視為垂直座標，導致表格欄列與字元順序被打散。
3. 當同一頁包含多個向量圖表（例如 *Research Methods* Ch09 p.17 同時有 `Figure 9.11` 與 `Figure 9.12`）時，`VectorFigureParser.extract_vector_figures` 未以 `next_fig_top` 限制每個圖表的 `vec_elems` 範圍，導致兩個圖表中間的正文段落被一併視為圖表內部文字而吞噬。

## 3. 修正或規避方式

1. 在 `src/literature_parser/services/parsers/digital_pdf.py` 的 `extract_page_xml` 中，先以 `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+', '', s_clean)` 清除非法控制字元後再執行 `html.escape`。
2. 在 `extract_page_xml` 中偵測整頁 `>65%` 旋轉行（`abs(dx) <= 0.15 and abs(dy) >= 0.85`），自動將 `(x0, y0, x1, y1)` 轉換至正向閱讀座標系。
3. 在 `src/literature_parser/services/parsers/layout/vector_figure_parser.py` 中，將 `fig_elems` 依 `top` 排序並以 `next_fig_top` 限制單一圖表的 `vec_elems` 收集範圍（`Refs: ISSUE-014`）。

## 4. 防回歸

- `tests/test_batch_resilience_and_table_structuring.py`（`TestBatchResilienceAndTableStructuring`）與全數 5 本書 128 章節 `MissPg = 0` 驗證。
