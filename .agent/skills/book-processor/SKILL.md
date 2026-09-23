---
name: book-processor
description: Enterprise-grade PDF and EPUB textbook conversion tool. Performs high-fidelity Markdown extraction with uniform LaTeX math, neural layout OCR, automated multi-metric verification, content continuity stitching, cross-book noise learning, Anki flashcard generation, and local AI review.
---

# Book Processor Skill (相容性總入口)

> 💡 本技能與 `document-processor` 保持同步相容。
> 專案現已全面分層為：
> 1. `document-processor`（總調度技能）
> 2. `textbook-processor`（教科書子技能）
> 3. `literature-processor`（學術文獻子技能）

---

## 📂 標準資料夾位置

- **輸入目錄**：
  - 書籍：`data/input/books/<filename>`
  - 學術文獻：`data/input/literature/<filename>`
- **輸出目錄**：
  - 書籍：`data/output/books/<book_title>/`
  - 學術文獻：`data/output/literature/<article_id_or_title>/`
- **瑕疵隔離區**：`data/needs_review/`

---

## 🛠️ 主動執行指引

AI Agent 接到任何轉檔需求時，直接調用終端執行：
```bash
# 轉換書籍
python run.py process data/input/books/<filename>

# 轉換學術文獻
python run.py process data/input/literature/<filename>
```
