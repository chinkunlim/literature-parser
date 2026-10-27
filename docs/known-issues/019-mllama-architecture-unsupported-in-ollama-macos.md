# ISSUE-019：Ollama macOS mllama Architecture Unsupported for Llama 3.2 Vision

- **狀態**：🟡 已規避 (Mitigated)
- **發現日期**：2026-10-27
- **Agent**：`Antigravity`
- **任務**：`TASK-062`

## 1. 現象

在 macOS 上執行本地 Ollama 服務時，呼叫 `llama3.2-vision:11b` 會拋出 HTTP 500 錯誤，底層 `llama-server` 終止。

- **錯誤訊息**：
  ```json
  {"error":"llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'"}
  ```
- **重現步驟**：
  ```bash
  ollama pull llama3.2-vision:11b
  curl -s http://127.0.0.1:11434/api/generate -d '{"model": "llama3.2-vision:11b", "prompt": "hi", "stream": false}'
  ```
- **影響範圍**：
  所有依賴 Ollama 內建 `mllama` 架構的模型（包括 Llama 3.2 Vision 11B）。

## 2. 根本原因

macOS 上運行的 Ollama 服務（v0.40.11）其打包的 `llama-server` 二進制檔尚未將 `mllama` 模型架構編譯進去，導致嘗試加載 Llama 3.2 Vision GGUF 權重時，`llama.cpp` 無法識別架構而崩潰。相比之下，`minicpm-v:latest` 與 macOS 原生 Apple Vision OCR（Swift `VNRecognizeTextRequest`）運作正常且具備完整的硬體加速。

## 3. 修正或規避方式

在 `EpubVisualAuditor` 中加入架構錯誤快篩與自適應容錯（`_model_failed` 標記）。當模型首次呼叫回傳 500 或未知架構錯誤時，自動停用該模型並優雅切換為 Fallback，避免每次驗證重複拋錯中斷流程。視覺審查核心採用本機原生 **Apple Vision OCR** + **MiniCPM-V 2.6** 雙重驗證。
相關程式碼註解加 `Refs: ISSUE-019`。

## 4. 防回歸

`tests/test_v55_tri_vision_and_dual_render.py`：
- `test_apple_vision_auditor_availability`
- `test_compare_rendered_pages_coverage_calculation`
- `test_dual_render_comparator_renders_pdf_and_runs_audit`
