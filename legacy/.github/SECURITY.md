# 資安政策與脫敏規範 (.github/SECURITY.md)

## 1. 支援版本 (Supported Versions)

| 版本 | 支援狀態 |
| :--- | :--- |
| `main` 分支最新版 | :white_check_mark: 支援安全維護與修復 |
| 歷史發布版本 | :x: 請直接更新至 `main` 最新版本 |

---

## 2. 漏洞回報流程 (Reporting Vulnerabilities)

若您在本專案中發現任何潛在安全漏洞（包含憑證外洩、任意程式碼執行風險等）：
1. 請**不要**在公開的 Issue 列表中提出漏洞細節。
2. 請聯繫專案維護者或於本地安全審核記錄中備忘。
3. 我們將於 48 小時內確認問題並提供修復補丁。

---

## 3. 本地離線主權與資料脫敏規範 (Local Sovereign & Sanitization)

為保障學術隱私與系統安全，本專案實施以下強制規範：
1. **離線模型隔離 (Offline Sovereign AI)**：
   - 所有的語義修復、LaTeX 公式補全與品質審查皆僅向本地執行的 Ollama 服務 (`http://localhost:11434`) 發出請求，絕不上傳至任何外部公共雲端或第三方伺服器。
2. **對話封存強制正則脫敏 (Conversation Redaction Protocol)**：
   - 所有存入 `conversations/raw/` 與 `conversations/summaries/` 的交談歷史，皆必須通過以下正則脫敏過濾器：
     - **API Keys / Secrets**：替換為 `[REDACTED_API_KEY]` 或 `sk-***`。
     - **密碼與 Token**：替換為 `[REDACTED_PASSWORD]`。
     - **電子郵件**：保留前 3 碼其餘遮蔽，格式如 `user***@domain.com`。
     - **個人身分證字號 / 學號**：保留前 3 碼其餘遮蔽，格式如 `411***`。
