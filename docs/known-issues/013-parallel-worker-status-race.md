# ISSUE-013：多 Worker 平行回寫狀態導致 split_pdf 旗標覆蓋

- **狀態**：Resolved
- **嚴重程度**：Medium
- **發現日期**：2026-10-25
- **解決日期**：2026-10-25
- **相關任務**：`TASK-044`
- **相關 ADR**：ADR-006, ADR-010

## 1. 現象與觸發條件

在 Apple M5 多核心平行處理章節時，特定章節已經轉換完成且驗證通過（`status: VERIFIED`、`verification_pass: True`、`markdown_generated: True`），但其 `split_pdf` 欄位值卻為 `False`，導致 `is_chapter_verified` 判定為未完成，無法觸發整本書籍的自動歸檔。

## 2. 根本原因

在多個 Worker 進行並發處理時：
1. 主進程或 Worker A 建立章節 PDF 並更新 `split_pdf=True`。
2. 同時運行的 Worker B 在完成自己的章節後讀取 `processing_status.json`（此時記憶體快照可能未包含 Worker A 剛寫入的最新改動），並將整體狀態快照重寫回磁碟，產生短暫的屬性覆蓋競爭。
3. `is_chapter_verified` 先前過度依賴 JSON 中的 `ch.get("split_pdf")` 單一布林值。

## 3. 解決方案

1. **實體磁碟存在性防護**：
   在 `CheckpointManager.is_chapter_verified` 中，除了檢查 JSON 旗標外，直接檢驗磁碟上章節 PDF 檔案是否實體存在：
   ```python
   ch_dir = self.book_dir / "chapters" / chapter_name
   pdf_exists = (ch_dir / f"{chapter_name}.pdf").exists() if ch_dir.exists() else False
   has_pdf = bool(ch.get("split_pdf") or pdf_exists)
   ```
2. **章節轉換更新點顯式註記**：
   在 `orchestrator.convert_single_chapter` 完成回寫狀態時，明確帶入 `split_pdf=True`，確保即使發生平行回寫亦不會遺失該屬性。

## 4. 驗證與防回歸

- 單元測試套件全通。
- 全書庫 5 本書重測中，所有 128 章節之驗證狀態均精確判定，未再出現假性未完成。
