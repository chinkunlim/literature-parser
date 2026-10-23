# ISSUE-006：跨頁插播正則巢狀量詞回溯導致處理卡死

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-23
- **Agent**：`antigravity`
- **任務**：`TASK-039`

## 1. 現象

在全書批次處理大型教科書之名詞解釋章節（如 `Research Methods: Design and Analysis` 之 `Glossary` 或長達數十頁之後置章節）時，程式在呼叫 `stitch_cross_page_continuity()` 後徹底停頓（進程佔用 100% CPU，但持續數小時無法完成）。

- **錯誤現象**：
  進程停滯在 `stitch_cross_page_continuity`，處理單一 12 頁之章節耗時超過 8.7 小時未終止。
- **重現步驟**：
  對包含大量以粗斜體開頭、短段落及跨頁插播元素的文字內容，呼叫 `text_utils.stitch_cross_page_continuity(text)`。
- **影響範圍**：
  全專案所有經由 `MarkdownConversionService` 與 `BookPostProcessor` 之後處理管線，阻斷無人值守批次處理。

## 2. 根本原因

在 `src/literature_parser/services/utils/text_utils.py` 的 `stitch_cross_page_continuity` 中，Rule 2 為了跳過跨頁插播的圖表、表格或注釋，使用了正則表達式：
```python
intervening = r"(?:(?:^|\n)(?:(?:!\[.*?\]\(.*?\)|<table[\s\S]*?</table>|\*[^*]+\*|[^\n]+)\n+))+"
```
由於 `(?:[^\n]+\n+)+` 與外層的 `(?:...)+` 存在高度重疊的巢狀貪婪量詞，在 Python 原生正則引擎（NFA）中，當遇到包含數百行密集條目、未以句號結尾或跨頁符號交錯的長文字時，嘗試在每一處斷點進行匹配失敗時會引發**災難性回溯 (Catastrophic Regex Backtracking)**，計算複雜度達到 $O(2^n)$。

## 3. 修正或規避方式

重構正則結構，消滅巢狀模糊量詞，改為以換行符為邊界的單行非重疊比對，並限制插播內容最大行數（`{1, 20}`）：
```python
intervening = r"(?:\n[^\n]+){1,20}\n"
pattern_str = rf"([A-Za-z0-9,;'\"]+)\n+<!-- PAGE:(\d+) -->({intervening})\n*([a-z][A-Za-z0-9]*\b)"
```
同時移除負向字元集中的 `\*`，允許以斜體或粗體正常結尾的段落平滑參與跨頁縫合。
修正後處理同一段長文字的時間由無窮回溯降至 **0.19 秒**。

## 4. 防回歸

已於單元測試 `tests/test_v52_unified_pymupdf_and_continuity_fixes.py` 中新增 `test_stitch_cross_page_continuity_with_bold_paragraph` 與高密度跨頁壓力測試，並在全量 4 本書 97 章節實測驗證。
