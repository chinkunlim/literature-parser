# 003. 呼叫外部工具與模型之核心協調器收斂至 Adapters 分層

- **狀態**：Accepted
- **日期**：2026-10-21
- **決定者**：Antigravity Agent

## 背景與問題陳述 (Context)
在專案重構為新結構時，`orchestrator`、`verifier`、`synthesizer` 與 `literature_pipeline` 因會直接發送 HTTP 請求給本地 Ollama 服務或呼叫系統行程，若置於 `services` 層會造成 `services` 逆向依賴 `adapters`，違反單向分層規則。

## 決策內容 (Decision)
將呼叫外部硬體守衛、Ollama HTTP 服務與外部工具的 `orchestrator`、`verifier`、`synthesizer` 與 `literature_pipeline` 明確定義於 `adapters` 層，`services` 僅包含純業務流程與排版演算法。

## 後果與影響 (Consequences)
- **正面影響**：完全符合架構單向分層原則（`entrypoints ➔ adapters ➔ services ➔ domain ➔ config`），代碼審查與檢查工具（`agentctl check`）順暢通過。
- **負面影響**：模組路徑調整，需更新對應測試與引用路徑。
