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
- **學術文獻**：放入 `DATA_DIR/input/literature/`，直接走雙欄中縫重組與 IMRAD 解析管線。

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

---

## 3. 和通用規範不同的例外

- 無例外。所有程式檔均嚴格遵守 `[quality]` 設定與標準分層規範。

---

## 4. 禁止事項

- **嚴禁污染輸入目錄**：永遠不要修改 `DATA_DIR/input/` 的原始書籍與論文檔案（嚴格唯讀）。
- **禁止在原始碼內寫入 Log 檔案**：Log 檔案一律輸出至 `DATA_DIR/logs/`，禁止在專案目錄內直接產生 `.log` 檔案。
- **禁止混淆數位與掃描版管線**：原生數位 PDF 嚴禁調用慢速 OCR，掃描版 PDF 嚴禁跳過 OCR。
