# 🗺️ docs/STRUCTURE.md (專案目錄地圖與功能備註)

> 💡 **重要規範**：所有參與專案的開發者與 AI Agent，嚴禁隨意在未經許可的位置新增頂層目錄。新增任何新檔案時，必須先查閱本地圖並於變更後同步更新！

---

## 專案完整目錄樹 (Directory Tree)

```text
books-project/
│
├── .git/hooks/pre-push             # 🛑 [Git安全鎖] 攔截一切未經授權的 git push，確保 Local-Only
├── .gitignore                      # 🙈 排除 scratch/, logs/, data/state/, __pycache__/ 等暫存
│
├── README.md                       # 📖 [專案總覽] 專案定位、核心特點與快速介紹
├── OPERATIONS.md                   # 🚀 [冷啟動指南] 30秒喚醒、Top 4 常用指令、疑難排除 (人與新AI專用)
├── AGENTS.md                       # 🤖 [跨Agent憲法] Codex/Claude 意圖指令路由表、行為四大鐵律
├── CHANGELOG.md                    # 📜 [版本日誌] 紀錄歷史與里程碑變更 (由 walkthrough 提煉)
├── PROJECT_INIT_STANDARD.md        # 🌟 [通用標準] 未來新專案直接丟給 AI 開案的通用模板
├── run.py                          # 🛠️ [總指揮中心] doctor, process, save, handoff, publish, test 指令入口
│
├── memory/                         # ⚡ [動態記憶層] (追蹤當前狀態、交接與歷史精華)
│   ├── TASKS.md                    # 📋 當前 Sprint 任務進度看板與驗收狀態
│   ├── HANDOFF.md                  # 🪪 離席交接卡片 (去上課前 1 分鐘更新，下個 AI 接手點)
│   └── sessions/                   # 🗄️ 跨 Agent 參考用的 1 頁式對話濃縮摘要
│       └── 2026-09-23-complete-architecture-and-standards.md
│
├── docs/                           # 🏛️ [靜態工程資產] (提交 Git 的永久規範)
│   ├── STRUCTURE.md                # 🗺️ [即本檔案] 完整檔案地圖與每個模組的功能備註
│   ├── CODING_RULES.md             # 🛡️ 軟硬體守衛、Ollama 自動除錯、結構化日誌、scratch 約定
│   ├── ARCHITECTURE.md             # 🏗️ 系統總體架構圖、數據流向與預留 Dashboard
│   └── adr/                        # 📜 架構決策紀錄 (ADR)
│       ├── 0001-ollama-hardware-guard-and-auto-verify.md
│       └── 0002-domain-split-book-and-paper.md
│
├── scratch/                        # 🧪 [臨時實驗室] 一次性測試腳本，不入 Git，保持代碼庫純淨
├── logs/                           # 📋 [診斷日誌] 結構化詳細日誌輸出 (Where + Why + How)
│
├── data/                           # 📥 [資料流核心] 雙軌實體路由與隔離防呆
│   ├── input/                      # 原始待處理檔案
│   │   ├── books/                  # 📚 專門存放書籍 (PDF/EPUB) ➔ 自動啟動書籍管線
│   │   └── journals/               # 📑 專門存放學術期刊/論文 (PDF) ➔ 自動啟動雙欄管線
│   ├── output/                     # 產出的筆記型 Markdown
│   │   ├── books/                  # 輸出按章節切分之 Obsidian 筆記
│   │   └── journals/               # 輸出含 Abstract、雙欄還原與文獻之論文筆記
│   ├── needs_review/               # 🚨 [人機隔離區] 遇疑難公式或壞頁自動存於此，不卡死主程序
│   └── state/                      # 💾 斷點續傳快照、TOC 預覽與 Dashboard 狀態
│
├── src/                            # 💻 [業務核心原始碼]
│   ├── guards/                     # 🛡️ 守衛防線
│   │   ├── hardware.py             # RAM/電池/SSD/MPS 檢測防線
│   │   ├── ollama_guard.py         # Ollama 連線探活、自動喚醒與優雅降級
│   │   └── validator.py            # 輸入 JSON 比對與輸出異常自動喚醒 Ollama
│   ├── utils/                      # 🛠️ 通用工具
│   │   └── logger.py               # 結構化診斷日誌工具
│   └── book_processor/             # ⚙️ 既有書籍與期刊處理核心引擎
│       ├── pipelines/              # 管線層 (textbook_pipeline, journal_pipeline)
│       ├── parsers/                # 解析層 (PDF, EPUB, LaTeX, 雙欄版面)
│       ├── verification/           # 檢驗層 (OllamaVerifier, rules)
│       └── core/                   # 核心調度 (orchestrator, splitter, inout)
│
└── dashboard/                      # 📊 [預留模組] 未來視覺化儀表板 (讀取 data/state/status.json)
```
