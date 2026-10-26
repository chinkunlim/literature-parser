# 本專案專屬規則 (PROJECT_RULES)

> 規則分兩層：`docs/standards/` 的其他文件是**所有專案通用**的規範（由專案模板提供，`agentctl update` 會更新）；
> 本檔是**只適用這個專案**的規則，由這個專案自己維護，模板更新時不會被覆蓋。每次開工都要讀。

## 1. 領域知識與術語

- **文獻 (Literature / Journal)**：指學術論文 PDF，具有雙欄排版、IMRAD 架構（Introduction, Method, Results, Discussion）、作者資訊與懸掛縮排參考文獻。
- **書籍 (Book / Textbook)**：指教科書 PDF / EPUB，具有多章節、目錄（TOC）、學習目標（Learning Objectives）、專有名詞（Glossary）與章末總結（End-of-Chapter）。
- **前置頁面 (Front Matter)**：指書籍正文之前的結構（Cover、Half-Title、Title-Page、Publish/Copyright、Dedication、Brief-Contents、TOC、About-Authors、Preface、Foreword 等）。
- **斷點紀錄 (Checkpoint)**：記錄章節處理與驗證狀態的清單檔，確保中斷後可優雅恢復（Resume）。
- **修復手冊 (Fix Playbook / Synthesizer)**：存放確定性排版修復規則與由本地 Ollama 演繹之代碼修復配方。
- **領域模型 (DocumentProfile)**：純領域層強型別 Dataclass，標準化封裝 metadata、geometry、typography、special_blocks 等設定。

---

## 2. 本專案特有的規則

### 2.1 輸入目錄「約定優於配置」 (Convention over Configuration)
- **數位教科書**：必須放入 `DATA_DIR/input/books/digital-pdf/`。管線直接調用向量 XML 解析，**嚴禁耗費算力呼叫 Vision 或 OCR**。
- **掃描教科書**：必須放入 `DATA_DIR/input/books/scanned-pdf/`。管線直接調用神經視覺 OCR 進行影像切分與文字識別。
- **學術文獻**：放入 `DATA_DIR/input/literature/`（支援 `digital-pdf/` 與 `scanned-pdf/` 子目錄），直接走雙欄中縫重組與 IMRAD 解析管線。

### 2.2 輸出命名衛生 (Folder & File Naming Hygiene)
- **禁用底線**：所有產出目錄與檔案名稱**一律禁用底線 `_`**，所有空格、標點符號統一轉換為連字號 `-`（例如 `output/books/Cognitive-Psychology-8th-ed/`）。
- **章節與附錄命名**：統一格式化為 `Ch01-Title`、`Appendix-A-Title`。

### 2.3 前言 (Front Matter) 獨立切分與純淨 Chapter 1 保證
- **Chapter 1 純淨保護**：`Chapter 1` 絕對不得包含 Cover、TOC、Preface 等前置頁面。若 PDF 書籤有瑕疵誤將 Chapter 1 標在第 1 頁，程式必須自動向後探測真實 Chapter 1 起始頁，將前方所有頁面提煉為 Front Matter。
- **獨立 PDF 切分與全量 Markdown 轉換**：所有 Front Matter 必須切分為獨立 PDF（存於 `chapters/00-01-Cover/` 等，以 `00-` 編號前綴排序），並與正文章節一樣完整轉換為對應的 `.md` 檔案，依序納入 Obsidian 雙鏈導航。

### 2.4 四階 Profile 繼承與全域共享知識庫
- **主 Profile 檔名統一**：書籍與文獻實例設定檔一律命名為標準 `profile.json`，並為舊工具維持 `book_profile.json` 或 `document_profile.json` 鏡像。
- **全域共享知識庫 (Shared Knowledge)**：
  - `front_matter_taxonomy.json`：前置頁標準分類正則庫。
  - `pedagogical_blocks.json`：特殊教學區塊庫（邊欄名詞、對話框、案例、例題、倫理、心智圖、公式等）。
- **Profile 建立樣本純淨度**：`ensure_book_profile()` 必須在切分後、轉換前單執行緒建立，且**嚴格排除 `00-*` 前置頁面**，只取真正的正文章節作為幾何與字級取樣。
- **排版細節完整性**：Profile 必須記錄奇偶頁非對稱邊欄與頁首（`PageAsymmetry`）、雙欄跨欄橫幅（`has_spanning_boxes`）、首字下沉（`has_drop_caps`）與圖表標題正則（`caption_patterns`）。

### 2.5 硬體守衛與離線主權 (Hardware Guard & Local AI)
- **硬體守衛優先**：所有啟動本地 Ollama 大模型推理或密集 OCR 運算的任務，必須事先通過 RAM（≥ 2.0GB/4.0GB）與電源狀態（電池低電量防護）檢查，資源不足時應優雅降級或中止。
- **純本地離線保證**：本地大模型服務僅綁定 `http://127.0.0.1:11434`，絕不將資料傳送至外部非授權端點。
- **Web 與 API 服務埠號**：本專案之 Web 儀表板與 REST API/MCP 服務固定綁定 `127.0.0.1:8767`（由 `HTTP_PORT=8767` 指定），避免與 Open WebUI (8080)、literature-fetch (8765) 或模板網頁 (8766) 衝突。

### 2.6 獨立轉換引擎與策略模式 (MarkdownConversionService)
- **單一職責與可重入**：核心 Markdown 轉換邏輯必須由 `MarkdownConversionService` 承載，嚴禁在 Pipeline/Orchestrator 內覆寫模組全域變數（如 `_STYLE`）或編寫逐頁拼接迴圈。
- **策略分離**：書籍採用 `BookPostProcessor`（處理 TOC、教學區塊、Front Matter 差異），論文採用 `LiteraturePostProcessor`（處理 IMRAD 標題、APA/IEEE 懸掛縮排與表格錨點）。

### 2.7 圖表獨立裁切與等寬邊距規範 (Figure & Table Cropping with Uniform Margins)
- **完整包覆**：所有 Figure 與 Table 必須獨立裁切成高畫質影像存於 `images/`，裁切範圍必須完整涵蓋 Caption（標題/編號）、圖表/表格本體與底部的 Notes（註釋/備註）。
- **上下左右等寬 Margin**：裁切時四邊必須外擴等寬呼吸邊距（預設 `16 pt`，約 5.6 mm，150 DPI 下約 33 px），於 `ProfileGeometry.uniform_crop_margin_pt` 開放微調。
- **表格雙軌呈現**：Markdown 內文保留結構化文字表格（供檢索與 AI 分析），並在該處嵌入獨立裁切圖片連結（供人類視覺對照）。
- **CSS 混合雙出**：輸出根目錄產出獨立 `style.css`，並在產出的 Markdown 檔頭自動嵌入 `<style>` 區塊。

### 2.8 三層漸進式品質檢驗體系 (Three-Tier Progressive Verification)
- **三維度權重**：轉換完成後依序執行排版檢查（`LayoutAuditor`, 35%）、詞語與公式檢查（`LexicalAuditor`, 35%）、語意與閱讀流檢查（`SemanticAuditor`, 30%）。
- **處置原則**：確定性瑕疵執行 Safe Auto-Fix（自動過濾洩漏頁首、清理孤立頁碼、閉合標籤、連字號斷詞黏合、統計符號標準化）；整體品質未達門檻（預設 85%）或排版破損時，隔離至 `DATA_DIR/needs_review/`。
- **報告雙輸出與 CLI**：同目錄產出視覺化 `AUDIT.md` 與結構化 `audit_report.json`，並提供獨立 CLI 指令 `book-processor verify -f path/to/chapter.md` 供隨時體檢。

### 2.9 樣式排版集中外部化與即時重刷 (Unified Theming & Instant Re-Theming)
- **8 大樣式分區全數外部化**：所有全域字型堆疊、60-30-10 出版調色盤、目錄開闔與深度（`toc_mode: close`）、圖表邊距、表格轉譯、教學模組、Obsidian 雙鏈導航與品質門檻一律集中收納於 `config/theme.json`（受 `theme.schema.json` 強型別校驗）。
- **全域母版與單書覆寫**：各書籍目錄可放置獨立 `theme.json` 實現零破壞性專用樣式覆寫；並可透過 `python3 scripts/apply_theme.py <book_dir>` 於毫秒級內對已轉出 Markdown 原地更新 `<style>` 區塊與 `style.css`。

### 2.10 Marker 式版面輪廓分析與段落邊界首提錨定 (Marker-Style Layout Framing & Paragraph-Boundary Anchoring)
- **段落邊界完整性**：內文提及圖表時**嚴禁在段落句子中插斷**，圖表必須在整段正文段落結束（`\n\n`）後才依序掛載輸出。
- **清單與多圖保護**：清單塊（List Block）內文提及圖表不應切斷清單連續性；同段多圖依序平鋪排列；子圖統一歸一為母圖（Figure 1A ➔ 1）；未引用孤立圖表於章末章節標題前安全釋放。
- **複雜表格轉譯**：遇跨欄、跨行或巢狀表頭表格時自動轉譯為結構化語意 HTML 表格（`<table class="book-table">`，支援 `colspan`/`rowspan`）。

### 2.11 原生 PyMuPDF 解析核心與流水線重疊並行 (Native Dual Engine & Concurrency)
- **記憶體直讀架構**：採用 PyMuPDF (fitz) 原生 API 一次性載入文檔至記憶體，直接抽取文字 span 樣式、向量路徑與高解析圖片，徹底消滅逐頁呼叫外部子進程的行程負擔；保留 Poppler 作為備援 fallback。
- **CPU-GPU 流水線並行**：實作 `PipelinedChapterProcessor`，在 CPU 正在解析下一章節的同時，由 GPU/Metal 本地 Ollama 對上一章節進行非同步背景語意驗證，達到資源最大化利用。

---

## 3. 和通用規範不同的例外

- 無例外。所有程式檔均嚴格遵守 `[quality]` 設定與標準分層規範。

---

## 4. 禁止事項

- **嚴禁污染輸入目錄**：永遠不要修改 `DATA_DIR/input/` 的原始書籍與論文檔案（嚴格唯讀）。
- **禁止在原始碼內寫入 Log 檔案**：Log 檔案一律輸出至 `DATA_DIR/logs/`，禁止在專案目錄內直接產生 `.log` 檔案。
- **禁止混淆數位與掃描版管線**：原生數位 PDF 嚴禁調用慢速 OCR，掃描版 PDF 嚴禁跳過 OCR。
