---
name: literature-processor
description: Specialized sub-skill for converting academic literature (journal articles, conference papers, preprints) into high-fidelity Markdown with two-column band flow, abstract extraction, and reference parsing.
---

# 📑 Literature Processor Sub-Skill (學術文獻專屬子技能)

本技能為專門處理各類學術文獻（Academic Literature，涵蓋期刊論文 Journal Articles、會議論文 Conference Papers、預印本 Preprints、學術報告）的專屬子技能，由 `document-processor` 總調度技能調派。

---

## 🎯 核心適用場景
- 來源文件：獨立單篇學術論文（PDF），通常為 5~40 頁，具備摘要、雙欄排版、IMRAD 架構與參考文獻。
- 輸入目錄：`data/input/literature/<filename>`
- 輸出目錄：`data/output/literature/<article_id_or_title>/`

---

## ⚙️ 專屬處理核心流程
1. **單篇原子性處理 (Atomic Processing)**：
   - 不進行章節切分（No Chapter Splitting），整篇視為不可分割之學術作品。
   - 提取並結構化作者姓名、所屬機構（Affiliation）、DOI 與對應作者資訊。
2. **雙欄帶狀排版流動 (Two-Column Band Flow Engine)**：
   - 絕非傳統由上而下掃描。垂直切分左欄與右欄閱讀邊界，左欄讀畢後順序銜接右欄。
   - 針對跨欄大標題、全寬圖表（Full-width Figures/Tables），自動偵測並維持全頁寬帶狀流動。
3. **學術版面噪訊過濾 (Academic Noise Filter)**：
   - 自動識別並剔除 APA、IEEE、Elsevier、Springer 等出版社之頁緣浮水印、版權聲明與重複頁首頁尾。
4. **IMRAD 標題解析與參考文獻解析 (Hanging-Indent References)**：
   - 規範化 Introduction, Method, Results, Discussion 等核心區塊層級。
   - 專屬懸掛縮排解析器：結構化解析 `[1]`, `(Smith et al., 2020)` 等參考文獻清單為清晰 Markdown 列表。
5. **學術排版 CSS 注入**：
   - 自動嵌入 `<style>` 樣式（Times New Roman 字型、兩端對齊、論文表格邊界優化）。
6. **出版商專屬噪訊萃取 (Publisher-Specific Pattern Extraction)**：
   - 從 `config/publishers/<apa|elsevier|...>.json` 載入 `author_note_patterns`、`footer_noise_patterns` 與 `table_note_patterns`。
   - APA：從雙欄底部正確萃取 Author Note、Correspondence、Acknowledgments，不再混入正文。
   - Elsevier：過濾 ScienceDirect banner、`* Corresponding author`、copyright 行。
7. **表格附注綁定 (Table Note Bonding)**：
   - `Note.`、`BART indicates`、`*p <` 等 APA 表格附注自動與上方 Markdown 表格綁定，防止跨頁漂移。
8. **OCR 統計符號修復 (OCR Stat Heal)**：
   - 修正 APA/Elsevier OCR 常見亂碼：`p o 0 01` → `$p < 0.01$`、`r = 0$ 82` → `$r = 0.82$`、`r 2003` → `© 2003`。
9. **自癒與隔離機制**：
   - LaTeX 數學公式（如統計統計值 $F(1, 24) = 4.32, p < .05$）標準化修復。
   - 遇異常或信度 < 0.80，自動隔離至 `data/needs_review/`。

---

## 🏗️ 技術架構摘要

```
orchestrator.py (detect_archetype='journal')
  └──► LiteraturePipeline.process()        [pipelines/literature_pipeline.py]
         └──► JournalPipeline.process()    [pipelines/journal_pipeline.py] (繼承基礎管線)
               ├── ConfigManager.load_hierarchical_config(archetype='literature')
               │     └── config/archetypes/literature.json  (原 journal.json)
               │     └── config/publishers/<publisher>.json (author_note_patterns 等)
               ├── DigitalPDFParser.parse_page_to_markdown()
               │     └── LayoutDetector.separate_footnotes()
               │           (載入 _STYLE['_publisher_config'] 動態萃取 Author Note)
               ├── IMRADResolver.resolve_structure()
               │     ├── _bond_table_notes()
               │     └── _fix_ocr_stats()
               ├── SemanticHeaderFormatter.format_header() (Ollama 語意重構作者群、TOC超連結、> Abstract)
               ├── LiteraturePipeline.sync_verified_tables() (高精確度 APA 數據表格同步還原)
               ├── ReferenceParser.clean_document_references()
               └── literature_style.build_literature_css() (獨立專屬學術樣式注入)
         └──► LiteraturePipeline 子類型後處理 (IEEE/preprint 擴充)
```

- 樣式模組：`src/book_processor/literature_style.py` (與 `book_style.py` 徹底解耦)
- 解析子模組：`src/book_processor/parsers/literature/` (原 `parsers/journal/`，已遷移)
- `parsers/journal/` 保留為向後相容 shim（自動轉導至 `parsers.literature`）
- 輸出檔案：`document_profile.json`（非 `book_profile.json`）
