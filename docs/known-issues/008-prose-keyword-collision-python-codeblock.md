# ISSUE-008：自然語言關鍵字碰撞誤判為 Python 程式碼區塊

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-23
- **Agent**：`antigravity`
- **任務**：`TASK-039`

## 1. 現象

在轉檔心理學與社會學書籍（如 `Career Counseling: Holism, Diversity, and Strengths` Chapter 9）時，正文中探討社會階層的段落被錯誤包裝在 Python 程式碼圍欄（````python ... ````）中：
```markdown
```python
social class worldview model examines how individuals...
```
```
導致整篇 Markdown 被語法高亮破壞，且在品質檢驗時觸發標題與排版雜訊警報。

- **錯誤現象**：
  自然語言敘述文字被標記為 ````python```` 程式碼塊。
- **重現步驟**：
  在內文包含 "class worldview", "class context", "class differences" 等社會學術語的頁面中呼叫 `LayoutDetector.detect_code_blocks()`。
- **影響範圍**：
  包含心理學、教育學、社會學領域之數位教科書。

## 2. 根本原因

在 `src/literature_parser/services/parsers/layout_detector.py` 的代碼辨識邏輯中，`CODE_INDICATORS` 定義了過於寬鬆的正則表達式：
```python
r"\bclass\s+\w+\b"
```
其本意為捕獲 Python 類別定義（如 `class MyClass:`），但缺乏了類別名稱語法規範、可選的繼承括號 `(...)` 與標誌性的冒號 `:` 結尾。因此，自然語言中的 `class worldview` 完全滿足 `\bclass\s+\w+\b`，加上周圍換行被累計為代碼行，導致誤判。

## 3. 修正或規避方式

1. **嚴格限制程式碼指示詞語法**：
   在 `src/literature_parser/services/parsers/layout_detector.py` 將 Python 類別指示詞替換為符合 Python 語法的嚴格模式：
   ```python
   r"\bclass\s+[A-Za-z_]\w*\s*(?:\([^)]*\))?\s*:"
   ```
2. **非空行數計數防護**：
   在 `src/literature_parser/services/parsers/layout/list_parser.py` 與 `layout_detector.py` 中，要求有效代碼區塊必須至少包含 `>= 2` 個非空代碼特徵行，空白行不計入代碼行數。

## 4. 防回歸

已於單元測試 `tests/test_v53_regex_bullet_and_watermark_filters.py` 中驗證 `class worldview` 與相關片語不會被判定為代碼塊，並在 `Career Counseling` 全書 27 章節中驗證零誤判。
