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
| [ISSUE-010](010-pdf-outline-embedded-null-bytes.md) | 🟢 已根治 (Resolved) | PDF 大綱包含尾端 Null 字元導致建檔崩潰 | Biopsychology 大綱書籤夾帶 \x00，在 os.makedirs 時拋出 ValueError: embedded null byte | TODO |
| [ISSUE-011](011-archive-path-substring-collision.md) | 🟢 已根治 (Resolved) | 歸檔比對因專案名稱命中字串導致書籍誤入文獻 | 資料目錄名稱 literature-parser 導致 is_lit 判斷一律命中，書籍誤歸檔至 processed-literature | TODO |
| [ISSUE-012](012-back-matter-credits-heading-density.md) | 🟢 已根治 (Resolved) | 教科書 Credits 頁面因標題密度檢查誤判為未通過 | Credits 超過 1000 字且未列入 is_back_matter 豁免，導致 check_heading_density 判定未達標題密度 | TODO |
| [ISSUE-013](013-parallel-worker-status-race.md) | 🟢 已根治 (Resolved) | 多 Worker 平行回寫狀態導致 split_pdf 旗標覆蓋 | 平行處理章節時因並發寫入 processing_status.json，短暫將 split_pdf 覆蓋為 False 導致假性未完成 | TODO |
| [ISSUE-014](014-xml-control-bytes-and-rotated-landscape-tables.md) | 🟢 已根治 (Resolved) | Unescaped XML control bytes (\x02) and 90-degree rotated landscape tables drop or scramble PDF pages | Custom vector symbol fonts emit raw ASCII control bytes (0x02) that crash ET.fromstring and silently drop 88 pages across Biopsychology and Research Methods; 90-degree rotated pages (dir=(0,-1)) scramble landscape tables like Career Counseling Table 2-1. | TODO |
| [ISSUE-015](015-table-list-degradation-and-vision-blindspot.md) | 🟢 已根治 (Resolved) | Table list/card degradation, multi-column heading intrusion, and Vision Auditor blindspots | TableParser degraded tables to bullet lists or skipped hyphenated/multi-line/left-column tables; LayoutDetector re-extracted top-of-page tables as EXHIBIT (Continued); verifier and VisualAuditor lacked deterministic table/ligature/heading checks. | TODO |
| [ISSUE-016](016-mermaid-arrow-corruption-eoc-profile-overwrite-and-hyphen-table-collision.md) | 🟢 已根治 (Resolved) | Mermaid Arrow Corruption, Profile EOC Pattern Overwrite, and Hyphenated Table ID Collision | clean_typography_artifacts corrupted Mermaid --> arrows and Markdown table \| --- \| dividers; DocumentProfile.to_dict() overwrote textbook eoc_heading_patterns; FigureFormatter dropped hyphenated tables (Table 1-1); VectorFigureParser cropped 182 bogus diagram_p* images. | TODO |
| [ISSUE-017](017-epub-gfm-table-mermaid-svg-and-two-col-soft-hyphen-healer.md) | 🟢 已根治 (Resolved) | Pure-Python EPUB exporter missing GFM pipe table & Mermaid SVG conversion, plus 2-column P1 header interleaving and U+00AD soft-hyphen artifacts | MarkdownToXHTML emitted raw GFM pipe tables and raw Mermaid code in EPUB; DigitalPDFParser forced single-column on top 45% of 2-column front-matter pages; U+00AD soft hyphens and orphan ** markers remained in Markdown. | TODO |
| [ISSUE-018](018-epub-xml-parsing-corruption-and-tag-interleaving.md) | 🟢 已根治 (Resolved) | EPUB 3 strict XML parsing error, comment corruption, and bold-italic tag interleaving | clean_typography_artifacts corrupted XML comments with em-dashes (<!— Page 1 —>); greedy bold/italic regex created mismatched tags; clean_decorative_noise turned @import into - import; macOS APFS collided Index.md with index.md | High | 2026-10-26 |
