# 🌟 PROJECT_INIT_STANDARD.md (新專案通用初始化標準指南)

> 💡 **使用方法 (How to Use)**：
> 當您未來開立任何新的軟體、資料科學或 AI 專案時，**只需將本文件內容直接複製貼給 AI Agent**，並下達指令：
> 
> *「請閱讀本指南，並嚴格依照本標準在當前工作區中初始化所有必要的資料夾、Markdown 文件、Git 安全鎖與總指揮 run 腳本，完成後向我彙報。」*

---

## 🎯 核心工程哲學 (The Core Philosophy)

1. **零冷啟動成本**：任何時候回到專案，任何人/AI 只要看 `OPERATIONS.md`，30 秒內即可開始跑指令。
2. **開場喚醒儀式 (Agent-Init)**：任何 AI 在對話第一步必須主動執行 `python run.py agent-init`，自動讀取工作守則與交接狀態。
3. **防 AI 幻覺與幽靈修復**：拒絕口頭宣稱「已修復」，所有改動必須有實體執行日誌與測試通過證據。
4. **Local-Only 安全保護**：預設封鎖所有遠端 Git Push，代碼存檔在本地，安全有保證。
5. **先更文檔後 Commit**：嚴禁只提交代碼而留下過期文檔，所有紀錄必須強制帶上日期（`YYYY-MM-DD`）。
6. **全英文 Commit 規範**：所有 Git Commit 訊息嚴格使用英文（Conventional Commits 格式）。
7. **人機協同守門人 (HITL)**：疑難雜症進隔離區 (`needs_review/`)，避免 AI 自作聰明無限卡死。
8. **零硬編碼絕對路徑 (Zero Hardcoded Paths)**：嚴禁寫死 `/Users/...`。一律使用以當前檔案動態推導的相對路徑，保證專案整體移動至任何資料夾或電腦時 100% 正常運作。
9. **macOS 原生能力與硬體協同優先**：在 Mac (尤其是 Apple Silicon) 環境下，優先評估系統內建功能（如 Apple Vision Framework、`sips`、Metal/MPS、CoreML），拒絕盲目推薦笨重跨平台套件。
10. **全自動主動執行 (Proactive Execution)**：AI 讀完需求或文檔後，凡可腳本化執行的操作必須直接調用終端執行，嚴禁只把指令印在對話框叫使用者手動跑。
11. **領域命名標準化 (`literature`)**：學術領域統一採用 `literature`，涵蓋期刊、論文、預印本與報告。
12. **根目錄零雜質原則**：全面廢除 `inbox`/`processed`/`output` 等過渡目錄，實體資料一律唯一歸屬於 `data/input/<domain>/` 與 `data/output/<domain>/`。
13. **標準持續自我迭代協議**：使用者每次提出治理新要求，AI 必須立即自動更新本指南，確保未來所有新專案皆享有一致最新標準。
14. **智慧軟硬體一體化看門狗**：監控待處理目錄新檔案的同時，必須結合 RAM/SSD/電池即時巡檢，來檔即轉且硬體受限時自動降級。
15. **根目錄零臨時與非標文檔規範**：根目錄除 README、OPERATIONS、AGENTS、CHANGELOG、PROJECT_INIT_STANDARD 外，嚴禁散落 `ISSUES.md` 或 `OPTIMIZATION_PROPOSAL.md` 等檔案（歷史議題歸 `memory/` 或 `docs/`，提案歸 `docs/`）。

---

## 一、 新專案必須建立的標準檔案與目錄結構

```text
my-new-project/
├── .git/hooks/pre-push         # 🛑 阻擋未授權 push 的本地安全鎖 (強制 ALLOW_PUSH=1)
├── .gitignore                  # 🙈 排除 scratch/, logs/, data/state/, data/needs_review/, .env
│
├── README.md                   # 📖 專案總覽
├── OPERATIONS.md               # 🚀【冷啟動手冊】30秒啟動步驟、Top 常用指令、疑難急救
├── AGENTS.md                   # 🤖【跨 Agent 憲法】意圖指令路由表、行為核心鐵律
├── CHANGELOG.md                # 📜【版本日誌】語意化版本與里程碑紀錄 (含發布日期)
├── PROJECT_INIT_STANDARD.md    # 🌟【通用標準】本指南本體（AI 每次提要求自動同步更新）
├── run.py (或 run.sh / Makefile)# 🛠️【總指揮中心】封裝 agent-init, doctor, run, save, handoff, publish, watchdog, archive-sessions
│
├── .agent/skills/              # 🧠【技能分層架構】
│   ├── document-processor/     # 👑【總調度技能】環境健檢、文檔特徵感知、子技能派發、雙軌審計
│   ├── textbook-processor/     # 📖【領域子技能】長篇教科書、章節切分、文意縫合、Anki 卡片
│   └── literature-processor/   # 📑【領域子技能】學術文獻、雙欄帶狀流動、摘要與參考文獻解析
│
├── memory/                     # ⚡【動態記憶層】
│   ├── TASKS.md                # 📋 當前 Sprint 任務進度看板與驗收清單 (標記 YYYY-MM-DD)
│   ├── HANDOFF.md              # 🪪 離席交接卡片（外出/上課前由 AI 自動更新，帶精確時間戳）
│   └── sessions/               # 🗄️ 跨對話雙軌歸檔 (YYYY-MM-DD-<topic>-summary.md + transcript.md)
│
├── docs/                       # 🏛️【靜態工程資產】(提案與歷史議題全部收納於此，不散落根目錄)
│   ├── STRUCTURE.md            # 🗺️ 專案完整目錄樹地圖與每支程式功能備註
│   ├── CODING_RULES.md         # 🛡️ 開發守則（日誌三要素、軟硬體守衛、scratch 約定、衝突協議）
│   ├── ARCHITECTURE.md         # 🏗️ 系統總體架構圖與數據流向
│   └── adr/                    # 📜 架構決策紀錄 (0001-xxx.md，標記 Accepted / Superseded)
│
├── scratch/                    # 🧪【臨時實驗室】一次性測試腳本專用夾（不入 Git）
├── logs/                       # 📋【診斷日誌】結構化日誌（強制包含 Where + Why + How to Fix）
│
├── data/                       # 📥【資料流核心】(根目錄絕不留存 inbox/processed/output 舊目錄)
│   ├── input/                  # 原始待處理實體資料
│   │   ├── books/              # 長篇書籍 (PDF/EPUB)
│   │   └── literature/         # 學術文獻 (期刊/論文/預印本 PDF)
│   ├── output/                 # 正式產出結果 (結構化 Markdown 雙鏈)
│   │   ├── books/              # 書籍章節輸出
│   │   └── literature/         # 文獻單篇解析輸出
│   ├── needs_review/           # 🚨 異常隔離區（信度 < 0.80 或修復失敗，留待人工審核）
│   └── state/                  # 斷點續傳快照與狀態檔
│
└── src/                        # 💻【業務核心原始碼】
```

---

## 二、 新專案 AI 代理必須嚴格遵守的核心鐵律 (Core Directives)

### 鐵律 0：對話開場喚醒儀式 (Session Warmup)
- 任何 AI 進入專案的第一個動作，必須在終端機主動執行：
  `python run.py agent-init`
  自動讀取專案守則、最新交接狀態（`HANDOFF.md`）與進行中任務（`TASKS.md`）。

### 鐵律 1：Git 本地安全鎖與禁令 (Zero-Push Policy)
- 專案建立第一步：必須安裝 `.git/hooks/pre-push`，任何未帶 `ALLOW_PUSH=1` 的 `git push` 自動阻斷。
- 開發時嚴禁在終端機隨意推送至遠端。

### 鐵律 2：代碼與文檔同步存檔與【全英文 Commit】(Doc-Before-Commit & English Protocol)
- 嚴禁只提交代碼而遺漏文檔！任何 Commit 前，AI 必須主動：
  1. 更新 `memory/TASKS.md` 勾選已完成項目並打上日期 `[YYYY-MM-DD]`。
  2. 若為中斷交接，更新 `memory/HANDOFF.md` 的時間戳記與接手指令。
  3. 若涉及檔案新增/刪除，更新 `docs/STRUCTURE.md`。
- **所有 Git Commit 訊息必須使用【英文】**，嚴格遵循 Conventional Commits 格式（如 `[YYYY-MM-DD] feat: ...`）。

### 鐵律 3：拒絕幽靈修復與軟硬體守衛原則 (Proof of Execution & Guarding)
- 嚴禁口頭宣告「已修復」，必須出示實體執行日誌或測試通過證據。
- 呼叫重度模型或高負載處理前，必須檢查系統可用 RAM（建議 ≥ 4GB）、電池狀態與磁碟空間，條件不符時主動優雅降級。
- 若有輸入驗證不符或輸出語法異常，必須具備自動調用模型自我修復的機制，修復失敗則送入 `needs_review/` 隔離區。

### 鐵律 4：決策衝突阻斷協議 (Conflict Circuit Breaker)
- AI 動工前必須先查閱 `docs/adr/` 中所有 `[Status: Accepted]` 的決策。
- 若發現當前需求或做法與既有 ADR 衝突，**嚴禁自行決定推翻**，必須立即暫停並主動向使用者發問確認。

### 鐵律 5：草稿隔離規範 (Scratchpad Discipline)
- 所有臨時試跑程式、測試腳本一律放在 `scratch/`。嚴禁污染根目錄與 `src/`。

### 鐵律 6：零硬編碼絕對路徑 (Zero Hardcoded Absolute Paths)
- 嚴禁寫死 `/Users/username/...`。一律使用以當前檔案動態推導的相對路徑（`Path(__file__).resolve().parent`），確保專案資料夾搬移至任何路徑或電腦時 100% 正常。

### 鐵律 7：macOS 原生能力與硬體協同優先 (macOS-Native Priority)
- 在 macOS (尤其是 Apple Silicon) 開發時，AI 嚴禁只盲目推薦跨平台重型套件。必須主動評估並優先建議 macOS 內建/原生功能（如 Apple Vision Framework OCR、Metal/MPS、sips、CoreML 等）。

### 鐵律 8：會話雙軌歸檔與瑕疵全隔離協議 (Dual-Track Archiving & Mandatory Quarantine)
- AI 離席交接（`handoff`）或重大結案（`publish`）時，必須自動配對產生：
  - `memory/sessions/YYYY-MM-DD-<topic>-summary.md`：**高密度總結**（先看這個掌握決策與結果）。
  - `memory/sessions/YYYY-MM-DD-<topic>-transcript.md`：**完整對話紀錄**（有疑問時深挖問答細節）。
- 任何模型處理失敗、超時、或信度 < 0.80 的瑕疵，一律自動拋入 `data/needs_review/` 隔離存檔，絕不卡死主批次程序。

### 鐵律 9：AI 全自動主動執行與禁止口頭派工原則 (Proactive Execution & Zero Passive Commands)
- **嚴禁消極在對話框輸出「請你在終端機執行...」**：凡是可以透過腳本或程式執行的操作（如環境健檢、讀檔後的流程觸發、轉檔管線、文檔更新、Git 本地提交、對話存檔），**AI 必須直接調用終端工具主動執行到底**，只回報執行結果與後續建議。

### 鐵律 10：學術文獻領域標準命名 (Standardized Domain Naming: `literature`)
- 知識庫與轉檔專案中，學術文件統一命名為 `literature`（學術文獻），涵蓋期刊 (Journal)、會議論文 (Conference Proceedings)、預印本 (Preprint) 與技術報告。

### 鐵律 11：乾淨根目錄與實體資料流隔離 (Zero Legacy Folders & Clean Root)
- 根目錄不得殘留任何歷史過渡資料夾（如 `inbox/`、`processed/`、`output/`）。
- 資料流嚴格統一於 `data/input/<domain>/` 與 `data/output/<domain>/` 實體存放。

### 鐵律 12：技能分層架構標準 (Skill Hierarchy: Master & Sub-Skills)
- 多領域處理專案中，Agent Skills 採分層架構：Master Orchestrator（總調度技能）分派至 Domain Sub-Skills（領域專屬子技能）。

### 鐵律 13：標準自更新協議 (Self-Updating Standard Protocol)
- 每次使用者對專案治理提出任何新的規格、要求或改進方向時，**AI 必須第一時間同步更新 `PROJECT_INIT_STANDARD.md` 與 `AGENTS.md`**。

### 鐵律 14：智慧軟硬體一體化看門狗規範 (Integrated Hardware-Aware Watchdog)
- 專案常駐監視服務必須深度整合「待處理目錄監聽」與「軟硬體守衛（RAM/SSD/電池/大模型探活）」，來檔即自動安全觸發轉檔；若硬體不足則主動告警並降級。

### 鐵律 15：根目錄零臨時與非標文檔規範 (Zero Ad-Hoc Markdown Files in Root)
- 根目錄只允許存在官方標準文檔（README、OPERATIONS、AGENTS、CHANGELOG、PROJECT_INIT_STANDARD）。所有排版分析或問題清單移至 `memory/` 或 `docs/`，所有優化提案與架構設計移至 `docs/`。

---

## 三、 開案一鍵初始化檢查清單 (AI Checklist)

任何 AI Agent 在接收到本指南後，必須按以下清單逐一檢查並主動執行，最後向使用者回報：
- [ ] 1. 建立 `.git/hooks/pre-push` 並給予執行權限 (`chmod +x`)。
- [ ] 2. 建立 `memory/`、`docs/`、`scratch/`、`logs/`、`data/input/`、`data/output/`、`data/needs_review/`。
- [ ] 3. 建立 `OPERATIONS.md`，填入該新專案的 30 秒啟動與常用指令。
- [ ] 4. 建立 `AGENTS.md`，填入該新專案的意圖派發清單與開場喚醒指令。
- [ ] 5. 建立 `docs/STRUCTURE.md`，標註當前所有模組職責。
- [ ] 6. 建立 `docs/CODING_RULES.md`，設定該專案的軟硬體門檻與日誌格式。
- [ ] 7. 建立 `.agent/skills/` 分層技能體系（總入口 + 專屬子技能）。
- [ ] 8. 在 `run.py` 封裝 `agent-init`、`doctor`、`process`、`save`、`handoff`、`publish`、`watchdog`、`archive-sessions` 等快捷指令。
- [ ] 9. 主動執行第一次本地 Git 初始化存檔（**使用英文 Commit**）：
  `[YYYY-MM-DD] chore: initialize project standard governance and architecture`。
