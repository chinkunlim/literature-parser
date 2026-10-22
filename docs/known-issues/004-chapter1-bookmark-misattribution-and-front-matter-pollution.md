# ISSUE-004：Chapter 1 書籤誤標在封面導致前置頁面污染正文

- **狀態**：Resolved
- **發現日期**：2026-10-22
- **Agent**：`antigravity`
- **任務**：`TASK-014`

## 1. 現象

在解析某些製作不精確的 PDF 教科書時，PDF 書籤（Bookmarks / Outline）的 `Chapter 1` 條目直接指向第 1 頁（物理封面 Cover）。
- **影響範圍**：
  - 切分出的 `Ch01.pdf` 包含了封面、版權頁、目錄 TOC 與前言 Preface 等前置頁面。
  - 後續正文解析與圖表提取時，封面圖片與目錄條目被當作 Chapter 1 內容轉換，導致章節標題與導航混亂。
  - Profile 幾何校準時誤將封面與前言無頁首的版面計入正文，導致頁首截止線漂移。

## 2. 根本原因

部分出版商或 PDF 壓製工具在產出大綱時，未針對 Front Matter 設立獨立書籤，或者直接將書籍首頁預設連結為第一章，缺乏「真實正文起始頁（genuine body page）」的內容語意校驗。

## 3. 修正或規避方式

在 [`PDFAnalyzer`](file:///Users/limchinkun/Desktop/projects/literature-parser/src/literature_parser/services/core/analyzer.py) 導入 [`verify_and_isolate_chapter1`](file:///Users/limchinkun/Desktop/projects/literature-parser/src/literature_parser/services/core/analyzer.py#L143-L203)：
1. 檢測第一章候選頁面：若 Chapter 1 書籤指向 $\le 3$ 頁，自動向後掃描直到偵測到真實 Chapter 1 正文大標題（如 `Chapter 1` 或 `Chapter One`）。
2. 真實起始頁 $P_{\text{true}}$ 確立後，將前方頁面 $1 \dots P_{\text{true}}-1$ 藉由 [`front_matter_taxonomy.json`](file:///Users/limchinkun/Desktop/projects/literature-parser/src/literature_parser/config/resources/shared_knowledge/front_matter_taxonomy.json) 匹配切分為獨立 Front Matter 區塊（`00-01-Cover`、`00-04-Publish`、`00-07-TOC` 等）。
3. 前置頁面獨立切出 PDF 並轉為 Markdown，全書 Profile 建立時嚴格排除 `00-*` 樣本。

## 4. 防回歸

對應單元測試：
- [`tests/test_v45_front_matter_and_pure_chapter1.py`](file:///Users/limchinkun/Desktop/projects/literature-parser/tests/test_v45_front_matter_and_pure_chapter1.py) 中的 `test_verify_and_isolate_chapter1_prepends_missing_front_matter`。
