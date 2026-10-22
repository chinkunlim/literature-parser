# ISSUE-005：全域狀態掃描以字串包含比對路徑導致書籍誤判為論文

- **狀態**：🟢 已解決 (Resolved)
- **發現日期**：2026-10-22
- **Agent**：`antigravity`
- **任務**：`TASK-023`, `TASK-024`

## 1. 現象

在調用 `GlobalStateManager.sync_from_output_dir()` 重建或同步 `global_status.json` 時，所有的教科書（例如 `Research-Methods-Design-and-Analysis-13th-ed`）被全部誤歸類為 `doc_type: "literature"`，導致進度看板與 Web Dashboard 無法正確分組呈現書籍與學術論文。

- **錯誤訊息**：
  ```text
  Research-Methods-Design-and-Analysis-13th-ed (literature): status=HAS_FAILURES, progress=76%
  Group-Counseling-Strategies-and-Skills-... (literature): status=HAS_FAILURES, progress=52%
  ```
- **重現步驟**：
  在 `output/books/` 下存在已處理書籍的目錄與 `processing_status.json`，執行 `GlobalStateManager().sync_from_output_dir()`，檢查產出的 `DATA_DIR/state/global_status.json`。
- **影響範圍**：
  全域進度快照 `global_status.json`、CLI `literature-parser status` 與 Web Dashboard 儀表板。

## 2. 根本原因

在 `src/literature_parser/services/core/global_state.py` 的 `sync_from_output_dir` 中，判斷 `doc_type` 採用了子字串包含比對：
```python
doc_type = "literature" if ("literature" in str(status_json) or book_data.get("archetype") == "journal") else "book"
```
然而，專案本體名稱為 `literature-parser`，所有在 `DATA_DIR`（預設相對路徑 `../../projects-data/literature-parser/`）下的檔案路徑字串 `str(status_json)` **必然包含 `"literature"` 字串**，導致條件恆為真，所有書籍皆被強制認定為 `literature`。

## 3. 修正或規避方式

改為使用相對路徑分割之精確頂層目錄判定（`rel_parts[0]`）：
```python
rel_parts = status_json.relative_to(out_path).parts
if len(rel_parts) > 0 and rel_parts[0] == "literature":
    doc_type = "literature"
elif len(rel_parts) > 0 and rel_parts[0] == "books":
    doc_type = "book"
elif book_data.get("archetype") in ("journal", "literature"):
    doc_type = "literature"
else:
    doc_type = "book"
```
相關程式碼已於 `src/literature_parser/services/core/global_state.py` 修正完畢。

## 4. 防回歸

已於單元測試 `tests/test_v43_input_segregation_and_naming.py` 及全套測試套件中進行路徑分流與全域狀態同步驗證，確保 `output/books` 下之文件永遠為 `doc_type == "book"`。
