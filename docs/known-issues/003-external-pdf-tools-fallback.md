# ISSUE-003：外部 PDF 工具 (poppler/pdfinfo/pdfimages) 缺失時之優雅降級

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-21
- **Agent**：`antigravity`
- **任務**：`TASK-011`

## 1. 現象

純環境或未安裝系統級 `poppler` (`pdfinfo`, `pdfimages`) 之主機上執行書籍或文獻解析時，流程拋出例外中斷。

- **錯誤訊息**：
  `FileNotFoundError: [Errno 2] No such file or directory: 'pdfinfo'` 或 `'pdfimages'`
- **重現步驟**：
  在未安裝 `poppler` 的乾淨環境中執行 `literature-parser process <file.pdf>`。
- **影響範圍**：
  `src/literature_parser/adapters/core/orchestrator.py` 及 `src/literature_parser/adapters/tools/image_manager.py`。

## 2. 根本原因

原有代碼預設主機已透過 `brew install poppler` 安裝 CLI 工具，直接以 `subprocess.run(["pdfinfo", ...])` 獲取總頁數，且使用 `pdfimages` 提取頁面圖片。未考慮工具缺失情況下的例外攔截與純 Python 退避機制。

## 3. 修正或規避方式

1. **純 Python PDF 頁數正則解析**：
   在 `orchestrator.py` 中增加讀取 PDF 二進制 `/Type\s*/Page[^s]` 與 `/Count\s+(\d+)` 之正則匹配，當 `pdfinfo` 執行拋出 `FileNotFoundError` 時自動無縫切換。
2. **圖像提取優雅降級**：
   在 `image_manager.py` 的 `extract_pdf_images` 中攔截 `FileNotFoundError`，記錄 warning 日誌並回傳空列表，不中斷主流程 Markdown 與數學公式解析。

## 4. 防回歸

- 單元測試覆蓋：`tests/test_v42_epub_exporter.py` 及 `tests/test_journal_conversion.py`
- 驗證各 CLI 工作流在缺少外部工具時均能正常完成。
