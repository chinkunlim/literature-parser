# 001. 教科書解析管線規格 (Textbook Pipeline Specification)

## 1. 概述
`TextbookPipeline` 專門負責多章節大型教科書之解析，具備前置頁面（Front Matter）獨立切分、純淨 Chapter 1 校驗、全章節 Markdown 轉換、目錄（TOC）導航抽取、章節物理切分、學習目標識別、奇偶頁非對稱邊欄、雙欄跨欄橫幅保護與 Obsidian 雙鏈導航。

## 2. 核心功能與處理階段
- **階段 1：大綱剖析與前言獨立切分**：
  - 載入全域共享知識庫 `front_matter_taxonomy.json`，精準匹配 Cover、Publish/Copyright、TOC、About-Authors、Preface、Dedication 等。
  - **純淨 Chapter 1 保護**：自動校驗 Chapter 1 真實起始頁；若書籤誤標在第 1 頁，自動向後探測真實章節正文，前方頁面全數獨立切出為 Front Matter。
  - 所有前置頁切分出獨立 PDF 存於 `chapters/00-01-Cover/` 等，以 `00-` 編號前綴維護目錄順序。
- **階段 2：正文多章抽樣與獨立 Profile 建立**：
  - 在章節切分完成後、Markdown 轉換前，主進程單執行緒執行 `ensure_book_profile()`。
  - **嚴格排除 `00-*` 前置頁面**，只取真正的正文章節（`Ch01`, `Ch02`）跳過封面頁取第 2~5 頁正文計算版心邊界、字級中位數與教學特殊區塊。
  - 寫入全書標準 `profile.json`（並相容 `book_profile.json` 鏡像）。
- **階段 3：全章節（含 Front Matter）Markdown 轉換**：
  - Front Matter 與正文章節全部轉為 `.md` 檔案。
  - 支援奇偶頁非對稱邊欄提取（偶數頁在左、奇數頁在右）、雙欄跨欄橫幅（`has_spanning_boxes`）與首字下沉（`has_drop_caps`）。
- **階段 4：雙鏈圖譜與 EPUB 3 匯出**：
  - 生成 `00-01-Cover` ➔ `00-07-TOC` ➔ `00-09-Preface` ➔ `Ch01` 完整順序雙向導航。
  - 生成全書目錄索引 `index.md`，並可打包為標準 EPUB 3 電子書。

## 3. 輸入與輸出目錄規範
- **輸入來源 (Convention over Configuration)**：
  - `DATA_DIR/input/books/digital-pdf/`：直接標定為數位向量教科書，執行文字與向量圖表提取，跳過 OCR 檢測。
  - `DATA_DIR/input/books/scanned-pdf/`：直接標定為掃描版教科書，直接調用 Vision 神經 OCR 解析。
  - `DATA_DIR/input/books/`（根目錄）：相容備援，未分流檔案由系統執行抽樣自動檢測。
- **輸出規格 (Folder Naming Hygiene)**：
  - 目標路徑：`DATA_DIR/output/books/<Book-Title>/`。
  - 命名衛生：資料夾與章節名稱全面禁用底線 `_`，統一以連字號 `-` 取代空格（例如 `Research-Methods-Design-and-Analysis-13th-ed`）。
