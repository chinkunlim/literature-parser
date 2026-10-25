# ADR-011：兩階段章節結構藍圖（Two-Pass Chapter Blueprint）、PyMuPDF+Docling 混合掃描與五大模組化渲染架構

- **狀態**：Accepted <!-- Proposed | Accepted | Superseded by ADR-NNN -->
- **日期**：2026-10-25
- **Agent**：`antigravity`
- **任務**：`TASK-046`

## 1. 背景與問題

為解決單階段逐頁猜測格式導致標題誤判與複雜表格漏抓之瓶頸，導入轉換前 ChapterBlueprintScanner（結合 PDF 次級書籤、PyMuPDF 向量幾何線條/色塊與選配 Docling TableFormer 引擎）產出 chapter_blueprint.json，並拆分為五大獨立渲染器與最終藍圖對帳檢查。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| A. 維持單階段逐頁轉換（Single-Pass），僅在既有函式內累加正則規則 | 修改幅度小 | 丟失 PDF 次級書籤（Sub-chapter Outline）與向量框線/底色色塊資訊，每頁孤立猜測標題與表格邊界，容易誤判或漏抓 |
| B. 全面改用 `MarkItDown` 或全量強制跑視覺模型（`Marker` / `Docling`）取代現有引擎 | 單一外部呼叫 | `MarkItDown` 對 PDF 僅用 `pdfminer.six` 抽純文字，完全喪失表格與雙欄排版；全頁跑重型視覺模型會使 800 頁教科書耗時逾 30 分鐘，且遺失側欄詞彙與抽認卡等教學結構 |
| C. **兩階段章節結構藍圖（Two-Pass Blueprint）＋ PyMuPDF 原生向量幾何主力 / Docling 補強外掛 ＋ 五大模組化渲染與藍圖對帳驗證** | 兼顧微秒級 2D 向量精準度與深度學習表格識別能力；轉檔前鎖定標題樹与表格分區並落地 `chapter_blueprint.json`；驗證階段可 100% 對帳預期結構與實際輸出 | 需新增 `domain/profiler/blueprint_schema.py`、`services/profiler/chapter_blueprint_scanner.py`、`adapters/parsers/docling_adapter.py` 與五大渲染器模組 |

## 3. 決策與理由

採用 **方案 C**：
1. **Pass 1（`ChapterBlueprintScanner`）**：在轉換任何章節文字前，結合 PDF 次級書籤（`doc.get_toc()`）、全章字型叢集與 PyMuPDF 向量幾何（`page.get_drawings()` 底色/框線 + `page.find_tables()`），並於純掃描檔或疑難無框線表格時支援 `DoclingBlueprintAdapter`（`docling`），產出並保存 `<chapter_dir>/chapter_blueprint.json`。
2. **Pass 2（五大模組化渲染器）**：拆分為 `HeadingBlockRenderer`、`TableZoneRenderer`、`CalloutAndExhibitRenderer`、`GlossaryAndEOCRenderer`、`ProseAndMathRenderer`，各司其職。
3. **Pass 3（`check_blueprint_compliance` 藍圖對帳）**：在 `AccuracyVerifier` 直接比對 `chapter_blueprint.json` 中的 `expected_tables` 與 `expected_headings`，確保最終 `.md` 100% 無漏轉。

## 4. 影響與代價

- **正面影響**：從根源解決標題誤判、表格漏抓與版面混亂問題，且每章皆有 `chapter_blueprint.json` 可供稽核對帳。
- **代價與注意事項**：`Docling` 外部呼叫統一收斂於 `adapters/parsers/docling_adapter.py`（符合 ADR-003 分層規則），並遵循記憶體安全閥保護。
