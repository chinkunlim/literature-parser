# SPEC-010：Web Studio, PDF/EPUB Comparison, and Correction Feedback Loop

- **狀態**：Implemented
- **建立日期**：2026-10-26
- **負責模組**：`web_app.py`, `mcp_server.py`, `web_data_service.py`, `correction_service.py`, `web/`

## 1. 需求描述

為文學與教科書轉檔管線提供互動式 Web 介面與 REST API / MCP 工具，達成：
1. **全域儀表板 (Dashboard)**：呈現書籍處理進度、驗證率與錯誤統計。
2. **雙欄對照與即時編輯 (Compare & Edit)**：左側章節 PDF 預覽（可翻頁、縮放）、右側 Markdown 編輯與 EPUB 排版預覽。
3. **閉環問題反饋與回歸保護 (Correction Feedback)**：儲存修改時記錄 Unified Diff、問題分類（OCR錯字、標題、表格等）與使用者備註，並支援一鍵生成自動化回歸測試以防止後續演算法回歸。

## 2. API Contract

### 2.1 RESTful Endpoints (FastAPI)
- `GET /api/dashboard`：回傳總書目、全數完工數、章節通過率、問題修正統計。
- `GET /api/books`：回傳所有書目清單。
- `GET /api/books/{id}/chapters`：回傳該書章節結構與評分。
- `GET /api/books/{id}/chapters/{ch}/markdown`：取得章節 Markdown 內文。
- `POST /api/books/{id}/chapters/{ch}/markdown`：儲存修正 Markdown，記錄 CorrectionRecord，並觸發 EPUB 背景重打包。
- `GET /api/books/{id}/chapters/{ch}/pdf/meta`：取得 PDF 頁數資訊。
- `GET /api/books/{id}/chapters/{ch}/pdf/page/{page_num}`：回傳 PyMuPDF 即時渲染之 PNG 影像串流。
- `GET /api/books/{id}/visual-diffs`：取得視覺對照截圖樣本清單。
- `GET /api/books/{id}/epub/file`：直接下載 compiled EPUB 3。
- `POST /api/books/{id}/rebuild-epub`：手動觸發 EPUB 重建。
- `GET /api/corrections`：列出問題修正紀錄。
- `POST /api/corrections/generate-tests`：觸發生成自動化單元測試。

### 2.2 MCP Tools (`entrypoints/mcp_server.py`)
- `list_books()`
- `get_book_chapters(book_id)`
- `get_chapter_markdown(book_id, chapter_id)`
- `update_chapter_markdown(book_id, chapter_id, new_content, issue_type, user_notes, rebuild_epub, confirm: bool)`
- `rebuild_book_epub(book_id, confirm: bool)`
- `list_corrections(book_id, issue_type)`
- `generate_regression_tests(confirm: bool)`

## 3. 資料庫規範

- 路徑：`DATA_DIR/db/corrections.json`
- 綱要：每筆紀錄包含 `id` (UUID), `book_id`, `chapter_id`, `created_at`, `issue_type`, `original_text`, `corrected_text`, `diff_snippet`, `user_notes`, `applied`。
