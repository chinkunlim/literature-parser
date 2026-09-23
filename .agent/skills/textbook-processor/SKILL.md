---
name: textbook-processor
description: Specialized sub-skill for converting academic textbooks (PDF/EPUB) into high-fidelity Markdown with chapter splitting, cross-page stitching, uniform LaTeX, and Anki flashcards.
---

# 📖 Textbook Processor Sub-Skill (長篇教科書專屬子技能)

本技能為專門處理長篇學術教科書（Textbooks）的專屬子技能，由 `document-processor` 總調度技能調派。

---

## 🎯 核心適用場景
- 來源文件：長篇多章節書籍（PDF 或 EPUB），通常大於 50 頁且包含目錄與章節結構。
- 輸入目錄：`data/input/books/<filename>`
- 輸出目錄：`data/output/books/<book_title>/`

---

## ⚙️ 專屬處理核心流程
1. **目錄解析與快速切分 (Rapid Chapter Splitting)**：
   - 解析 PDF 內嵌目錄 (TOC) 或基於正則定位 `Chapter 1`, `Chapter 2` 等標題。
   - 使用輕量 PDF 切分器秒級產出獨立章節 PDF，避免單一龐大文件造成記憶體溢出。
2. **跨頁斷句與文意縫合 (Cross-Page Stitching)**：
   - 頁尾連字號 (`-`) 與跨頁斷句自動平滑對接。
   - 避免跨頁頁碼、頁首/頁尾雜訊破壞段落連貫性。
3. **版面特色區塊抽取**：
   - 學習目標 (`Learning Objectives`)、案例對話框 (`Dialogue Block`)、教學表格。
   - 複雜表格自動啟用 HTML 原生相容標籤，保留斑馬紋與儲存格合併。
4. **主動回憶卡片與名詞解釋 (Active Recall & Anki)**：
   - 每章末尾提取黑體專有名詞定義，匯整為獨立的 Key Terms 區塊。
   - 自動生成可直接匯入 Anki 的 `<Chapter>_flashcards.tsv`。
5. **雙軌驗證與信度隔離**：
   - 檢驗詞彙覆蓋率、LaTeX 定界符平衡。
   - 遇見複雜瑕疵若信度 $< 0.80$，自動隔離至 `data/needs_review/`。
