# 001. 教科書解析管線規格 (Textbook Pipeline Specification)

## 1. 概述
`TextbookPipeline` 專門負責多章節大型教科書之解析，具備目錄（TOC）導航抽取、章節物理切分、學習目標識別與 Anki 卡片匯出功能。

## 2. 核心功能
- **目錄剖析與章節拆分**：利用 PDF Outline 或正文特徵自動識別 Chapter 範圍，執行無損切分。
- **邊欄與專有名詞提取**：自動辨識 Margin Glossaries，轉換為側欄卡片。
- **學習目標與章末總結**：抽取 Learning Objectives (LO) 與 End of Chapter (EOC) 練習題。
- **EPUB 與 Obsidian 整合**：生成雙向導航標籤與出版商特化 CSS 樣式。

## 3. 輸入與輸出目錄規範
- **輸入來源 (Convention over Configuration)**：
  - `DATA_DIR/input/books/digital-pdf/`：直接標定為數位向量教科書，執行文字與向量圖表提取，跳過 OCR 檢測。
  - `DATA_DIR/input/books/scanned-pdf/`：直接標定為掃描版教科書，直接調用 Vision 神經 OCR 解析。
  - `DATA_DIR/input/books/`（根目錄）：相容備援，未分流檔案由系統執行抽樣自動檢測。
- **輸出規格 (Folder Naming Hygiene)**：
  - 目標路徑：`DATA_DIR/output/books/<Book-Title>/`。
  - 命名衛生：資料夾與章節名稱全面禁用底線 `_`，統一以連字號 `-` 取代空格（例如 `Research-Methods-Design-and-Analysis-13th-ed`）。
