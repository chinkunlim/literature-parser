# ISSUE-018：EPUB 3 strict XML parsing error, comment corruption, and bold-italic tag interleaving

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-26
- **Agent**：`Antigravity`
- **任務**：`TASK-048`

## 1. 現象

在電子書閱讀器（如 Apple Books、Calibre 或 EPUB 閱讀外掛）開啟新匯出的 EPUB 時，頁面無法渲染並跳出 XML 解析中斷錯誤：

- **錯誤訊息**：
  ```text
  This page contains the following errors:
  error on line 16 at column 1: internal error: detected an error in element content
  Below is a rendering of the page up to the first error.
  ```
- **重現步驟**：
  1. 將含有多破折號註解（如 `<!-- Page 1 -->` 經排版正規化後轉為 `<!— Page 1 —>`）或粗斜體相鄰標記（如 `***A**B*`）的章節匯出為 EPUB 3。
  2. 使用標準嚴格 XHTML5/XML 閱讀器開啟，即觸發解析器中斷。
- **影響範圍**：`epub_exporter.py`、`text_utils.py`、`epub_visual_auditor.py`、`markdown_updater.py`。

## 2. 根本原因

1. **排版正規化破壞 XML 註解格式**：
   - `clean_typography_artifacts` 將 `--` 轉換為長破折號 `—`，使 HTML 註解 `<!-- ... -->` 被轉寫為 `<!— ... —>`，直接違反 W3C XML 規範（XML 規定註解必須以 `<!--` 開頭、`-->` 結尾，且註解內容不得包含雙連字號或長破折號變形）。
   - Obsidian 雙向導航標籤 `<![—–-]+ OBSIDIAN_NAV_START ...>` 未被完全清理，殘留在匯出的 XHTML 中。
2. **粗斜體解析正規表示式貪婪匹配導致標籤交錯**：
   - 舊修補規則 `re.sub(r'<strong><em>(.*?)</strong>(.*?)</em>', ...)` 在面對合法巢狀標籤時跨標籤貪婪匹配，將原本正確的 XHTML 扭曲為 `<strong><em>A</em></em></strong><em><em>B</em>`。
   - 原始 Markdown 中存在 `***A**B*`、`**His Wife for a Hat***`、`**2.***Temporality.*` 等混用或相連標記，在一般替換下產生了 `<strong><em>...</strong>...</em>` 之標籤順序顛倒問題。
3. **CSS `@import` 規則被誤轉為清單標記**：
   - `clean_decorative_noise` 中的 `re.sub(r'(?m)^[ \t]*m?@\s*', '- ', text)` 誤將 `<style>` 內開頭為 `@import url(...)` 的規則替換為 `- import url(...)`。
4. **macOS 檔案系統不區分大小寫造成索引覆蓋**：
   - 在 macOS APFS 檔案系統上，書本的主題索引章節 `Index.md` 與全書圖譜索引 `index.md` 路徑衝突，鏡像複製時導致全書索引被章節內容覆蓋。

## 3. 修正或規避方式

1. **純 Python 輕量級 XHTML 標籤棧自愈器 (`XHTMLSanitizer`)**：
   - 於 `epub_exporter.py` 實作基於 `html.parser.HTMLParser` 的 `XHTMLSanitizer`，維護標籤棧（tag stack）。
   - 遇到錯位關閉時逆序出棧閉合並重新開啟對應標籤，保證 100% 符合 XML 樹狀結構；所有 void tags 自閉合 `<tag />`（`Refs: ISSUE-018`）。
2. **嚴格有序的負向環視粗斜體語法層級解析**：
   - 移除會破壞合法標籤的盲目 regex，依序使用完整三星、未閉合混用、獨立雙星與單星負向環視比對（`Refs: ISSUE-018`）。
3. **加固 XML 註解保護與標準化**：
   - 於 `text_utils.py` 的 `clean_typography_artifacts` 中優先將 `<![-—–]+` 標準化為 `<!-- ... -->` 並使用 `_stash` 隔離，避免被破折號轉換規則觸碰（`Refs: ISSUE-018`）。
   - 於 `clean_decorative_noise` 加入 `(?!import\b|media\b|keyframes\b|font-face\b|charset\b)` 負向環視保護 CSS at-rules（`Refs: ISSUE-018`）。
4. **Markdown 全量更新器 (`MarkdownUpdater`)**：
   - 於 `markdown_updater.py` 批次修復磁碟上所有 138 個 Markdown 檔案，排除 `index.md` 衝突並重新建立完整的圖譜索引與雙向導航（`Refs: ISSUE-018`）。
5. **EPUB 視覺稽核層整合 XML 檢驗**：
   - 於 `epub_visual_auditor.py` 中以 `xml.etree.ElementTree.fromstring` 逐章節校驗 XHTML，任何語法錯誤均納入缺陷檢測與閉環修復（`Refs: ISSUE-018`）。

## 4. 防回歸

- `tests/test_v42_epub_exporter.py`：驗證 `XHTMLSanitizer`、粗斜體解析層級、Void tags 自閉合與 XML 樹狀合法性。
- `tests/test_markdown_updater.py`：驗證 `clean_markdown_text` 修正 `@import`、標準化註解、清理空符號與章節索引生成。
