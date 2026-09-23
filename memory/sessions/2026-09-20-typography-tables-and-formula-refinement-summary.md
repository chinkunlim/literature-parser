# 📌 會話精要總結 (Executive Summary): 排版、表格與跨頁內容語義修復

- **會話日期**: `2026-09-20`
- **會話 ID**: `cb3aa69b-509b-4784-96e1-9d645c7ff32b`
- **對應完整對話紀錄**: [`2026-09-20-typography-tables-and-formula-refinement-transcript.md`](./2026-09-20-typography-tables-and-formula-refinement-transcript.md)
- **主題類別**: 表格行斑馬紋/跨行合併解析、字體突兀粗體修復、全域語意連貫性自檢

---

## 🎯 一、 使用者核心需求
1. 檢視並修復 `Research Methods 13th ed` 第一章排版缺陷：
   - 出現兩段突兀過大、過粗（bold）的標題字體。
   - 表格識別漏字、跨行（Row Merge）未正確對齊、欄位背景色彩斑馬紋遺失。
   - 名詞解釋移到章尾的格式微調。
2. 提出關鍵洞察：**「程式除了檢查版面，更應從『內容是否有意義、是否連貫』著手」**，要求加入語意層面的內容檢驗機制。
3. 修改程式後全量重新輸出驗證。

---

## 💡 二、 關鍵問題診斷與修復方案
1. **字體突兀放大與粗體錯誤 (Typography Normalization)**：
   - **原因**：PDF 提取時某些強調標籤（Span tags）包含原書特殊的點陣或強調字重，被直接映射為 Markdown `# Heading` 或粗體，導致段落視覺失真。
   - **解法**：建立字型尺寸分佈統計，將文字大小限制在相對於本文（Body）的標準比例內，避免偽標題誤判。
2. **多行合併表格 (Complex Merged Table Handling)**：
   - **原因**：標準 Markdown Table 不支援 `rowspan` 與 `colspan`，導致複雜結構擠壓或遺失單元格文字。
   - **解法**：引入帶有 HTML 原生表格 fallback 的架構，在偵測到多行多列跨越時，自動採用相容性 HTML `<table>` 渲染，保留完整單元格數據與斑馬紋樣式。
3. **內容語意連貫性檢驗 (Semantic Continuity Linter)**：
   - **解法**：新增語義審計層，比對前後段落的詞性與標點斷句，若發現斷章取義或語義不通（如 OCR 錯亂垃圾字），自動觸發告警或本地修復。

---

## 🛠️ 三、 模組異動與交付成果
- **更新模組**：
  - `src/book_processor/extractors/text_extractor.py`（字體加權與異常標題平滑化）
  - `src/book_processor/extractors/table_extractor.py`（HTML 複雜表格 fallback）
  - `src/book_processor/verifiers/semantic_verifier.py`（語義連貫性審計）
- **交付檔案**：
  - 第一本書籍全章節重新轉換完成，驗證表格完整性與語法零報錯。
