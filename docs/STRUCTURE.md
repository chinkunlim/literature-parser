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
├── AGENTS.md                       # 🤖 [跨Agent憲法] Codex/Claude 意圖指令路由表、行為五大鐵律
├── CHANGELOG.md                    # 📜 [版本日誌] 紀錄歷史與里程碑變更 (由 walkthrough 提煉)
├── PROJECT_INIT_STANDARD.md        # 🌟 [通用標準] 未來新專案直接丟給 AI 開案的通用模板
├── run.py                          # 🛠️ [總指揮中心] agent-init, doctor, process, save, handoff, publish, test 指令入口
│
├── .agent/skills/                  # 🧠 [技能分層架構]
│   ├── document-processor/         # 👑 [總調度技能] 環境健檢、文檔特徵感知、子技能派發、雙軌審計
│   ├── textbook-processor/         # 📖 [領域子技能] 長篇教科書、章節切分、文意縫合、Anki 卡片
│   └── literature-processor/       # 📑 [領域子技能] 學術文獻、雙欄帶狀流動、摘要與參考文獻解析
│
├── memory/                         # ⚡ [動態記憶層] (追蹤當前狀態、交接與歷史精華)
│   ├── TASKS.md                    # 📋 當前 Sprint 任務進度看板與驗收狀態
│   ├── HANDOFF.md                  # 🪪 離席交接卡片 (去上課前 1 分鐘更新，下個 AI 接手點)
│   └── sessions/                   # 🗄️ 全歷史對話雙軌歸檔 (Summary + Transcript)
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
├── data/                           # 📥 [資料流核心] 雙軌實體路由與隔離防呆 (無 inbox/output 殘留)
│   ├── input/                      # 原始待處理實體檔案
│   │   ├── books/                  # 📚 專門存放長篇書籍 (PDF/EPUB) ➔ 自動啟動書籍管線
│   │   └── literature/             # 📑 專門存放學術文獻/論文 (PDF) ➔ 自動啟動雙欄文獻管線
│   ├── output/                     # 產出的筆記型 Markdown
│   │   ├── books/                  # 輸出按章節切分之 Obsidian 筆記
│   │   └── literature/             # 輸出含 Abstract、雙欄還原與文獻之論文筆記
│   ├── needs_review/               # 🚨 [人機隔離區] 遇疑難公式或壞頁自動存於此，不卡死主程序
│   └── state/                      # 💾 斷點續傳快照、TOC 預覽與 Dashboard 狀態
│
├── src/                            # 💻 [業務核心原始碼]
│   ├── guards/                     # 🛡️ 守衛防線
│   │   ├── hardware.py             # RAM/電池/SSD/MPS 檢測防線
│   │   ├── ollama_guard.py         # Ollama 連線探活、自動喚醒與優雅降級
│   │   ├── prompts.py              # 📝 集中預設的固定提示詞 (LaTeX 修復、Manifest 校驗、論文雙欄)
│   │   └── validator.py            # 輸入 JSON 比對與輸出異常自動喚醒 Ollama (信度 < 0.80 自動隔離)
│   ├── utils/                      # 🛠️ 通用工具
│   │   └── logger.py               # 結構化診斷日誌工具
│   └── book_processor/             # ⚙️ 既有書籍與期刊處理核心引擎
│       ├── pipelines/              # 管線層 (textbook_pipeline, literature_pipeline)
│       ├── parsers/                # 解析層 (PDF, EPUB, LaTeX, 雙欄版面)
│       ├── verification/           # 檢驗層 (OllamaVerifier, rules)
│       └── core/                   # 核心調度 (orchestrator, splitter, inout)
│
└── dashboard/                      # 📊 [預留模組] 未來視覺化儀表板 (讀取 data/state/status.json)
```

---

## 歷史資料夾清理與遷移說明 (Legacy Folder Clean-up)

1. **`inbox/`、`processed/` 與 `output/` 徹底退役**：
   - 歷史建立的過渡資料夾已全數刪除。
   - 所有實體 PDF/EPUB 檔案與已生成結果，已完整物理遷移至 `data/input/books/`、`data/input/literature/`、`data/output/books/` 與 `data/output/literature/`。
   - 專案根目錄全面保持整潔純淨，杜絕路徑混淆與孤兒檔案。
2. **`scratch/`**：
   - 臨時性 xml 檔案 (`scratch_p8.xml`, `stdout.xml`) 及一次性測試程式全數收納於 `scratch/`。
