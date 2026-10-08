# 🗄️ 會話摘要：標準 EPUB 3 電子書自適應生成架構與多格式發布管線

- **檔案對應**：`conversations/raw/009_epub_exporter_and_multi_format_pipeline.md`
- **CID**：`b4c10a12-88f1-4df2-a392-7f283d9021e5`
- **日期**：2026-09-25 至 2026-09-26

## 核心目標與背景
建立高品質、零依賴、全自動之 EPUB 3 電子書發布管線。將已排版完成之 Markdown 教科書與學術論文無損打包為符合 IDPF 國際標準規範之 EPUB 3 電子書，支援深淺色閱讀模式、響應式表格與 MathML 數學公式渲染。

## 關鍵成果與技術突破
1. **多格式匯出模組建立 (`src/doc_processor/exporter/`)**：
   - `EpubExporter`: 統一跨書籍與學術文獻的 EPUB 3 匯出控制器，具備自適應引擎選擇（Pandoc 優先 + 純 Python 回退）。
   - `PurePythonEpubBuilder`: 零外部依賴 EPUB 3 封裝引擎，嚴格遵循 IDPF 規範（未壓縮 mimetype 居首位、container.xml、content.opf、雙導航 nav.xhtml 與 toc.ncx、CSS 樣式表、圖片打包與 MathML 宣告）。
   - `MarkdownToXHTML`: 實裝 HTML 標籤棧追蹤器（Tag-Stack Tracker），保證多行 HTML 區塊與巢狀標籤不被破壞；修正 void tags 自閉合 (`<img />`, `<br />`, `<hr />`)、布林屬性規範化 (`<details open="open">`) 與 XML 特殊字符轉義。
   - `LaTeXToMathML`: 支援 LaTeX 公式轉 MathML（`<math>`），並嚴格保護貨幣符號（`&#36;15.50`）。
   - `epub_styles.py`: 提供 EPUB 3 專屬排版樣式表，支援閱讀器深淺色模式自適應、響應式表格與圖說美化。
2. **教科書多章節合併與單章獨立匯出**：
   - 自動遍歷 `chapters/` 將所有章節整合進同一本電子書，具備完整層級導航與 Spine 順序。
3. **CLI 總入口整合 (`run.py epub`)**：
   - 新增獨立指令 `uv run python run.py epub <path>`。
   - 於 `process` 與 `batch` 深度整合 `--epub` 參數，轉檔完成後自動輸出 EPUB 3。
4. **全套測試 100% 通過**：
   - 新增 `tests/test_v42_epub_exporter.py`，全套 240/240 單元測試 100% 通過。
