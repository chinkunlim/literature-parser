# 對話摘要：PDF/EPUB 初始文字圖片抽取與書籍格式切分

- **檔案對應**：`conversations/raw/001_pdf_epub_extraction_and_sample_slicing.md`
- **CID**：`e81a99f1-8fd6-4393-8186-db1c305c5170`

## 核心目標與背景
PDF/EPUB 初始文字圖片抽取與書籍格式切分。解決長篇專書、期刊多欄排版、特殊表格與數學公式轉換 Markdown 之精準度。

## 關鍵成果與技術突破
1. 建立 PyMuPDF 與 pdfplumber 混合抽取管道。
2. 整合 Ollama 本地模型（Qwen/Llama）自動修復表格與 LaTeX 公式語法錯誤。
3. 建立斷點續跑（Checkpoint）機制與標準化 Export 管道。
