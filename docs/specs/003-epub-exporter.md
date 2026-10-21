# 003. EPUB 3 電子書匯出管線規格 (EPUB Exporter Specification)

## 1. 概述
`src.literature_parser.services.exporter.epub_exporter` 與 `PurePythonEpubBuilder` 提供標準 EPUB 3 規格電子書打包功能，支援純 Python 環境無依賴生成，並原生支援 LaTeX 轉換 MathML 與 Obsidian 筆記跨章節雙向導航。

## 2. 核心功能
- **純 Python EPUB 3 引擎**：在無需安裝 Pandoc 或 Calibre 的環境下，原生組裝 `mimetype`、`META-INF/container.xml`、OPF 封裝文檔及 NCX/NAV 目錄。
- **LaTeX 轉 MathML**：解析 Markdown 中的行內 `$...$` 與獨立區塊 `$$...$$` 數學公式，轉換為符合 EPUB 3 規範的 MathML 標籤，保留貨幣符號轉義。
- **XHTML 標準化過濾**：自動將 Markdown 轉換之 HTML 閉合自閉合標籤（如 `<img />`、`<br />`、`<hr />`），確保 100% 符合 XML 嚴格驗證。
- **教科書與文獻雙模式**：
  - **書籍模式**：聚合多章節 Markdown，自動維護章節前後雙向導航及階層目錄。
  - **文獻模式**：封裝單篇論文為便攜式電子書，包含 DOI、作者與參考文獻。
