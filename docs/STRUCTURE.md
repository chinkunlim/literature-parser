# 🗺️ docs/STRUCTURE.md (專案目錄地圖與功能備註)

> 📌 **版本類型說明**：
> - **【完整詳細版】（Comprehensive Detailed Map - 即本檔案）**：全景詳盡列出專案中**每一個資料夾與關鍵檔案**的具體職責、功能定義、依賴關係與架構備註。未來新增或重構檔案時，必須以此檔案為唯一權威依據進行同步更新。
> - **【精簡摘要版】（Summary / High-level Overview）**：請參閱 [`README.md`](file:///Users/limchinkun/Desktop/books/README.md) 或 [`OPERATIONS.md`](file:///Users/limchinkun/Desktop/books/OPERATIONS.md)，提供 30 秒快速冷啟動之高階目錄摘要。

---

## 一、 專案完整目錄樹結構 (Complete Directory Tree)

```text
books-project/
│
├── .git/hooks/pre-push             # 🛑 [Git安全鎖] 攔截一切未經授權的 git push，確保 Local-Only (ALLOW_PUSH=1 解鎖)
├── .gitignore                      # 🙈 排除 scratch/, logs/, data/state/, .env, __pycache__, *.tmp.* 等暫存
├── pyproject.toml                  # 📦 現代 Python 打包、依賴管理與工具配置 (ruff, mypy, pytest)
├── .env.example                    # 🔑 12-Factor 環境變數配置範本 (嚴禁提交真實 .env)
│
├── README.md                       # 📖 [專案總覽 - 摘要版] 專案定位、核心特點與快速介紹
├── OPERATIONS.md                   # 🚀 [冷啟動指南 - 摘要版] 30秒喚醒、Top 常用指令、同步時機矩陣、疑難排除
├── AGENTS.md                       # 🤖 [跨Agent憲法] 意圖指令路由表、核心鐵律、六大黃金同步矩陣、防重構標準
├── CHANGELOG.md                    # 📜 [版本日誌] 紀錄歷史與里程碑變更 (語意化版號 + 具體日期)
├── PROJECT_INIT_STANDARD.md        # 🌟 [通用標準] 30大核心鐵律、雙層規範、開案一鍵初始化檢查清單
├── run.py                          # 🛠️ [總指揮中心] 極簡 CLI 派發器 (<200行)，所有指令派發至 src/cli/*
│
├── .agent/skills/                  # 🧠 [技能分層架構] (Agent Skills)
│   ├── document-processor/         # 👑 [總調度技能] 環境健檢、文檔特徵感知、子技能派發、雙軌審計
│   │   └── SKILL.md
│   ├── textbook-processor/         # 📖 [領域子技能] 長篇教科書、章節切分、文意縫合、Anki 卡片
│   │   └── SKILL.md
│   └── literature-processor/       # 📑 [領域子技能] 學術文獻、雙欄帶狀流動、摘要與參考文獻解析
│       └── SKILL.md
│
├── memory/                         # ⚡ [動態記憶層] (追蹤當前狀態、交接與歷史精華)
│   ├── TASKS.md                    # 📋 當前 Sprint 任務進度看板與驗收狀態 (標註 [YYYY-MM-DD])
│   ├── HANDOFF.md                  # 🪪 離席交接卡片 (去上課前 1 分鐘更新，下個 AI 接手點)
│   └── sessions/                   # 🗄️ 全歷史對話雙軌歸檔 (Summary + Transcript 配對封存)
│
├── docs/                           # 🏛️ [靜態工程資產] (提交 Git 的永久規範與歷史資產)
│   ├── STRUCTURE.md                # 🗺️ [即本檔案 - 完整詳細版] 全景檔案地圖與每個模組的功能備註
│   ├── CODING_RULES.md             # 🛡️ 開發守則（雙層架構：第一部通用基線 + 第二部領域擴充）
│   ├── ARCHITECTURE.md             # 🏗️ 系統總體架構圖、數據流向與 Dashboard 設計
│   ├── ISSUES_ARCHIVE.md           # 📜 歷史排版議題與品質分析深度存檔
│   ├── OPTIMIZATION_PROPOSAL.md    # 💡 歷史微模組優化與 M5 硬體架構 RFC 提案存檔
│   └── adr/                        # 📜 架構決策紀錄 (ADR)
│       ├── 0001-ollama-hardware-guard-and-auto-verify.md
│       └── 0002-domain-split-book-and-paper.md
│
├── scratch/                        # 🧪 [臨時實驗室] 一次性測試腳本，不入 Git，保持代碼庫純淨
├── logs/                           # 📋 [診斷日誌] 結構化詳細日誌輸出 (Where + Why + How)
│
├── data/                           # 📥 [資料流核心] 雙軌實體路由與隔離防呆
│   ├── input/                      # 原始待處理實體檔案
│   │   ├── books/                  # 📚 專門存放長篇書籍 (PDF/EPUB) ➔ 自動啟動書籍管線
│   │   └── literature/             # 📑 專門存放學術文獻/論文 (PDF) ➔ 自動啟動雙欄文獻管線
│   ├── output/                     # 產出的筆記型 Markdown
│   │   ├── books/                  # 輸出按章節切分之 Obsidian 筆記
│   │   └── literature/             # 輸出含 Abstract、雙欄還原與文獻之論文筆記 (document_profile.json)
│   ├── needs_review/               # 🚨 [人機隔離區] 遇疑難公式或壞頁自動存於此，不卡死主程序
│   └── state/                      # 💾 斷點續傳快照、TOC 預覽與 Dashboard 狀態
│
├── tests/                          # 🧪 [自動化測試體系] (229 個單元測試 100% PASS)
│   ├── __init__.py                 # 動態注入 sys.path，確保任何環境直跑 unittest/pytest
│   └── test_*.py                   # 27 個測試檔案，平坦結構於 tests/ 頂層
│
├── src/                            # 💻 [業務核心原始碼] (Clean Architecture)
│   ├── cli/                        # 🎛️ [CLI 領域模組] 拆分自原 1,820 行 run.py (< 500行規範)
│   │   ├── __init__.py             # 統一匯出所有 CLI 函式
│   │   ├── common.py               # 根路徑動態錨定、過期暫存清理、文檔時間戳同步
│   │   ├── cli_audit.py            # cmd_audit: 排版格式全維度稽核與 AI 複核
│   │   ├── cli_fix.py              # cmd_fix: 修復手冊清單、套用、沙盒測試與 Ollama 合成
│   │   ├── cli_git.py              # cmd_agent_init, save, handoff, end-session, publish, archive-sessions
│   │   ├── cli_process.py          # cmd_process, batch: 單檔與批次轉檔管線派發
│   │   └── cli_project.py          # cmd_doctor, watchdog, init-project, obsidian-link, status, dashboard
│   │
│   ├── guards/                     # 🛡️ [守衛防線]
│   │   ├── hardware.py             # RAM/電池/SSD/MPS 檢測防線 (支援電源感知與 macOS memorystatus_vm_pressure)
│   │   ├── ollama_guard.py         # Ollama 連線探活、自動背景喚醒與純規則優雅降級
│   │   ├── prompts.py              # 📝 [PromptRegistry] 專案統一強型別固定提示詞中樞 (12 大提示詞)
│   │   └── validator.py            # 輸入 JSON 比對與輸出異常自動喚醒 Ollama (信度 < 0.80 自動隔離)
│   │
│   ├── utils/                      # 🛠️ [通用工具]
│   │   └── logger.py               # 結構化診斷日誌工具 (Where + Why + How)
│   │
│   └── doc_processor/              # ⚙️ [文檔處理核心引擎] (教科書與學術文獻一體化架構)
│       ├── book_style.py           # 📖 教科書專屬排版樣式表 (紫李主題、Anki 閃卡、學習目標)
│       ├── literature_style.py     # 📑 學術文獻專屬排版樣式表 (APA 三線表、作者卡片、期刊元數據)
│       ├── style_loader.py         # 樣式表動態載入器
│       ├── config.py               # 引擎全局設定常數
│       ├── cli.py                  # doc-processor 子命令行入口
│       ├── profiles/               # 📐 版面設定檔 (全數統一為 literature_*.json 與 publisher_*.json)
│       │
│       ├── pipelines/              # [管線層]
│       │   ├── textbook_pipeline.py    # 長篇書籍章節切分管線
│       │   └── literature_pipeline.py  # 🎯 學術文獻主管線 (雙欄帶狀流動、APA 表格對齊、IMRAD 標題)
│       │
│       ├── parsers/                # [解析層] (PDF, EPUB, LaTeX, 雙欄版面)
│       │   ├── digital_pdf.py      # 原生數位 PDF 解析器 (XML 樣式感知、雙欄、頁眉/頁腳過濾)
│       │   ├── scanned_pdf.py      # 掃描版 PDF 解析器 (OCR 降級備用)
│       │   ├── epub_parser.py      # EPUB 電子書結構解析器
│       │   ├── math_latex.py       # LaTeX 數學公式識別與轉譯
│       │   ├── layout_detector.py  # 📐 版面特徵總協調器 (662行，已模組化委派子解析器)
│       │   ├── layout/             # 📐 版面特徵子解析器專屬目錄
│       │   │   ├── vector_figure_parser.py # 向量圖表、流程圖與符號圖式抽取與裁切
│       │   │   ├── eoc_parser.py           # 章末練習題（雙欄解交錯）、詞彙雙向索引表與延伸網站
│       │   │   ├── table_parser.py         # 表格識別、APA 對齊與多行附註隔離
│       │   │   ├── table_llm_fixer.py      # 複雜表格調用 Ollama 重構
│       │   │   ├── margin_parser.py        # 邊欄註解、名詞解釋與側欄詞彙框
│       │   │   ├── callout_parser.py       # GitHub Alert 提示框 (> [!NOTE]) 與圖表斜體說明
│       │   │   └── list_parser.py          # 列表、縮排代碼塊與註腳分離
│       │   └── literature/         # 🎯 學術文獻專用解析子套件
│       │       ├── metadata_extractor.py   # 論文標題、作者群、期刊卷期與 Abstract 提取
│       │       ├── imrad_resolver.py       # IMRAD 架構對齊、章節位移與輔助區塊歸攏
│       │       ├── figure_formatter.py     # 圖表語義定位與句子自動無縫縫合
│       │       └── reference_parser.py     # 參考文獻獨立切分與條目重構
│       │
│       ├── verification/           # [檢驗層]
│       │   ├── format_auditor.py   # 8 維度文獻排版格式全自動稽核器 (0~100 分數評級)
│       │   ├── ollama_verifier.py  # 本地大模型深度語義複核與視覺多模態比對
│       │   ├── ollama_healer.py    # 破損 LaTeX 公式與文本自我修復器
│       │   ├── rules.py            # 排版規則庫
│       │   ├── verifier.py         # 基礎文本還原度稽核器
│       │   ├── visual_auditor.py   # 視覺排版稽核
│       │   └── review_manager.py   # 人工審查調度
│       │
│       ├── fixes/                  # 🔧 [專案修復手冊]
│       │   ├── playbook.py         # 8 大專用排版修復配方庫與審核調度引擎
│       │   ├── synthesizer.py      # 🤖 Ollama 自動代碼修復合成器 (AST 靜態沙盒與自我修復循環)
│       │   ├── staged/             # 🧪 待審核 AI 自動生成修復配方隔離區 (Pending Review)
│       │   └── promoted/           # 🚀 已核准並轉正之正式修復配方庫
│       │
│       ├── utils/                  # [輔助工具層]
│       │   ├── shared_text.py      # 💡 跨模組共用純函數文字與正則工具 (孤立頁碼, KaTeX貨幣, OCR統計, 水印, 引用)
│       │   ├── text_utils.py       # 文本清理通用函式庫 (連字號縫合, 首字下沉修復, 排版符號)
│       │   ├── obsidian_linker.py  # Obsidian 全書 index.md 索引與章節前後導航雙鏈注入
│       │   ├── anki_exporter.py    # Anki 記憶閃卡匯出工具
│       │   └── system.py           # 系統底層調用輔助
│       │
│       ├── profiler/               # [版面探測層]
│       │   ├── coordinate_calibrator.py # 文獻物理幾何座標校準與 document_profile.json 生成
│       │   ├── special_block_scanner.py # 特殊區塊掃描器
│       │   ├── publisher_detector.py    # 出版商特徵自動探測 (Elsevier, APA, CUP, AIP, etc.)
│       │   ├── model_advisor.py         # 本地大模型規格建議
│       │   └── ollama_profiler.py       # 利用 Ollama 探測書籍版面特徵
│       │
│       └── core/                   # [核心調度層]
│           ├── orchestrator.py     # 主流程協調調度器
│           ├── global_state.py     # 全域轉檔狀態管理器 (global_status.json)
│           ├── invariants.py       # 🚨 QualityInvariantGuard: 零容忍防呆物理門禁 (避免有錯還報對)
│           ├── splitter.py         # PDF 章節切割器
│           ├── learner.py          # 專案自我學習調度
│           └── watchdog.py         # 檔案監控核心
│
├── config/                         # ⚙️ [層級式配置系統]
│   ├── archetypes/                 # L1 文件類型特徵設定 (literature.json, textbook.json)
│   ├── publishers/                 # L2 出版商特徵設定 (apa, elsevier, wiley, springer, ieee, aip, cup)
│   └── shared_knowledge/           # L3 跨文件共用知識 (IMRAD 區塊別名, Unicode 映射)
│
└── dashboard/                      # 📊 [視覺化儀表板] 靜態零依賴 HTML 看板 (index.html)
```

---

## 二、 核心模組功能與架構設計備註 (Detailed Functional Registry)

### 1. 指揮中樞與 CLI 分層 (`run.py` & `src/cli/`)
- **`run.py`**：保持極簡（$\le 200$ 行），僅作為 `argparse` 入口與分發器，嚴禁承載具體業務邏輯。
- **`src/cli/common.py`**：集中定義根目錄相對錨定路徑 `ROOT`、清理 dangling 暫存檔 `clean_dangling_tmp_files()`，以及文件日期同步器 `sync_markdown_dates()`。
- **`src/cli/cli_audit.py`**：實裝 `audit` 指令，對單檔或 `data/output/literature/` 全量進行 8 維度格式稽核，支援 `--ollama` AI 複核與 `--fix` 自動匹配配方修復。
- **`src/cli/cli_fix.py`**：實裝 `fix` 指令族群（`list`, `apply`, `info`, `review`, `test`, `promote`, `reject`, `synthesize`），管理與審核排版修復程式。
- **`src/cli/cli_git.py`**：實裝日常進度存檔 `save`（測試門禁 + 英文 Commit）、離席交接 `handoff`、對話結束閉環 `end-session`、版本發布 `publish`，以及全自動雙軌對話封存 `archive-sessions`。
- **`src/cli/cli_process.py`**：實裝單檔轉檔 `process` 與目錄批次轉檔 `batch`，內建硬體冷卻感知與管線派發。
- **`src/cli/cli_project.py`**：實裝系統環境健檢 `doctor`、常駐軟硬體看門狗 `watchdog`、新專案一鍵初始化 `init-project`、Obsidian 雙鏈生成 `obsidian-link`，以及全局進度快照 `status` 與 HTML 看板 `dashboard`。

### 2. 守衛防線 (`src/guards/`)
- **`hardware.py`**：提供 `check_hardware_safety()`，動態計算可用記憶體（包含 free 與 inactive 頁面），感知 macOS `memorystatus_vm_pressure_level`，在 AC 插電與電池模式下自動調整放行門檻。
- **`ollama_guard.py`**：封裝 Ollama REST API，提供連線探活、後台進程自動拉起與服務離線時的純規則優雅降級。
- **`prompts.py`**（`PromptRegistry`）：**專案唯一提示詞中樞**。收攏 12 大固定提示詞，嚴禁各模組散落硬編碼 prompt，並注入 KaTeX `\$`、正則 `\g<1>`、APA 表格附註結構與雙欄閱讀流。
- **`validator.py`**：負責輸入書籍 `manifest.json` 結構校驗與輸出 LaTeX 括號閉合診斷，異常時自動喚醒 Ollama 進行自我修復。

### 3. 排版解析與版面抽取 (`src/doc_processor/parsers/`)
- **`layout_detector.py`**：版面特徵總協調器，行數控制於 662 行，向下委派專屬子解析器。
- **`layout/vector_figure_parser.py`**：專門識別有向量字型或邊界特徵之圖表（Figure 1.1），調用 `pdftoppm` 精準局部裁切與命名。
- **`layout/eoc_parser.py`**：專門處理章末練習題、Key Terms 雙向連結表、Related Internet Sites 等高密度排版區塊，支援雙欄解交錯。
- **`layout/table_parser.py`**：專門處理 ASCII/XML 座標表格，支援 APA 三線表對齊與多行表格附註隔離至 `<tfoot>`。
- **`literature/metadata_extractor.py`**：專門處理多期刊學術論文元數據提取（標題、作者單位、DOI、卷期與 Abstract）。
- **`literature/imrad_resolver.py`**：學術論文 IMRAD 架構映射與標題正規化，過濾 NIH 浮水印並歸攏特別章節。
- **`literature/figure_formatter.py`**：實裝圖表語義定位演算法，將圖表移至內文首次提及之段落之後，並無縫縫合被切斷之段落。

### 4. 檢驗、手冊修復與共用工具 (`src/doc_processor/verification/`, `fixes/`, `utils/`)
- **`verification/format_auditor.py`**：8 維度排版格式稽核器，產出評分報告並推薦匹配的修復配方。
- **`core/invariants.py`**（`QualityInvariantGuard`）：**零容忍防呆門禁**。檢核 7 大硬性不變量，一票否決偽陽性，杜絕「有錯還報對」。
- **`fixes/playbook.py`**（`FixPlaybook`）：8 大專用修復配方庫（CUP 側欄、Elsevier 粘連參考文獻、無括號年份引用、建議清單降級、孤立頁碼、KaTeX 貨幣轉義、OCR 統計符號修復、NIH 水印過濾）。
- **`fixes/synthesizer.py`**（`OllamaRecipeSynthesizer`）：Ollama 程式修復合成器，經 AST 靜態沙盒校驗與沙盒測試後將代碼隔離存放在 `staged/`。
- **`utils/shared_text.py`**：**共用文字與正則工具庫**。收攏跨模組純函數清洗轉換邏輯，零副作用，供全專案共同繼承。
