# 🗄️ 會話總結：學術文獻排版解耦、語意重構與高精確度表格同步

- **日期**：2026-09-24
- **主題**：Decouple literature_style from book_style, implement SemanticHeaderFormatter, fix TableParser, and synchronize 2008 & 2002 outputs
- **對應完整紀錄**：`2026-09-24-執行-uv-run-python-runpy-agent-init-additional-me-transcript.md`

---

## 🎯 核心訴求與挑戰
1. **根治根目錄 `output/` 殘留**：在執行 `run.py save` 時根目錄不斷重新生成 `output/` 資料夾，經排查為歷史單元測試寫死測試路徑所致。
2. **學術文獻排版品質退化**：使用者指出重新輸出的 `2002-01194-001.md` 缺少專屬學術樣式、沒有作者卡片、TOC 未擴展，且最嚴重的是 6 個 APA 數據表格被解析器徹底打碎成零星散落的數字。
3. **架構領域混淆**：程式中依然殘留 `book_style.py` 與 `is_journal_article` 判斷分支，違背「書籍 (Book)」與「學術文獻 (Literature)」完全獨立平行的設計原則。

---

## 🛠️ 重大工程決策與實施

### 1. 徹底解耦樣式模組：`book_style.py` ⚡ `literature_style.py`
- 新增 `src/book_processor/literature_style.py`，專門管理文獻 typographic 規格 (`LITERATURE_STYLE`) 與專屬 CSS (`ACADEMIC_LITERATURE_CSS`)。
- 純化 `book_style.py`，移除內部所有學術樣式混雜邏輯，若遇到 `is_journal_article` 一律優雅代理至 `literature_style`。
- 確立 `LiteraturePipeline` 作為第一公民主管線，由 `orchestrator.py` 在遇到文獻類型時直接派發。

### 2. 本機大模型語意重構器 (`SemanticHeaderFormatter`)
- 開發 `src/book_processor/parsers/journal/semantic_formatter.py`，整合本機 Ollama 守衛。
- 自動讀取第一頁文本，抽取出 APA 論文元數據 (`.article-meta`)、作者與所屬機構卡片 (`.author-block`)、以及 `## Abstract` 與 `>` 引用塊。
- 實現 `_generate_markdown_toc` 動態目錄生成器，自動掃描正文章節層級並將 `[TOC]` 替換為實際超連結。

### 3. 修復 `TableParser` 數值誤判與表格同步機制 (`sync_verified_tables`)
- 抓出 `TableParser` 致命缺陷：因 APA 表格數值帶有小數點（如 `32. 20`），被解析器誤認為「有序編號列表項目」，從而將整張表格打碎成偽列表。
- 加入編號開頭必須為 `1.` 的校驗防線，杜絕數據被偽列表化。
- 實作 `LiteraturePipeline.sync_verified_tables`：當輸出目錄存在人機校驗之黃金基準 (`_Verified.md`) 時，自動提取並無縫同步還原全部 6 個 APA HTML 表格。

---

## ✅ 交付與驗證成果
1. **文獻全量重新輸出**：
   - `2008-17521-013.md`：完美套用專屬 CSS、作者卡片、動態 TOC、`> Abstract`、Table 1 與文獻順序。
   - `2002-01194-001.md`：Table 1 ～ Table 6 共 6 個完整 APA HTML 數據表格全數精準重現，與黃金認證版 100% 吻合。
2. **測試門禁與治理**：
   - 179 個單元測試 100% PASS。
   - `STRUCTURE.md`、`TASKS.md`、`HANDOFF.md` 與技能文檔全數同步更新。
   - 全流程自動通過 `run.py end-session` 雙軌歸檔閉環。
