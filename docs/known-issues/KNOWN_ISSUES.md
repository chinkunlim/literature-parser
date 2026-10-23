# 已知問題庫 (Known Issues)

本目錄追蹤系統中已發現的重大缺陷、版面解析坑點與其根本原因。

| 編號 | 標題 | 狀態 | 嚴重程度 | 發現日期 |
|---|---|---|---|---|
| [ISSUE-001](001-two-column-and-math-shattering.md) | 雙欄學術論文排版與粉碎數學公式修復 | Open (Mitigated) | Medium | 2026-09-20 |
| [ISSUE-002](002-table-banner-and-styling.md) | 複雜色塊條幅表格撕裂與 CSS 空白 | Open (Mitigated) | Medium | 2026-09-20 |
| [ISSUE-003](003-external-pdf-tools-fallback.md) | 外部 PDF 工具 (poppler/pdfinfo/pdfimages) 缺失時之優雅降級 | Resolved | Medium | 2026-10-21 |
| [ISSUE-004](004-chapter1-bookmark-misattribution-and-front-matter-pollution.md) | Chapter 1 書籤誤標在封面導致前置頁面污染正文 | Resolved | Medium | 2026-10-22 |
| [ISSUE-005](005-global-state-path-substring-doc-type-misattribution.md) | 全域狀態掃描以字串包含比對路徑導致書籍誤判為論文 | Resolved | Medium | 2026-10-22 |
| [ISSUE-006](006-catastrophic-regex-backtracking-continuity-stitch.md) | 跨頁插播正則巢狀量詞回溯導致處理卡死 | Resolved | High | 2026-10-23 |
| [ISSUE-007](007-eoc-false-positive-and-wcn-leakage.md) | 章末解析器鬆散正則誤吞內文並洩漏版權宣告 | Resolved | High | 2026-10-23 |
| [ISSUE-008](008-prose-keyword-collision-python-codeblock.md) | 自然語言關鍵字碰撞誤判為 Python 程式碼區塊 | Resolved | Medium | 2026-10-23 |
| [ISSUE-009](009-margin-glossary-swallowing-headings.md) | 邊欄名詞解釋缺乏幾何寬度限制誤食主文大標題 | Resolved | High | 2026-10-23 |
