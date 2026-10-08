# 對話摘要：Research Methods 13th ed. 專書轉換與排版調校

- **檔案對應**：`conversations/raw/002_research_methods_conversion_and_tuning.md`
- **CID**：`74bb97d9-21b3-4f9e-bc48-c843c08ee7a1`

## 核心目標與背景
Research Methods 13th ed. 專書轉換與排版調校。解決長篇專書、期刊多欄排版、特殊表格與數學公式轉換 Markdown 之精準度。

## 關鍵成果與技術突破
1. 建立 PyMuPDF 與 pdfplumber 混合抽取管道。
2. 整合 Ollama 本地模型（Qwen/Llama）自動修復表格與 LaTeX 公式語法錯誤。
3. 建立斷點續跑（Checkpoint）機制與標準化 Export 管道。
