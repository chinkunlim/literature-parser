# 🗺️ docs/STRUCTURE.md (專案目錄地圖與功能備註)

> 💡 **重要規範**：所有參與專案的開發者與 AI Agent，嚴禁隨意在未經許可的位置新增頂層目錄。新增任何新檔案時，必須先查閱本地圖並於變更後同步更新！

---

## 專案完整目錄樹 (Directory Tree)

```text
books-project/
│
├── .git/hooks/pre-push             # 🛑 [Git安全鎖] 攔截一切未經授權的 git push，確保 Local-Only (ALLOW_PUSH=1 解鎖)
├── .gitignore                      # 🙈 排除 scratch/, logs/, data/state/, .env, __pycache__ 等暫存
├── pyproject.toml                  # 📦 現代 Python 打包、依賴管理與工具配置 (ruff, mypy, pytest)
├── .env.example                    # 🔑 12-Factor 環境變數配置範本 (嚴禁提交真實 .env)
│
├── README.md                       # 📖 [專案總覽] 專案定位、核心特點與快速介紹
├── OPERATIONS.md                   # 🚀 [冷啟動指南] 30秒喚醒、Top 常用指令、同步時機矩陣、疑難排除
├── AGENTS.md                       # 🤖 [跨Agent憲法] 意圖指令路由表、十大核心鐵律、六大黃金同步矩陣
├── CHANGELOG.md                    # 📜 [版本日誌] 紀錄歷史與里程碑變更 (語意化版號 + 具體日期)
├── PROJECT_INIT_STANDARD.md        # 🌟 [通用標準] 24大核心鐵律、雙層規範、開案一鍵初始化檢查清單
├── run.py                          # 🛠️ [總指揮中心] agent-init, doctor, process, save, handoff, publish, watchdog, end-session
│
├── .agent/skills/                  # 🧠 [技能分層架構]
│   ├── document-processor/         # 👑 [總調度技能] 環境健檢、文檔特徵感知、子技能派發、雙軌審計
│   ├── textbook-processor/         # 📖 [領域子技能] 長篇教科書、章節切分、文意縫合、Anki 卡片
│   └── literature-processor/       # 📑 [領域子技能] 學術文獻、雙欄帶狀流動、摘要與參考文獻解析
│
├── memory/                         # ⚡ [動態記憶層] (追蹤當前狀態、交接與歷史精華)
│   ├── TASKS.md                    # 📋 當前 Sprint 任務進度看板與驗收狀態 (標註 YYYY-MM-DD)
│   ├── HANDOFF.md                  # 🪪 離席交接卡片 (去上課前 1 分鐘更新，下個 AI 接手點)
│   └── sessions/                   # 🗄️ 全歷史對話雙軌歸檔 (Summary + Transcript 配對封存)
│
├── docs/                           # 🏛️ [靜態工程資產] (提交 Git 的永久規範與歷史資產)
│   ├── STRUCTURE.md                # 🗺️ [即本檔案] 完整檔案地圖與每個模組的功能備註
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
├── tests/                          # 🧪 [自動化測試體系] (179 個測試全部 PASS)
│   ├── __init__.py                 # 動態注入 sys.path，確保任何環境直跑 unittest/pytest
│   └── test_*.py                   # 21 個測試檔案，平坦結構於 tests/ 頂層
│                                   # (含 unit + integration 測試，以 test_v<version>_*.py 命名)
│
├── src/                            # 💻 [業務核心原始碼] (Clean Architecture)
│   ├── guards/                     # 🛡️ 守衛防線
│   │   ├── hardware.py             # RAM/電池/SSD/MPS 檢測防線
│   │   ├── ollama_guard.py         # Ollama 連線探活、自動喚醒與優雅降級
│   │   ├── prompts.py              # 📝 集中預設的固定提示詞 (LaTeX 修復、Manifest 校驗、論文雙欄)
│   │   └── validator.py            # 輸入 JSON 比對與輸出異常自動喚醒 Ollama (信度 < 0.80 自動隔離)
│   ├── utils/                      # 🛠️ 通用工具
│   │   └── logger.py               # 結構化診斷日誌工具
│   └── book_processor/             # ⚙️ 書籍與文獻處理核心引擎 (後續計畫更名 doc_processor)
│       ├── pipelines/              # 管線層
│       │   ├── textbook_pipeline.py    # 長篇書籍章節切分管線
│       │   ├── journal_pipeline.py     # 內部基礎管線 (被 LiteraturePipeline 繼承)
│       │   └── literature_pipeline.py  # 🎯 學術文獻主管線 (orchestrator 直接調用此管線)
│       ├── parsers/                # 解析層 (PDF, EPUB, LaTeX, 雙欄版面)
│       │   ├── literature/         # 🎯 學術文獻解析子模組 (IMRAD, Reference)  [原 journal/]
│       │   └── journal/            # 🔄 向後相容 shim → 重導至 parsers.literature
│       ├── verification/           # 檢驗層 (OllamaVerifier, rules)
│       ├── utils/                  # 輔助模組 (obsidian_linker 雙鏈與索引生成)
│       └── core/                   # 核心調度 (orchestrator, global_state 全域狀態, splitter)
│
├── config/                         # ⚙️ [層級式配置系統]
│   ├── archetypes/                 # L1 文件類型特徵設定
│   │   ├── literature.json         # 學術文獻 (原 journal.json，已重命名)
│   │   └── textbook.json           # 教科書
│   ├── publishers/                 # L2 出版商特徵設定 (apa, elsevier, wiley, springer, ieee)
│   └── shared_knowledge/           # L3 跨文件共用知識
│       ├── literature_sections.json # IMRAD 段落別名 (原 journal_sections.json，已重命名)
│       └── symbol_mappings.json    # Unicode → LaTeX 映射
│
└── dashboard/                      # 📊 [視覺化儀表板] 靜態零依賴 HTML 看板
```

---

## 歷史資料夾清理與遷移說明 (Legacy Folder Clean-up)

1. **`inbox/`、`processed/` 與 `output/` 徹底退役**：
   - 歷史建立的過渡資料夾已全數刪除。
   - 所有實體 PDF/EPUB 檔案與已生成結果，已完整物理遷移至 `data/input/books/`、`data/input/literature/`、`data/output/books/` 與 `data/output/literature/`。
   - 專案根目錄全面保持整潔純淨，杜絕路徑混淆與孤兒檔案。
2. **`scratch/`**：
   - 臨時性 xml 檔案 (`scratch_p8.xml`, `stdout.xml`)、歷史過渡腳本（`verify_accuracy.py` 等）及一次性測試程式全數收納於 `scratch/`。
