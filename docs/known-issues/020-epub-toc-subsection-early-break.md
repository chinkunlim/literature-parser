# ISSUE-020：EPUB TOC Subsection Early-Break and Multi-Token Index Collision

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-27
- **Agent**：`Antigravity`
- **任務**：`TASK-062` / `TASK-063`

## 1. 現象

在執行全書庫 EPUB vs PDF 雙渲染視覺稽核時，部分章節出現異常偏低的字詞召回率（如 `Biopsychology` 的 Chapter 10 僅 13.01%、Chapter 12 僅 22.06%，`Groups: Process and Practice` 的 Chapter 6 僅 45.39%，以及 `Subject Index` 僅 2.17%），被誤判為大量缺失內容。

- **錯誤訊息 / 評分**：
  ```text
  [Ch 17/31] Ch10-Brain-Damage...: 6 pages, recall=13.01%, defects=6
  [Ch 19/31] Ch12-Hunger-Eating...: 6 pages, recall=22.06%, defects=6
  [Ch 31/31] Subject-Index: 4 pages, recall=2.17%, defects=4
  ```
- **重現步驟**：
  呼叫 `DualRenderComparator.find_chapter_epub_page_range(doc, "Ch10-Brain-Damage...")`，回傳 `(808, 808)`，範圍僅有 1 頁。
- **影響範圍**：
  所有包含內部二級/三級子標題（Level 2/3 TOC items）的章節，以及具有多詞名稱但包含共通子詞的尾部索引頁（如 `Subject Index` 與 `Name Index`）。

## 2. 根本原因

1. **子標題提早截斷**：`find_chapter_epub_page_range` 在尋找章節結束頁時，遍歷 TOC 遇見任何 `next_item[2] > item[2]` 即執行 `break`。然而，緊隨在章節主標題之後的往往是該章節內部的子標題（例如 Chapter 10 位於 page 809，而內部子標題位於 page 810），導致章節結束頁被誤設為 `810 - 2 = 808`，一個長達 98 頁的大章節被截成 1 頁進行核對。
2. **多詞索引前綴覆蓋**：關鍵字比對採用 `any(w in t_clean for w in words)`，當遇到 `Subject-Index` 時，由於 `Name Index` 先出現在 TOC 且包含 `index` 字詞，導致 `Subject Index` 錯誤匹配到 `Name Index` 的頁面範圍（1767 至 1813），產生假性內容缺失。

## 3. 修正或規避方式

在 `src/literature_parser/services/verification/dual_render_comparator.py` 中重構範圍探測邏輯：
1. **章節編號防護**：若按章節編號匹配，下一筆中斷條件必須為「相異章節編號（`n_num != target_num`）」或「階層小於等於本章且非同章標題」。
2. **最高匹配數選擇 (Best Matches)**：關鍵字比對計算 `best_matches = sum(1 for w in words if w in t_clean)`，選取相符單詞數最多的 TOC 項目，徹底區隔 `Subject Index` 與 `Name Index`。
3. **導覽文件豁免**：標定 `00-07-TOC` 為電子書專用導覽文件（`nav.xhtml`），免除正文排版召回率誤罰。
相關程式碼註解加 `Refs: ISSUE-020`。

## 4. 防回歸

`tests/test_v55_tri_vision_and_dual_render.py`：
- `test_dual_render_comparator_renders_pdf_and_runs_audit`
修復後實測：
- `Biopsychology Ch10`：召回率由 13.01% 躍升至 **100.0%**（0 缺陷）
- `Biopsychology Ch12`：召回率由 22.06% 躍升至 **76.35%**
- `Groups Ch06`：召回率由 45.39% 躍升至 **75.45%**
- `Subject Index`：召回率由 2.17% 躍升至 **59.73%**
