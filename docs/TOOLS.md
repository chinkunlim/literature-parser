# 工具庫與解析器規範 (docs/TOOLS.md)

## 1. 核心底層解析器矩陣 (Core Parsers Matrix)

本專案採用分層協同工具架構，依任務特徵調度最合適的解析庫：

| 工具庫 / 模組 | 角色與主要職責 | 適用場景與呼叫時機 | 特殊約束 / 注意事項 |
| :--- | :--- | :--- | :--- |
| **PyMuPDF (`fitz`)** | 快速向量幾何提取、文字塊提取、PDF 目錄解析 | 全域首道掃描、章節目錄定位、頁面尺寸測量 | 高效但文字流順序需重新以幾何排序演算法整理 |
| **`pdfplumber`** | 視覺網格表格抽取、文字精確邊界框 (BBox) 檢測 | 具有清晰外框線或交錯背景色的結構化表格 | 運算較耗時，僅在偵測到表格特徵區域時按需呼叫 |
| **`PDFMiner.six`** | 底層字元度量（Font, Size, Matrix）、Glyph 座標 | 字體大小層級判定（辨識 H1/H2/H3/正文/附註） | 僅作為微觀排版分析使用，不承擔大量巨集文字串流 |
| **Apple Vision Framework** | 原生神經網路 OCR (`VNRecognizeTextRequest`) | 掃描版書籍 (Scanned PDF)、圖片內文字與流程圖辨識 | macOS 原生零依賴，自動調用 ANE 神經引擎，極致省電 |
| **`sips` (macOS CLI)** | 原生圖像尺寸調整、色彩空間轉換與格式轉檔 | 圖片萃取後壓縮、高解析向量圖縮圖生成 | 系統原生二進位工具，避免引入重型 Pillow 二進位擴充 |
| **`EpubExporter`** | EPUB 3 容器打包控制器（Pandoc 優先 + 純 Python 回退） | 將轉換產出 Markdown 打包為國際標準電子書 | 嚴格遵守 IDPF 規範、MathML 數學標籤與深淺色自適應 |

---

## 2. 專責解析子模組架構 (`src/doc_processor/parsers/`)

為避免單一上帝類別（God Class），版面解析層依職責明確拆分為專責子模組：

### 2.1 向量圖表解析器 (`VectorFigureParser`)
- **檔案**：`src/doc_processor/parsers/layout/vector_figure_parser.py`
- **職責**：專責抽取 PDF 頁面中由路徑、曲線、座標軸構成之向量圖形與研究流程圖。
- **核心演算法**：坐標軸刻度數字過濾（防止 `20 20 1 1` 洩漏污染正文），並將圖說（Caption）精確綁定至圖形實體。

### 2.2 章末專屬區塊解析器 (`EndOfChapterParser`)
- **檔案**：`src/doc_processor/parsers/layout/eoc_parser.py`
- **職責**：專責解析教科書章末專屬元件（複習問題、思維討論題、專用術語表、延伸閱讀）。
- **核心演算法**：自動辨識題號邊界、過濾非術語粗體干擾，並產出結構化 Anki 記憶卡資料結構。

### 2.3 語意圖表定位器 (`SemanticPlacement`)
- **檔案**：`src/doc_processor/parsers/layout/semantic_placement.py`
- **職責**：落實學術文獻「圖表首引後排」原則。
- **核心演算法**：掃描正文內提及該圖表的第一個句子，等待該完整自然段落結束後，始行插入該圖表與說明，杜絕段落遭圖表腰斬。

### 2.4 純文字共用工具庫 (`shared_text.py`)
- **檔案**：`src/doc_processor/utils/shared_text.py`
- **職責**：跨模組無狀態純函數（Pure Functions），零 I/O、確定性輸出。
- **提供工具**：
  - `clean_orphan_page_numbers()`: 孤立頁碼過濾
  - `escape_katex_currency()`: 貨幣符號 `\$` 轉義
  - `repair_ocr_statistics_symbols()`: 統計符號（$\eta^2$, $\chi^2$, $p < .05$）修復
  - `filter_manuscript_watermarks()`: Elsevier / IEEE 浮水印清洗

---

## 3. 修復工具與手冊庫 (`FixPlaybook`)

- **檔案**：`src/doc_processor/fixes/`
- **修復工具清單**：
  - `recipe_ch02_heading_split.py`: 解決標題長段落誤升格為 H3 粗體問題
  - `recipe_apa_table_notes.py`: 解決 APA 表格附註（Table Notes）黏連正文問題
  - `recipe_latex_bracket_balance.py`: 解決 LaTeX 公式括號未閉合問題
  - `recipe_double_column_flow.py`: 解決學術雙欄閱讀流倒置問題
- **沙盒晉升機制**：所有由 Ollama 合成之修復程式皆須經 AST 語法檢查與單元測試驗證後，暫存於 `fixes/staged/`，經審計通過後晉升至 `fixes/promoted/`。
