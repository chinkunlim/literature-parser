# 規格書：獨立 MarkdownConversionService 與三層漸進檢驗體系

- **狀態**：Implemented
- **負責模組**：`services.converter.*`, `services.verification.*`
- **相關任務**：`TASK-016`, `TASK-017`
- **最後更新**：2026-10-22

---

## 1. 需求與背景

在原系統中，「PDF 轉換為 Markdown」的邏輯分散在 `BookProcessorOrchestrator` 與 `LiteraturePipeline` 中，存在長達數百行之大型函式與模組全域變數修改（如 `_digital_pdf_mod._STYLE = ...`），不僅阻礙了多核心並發安全，也使得品質檢驗缺乏客觀的多維度量化指標。

本規格書定義：
1. 獨立可重入的 `MarkdownConversionService` 與策略模式後處理器。
2. 獨立的高畫質圖表裁切器 `ElementCropper`（包覆 Caption + Notes + 16pt 等寬 Margin）與雙軌表格呈現。
3. CSS 混合雙出（獨立 `style.css` + Markdown 檔頭嵌入 `<style>`）。
4. 三層漸進式品質檢驗體系（排版、詞語、語意）與評分引擎 `QualityInspectionEngine`。

---

## 2. 轉換服務規格 (`services.converter`)

### 2.1 強型別資料契約 (`models.py`)
- `ConversionOptions`：控制抽取圖片、裁切圖表、等寬 Margin、TOC 模式、標題補齊、CSS 產出與 Front Matter 標記。
- `CroppedElement`：記錄裁切之 Figure 或 Table 的原始 BBox、加入等寬 Margin 後之 Padded BBox、檔案路徑、Caption 與 Notes。
- `ConversionResult`：回傳轉換後之 Markdown、CSS 內容、圖片清單、裁切元素清單與執行統計。

### 2.2 策略模式後處理器 (`strategies/`)
- `BookPostProcessor`：
  - H1 標題補全與正規化（嚴格排除 `00-*` 前置頁面）。
  - 可折疊目錄 TOC 生成（`<summary>📑 Table of Contents</summary>`）。
  - 插入表格雙軌對照連結：`<p align="center"><img src="images/table_*.png" ... /></p>`。
  - 跨頁未完句連續性接合（`stitch_cross_page_continuity`）。
  - 章末 Anki 抽認卡與重點單字匯出。
- `LiteraturePostProcessor`：
  - 論文標題晉升為 H1。
  - IMRAD 結構化標題解析。
  - APA / IEEE 懸掛縮排參考文獻標準化。
  - 插入表格雙軌對照連結與 `<figure>` 渲染。

### 2.3 圖表裁切規格 (`ElementCropper`)
- 計算包含 Caption、本體與 Notes 的整體 BBox。
- 上下左右四邊等距外擴 `uniform_crop_margin_pt = 16.0`（約 5.6 mm，150 DPI 下約 33 px）。
- 以語義標籤（`figure_1.png`、`table_1.png`）存入該章節之 `images/` 目錄。

---

## 3. 三層漸進檢驗體系規格 (`services.verification`)

### 3.1 評分權重矩陣
| 維度 | 評估模組 | 核心檢查項 | 權重 |
|---|---|---|---|
| **排版維度** | `LayoutAuditor` | 標題 H1 唯一性、大綱單調性、TOC 錨點合法性、表格閉合、圖片實體存在性、頁首頁尾雜訊。 | **35%** |
| **詞語維度** | `LexicalAuditor` | 混成辭典單字覆蓋率、形態素衍生分析、連字號斷詞平滑黏合、LaTeX 公式定界符成對與統計檢定式正規化。 | **35%** |
| **語意維度** | `SemanticAuditor` | 跨頁未完句接合、雙欄流向順序性、內文引註與章末 References 交叉比對、圖表指涉完整性。 | **30%** |

### 3.2 評分與處置規則
- 總分計算：$\text{Overall} = 0.35 \times \text{Layout} + 0.35 \times \text{Lexical} + 0.30 \times \text{Semantic}$。
- 合格門檻：預設 Overall $\ge 85.0\%$ 判定為 `PASS`，否則為 `NEEDS REVIEW`。
- Safe Auto-Fix：確定性瑕疵自動修復（自動閉合標籤、清除洩漏頁首、黏合連字號、統計符號標準化）。
- 報告產出：於文件同目錄產出視覺化 `AUDIT.md` 與機器結構化 `audit_report.json`。

### 3.3 獨立 CLI 指令
```bash
python -m literature_parser.entrypoints.doc_cli verify -f path/to/chapter.md
```
可在終端機印出即時儀表板並輸出檢驗報告。
