# ISSUE-007：章末解析器鬆散正則誤吞內文並洩漏版權宣告

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-23
- **Agent**：`antigravity`
- **任務**：`TASK-039`

## 1. 現象

在解析 Cengage 等出版社的數位教科書章節（如 `Groups: Process and Practice` Chapter 1）時，章節在正文進行到一半時突然被截斷中斷，後續頁面未被收錄為本文；同時在產出的 Markdown 頁尾出現未過濾的版權雜訊行：
```text
Copyright 2018 Cengage Learning. All Rights Reserved. May not be copied...
WCN 02-200-203
```
導致該章節在驗證時觸發 `LEAKED_FOOTER` 與句子不完整錯誤。

- **錯誤訊息**：
  `QualityInvariantGuard: Chapter truncated prematurely; leaked running footer 'WCN 02-200-203'`
- **重現步驟**：
  在內文包含 `summary`（如 "In summary, the leader must..."）或非標題的 `references.` 單字頁面，執行 `EndOfChapterParser.parse_pages()`。
- **影響範圍**：
  數位版教科書 `digital-pdf` 處理流程中，正文包含章末關鍵字的小寫敘述段落。

## 2. 根本原因

1. `src/literature_parser/services/parsers/layout/eoc_parser.py` 中的章末判定使用了鬆散的正則：
   ```python
   re.compile(r"^(?:Chapter\s+)?(?:Summary|References|Key\s+Terms|Review\s+Questions)\b", re.IGNORECASE)
   ```
   且未檢查該文字片段的字級大小（font size）、粗體屬性（is_bold）或基線水平位置。當作者在段落開頭寫下 lowercase 的 `summary` 或 `references` 時，整個頁面下方及後續頁面被誤當成章末模組，導致主要內容被吞噬。
2. 此外，當頁面被提早截斷時，跳過了標準的頁尾過濾流程，使得頁底之 WCN 編號與授權聲明殘留於輸出 Markdown 中。

## 3. 修正或規避方式

1. **嚴格限制 EOC 標題屬性**：
   在 `EndOfChapterParser` 中加入幾何與樣式防護：
   - 標題文本不得全為小寫：`not txt.islower()`。
   - 字級必須大於等於標題閾值（`size >= 12`）、或者是粗體（`is_bold`）、或者是全大寫（`txt.isupper()`）。
   - 水平位置限制：該標題所在水平線上左側不得有其他正文內容。
2. **輸出端全域保險過濾**：
   在 `src/literature_parser/services/parsers/digital_pdf.py` 輸出 Markdown 前，加入全域保險過濾正則，徹底清洗 `Copyright ... Cengage Learning` 與 `WCN \d{2}-\d{3}`。

## 4. 防回歸

已於單元測試 `tests/test_v53_regex_bullet_and_watermark_filters.py` 中增加：
- `test_digital_pdf_drops_cengage_running_footer`
- `test_running_footer_filters_wcn_and_permissions`
並在 Cengage 書籍 21 個章節乾淨重跑中驗證全數通過。
