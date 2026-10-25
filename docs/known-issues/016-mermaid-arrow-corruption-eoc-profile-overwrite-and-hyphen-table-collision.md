# ISSUE-016：Mermaid Arrow Corruption, Profile EOC Pattern Overwrite, and Hyphenated Table ID Collision

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-26
- **Agent**：`Antigravity`
- **任務**：`TASK-047`

## 1. 現象

使用者抽檢 5 本教科書的 Markdown 輸出時發現 6 個具體排版與語法缺陷：
1. **Mermaid 語法報錯**（`Research Methods` 全書 17 章）：`Error: Lexical error on line 3. Unrecognized text. ...["Characteristics"] —> N13["Empirical"]-----------------------^`。
2. **章末小標題與 `Key Terms` 格式失效**（`Research Methods`）：`Related Internet Sites`、`Key Terms and Concepts`、`Practice Test`、`Challenge Exercises` 未被識別為章末小標題，且 `Key Terms` 多欄表格退化為散亂段落或 `| — |` 無效表格分隔線。
3. **無意義圖片隨機出現**（`Groups` 134 張、`Research Methods` 39 張等共 182 張 `diagram_pXX_XX.png`）：在目錄頁、版權頁或一般列表下方突然出現局部文字截圖。
4. **複雜表格漏失或欄位錯位**（`Career Counseling`）：`Table 1-1`、`Table 9-1`、`Table 16-1` 消失並被 `Table 1-2`、`Table 9-2`、`Table 16-2` 覆蓋；`Table 2-1` 第一欄 `Realistic` 空白；多行儲存格被拆成數十列獨立 `<tr>`。
5. **跨行標題被拆成兩行**：超過 70 字元或不含小寫介系詞開頭的雙行標題被拆成兩個獨立 `#` 標題或「標題 + 內文碎片」。

## 2. 根本原因

1. **`clean_typography_artifacts()` 未保護程式碼區塊與表格分隔列**：`text_utils.py` 全域執行 `re.sub(r'---', '—', text)` 與 `re.sub(r'--', '—', text)`，把 ```` ```mermaid ```` 內的 `-->` 改壞成 `—>`，並把 Markdown 表格分隔列 `| --- |` 改壞成 `| — |`。
2. **`DocumentProfile.to_dict()` 覆蓋 `eoc_heading_patterns`**：`profile_schema.py` 的 `ProfileSpecialBlocks.eoc_heading_patterns` 預設僅有 4 個期刊標題（`References`, `Author Note`, `Summary`, `Review Questions`）。當 `orchestrator.py` 將 `DocumentProfile.to_dict()` 存回 `profile.json` / `book_profile.json` 時，洗掉了教科書原本的 `Key Terms and Concepts`、`Related Internet Sites`、`Practice Test`、`Challenge Exercises` 規則。
3. **`FigureFormatter.reposition_figures_and_tables()` 不支援連字號表格編號**：`figure_formatter.py` 的表格編號正則 `\d+[\.\d]*` 遇到 `Table 1-1` 與 `Table 1-2` 時都只擷取到 `tbl_id = "1"`，導致 `tbl_dict["1"]` 用 `Table 1-2` 覆蓋刪除了 `Table 1-1`（同理刪除了 `Table 9-1`、`Table 16-1`），並把 `**Table 1-2**` 的前導 `**` 留在原地。
4. **`VectorFigureParser` 無標題截圖啟發式過於寬鬆**：`vector_figure_parser.py` 只要遇到冒號 `:` 結尾且下方 200pt 內有 4 個短字串（包含頁碼、選項或縮寫），就自動截圖為 `diagram_pXX_XX.png`。
5. **`TableParser` 左邊界 `115pt` 限制與多行儲存格未垂直聚類**：`Table 2-1` 的置中標題 `left=178.9` 與第一欄 `Realistic` (`left=60.0`) 差距 `118.9pt > 115.0pt`，導致第一欄被裁切；且多欄表格未將同一儲存格內的換行文字合併至同一個 `<td>`。

## 3. 修正或規避方式

- 在 `text_utils.py` (`clean_typography_artifacts`) 中先遮罩保護 fenced code blocks 與 Markdown 表格分隔列（`Refs: ISSUE-016`）。
- 在 `profile_schema.py` 與 `style_loader.py` 補齊完整教科書 `eoc_heading_patterns` 並以聯集合併（`Refs: ISSUE-016`）。
- 在 `figure_formatter.py` 支援連字號與 `(Continued)` 表格編號，消除覆蓋與 `**` 截斷（`Refs: ISSUE-016`）。
- 在 `vector_figure_parser.py` 移除無標題隨機截圖啟發式，並清理 182 張 `diagram_p*.png`（`Refs: ISSUE-016`）。
- 在 `table_parser.py` 放寬置中表格標題左邊界偵測、實作多行儲存格垂直合併與 `Box 9-1~9-6` 內嵌表格解析（`Refs: ISSUE-016`）。
- 在 `digital_pdf.py`、`layout_healer.py` 與 `rules.py` 強化跨行標題縫合與 Mermaid / 表格 / EOC 硬性驗證。

## 4. 防回歸

- `tests/test_spotcheck_defects_and_visual_audit.py`：涵蓋 Mermaid `-->` 保護、`Key Terms` / `Related Internet Sites` EOC 解析、連字號表格 `Table 1-1` & `Table 1-2` 錨定、無標題 `diagram_p*` 抑制、`Table 2-1` / `Table 1-1` / `Table 9-1` 複雜表格解析與跨行標題縫合測試。
