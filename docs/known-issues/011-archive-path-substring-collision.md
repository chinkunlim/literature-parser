# ISSUE-011：歸檔比對因專案名稱命中字串導致書籍誤入文獻

- **狀態**：Resolved
- **嚴重程度**：High
- **發現日期**：2026-10-24
- **解決日期**：2026-10-24
- **相關任務**：`TASK-044`
- **相關 ADR**：ADR-008, ADR-010

## 1. 現象與觸發條件

所有完成驗證的教科書均未移入 `input/processed/processed-books/`，而是全數被錯誤搬移至 `input/processed/processed-literature/`。

## 2. 根本原因

原歸檔邏輯使用字串包含檢查：
```python
is_lit = "literature" in str(source_path).lower()
```
因為專案本身與資料目錄全路徑名稱即為 `literature-parser`（例如 `/Users/.../projects-data/literature-parser/input/books/sample.pdf`），導致任何檔案的絕對路徑轉字串後必定包含 `"literature"`，引發 100% 的假陽性判斷。

## 3. 解決方案

改以輸入根目錄解析相對路徑，檢驗路徑組成元素是否包含獨立的 `literature` 目錄段落：
```python
p_resolved = Path(source_path).resolve()
try:
    rel = p_resolved.relative_to(app_cfg.input_dir.resolve())
    if "literature" in [part.lower() for part in rel.parts]:
        is_lit = True
except ValueError:
    pass
```

## 4. 驗證與防回歸

- 撰寫 `tests/test_archive_paths.py` 驗證書籍與文獻分流。
- 批次實測中 5 本教科書全部精準歸檔至 `processed-books/`，`processed-literature/` 無任何書籍污染。
