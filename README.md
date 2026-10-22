# literature-parser

> Enterprise-grade PDF & EPUB Structured Markdown & Image Extractor with Neural Layout OCR, LaTeX Math & Local Ollama AI Verification.

本專案專注於將教科書（Textbooks）與學術文獻/期刊論文（Academic Literature / Journals）從 PDF 與 EPUB 高精度解析為結構化 Markdown、提取圖表與數學公式（LaTeX），並具備本地 Ollama 自我修復、硬體守衛、四階 Profile 版面樣式繼承與 EPUB 3 匯出功能。

---

## 核心設計特色 (Key Architectural Highlights)

1. **約定優於配置的輸入分流 (Convention-Based Input Routing)**：
   - `DATA_DIR/input/books/digital-pdf/`：原生數位教科書，直接利用向量 XML 提取樣式與幾何邊界，**速度極快、零額外 OCR 負擔**。
   - `DATA_DIR/input/books/scanned-pdf/`：掃描版教科書，直接調用神經視覺 / OCR 進行影像切分與文字識別。
   - `DATA_DIR/input/literature/`：期刊論文，直接走雙欄中縫重組與 IMRAD 標題晉升管線（支援 `digital-pdf/` 與 `scanned-pdf/` 子目錄）。
2. **目錄衛生規範 (Folder Naming Hygiene)**：
   - 產出資料夾一律**禁用底線 `_`**，空格統一以連字號 `-` 取代（例如 `output/books/Research-Methods-13th-ed/`）。
   - 章節目錄與檔案統一遵循標準命名格式：`Ch01-Title`、`Appendix-A-Title`。
3. **前言 (Front Matter) 獨立切分與純淨 Chapter 1 保證**：
   - `Cover`、`Title-Page`、`Publish/Copyright`、`Dedication`、`TOC`、`About-Authors`、`Preface` 等所有前置頁面均獨立切分為獨立 PDF（`00-01-Cover`、`00-07-TOC` 等）。
   - 自動向後探測真實 Chapter 1 起始頁，絕不讓 Chapter 1 吸收前置頁面。
   - **全面轉為 Markdown**：Front Matter 與正文章節皆產出對應的 `.md` 檔案，Obsidian 雙鏈依實體順序完整串接。
4. **四階 Profile 繼承與全域共享知識庫 (Hierarchical Profiles & Shared Knowledge)**：
   - `Level 1 原型預設`（Textbook / Literature）➔ `Level 2 出版社模板`（APA, Elsevier, Pearson, Wiley...）➔ `Level 3 全域共享知識庫`（`front_matter_taxonomy.json`, `pedagogical_blocks.json`）➔ `Level 4 實例 Profile`（統一規範檔名 `profile.json`，並為舊工具提供鏡像相容）。
   - **排版細節完整記錄**：奇偶頁非對稱結構（`PageAsymmetry`，左右翻頁裝訂邊與邊欄相反）、雙欄跨欄橫幅（`has_spanning_boxes`）、首字下沉（`has_drop_caps`）與圖表標題正則（`caption_patterns`）。
5. **獨立 Markdown 轉換引擎與策略模式 (MarkdownConversionService)**：
   - 將核心轉換職責從管線中解耦，建立純粹可重入的 `MarkdownConversionService`，徹底消除對模組全域變數的污染，支援 Apple Silicon 多核心並發安全。
   - 透過 `BookPostProcessor` 與 `LiteraturePostProcessor` 策略注入，分流處理書籍教學區塊/TOC 與論文 IMRAD/文獻引用結構化。
6. **Figure 與 Table 獨立裁切（含 Caption/Notes/四邊等寬 Margin）與雙軌表格呈現**：
   - 完整包覆 Caption、圖表/表格本體與 Notes 註釋，上下左右四邊等寬外擴 16 pt（約 5.6 mm，150 DPI 下約 33 px）呼吸邊距。
   - 表格採雙軌呈現：Markdown 保留結構化文字（供全文檢索與 AI 分析），並在該處嵌入獨立裁切圖片對照連結。
7. **CSS 混合雙出 (Dual CSS Output)**：
   - 輸出目錄產出獨立 `style.css` 供網頁瀏覽與 EPUB 3 引用，同時在 Markdown 檔頭自動嵌入 `<style>` 區塊，保證在 Obsidian、Typora、VS Code 等任何原生預覽器中開箱即見完整排版美化效果。
8. **三層漸進式品質檢驗體系 (Three-Tier Quality Verification)**：
   - **第一層：排版檢查 (LayoutAuditor, 35%)**：H1 唯一性、大綱單調遞進、TOC 錨點跳轉有效性、表格標籤閉合、圖片實體存在性、頁首頁尾雜訊過濾。
   - **第二層：詞語檢查 (LexicalAuditor, 35%)**：混成辭典比對、形態素衍生分析、連字號斷詞平滑黏合、首字下沉修復、LaTeX 公式定界符成對與破碎統計檢定式正規化。
   - **第三層：語意檢查 (SemanticAuditor, 30%)**：跨頁未完句連續縫合、雙欄流向順序性、內文引註與章末 References 交叉比對、圖表指涉完整性；低信心時按需喚醒本地 Ollama 深度覆核。
9. **閉環自我修復 (Closed-Loop Layout Healing)**：
   - 當格式稽核器偵測到頁首殘留（`LEAKED_HEADER`）或頁尾殘留（`LEAKED_FOOTER`）時，自動計算幾何位移並即時重寫 `profile.json`，全書後續章節自動受益。
10. **原生 PyMuPDF 解析核心與流水線重疊並行 (Native Dual Engine & Concurrency)**：
   - 引入 PyMuPDF 作為高能原生核心，文檔記憶體一次載入，提取文字 span、向量線條與高解析切圖，徹底消滅逐頁 `pdftohtml`/`pdftoppm` 子行程喚起開銷；保留 Poppler CLI 作為透明後備。
   - 實作 Producer-Consumer 流水線並行（`PipelinedChapterProcessor`），當 CPU 正在解析 Chapter 2 時，GPU/Metal Ollama 同步對 Chapter 1 進行背景語意稽核，消除互鎖等待。
11. **Marker 式版面輪廓分析與段落邊界首提錨定 (Marker-Style Layout & Anchoring)**：
   - 依據版面輪廓骨架（Layout Frame）進行正文跨頁斷句縫合；提及圖表時**嚴禁在段中插入截斷句子**，嚴格在整段段落結束（`\n\n`）後才依序掛載輸出。
   - 清單塊完整性保護、同段多圖平鋪佇列、子圖智慧歸一（Figure 1A ➔ 1），以及孤立未引用圖表安全章末釋放。
   - 遇跨行跨欄之複雜表格自動轉譯為語意 HTML 表格（`<table class="book-table">`，支援 `colspan`/`rowspan`）。
12. **集中外部化設定與一鍵即時重刷 (`config/theme.json` & `apply_theme.py`)**：
   - 將「字型系統（Google Fonts/字型堆疊）、60-30-10 出版調色盤、目錄開闔與深度（`toc_mode: close`）、圖表錨定邊距、表格轉譯、教學模組、Obsidian 導航、品質門檻」全數收納於根目錄 `config/theme.json`（附帶 `theme.schema.json`）。
   - 支援「全域母版 ＋ 單書選填覆寫」分層機制，免修 Python 程式碼即可自訂外觀；並提供 `scripts/apply_theme.py` 於數毫秒內重刷已轉出 Markdown 之樣式與目錄。

---

## 快速開始

### 1. 環境前置檢查
本專案依賴純本地 Python 工具鏈與可選的本地 OCR / PDF 轉換工具：

```bash
# 系統前置軟硬體與 Ollama 健康檢查
uv run literature-parser doctor
```

系統建議工具（選配，用於掃描版 PDF OCR 與快速切分）：
```bash
brew install poppler tesseract
```

### 2. 環境與依賴
專案採用 `uv` 管理環境與虛擬隔離環境：
```bash
python3 scripts/agentctl.py setup --install
```

環境設定檔複製自 `.env.example`（設定檔與資料夾位於專案目錄外之 `DATA_DIR`）：
```bash
cp .env.example .env
```

---

## 常用指令 (CLI)

本專案提供統一命令行入口 `literature-parser`（亦相容 `book-processor` 與 `doc-processor`）：

### 處理文獻或書籍
```bash
# 處理單一學術文獻或書籍
uv run literature-parser process path/to/document.pdf --type journal
uv run literature-parser process path/to/textbook.pdf --type book

# 批次遞迴處理整個目錄
uv run literature-parser batch path/to/folder/ --type journal

# 匯出結構化 Markdown 為標準 EPUB 3 電子書（支援書籍多章節與單篇論文）
uv run literature-parser epub path/to/output_dir/ --type book

# 為轉換後之書籍自動生成 Obsidian 雙向導航雙鏈與全書 index.md
uv run literature-parser obsidian-link path/to/book_output_dir/
```

### 樣式與排版重刷 (Re-Theming)
```bash
# 根據 config/theme.json 或該書 theme.json，毫秒級快速重刷已轉出之 Markdown 樣式與目錄
python3 scripts/apply_theme.py path/to/book_output_dir/
```

### 驗證與自動修復
```bash
# 執行三層式漸進品質檢驗（排版、詞語、語意），並產出 AUDIT.md 視覺化報告與 audit_report.json
uv run book-processor verify -f path/to/chapter.md

# 執行 Markdown 排版格式與數學符號稽核
uv run literature-parser audit path/to/chapter.md --ollama --fix

# 查看或套用專案排版修復配方 (Fix Playbook)
uv run literature-parser fix list
uv run literature-parser fix apply clean_orphan_page_numbers path/to/chapter.md

# 自主合成排版瑕疵修復配方（沙盒測試與 AST 安全防護）
uv run literature-parser fix synthesize "瑕疵症狀描述"
```

### 監控、儀表板與自動化
```bash
# 查看全域文獻處理進度快照
uv run literature-parser status

# 生成並瀏覽 HTML 視覺化進度看板
uv run literature-parser dashboard

# 啟動軟硬體看門狗（常駐監控 DATA_DIR/input 來檔自動轉檔）
uv run literature-parser watchdog
```

---

## 執行測試與品質檢查

```bash
# 執行全套單元與整合測試
uv run --offline python -m unittest discover -s tests -v

# 執行架構分層、型別、註解與秘密審查
python3 scripts/agentctl.py check
```

---

## 檔案與資料分離原則 (Data Isolation)
所有書籍輸入、產出 Markdown、斷點資訊與 Log 均置於專案外的 `DATA_DIR`（預設為 `../../projects-data/literature-parser`）：
- `DATA_DIR/input/`：原始書籍與論文（唯讀，結構即配置）：
  - `books/digital-pdf/`：原生數位版 PDF 教科書
  - `books/scanned-pdf/`：掃描版 PDF 教科書
  - `literature/`：期刊文獻論文（預設雙欄數位論文，亦支援 `digital-pdf/` 與 `scanned-pdf/` 子目錄）
- `DATA_DIR/output/`：轉換產出之 Markdown 與圖像（目錄一律使用連字號 `-`，禁用底線）：
  - `books/<Book-Title>/`：各章節 Markdown、獨立 PDF、`profile.json`、圖像與 EPUB 3
  - `literature/<Paper-Title>/`：論文 Markdown、圖表與 EPUB 3
- `DATA_DIR/needs_review/`：低信心度或需人工複審之段落隔離區
- `DATA_DIR/state/`：斷點清單與處理進度
- `DATA_DIR/logs/`：結構化執行紀錄（`process.log`）

---

## 安全性與隱私 (Security & Privacy)
- **零資料上雲**：所有文字處理、版面辨識與大模型驗證均在本地執行，Ollama 服務預設僅綁定 `http://127.0.0.1:11434`。
- **機密隔離**：專案程式碼內嚴禁硬編碼任何 API Key，機密與金鑰統一存放於本地 `.env`。

---

## 文件索引

- [`AGENTS.md`](AGENTS.md) — Agent 規則與「文件放哪裡」對照表
- [`.agents/handoff/LATEST.md`](.agents/handoff/LATEST.md) — 交接看板
- [`docs/adr/DECISIONS.md`](docs/adr/DECISIONS.md) — 架構決策紀錄 (ADR)
- [`docs/known-issues/KNOWN_ISSUES.md`](docs/known-issues/KNOWN_ISSUES.md) — 已知問題庫
- [`docs/specs/SPECS.md`](docs/specs/SPECS.md) — 功能規格清單
- [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) — 系統架構與分層設計
- [`docs/standards/PROJECT_RULES.md`](docs/standards/PROJECT_RULES.md) — 本專案特有規則
- [`CHANGELOG.md`](CHANGELOG.md) — 版本變更紀錄
