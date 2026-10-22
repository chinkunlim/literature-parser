# 系統架構說明 (ARCHITECTURE)

> 本系統採用標準分層架構（Layered Architecture）結合管道-過濾器架構（Pipes and Filters）與策略模式（Strategy Pattern）。
> 分層由上而下：`entrypoints ➔ adapters ➔ services ➔ domain ➔ config`，上層可依賴下層，嚴禁逆向依賴。

---

## 1. 系統分層架構圖

```mermaid
flowchart TD
    subgraph Entrypoints ["1. entrypoints 層"]
        CLI["literature_parser.entrypoints.cli<br>(Unified CLI)"]
        RunCmd["literature_parser.entrypoints.run<br>(Command Center)"]
        DocCLI["literature_parser.entrypoints.doc_cli<br>(Subcommands Dispatcher)"]
    end

    subgraph Adapters ["2. adapters 層 (外部 I/O 與工具適配)"]
        Orchestrator["adapters.core.orchestrator<br>(Pipeline Orchestrator)"]
        LitPipe["adapters.pipelines.literature_pipeline<br>(Academic Literature Pipeline)"]
        OllamaAdp["adapters.verification.ollama_*<br>(Ollama AI Healer & Verifier)"]
        GuardsAdp["adapters.guards.*<br>(Hardware & Ollama Safety Guards)"]
        FixSynth["adapters.fixes.synthesizer<br>(Recipe Synthesizer)"]
    end

    subgraph Services ["3. services 層 (業務流程與排版解析)"]
        TextbookPipe["services.pipelines.textbook_pipeline"]
        Converter["services.converter.*<br>(MarkdownConversionService, Cropper, Strategies)"]
        Parsers["services.parsers.*<br>(digital_pdf, layout, math, epub)"]
        CfgMgr["services.config_manager<br>(Hierarchical Config)"]
        Exporter["services.exporter.epub_exporter<br>(EPUB 3 Builder)"]
        VerifyService["services.verification.*<br>(Format Auditor, Rules)"]
    end

    subgraph Domain ["4. domain 層 (純邏輯與資料模型)"]
        Advisor["domain.profiler.model_advisor<br>(Model Selection & Advice)"]
        ProfileSchema["domain.profiler.profile_schema<br>(Canonical DocumentProfile Schema)"]
    end

    subgraph Config ["5. config 層 (唯一可讀取環境變數之層級)"]
        Settings["config.settings<br>(AppConfig, DATA_DIR, 127.0.0.1)"]
        ProcConfig["config.processor_config<br>(Thresholds & Settings)"]
        Env["config.env<br>(Safe Env Accessors)"]
        Resources["config.resources<br>(Archetypes, Profiles, Publishers)"]
    end

    Entrypoints --> Adapters
    Entrypoints --> Services
    Adapters --> Services
    Adapters --> Domain
    Adapters --> Config
    Services --> Domain
    Services --> Config
    Domain --> Config
```

---

## 2. 核心處理管道與數據流向

```mermaid
flowchart TD
    %% 階段 1：輸入與安全前檢
    subgraph S1 ["階段 1：目錄結構約定與前置安全檢查 (Convention Ingestion & Pre-flight)"]
        InBooksDigital["書籍數位版 (Digital PDF)<br>DATA_DIR/input/books/digital-pdf/"] --> Ingest["目錄約定解析<br>(Convention over Config)"]
        InBooksScanned["書籍掃描版 (Scanned PDF)<br>DATA_DIR/input/books/scanned-pdf/"] --> Ingest
        InLit["期刊論文 (Literature)<br>DATA_DIR/input/literature/"] --> Ingest
        Ingest --> CLI["CLI 入口 / Watchdog<br>(run.py / doc_cli.py)"]
        CLI --> HWGuard{"硬體安全檢查<br>adapters.guards.hardware<br>(RAM ≥ 2GB, 電池/電源)"}
        HWGuard -- 資源不足 --> Abort["終止處理並記錄警告"]
        HWGuard -- 通過 --> Router{"目錄標籤直接分流<br>(無須啟發式猜測)"}
    end

    %% 階段 2：雙軌專門解析管線
    subgraph S2A ["階段 2A：教科書處理管線 (TextbookPipeline)"]
        Router -- 書籍 (Book) --> Splitter["目錄剖析與章節無損切分<br>core.splitter.PDFSplitter"]
        Splitter --> ChapterPDF["章節獨立 PDF"]
        ChapterPDF --> BookParser["版面解析<br>digital-pdf: 向量結構提取<br>scanned-pdf: Vision 神經 OCR"]
        BookParser --> BookFeatures["邊欄術語 (Glossary)<br>學習目標 (LO) / 章末總結 (EOC)<br>數學公式 (math_latex)"]
        BookFeatures --> AnkiGen["Anki 抽認卡生成<br>utils.anki_exporter"]
    end

    subgraph S2B ["階段 2B：期刊文獻處理管線 (LiteraturePipeline)"]
        Router -- 期刊/論文 (Literature) --> GutterDetect["雙欄幾何間距偵測<br>(Two-Column Gutter Detection)"]
        GutterDetect --> OrderStitch["跨欄文字流序重組<br>(Left-to-Right Column Stitch)"]
        OrderStitch --> IMRAD["IMRAD 標題晉升與作者註記"]
        IMRAD --> BibParse["參考文獻懸掛縮排解析<br>(APA / IEEE References)"]
    end

    %% 階段 3：品質檢驗與本地 AI 自我修復
    subgraph S3 ["階段 3：品質檢驗與本地 AI 自我修復 (Verification & Self-Healing)"]
        BookFeatures --> Auditor["確定性規則稽核<br>format_auditor & rules.py<br>(連續性、表格邊界、LaTeX 語法)"]
        BibParse --> Auditor
        Auditor --> ScoreCheck{"稽核評分與不變量守衛<br>QualityInvariantGuard"}
        ScoreCheck -- 驗證通過 --> OutStage
        ScoreCheck -- 格式破損 / 低信心度 --> Circuit{"斷路器檢查<br>CircuitBreaker"}
        Circuit -- 達到上限 --> Quarantine["隔離至 DATA_DIR/needs_review/<br>(附失敗原因，繼續後續批次)"]
        Circuit -- 容許修復 --> LLMGuard{"本地 AI 守衛<br>(RAM ≥ 4GB & Ollama 運行)"}
        LLMGuard -- 硬體受限 --> Quarantine
        LLMGuard -- 硬體允許 --> Healer["本地 AI 自我修復<br>adapters.verification.layout_healer<br>(Ollama 127.0.0.1:11434)"]
        Healer --> Auditor
    end

    %% 階段 4：知識匯出與多格式發布
    subgraph OutStage ["階段 4：知識匯出與多格式發布 (Export & Delivery)"]
        MarkdownOut["標準結構化 Markdown<br>DATA_DIR/output/"]
        MarkdownOut --> Obsidian["Obsidian 雙向筆記鏈結<br>utils.obsidian_linker (index.md)"]
        MarkdownOut --> EPUB["EPUB 3 封裝匯出<br>services.exporter.epub_exporter"]
        MarkdownOut --> Checkpoint["更新斷點 Manifest<br>core.checkpoint.CheckpointManager"]
    end
```

1. **實體路由與前置檢查 (Pre-flight & Routing)**：
   - 使用者透過 CLI 輸入 PDF/EPUB 檔案。
   - `adapters.guards.hardware` 進行記憶體 (RAM)、電源 (AC/Battery) 與硬碟空間檢查。
   - 根據文檔類型自動分流至書籍管道 (`TextbookPipeline`) 或期刊文獻管道 (`LiteraturePipeline`)。

2. **核心解析與版面偵測 (Layout Detection & Parsing)**：
   - `services.parsers.digital_pdf` 與 `layout_detector` 提取文字區塊、頁首頁尾雜訊過濾。
   - 識別雙欄文字流向（Two-Column Gutter Detection）、表格邊界 (`table_parser`) 與數學公式 (`math_latex`)。
   - 提取教科書學習目標、專有名詞邊欄，或文獻之 IMRAD 結構與作者註記。

3. **自我修復與驗證 (Verification & Self-Healing)**：
   - 輸出前經過 `services.verification.format_auditor` 與 `rules.py` 檢查連續性、表格對齊與 LaTeX 語法。
   - 遇到低信心度或排版破損時，若本地硬體允許，喚醒本地 Ollama 模型進行自我修復 (`ollama_healer`)。
   - 異常或需人工覆核段落隔離至 `DATA_DIR/needs_review/`，避免阻塞批次轉檔。

4. **筆記連結與多格式發布 (Export & Linking)**：
   - 產出標準 Markdown，並由 `obsidian_linker` 生成雙向導航雙鏈與全書 `index.md`。
   - 支援透過 `epub_exporter` 打包成現代化、含 MathML / LaTeX 樣式之標準 EPUB 3 電子書。

---

## 3. 資料與程式碼分離 (Data Isolation)
專案所有運算資料均存放在專案外的 `DATA_DIR`：
- `input/`：原始輸入檔案（只讀，目錄結構即配置）：
  - `books/digital-pdf/`：數位向量教科書（直接調用 XML 樣式提取，不跑 OCR）。
  - `books/scanned-pdf/`：掃描版教科書（直接調用 Vision 神經 OCR 解析）。
  - `books/`（根目錄）：未分流時相容備援（自動執行抽樣檢測）。
  - `literature/`：期刊文獻論文（預設雙欄數位論文，亦相容 `scanned-pdf/` 子目錄）。
- `output/`：轉換產物（資料夾一律禁用底線 `_`，統一以連字號 `-` 取代空格）：
  - `books/<Book-Title-With-Hyphens>/`：章節 Markdown、抽像影像、EPUB 3 與 Obsidian 雙鏈。
  - `literature/<Paper-Title-With-Hyphens>/`：結構化論文 Markdown、圖表與 EPUB 3。
- `needs_review/`：隔離待覆核內容（格式損壞且無法自我修復之頁面）
- `state/`：斷點清單與進度快照
- `logs/`：結構化日誌（`process.log`）

---

## 4. 四階設定階層與統一 Profile 規格 (Hierarchical Profiles & Schema)

本專案採四層式由粗至精的幾何與版面樣式繼承模型，並統一以強型別 `DocumentProfile` 作為領域層資料載體：

```mermaid
flowchart TD
    L1["階層 1：全局原形基準 (Archetype Defaults)<br>config/resources/archetypes/{textbook,literature}.json"]
    L2["階層 2：出版社模板與噪音規則 (Publisher Rules)<br>config/resources/publishers/{pub}.json + profiles/literature_{pub}.json"]
    L3["階層 3：跨文件共享知識 (Shared Knowledge Repository)<br>config/resources/shared_knowledge/{literature_sections,front_matter_taxonomy,pedagogical_blocks,symbol_mappings}.json"]
    L4["階層 4：個別文件實例 Profile (Instance Canonical Profile)<br>DATA_DIR/output/.../profile.json (鏡像相容 book_profile.json / document_profile.json)"]

    L1 -->|基礎排版參數| L2
    L2 -->|合併覆寫樣式| L3
    L3 -->|累積全域規則與結構分類| L4
    Auditor["格式品質稽核器 (Format Auditor)"] -.->|閉環幾何修正 (Closed-Loop Healing)<br>LEAKED_HEADER / LEAKED_FOOTER| L4
```

1. **統一檔名與向後相容**：
   - 實例輸出目錄一律將主 Profile 命名為標準 `profile.json`。
   - `ConfigManager` 與各 Parser 具備自動向後相容，讀取時優先查找 `profile.json`，缺失時自動降級讀取 `document_profile.json` 或 `book_profile.json`。
   - 寫入時同時儲存規範之 `profile.json`，並為舊有工具維護相容之鏡像檔案。

2. **強型別領域模型與排版細節 (`DocumentProfile`)**：
   - `meta` (`ProfileMetadata`)：文件分類 (`book` / `literature`)、模式 (`digital` / `scanned`)、標題、出版社與前置頁結構清單 (`front_matter_sections`)。
   - `geometry` (`ProfileGeometry`)：頁面尺寸、`header_cutoff_y`、`footer_cutoff_y`、雙欄中縫 (`gutter_split_x`)、奇偶頁非對稱結構（`PageAsymmetry`，左頁偶數頁邊欄在左、右頁奇數頁邊欄在右）與雙欄跨欄橫幅（`has_spanning_boxes`）。
   - `typography` (`ProfileTypography`)：H1/H2/H3 字級閾值、內文字級、Unicode-LaTeX 對照、首字下沉（`has_drop_caps`）與圖表標題正則（`caption_patterns`）。
   - `special_blocks` (`ProfileSpecialBlocks`)：動態教學區塊清單（`active_blocks`，如 `margin_glossary`, `dialogue`, `worked_example`, `case_study`）與對應樣式正則規則（`block_rules`）。

3. **Front Matter 獨立切分與純淨 Chapter 1 保證**：
   - 書籍大綱自動將 Cover、Title-Page、Publish/Copyright、Dedication、TOC、About-Authors、Preface 等切分出獨立 PDF（`00-01-Cover`、`00-02-Publish`、`00-07-TOC` 等）。
   - 自動向後探測並校驗真實 Chapter 1 起始頁，徹底杜絕 Chapter 1 吸收前置頁面；所有 Front Matter 均會產出獨立 `.md` 並無縫接入 Obsidian 雙鏈與 EPUB 3 目錄。
   - 全書 `profile.json` 在切分後由主進程單執行緒建立（`ensure_book_profile`），嚴格排除 `00-*` 前置頁面作為幾何樣本，消除多核心並發爭用。

4. **閉環自我修復 (Closed-Loop Layout Healing)**：
   - 當後期 Format Auditor 或本地 AI 驗證器偵測到頁首殘留 (`LEAKED_HEADER`) 或頁尾殘留 (`LEAKED_FOOTER`) 時，呼叫 `CoordinateCalibrator.adjust_geometry_from_feedback()`。
   - 動態計算並修正幾何截止線，同步重寫本機之 `profile.json` 與鏡像檔案，實現「偵測到一次排版雜訊，即全本自動校正」之閉環自我修復。

---

## 5. 獨立轉換引擎與策略模式 (MarkdownConversionService & ElementCropper)

為消除龐大管線的職責耦合與多核心轉檔時全域變數污染問題，系統將純粹轉換邏輯封裝至 `services/converter/`：

```mermaid
flowchart TD
    InPDF["輸入 PDF (章節或論文)"] --> Engine["MarkdownConversionService.convert()<br>(pdf, profile, options, strategy)"]
    Profile["DocumentProfile (4-Layer Canonical)"] --> Engine
    
    subgraph ConversionProcess ["內部轉換流水線"]
        StepImg["圖片萃取 (ImageManager)"] --> StepCrop["Figure & Table 獨立裁切 (ElementCropper)<br>(含 Caption/Notes 與等寬 16pt Margin)"]
        StepCrop --> StepParse["逐頁分流解析 (DigitalPDFParser / ScannedPDFParser)"]
        StepParse --> StepStrategy["策略語義後處理 (BookPostProcessor / LiteraturePostProcessor)"]
        StepStrategy --> StepCSS["CSS 雙出組裝 (style.css 檔案 + 檔頭 <style>)"]
    end
    
    Engine --> Result["強型別 ConversionResult<br>(markdown, css, images, cropped_elements, stats)"]
```

1. **單一職責與強型別契約**：
   - 核心轉換服務不直接進行發布或斷路隔離，專注於回傳包含 Markdown、CSS、圖片與裁切物件之 `ConversionResult`。
2. **Figure 與 Table 獨立裁切**：
   - `ElementCropper` 完整包覆 Caption、圖表/表格本體與 Notes，上下左右四邊等距外擴 `uniform_crop_margin_pt = 16.0` 呼吸邊距。
   - 表格採雙軌呈現：Markdown 保留結構化文字（供全文檢索與 AI 分析），並在該處嵌入獨立裁切圖片對照連結。
3. **CSS 混合雙出**：
   - 輸出目錄產出獨立 `style.css`，並在產出的 Markdown 檔頭自動嵌入 `<style>` 區塊，保證在任何原生預覽器中開箱即見完整排版美化效果。

---

## 6. 三層漸進式品質檢驗體系 (Three-Tier Quality Verification)

轉換完成之 Markdown 經過 `services.verification.quality_engine` 進行排版、詞語、語意三維度之階梯檢驗：

1. **第一層：確定性排版檢查 (LayoutAuditor, 佔比 35%)**：
   - 檢驗 H1 唯一性、大綱單調遞進、段落誤升標題檢測、TOC 錨點跳轉有效性、表格標籤閉合、圖片實體存在性、頁首頁尾雜訊。
   - 提供 Safe Auto-Fix（自動過濾洩漏頁首、清理孤立頁碼、閉合標籤）。
2. **第二層：詞語與符號詞法檢查 (LexicalAuditor, 佔比 35%)**：
   - 結合系統字典與領域辭典、形態素衍生分析、行末連字號斷詞平滑黏合、首字下沉破損修復、LaTeX 公式定界符成對與破碎統計檢定式正規化。
3. **第三層：雙階段語意檢查 (SemanticAuditor, 佔比 30%)**：
   - **階段 3A（確定性語意守衛）**：跨頁未完句連續性分析（頁末無標點 ➔ 次頁小寫平滑接合）、雙欄閱讀流向中斷檢測、內文引註與章末 References 交叉比對、圖表指涉完整性。
   - **階段 3B（本地 AI 深度覆核）**：評分低於門檻（預設 85%）或排版疑似破損時，按需喚醒本地 Ollama（RAM ≥ 4GB）進行深度語意審核並產出修復建議。
4. **輸出報告與獨立 CLI**：
   - 在該 Markdown 同目錄產出視覺化報告 `AUDIT.md` 與機器結構化檔案 `audit_report.json`。
   - 提供獨立 CLI 指令 `book-processor verify -f path/to/chapter.md` 供隨時體檢。

---

## 7. 原生雙引擎解析核心與流水線重疊並行 (Native Dual Engine & Concurrency)

為大幅消除舊有逐頁喚起外部 subprocess（`pdftohtml`, `pdftoppm`, `pdfseparate`）的系統進程啟動開銷，系統引入 PyMuPDF 原生雙引擎與流水線並行架構：

```mermaid
flowchart LR
    PDF["輸入 PDF"] --> Engine["PDFDocumentEngine (adapters.parsers.pdf_engine)"]
    Engine --> Mode{"引擎分流"}
    Mode -->|原生模式 (預設)| PyMuPDF["PyMuPDF 原生記憶體解析<br>(page.get_text, get_pixmap, insert_pdf)"]
    Mode -->|後備模式 (CLI 相容)| Poppler["Poppler CLI Subprocess<br>(pdftohtml / pdftoppm)"]
    
    subgraph PipelineOverlap ["Producer-Consumer 重疊流水線 (PipelinedChapterProcessor)"]
        CPUWorker["CPU 解析執行緒<br>(解析 Chapter N+1)"]
        Queue["內部緩衝佇列"]
        GPUWorker["GPU / Ollama 稽核執行緒<br>(語意稽核 Chapter N)"]
        CPUWorker --> Queue --> GPUWorker
    end
```

1. **零進程啟動開銷**：文檔只在記憶體中載入一次，直接提取文字 span 幾何資訊、向量除線與微秒級 Pixmap 記憶體切圖。
2. **流水線重疊執行**：CPU 密集之幾何解析與 GPU/Metal 密集之本地 Ollama 模型推論相互重疊，徹底消滅等待互鎖。

---

## 8. Marker 式版面輪廓分析與段落首提錨定 (Marker-Style Layout & Anchoring)

正文流向與圖表穿插策略遵循 Marker 風格之版面解構與語意錨定原則：

```mermaid
flowchart TD
    RawPages["跨頁原始文字與圖表"] --> LayoutFrame["版面輪廓骨架分析 (DocumentLayoutFrame)"]
    LayoutFrame --> ProseStitch["正文跨頁斷句平滑接合 (Sentence Healing)"]
    ProseStitch --> ParagraphBlocks["以完整段落 (\\n\\n) 為單位的純文字區塊"]
    
    ParagraphBlocks --> AnchorEmitter["語意錨定發射器 (reposition_figures_and_tables)"]
    AnchorEmitter --> Rule1["段落完整性：嚴禁句中插圖，整段結束後始掛載"]
    AnchorEmitter --> Rule2["清單塊保護：清單項目內部提圖時，待清單結束後掛載"]
    AnchorEmitter --> Rule3["同段多圖平鋪：依提及先後循序掛載"]
    AnchorEmitter --> Rule4["子圖智慧歸一：Figure 1A / 1B 對齊母圖 Figure 1"]
    AnchorEmitter --> Rule5["孤立圖表安全釋放：未被文中提及之圖表於章末集中輸出"]
    
    AnchorEmitter --> CleanMD["出版級語意 Markdown"]
```

- **表格自適應呈現**：簡單無合併儲存格的表格輸出標準 Markdown 管道表格；若偵測到表頭分組（`colspan > 1`）或儲存格跨行（`rowspan > 1`），自動轉譯為具備語意屬性的 `<table class="book-table">`，由 CSS 進行美化，結構零丟失。

---

## 9. 全專案集中外部化設定與即時重刷系統 (Unified Theme & Instant Re-Theming)

系統將所有可配置之排版與管線規則收斂至獨立設定檔 `config/theme.json`：

```mermaid
flowchart TD
    GlobalJSON["全域預設母版<br>config/theme.json (8大分區)"] --> StyleLoader["style_loader.load_theme()"]
    BookJSON["單書專屬覆寫 (選填)<br>{output_dir}/theme.json"] -.->|深層遞迴合併| StyleLoader
    Schema["IDE 規範校驗<br>config/theme.schema.json"] -.-> GlobalJSON

    StyleLoader --> ActiveConfig["統一合併後之強型別設定"]
    ActiveConfig --> CSSGen["CSS 產生器 (book_style / literature_style)"]
    ActiveConfig --> TOCGen["TOC 產生器 (layout_detector)"]
    ActiveConfig --> FastCLI["一鍵即時重刷工具<br>scripts/apply_theme.py"]
```

1. **8 大語意分區**：`typography`、`palette`、`layout`、`artifacts`、`tables`、`learning_blocks`、`navigation`、`quality`。
2. **目錄開闔與深度**：支援 `toc_mode`（`close` / `open` / `none`）、`toc_depth`（預設收錄至 H3）與自訂標題。
3. **即時重刷 CLI**：提供 `python3 scripts/apply_theme.py [書籍輸出目錄]`，於數毫秒內在已產出的 Markdown 檔中抽換 `<style>` 區塊、重刷 TOC 並生成 `style.css`，免去重新解析 PDF 的昂貴運算。

