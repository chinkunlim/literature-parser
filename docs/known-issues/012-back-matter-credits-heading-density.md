# ISSUE-012：教科書 Credits 頁面因標題密度檢查誤判為未通過

- **狀態**：Resolved
- **嚴重程度**：Medium
- **發現日期**：2026-10-24
- **解決日期**：2026-10-24
- **相關任務**：`TASK-044`
- **相關 ADR**：ADR-005, ADR-010

## 1. 現象與觸發條件

在 *Biopsychology* 的章節驗證中，`Credits` 章節轉換 Markdown 順利完成，但在執行自動驗證時被標記為 `[FAILED]`：
```text
• Heading Hierarchy Density: [FAIL] (0 headings found)
Chapter Overall Accuracy: [FAILED (CHECK ISSUES)]
```
導致整本書無法進入 100% 驗證完成狀態，無法觸發自動歸檔。

## 2. 根本原因

`check_heading_density` 規範當章節字數超過 1000 字且非 front_matter / back_matter 時，至少必須包含 2 個 `##` 或 `###` 子標題。
`Credits` 頁面字數達 3,374 字（記載各圖表、照片授權清單），但 `verifier.py` 的 `is_back_matter` 僅檢查了 `glossary`, `references`, `index` 等，漏掉了 `credits`、`acknowledgments`、`appendix`、`sources` 等常見後記標題，導致判定要求過於嚴苛。

## 3. 解決方案

在 `src/literature_parser/adapters/verification/verifier.py` 中擴充 `is_back_matter` 的關鍵字清單：
```python
is_back_matter = any(bm in ch_name.lower() for bm in (
    'glossary', 'references', 'index', 'author-index', 'subject-index',
    'license', 'eula', 'agreement', 'credits', 'acknowledgements',
    'acknowledgments', 'epilogue', 'appendix', 'appendices', 'sources', 'photo-credits'
))
```

## 4. 驗證與防回歸

- 單元測試套件全數通過。
- 重新驗證 *Biopsychology* 的 `Credits` 章節，順利取得 `[SUCCESS (PASS)]`。
