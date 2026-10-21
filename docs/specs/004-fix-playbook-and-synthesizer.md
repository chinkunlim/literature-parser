# 004. 排版修復手冊與配方合成規格 (Fix Playbook & Recipe Synthesizer Specification)

## 1. 概述
提供排版瑕疵修復之規則手冊庫 (`FixPlaybook`) 與基於本地 Ollama LLM 的自主配方合成器 (`OllamaRecipeSynthesizer`)，具備靜態 AST 安全檢查、隔離沙盒測試與三階段生命週期管理。

## 2. 核心功能
- **排版瑕疵手冊 (Playbook)**：內建多種標準化修復配方（如清理孤兒頁碼、降級雜訊標題、修復 Elsevier 粘連參考文獻、KaTeX 貨幣符號轉義等）。
- **自主配方合成 (Recipe Synthesizer)**：針對未登錄之未知排版瑕疵，自動提示本地 Ollama 生成 Python 正則或字串轉換函式。
- **AST 語法安全守衛**：在載入與執行合成代碼前，解析 Python AST 語法樹，全面攔截危險模組 (`os`, `sys`, `subprocess`, `socket`) 與內建危險函式 (`eval`, `exec`, `open`)。
- **沙盒驗證與生命週期流轉**：
  - 在臨時獨立沙盒中測試配方轉換之冪等性與準確性。
  - 三階段狀態機：`staged`（待審查）➔ `promoted`（晉升正式）或 `rejected`（拒絕淘汰）。
