# ISSUE-010：PDF 大綱包含尾端 Null 字元導致建檔崩潰

- **狀態**：Resolved
- **嚴重程度**：High
- **發現日期**：2026-10-24
- **解決日期**：2026-10-24
- **相關任務**：`TASK-044`
- **相關 ADR**：ADR-008

## 1. 現象與觸發條件

在執行大型數位版教科書（如 *Biopsychology, Global Edition*）批次處理時，管線在章節切分或建立章節輸出目錄時崩潰並拋出錯誤：
```text
ValueError: embedded null byte
```
導致整批次中斷無法繼續。

## 2. 根本原因

部分數位版 PDF 出版商的大綱書籤 (TOC / Outlines) 在章節標題名稱尾端夾帶 C-style 空位元組填充（例如 `'Epilogue\x00\x00\x00\x00\x00'`）。
當章節名稱未經清洗直接作為資料夾路徑呼叫 `os.makedirs()` 或 `Path.mkdir()` 時，底層作業系統系統呼叫嚴禁字串中出現空字元，引發 Python `ValueError`。

## 3. 解決方案

1. **正則字元清洗**：
   在 `services/utils/text_utils.py` 的 `sanitize_filename`，以及 `services/core/analyzer.py` 的 `get_sections`、`adapters/core/orchestrator.py` 的大綱解析層，全面加入控制字元清洗正則：
   ```python
   re.sub(r'[\x00-\x1f\x7f]', '', title).strip()
   ```
2. **檢查點自我淨化**：
   在 `services/core/checkpoint.py` 的 `_load()` 邏輯中，自動清洗歷史 manifest 殘留之含 `\x00` 鍵值，防止舊快照污染當前執行緒。

## 4. 驗證與防回歸

- 單元測試套件全通。
- *Biopsychology* 全書 31 個章節全數成功剖析切分，零崩潰順利驗證通過。
