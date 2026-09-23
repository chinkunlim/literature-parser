# ADR-0002: 書籍與期刊領域解耦與 data/ 實體目錄路由

- **日期**：2026-09-23
- **狀態**：[Status: Accepted]
- **決策者**：使用者 & Antigravity

---

## 背景與問題陳述 (Context)

使用者需要將不同類型的電子檔（書籍、學術期刊、論文）轉換為方便做筆記的 Markdown 格式（如 Obsidian 雙鏈筆記）：
1. **版面結構迥異**：書籍以多章節、單欄、深度樹狀目錄為特徵；期刊論文以雙欄排版、摘要 (Abstract)、引用文獻 (Citations/BibTeX) 為特徵。
2. **AI 自動猜測的不可靠性**：如果讓 AI 或規則去啟發式猜測檔案類型，極易發生判斷失誤，導致拿雙欄切割器去切整本教材，或拿書籍章節拆分器去處理 6 頁論文。
3. **未來的擴充需求**：未來可能還會增加投影片（Slides/PPT）、網頁剪藏等格式，程式如果未良好解耦，每次擴充都會引發嚴重的代碼回歸與衝突。

---

## 決策內容 (Decision)

1. **實體路徑即路由 (Convention-based Routing)**：
   - 在 `data/input/` 下實體劃分 `books/` 與 `journals/`。
   - 使用者將檔案丟入對應資料夾，程式透過輸入路徑直接確定調用 `BookPipeline` 或是 `JournalPipeline`，達到 100% 零猜測誤差。
2. **雙軌核心與共享基礎庫**：
   - 在 `src/book_processor/pipelines/` 徹底分離 `textbook_pipeline.py` 與 `journal_pipeline.py`。
   - 共享底層的核心 OCR、LaTeX 正規化工具與安全守衛。
3. **人機隔離防呆區 (`data/needs_review/`)**：
   - 任何無法透過自動化或 Ollama 自我修復的疑難頁面，自動拋入隔離區，主轉檔流程不停滯。

---

## 後果與影響 (Consequences)

### 正面影響 (Pros)
- 徹底消除分類猜測錯誤與 Token 浪費。
- 未來擴充新電子檔類型（如 `data/input/slides/`）時，只需新增對應適配器，既有書籍與論文程式碼完全不受影響。
- 產出目錄結構清晰，直接對接 Obsidian 筆記庫。

### 負面影響 / 限制 (Cons)
- 使用者存放檔案時需手動放至正確的子資料夾。
