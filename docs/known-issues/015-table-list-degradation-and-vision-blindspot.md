# ISSUE-015：Table list/card degradation, multi-column heading intrusion, and Vision Auditor blindspots

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-25
- **Agent**：`antigravity`
- **任務**：`TASK-045`

## 1. 現象

TableParser degraded tables to bullet lists or skipped hyphenated/multi-line/left-column tables; LayoutDetector re-extracted top-of-page tables as EXHIBIT (Continued); verifier and VisualAuditor lacked deterministic table/ligature/heading checks.

- **錯誤訊息**：章節輸出中 `Table X.X` / `Table X-X` 退化為條列清單（`- ` / `1. `）、`<div class="comparison-card">` 或散落純文字，且部分標題混入雙欄正文（例如 `## 4.1 Neural Conduction ... resting membrane potential.`）或出現斷裂連字（`di ficult`, `in fluence`），但驗證器仍判定 `[PASS]`。
- **重現步驟**：解析 *Career Counseling*（連字號表格 `Table 1-1.`、置中標題表格）、*Biopsychology*（雙欄頁面左欄表格 `Table 14.1`、PDF 亂序 stream）與 *Research Methods*（多行底部對齊表頭 `Table 9.2`、`Table 16.2` 及頁頂表格 `Table 2.1`）。
- **影響範圍**：5 本書共 40+ 個表格與 98 個異常標題、1,130 處斷裂連字。

## 2. 根本原因

1. **表格退化與漏抓**：`TableParser` 舊版對單欄清單式表格與雙欄破折號表格直接輸出為 `- ` 清單或 `<div class="comparison-card">`；正則僅支援 `Table \d+\.\d+` 而漏抓 `Table 1-1.`；未先依 `(top, left)` 排序 `text_elements` 導致亂序 PDF stream 提早觸發大型標題 `break`；未處理雙欄頁左欄表格邊界與多行底部對齊表頭。
2. **頁頂表格重複渲染**：`LayoutDetector.extract_exhibits` 未接收 `already_consumed=tbl_consumed`，其頁頂 `EXHIBIT (Continued)` 啟發式規則將頁頂表格文字再次抽取為區塊引用。
3. **驗證器與 Vision Auditor 盲區**：`AccuracyVerifier` 僅將詞彙率、噪音與圖片視為硬性條件；`VisualAuditor` 每章僅抽樣固定頁碼（Page 1、首個已成功建立 `<table>` 的頁），對於根本沒產出 `<table>` 的退化表格頁完全不會抽樣，且批次多執行緒同時呼叫 Ollama Vision 時因逾時而靜默退回啟發式高分（8.5/10）。

## 3. 修正或規避方式

1. 重構 `TableParser.extract_page_tables` 與 `format_tables`，支援連字號表頭、置中表頭、雙欄左欄邊界、多行表頭合併與多行儲存格拼接，並統一以 `<table class="textbook-table">` 輸出（`Refs: ISSUE-015`）。
2. `LayoutDetector.extract_exhibits` 傳入 `already_consumed` 並排除含 `Table`/`Figure` 標題的頁頂區塊。
3. 在 `text_utils.py` 實作 `repair_broken_ligatures()`，在 `digital_pdf.py` 實作雙欄自動偵測與標題字級防呆，在 `rules.py` / `verifier.py` 新增 `check_unformatted_table_blocks`、`check_broken_ligatures` 與強化版 `check_heading_prose_intrusion`，並在 `VisualAuditor` 優先抽樣含 `Table` 卻無 `<table>` 的頁面、在 `OllamaVerifier` 加入 `_OLLAMA_SEMAPHORE` 序列化保護。

## 4. 防回歸

- `tests/test_batch_resilience_and_table_structuring.py`（`TestBatchResilienceAndTableStructuring`）。
