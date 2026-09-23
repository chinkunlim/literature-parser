# 🗄️ 會話深度總結：初期書籍解析管線、OCR 引擎與 LaTeX 規範化開發

- **對應完整對話紀錄**：[2026-09-18-initial-textbook-pipeline-development-transcript.md](2026-09-18-initial-textbook-pipeline-development-transcript.md)
- **會話日期區間**：2026-09-16 至 2026-09-18
- **參與角色**：使用者 & AI Assistant
- **核心主題**：建立企業級教科書 PDF/EPUB 結構化轉檔引擎、LaTeX 數學公式尺寸統一、章節切割與 Anki 卡片匯出

---

## 📌 執行摘要 (Executive Summary)

本會話為專案創始期的核心實作階段，主要解決從原始 PDF 及 EPUB 教科書中提取高保真 Markdown 的挑戰：

1. **章節極速分割 (Chapter Splitter)**：
   - 解決痛點：不依賴 OCR 即可利用 PDF 向量樹狀目錄在數秒內切分出獨立章節 PDF。
   - 產出模組：`src/book_processor/core/splitter.py`。
2. **數學公式與 LaTeX 規範化 (LaTeX Normalization)**：
   - 解決痛點：解決 OCR 截圖式公式模糊與分數縮小（shrunk fractions）問題。
   - 決策：強制使用 `\displaystyle` 與 `\dfrac` 確保與正文字體 100% 同比例。
   - 產出模組：`src/book_processor/parsers/math_latex.py`。
3. **主動回想與 Anki 卡片自動生成**：
   - 提取頁邊術語與重要概念，自動生成可折疊抽屜與 TSV 卡片檔。
   - 產出模組：`src/book_processor/utils/anki_exporter.py`。
4. **M5 晶片高並發多核心工作池**：
   - 針對 Apple Silicon M-series 晶片特化 P-core 與 E-core 排程。
   - 產出模組：`src/book_processor/concurrency/m5_worker_pool.py`。

---

## 🔍 若需深挖細節

若需查詢當初各項公式正則表達式、排版參數調整的討論過程，請參閱詳細對話：
👉 [2026-09-18-initial-textbook-pipeline-development-transcript.md](2026-09-18-initial-textbook-pipeline-development-transcript.md)
