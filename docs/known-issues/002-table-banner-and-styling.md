# 002. 複雜色塊條幅表格撕裂與 CSS 空白

- **狀態**：Open (Mitigated)
- **嚴重程度**：Medium
- **發現日期**：2026-09-20
- **相關模組**：`src/literature_parser/services/parsers/layout/table_parser.py`, `src/literature_parser/services/book_style.py`

## 問題現象
教科書中的雙色條幅對照表（如 Table 2.3）在轉檔為 Markdown 表格時容易破版，遺失分類色塊與橫跨欄位（Colspan）屬性。

## 根本原因
Markdown 原生語法缺乏進階樣式與 Colspan 支援，純文字表格無法表達複雜卡片式視覺結構。

## 緩解與解決方案
- 實作三種表格範式解析（分類大表、雙階段條幅對照表、卡片清單）。
- 在 EPUB 匯出與 HTML 呈現時注入 `book_style.py` 定義之專屬 CSS 樣式，保留原始色彩與排版層次。
