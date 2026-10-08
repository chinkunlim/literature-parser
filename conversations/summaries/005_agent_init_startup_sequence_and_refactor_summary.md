# 對話摘要：Agent-Init 啟動序列與核心 Doc Processor 重構

- **檔案對應**：`conversations/raw/005_agent_init_startup_sequence_and_refactor.md`
- **CID**：`e5c9c030-a93d-4e56-a262-881bedac3eab`

## 核心目標與背景
Agent-Init 啟動序列與核心 Doc Processor 重構。解決長篇專書、期刊多欄排版、特殊表格與數學公式轉換 Markdown 之精準度。

## 關鍵成果與技術突破
1. 建立 PyMuPDF 與 pdfplumber 混合抽取管道。
2. 整合 Ollama 本地模型（Qwen/Llama）自動修復表格與 LaTeX 公式語法錯誤。
3. 建立斷點續跑（Checkpoint）機制與標準化 Export 管道。
