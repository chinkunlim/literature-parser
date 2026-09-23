# 📌 會話精要總結 (Executive Summary): Research Methods 教科書轉檔與排版優化

- **會話日期**: `2026-09-17` ~ `2026-09-18`
- **會話 ID**: `74bb97d9-9bba-4680-900c-e5a79d616708`
- **對應完整對話紀錄**: [`2026-09-18-research-methods-book-conversion-transcript.md`](./2026-09-18-research-methods-book-conversion-transcript.md)
- **主題類別**: 書籍轉檔實測、章節佈局微調、表格結構與名詞解釋整合

---

## 🎯 一、 使用者核心需求
1. 清理 `output/` 資料夾後，完整運行轉檔管線處理 `inbox/Research Methods, Design, and Analysis 13th ed.pdf`。
2. 排查並修正排版瑕疵：
   - `Practice Set` 內容出現非預期突兀空行。
   - `Table 1.1`, `Table 1.2`, `Table 2.1` 格式與原書排版不符，且表格下方附註文字（如 *"A four-level measurement system..."*）被誤判為獨立正文段落。
   - `Learning Objective` 項目取消 bullet 符號。
   - `Appendix` 頁碼被當作表格數據提取，排版空格跑版。
   - 跨頁段落縫合不良問題。
3. 規範每章末尾的名詞解釋（Glossary/Key Terms）：統一提取並置於章節末尾，以列表或 Anki 卡片格式呈現。
4. 更新 `SKILL.md` 與 `README.md`，供後續 AI Agent 協同依循。

---

## 💡 二、 關鍵問題診斷與修復方案
1. **表格附註誤判為正文段落**：
   - **原因**：佈局分析器以區塊垂直間距分段，緊接表格的註解文字因缺少特定標籤被歸入正文 flow。
   - **解法**：在表格識別後增加鄰近註解探針，偵測以 `Note:`, `Source:`, `A ... system is provided...` 開頭的鄰近行，自動包裹進 `<div class="table-note">` 或 Markdown 表格註解區塊。
2. **跨頁斷句縫合 (Cross-Page Stitching)**：
   - **原因**：頁尾句號缺失或單詞斷字（hyphenation）被生硬截斷。
   - **解法**：引入文意連貫性檢測器，對頁尾末字為小寫字母、連字號 `-` 或缺少標點者，自動與次頁首段合併。
3. **章末專有名詞與 Anki 卡片抽取**：
   - **解法**：建立名詞提取過濾器，鎖定章節內的黑體專有名詞定義，於章尾生成獨立的 Key Terms 區塊與可匯入 Anki 的 TSV/Markdown 格式。

---

## 🛠️ 三、 模組異動與交付成果
- **更新模組**：
  - `src/book_processor/extractors/table_extractor.py`（表格結構與附註解析）
  - `src/book_processor/stitcher/text_stitcher.py`（跨頁語義縫合）
  - `src/book_processor/formatters/anki_exporter.py`（名詞解釋抽取）
  - `.agent/skills/book-processor/SKILL.md` & `README.md`（操作手冊同步）
- **交付檔案**：
  - `Research Methods, Design, and Analysis 13th ed` 完整章節輸出至 `output/`。
