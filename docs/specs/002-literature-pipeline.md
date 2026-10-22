# 002. 學術期刊文獻解析管線規格 (Literature Pipeline Specification)

## 1. 概述
`LiteraturePipeline` 專注於單篇學術期刊、會議論文與預印本之解析，重點在於雙欄還原、IMRAD 標題晉升與參考文獻標準化。

## 2. 核心功能
- **雙欄幾何分割與重排**：動態計算中央欄間隙（Gutter），準確依照左右欄順序讀取段落。
- **IMRAD 結構化**：辨識 Introduction, Method, Results, Discussion 與 Author Notes，標準化 Markdown 標題層次。
- **參考文獻懸掛縮排解析**：解析 APA、IEEE 等多種引用格式，標準化文獻條目。
- **出版商版面適配**：支援 Springer, IEEE, Elsevier, APA 等出版商自適應過濾規則。

## 3. 輸入與輸出目錄規範
- **輸入來源 (Convention over Configuration)**：
  - `DATA_DIR/input/literature/`：預設為雙欄數位期刊論文（亦支援 `scanned-pdf/` 與 `digital-pdf/` 子目錄）。
- **輸出規格 (Folder Naming Hygiene)**：
  - 目標路徑：`DATA_DIR/output/literature/<Paper-Title>/`。
  - 命名衛生：資料夾與產出檔案全面禁用底線 `_`，統一以連字號 `-` 取代空格。
