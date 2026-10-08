# 對話摘要：複雜跨頁表格、合併儲存格與雙欄排版強化

- **檔案對應**：`conversations/raw/003_table_recognition_and_dual_column_layout.md`
- **CID**：`cb3aa69b-821e-450f-a496-5e5d36e2f694`

## 核心目標與背景
複雜跨頁表格、合併儲存格與雙欄排版強化。解決長篇專書、期刊多欄排版、特殊表格與數學公式轉換 Markdown 之精準度。

## 關鍵成果與技術突破
1. 建立 PyMuPDF 與 pdfplumber 混合抽取管道。
2. 整合 Ollama 本地模型（Qwen/Llama）自動修復表格與 LaTeX 公式語法錯誤。
3. 建立斷點續跑（Checkpoint）機制與標準化 Export 管道。
