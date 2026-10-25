# SPEC-009：自適應版面剖析、歸檔分流與批次斷點續傳規格

- **狀態**：Implemented
- **負責模組**：
  - `literature_parser.services.profiler.stage0_profiler`
  - `literature_parser.services.converter.component_registry`
  - `literature_parser.adapters.guards.resilience_guard`
  - `literature_parser.adapters.core.orchestrator`
  - `literature_parser.services.core.checkpoint`

---

## 1. 模組目標

提供教科書與學術文獻轉換之端到端自主適應、斷點續傳與物理檔案隔離能力：
1. **Stage 0 自適應版面剖析 (Autonomous Profiler)**：在正式平行轉檔前，純淨採樣第一正文章節，自動辨識多欄佈局、邊欄幾何與出版社特殊區塊。
2. **元件登錄體系 (Component Registry)**：解耦各種排版元件（Callout 提示框、統計表格、學習目標、術語邊欄）之辨識與處理策略。
3. **安全容災守衛 (Resilience Guard)**：提供記憶體不足降頻、連續失敗斷路器保護與自癒嘗試。
4. **目錄嚴格分流歸檔 (Archive Segregation)**：100% 驗證通過之書籍原檔自動歸檔至 `input/processed/processed-books/`，學術論文歸檔至 `input/processed/processed-literature/`。
5. **CLI `--resume` 斷點續傳**：已通過出版級驗收之章節自動略過，並結合實體檔案存在性檢查，杜絕多執行緒競爭與假性未完成。

---

## 2. 規格細節

### 2.1 歸檔路徑與分流邏輯
- 採用相對路徑比對 `source_path.relative_to(app_cfg.input_dir)`。
- 若路徑元素包含 `literature`，分流至 `app_cfg.processed_literature_dir`。
- 其他歸類為書籍，分流至 `app_cfg.processed_books_dir`。
- 批次與大綱發現邏輯（`discover_books` 與 `rglob`）自動過濾任何路徑包含 `processed*` 之檔案。

### 2.2 Checkpoint 原子性與實體防護
- 檢查點寫入採用 `tempfile.mkstemp` + `os.replace` 原子交換。
- `is_chapter_verified` 條件：
  - `status == "VERIFIED"`
  - `verification_pass is True`
  - `markdown_generated is True`
  - `split_pdf is True` 或磁碟實體章節 PDF 檔案存在。
- 載入歷史 manifest 時自動正則過濾 `[\x00-\x1f\x7f]` 髒資料。

---

## 3. 驗收標準與驗證成果

1. 全書庫 5 本教科書（2,431 頁、128 個章節，涵蓋數位版與神經 OCR 掃描版）100% 通過多維度出版級驗收。
2. 5 本原書全數移入 `input/processed/processed-books/`，`input/books/` 完全清空。
3. `tests/test_archive_paths.py` 等 336 項單元與整合測試全通。
