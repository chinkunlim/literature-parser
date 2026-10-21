# 002. 學術期刊文獻解析管線規格 (Literature Pipeline Specification)

## 1. 概述
`LiteraturePipeline` 專注於單篇學術期刊、會議論文與預印本之解析，重點在於雙欄還原、IMRAD 標題晉升與參考文獻標準化。

## 2. 核心功能
- **雙欄幾何分割與重排**：動態計算中央欄間隙（Gutter），準確依照左右欄順序讀取段落。
- **IMRAD 結構化**：辨識 Introduction, Method, Results, Discussion 與 Author Notes，標準化 Markdown 標題層次。
- **參考文獻懸掛縮排解析**：解析 APA、IEEE 等多種引用格式，標準化文獻條目。
- **出版商版面適配**：支援 Springer, IEEE, Elsevier, APA 等出版商自適應過濾規則。
