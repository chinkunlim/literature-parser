# 003. EPUB 3 電子書匯出管線規格 (EPUB Exporter Specification)

## 1. 概述
`src.literature_parser.services.exporter.epub_exporter`、`PurePythonEpubBuilder` 與 `EpubVisualAuditor` 提供標準出版級 EPUB 3 規格電子書打包與視覺品質閉環檢驗功能，支援純 Python 環境無依賴生成，並原生支援 LaTeX 轉換 MathML、GFM 表格轉 XHTML、Mermaid 轉向量 SVG、階層超連結目錄與 Obsidian 筆記跨章節雙向導航。

## 2. 核心功能
- **純 Python EPUB 3 引擎**：在無需安裝 Pandoc 或 Calibre 的環境下，原生組裝 `mimetype`、`META-INF/container.xml`、OPF 封裝文檔及 NCX/NAV 目錄。
- **XHTMLSanitizer 嚴格 XML 標籤棧自愈器**：基於 `html.parser.HTMLParser` 維護標籤棧（tag stack），錯位閉合時逆序修復並補全閉合標籤，Void tags 嚴格自閉合 `<tag />`，保證 100% 通過 `xml.etree.ElementTree` 語法驗證。
- **GFM 管線表格與 Mermaid 向量繪製**：
  - 將 GFM 表格（`| Col1 | Col2 |`）轉換為出版級語意化 `<div class="table-container"><table class="textbook-table">...`。
  - 將 ` ```mermaid ` 概念圖透過 `MermaidToSVGConverter` 動態繪製為嵌入式向量 `<svg>`，解決電子書閱讀器無法執行 JavaScript 的痛點。
- **TOCResolver 出版級階層目錄與超連結跳轉**：
  - 自動掃描全書結構，建構 `Part / Unit -> Chapter -> Section` 巢狀階層樹。
  - 書內目錄（`00-07-TOC`）渲染為出版級 HTML，包含點線導引（`.toc-dots`）與頁碼對齊（`.toc-page`），所有項目自帶 `<a href="...">` 錨點超連結。
  - 同步輸出 EPUB 3 多層巢狀 `<nav epub:type="toc">` 與 EPUB 2 相容的 `toc.ncx` 側邊欄樹狀目錄。
- **原書 PDF 與 EPUB 並排視覺對比 (`EpubVisualAuditor`)**：
  - 自動比對 `DATA_DIR/input/processed/processed-books/` 中的原書 PDF。
  - 抽樣代表性頁面（TOC、表格、圖片、專欄），高解析度渲染並等高拼接生成 side-by-side 並排對比圖（`visual_diff_samples/`），輸出 `visual_diff_report.json`。
- **Markdown 離線同步更新器 (`MarkdownUpdater`)**：
  - 批次自愈磁碟上所有 chapter Markdown，自動修正 CSS `@import`、標準化註解、排除 `index.md` 命名衝突，並將全書圖譜索引與進度表更新至 100%。
