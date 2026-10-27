# SPEC-011：三視覺模型全頁雙渲染並排交叉審查規格

- **狀態**：Implemented
- **日期**：2026-10-27
- **相關任務 / ADR**：TASK-062 / ADR-014

## 1. 目標

建立出版級的雙向渲染並排對比能力。將產出之 EPUB 3 與原始章節 PDF 同步渲染為 150 DPI 高解析度 PNG 畫面，透過原生 Apple Vision OCR、本地 MiniCPM-V 2.6 與多模態視覺模型進行字詞召回率（Word Recall）與排版瑕疵（Layout Defect）逐頁深度比對，確保轉檔內容無缺失、排版無撕裂。

## 2. 使用情境

1. **品質驗收 (Gate 2)**：在書籍產出 EPUB 3 後，自動化執行全書或抽樣雙渲染畫面比對。
2. **Web Studio 對照展示**：在 Web 介面並排檢視 PDF 原始頁與 EPUB 渲染頁，並視覺化標記字詞差異。
3. **離線與 CI/CD 稽核**：透過 CLI 工具 `python3 scripts/run_visual_cross_audit.py` 無人值守運行全書庫交叉審查。

## 3. 需求

- **必須 (Must)**：
  - 支援原生 Apple Vision Framework 呼叫（macOS Swift VNRecognizeTextRequest），執行速度需小於 0.1s/頁。
  - 支援 EPUB 3 TOC 結構解析與章節頁面範圍鎖定。
  - 支援動態擴展比率視窗映射（$R = \text{EPUB頁數} / \text{PDF頁數}$），聚合視窗內字詞流。
  - 支援本地 Ollama MiniCPM-V 2.6 排版瑕疵（標題陰影、雙欄重疊、撕裂）扣分檢測。
  - 支援自適應模型降級（若特定架構如 mllama 500 時優雅略過，不中斷流水線）。
- **可選 (Nice to have)**：
  - `--stride` 步長參數，支援 1（全密集逐頁）至 10（快速抽檢）。
  - 自動生成 JSON 結構化審查報告至 `$DATA_DIR/evals/visual_audit/<book>/`。
- **不做 (Out of scope)**：
  - 不引入第三方付費雲端 OCR API。

## 4. 介面 / API

### 4.1 CLI 介面
```bash
uv run --offline python scripts/run_visual_cross_audit.py [--stride N] [--book FILTER] [--max-chapters M]
```

### 4.2 模組 API
- `AppleVisionAuditor.extract_page_ocr(image_path: Path) -> Dict[str, Any]`
- `DualRenderComparator.cross_audit_chapter(chapter_name, pdf_path, epub_path, eval_dir, sample_stride) -> Dict[str, Any]`
- `VisualCrossAuditOrchestrator.audit_book(book_dir, sample_stride, max_chapters) -> Dict[str, Any]`

## 5. 驗收標準

- [x] Apple Vision 橋接腳本正常執行並以 JSON 輸出幾何邊界與字詞流。
- [x] 正文章節在動態重排版視窗下之字詞召回率達 75% 以上（實測達 80%~95%）。
- [x] MiniCPM-V 正確檢測排版扣分項目（標題陰影 -10、雙欄撕裂 -20、重疊 -25）。
- [x] 遭遇不相容 VLM 模型時自動略過並記錄降級，不拋出例外崩潰。
- [x] 單元測試 `tests/test_v55_tri_vision_and_dual_render.py` 全數通過。

## 6. 未決問題

- 無。
