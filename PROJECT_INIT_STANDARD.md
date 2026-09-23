# 🌟 PROJECT_INIT_STANDARD.md (新專案通用初始化標準指南)

> 💡 **使用方法 (How to Use)**：
> 當您未來開立任何新的軟體、資料科學或 AI 專案時，**只需將本文件內容直接複製貼給 AI Agent**，並下達指令：
> 
> *「請閱讀本指南，並嚴格依照本標準在當前工作區中初始化所有必要的資料夾、Markdown 文件、Git 安全鎖與總指揮 run 腳本，完成後向我彙報。」*

---

## 🎯 核心工程哲學 (The Core Philosophy)

1. **零冷啟動成本**：任何時候回到專案，任何人/AI 只要看 `OPERATIONS.md`，30 秒內即可開始跑指令。
2. **開場喚醒儀式 (Agent-Init)**：任何 AI 在對話第一步必須執行 `python run.py agent-init`，自動讀取工作守則與交接狀態。
3. **防 AI 幻覺與幽靈修復**：拒絕口頭宣稱「已修復」，所有改動必須有實體執行日誌與測試通過證據。
4. **Local-Only 安全保護**：預設封鎖所有遠端 Git Push，代碼存檔在本地，安全有保證。
5. **先更文檔後 Commit**：嚴禁只提交代碼而留下過期文檔，所有紀錄必須強制帶上日期（`YYYY-MM-DD`）。
6. **全英文 Commit 規範**：所有 Git Commit 訊息嚴格使用英文（Conventional Commits 格式）。
7. **人機協同守門人 (HITL)**：疑難雜症進隔離區 (`needs_review/`)，避免 AI 自作聰明無限卡死。
8. **零硬編碼絕對路徑 (Zero Hardcoded Paths)**：嚴禁寫死 `/Users/...`。一律使用以當前檔案動態推導的相對路徑，保證專案整體移動至任何資料夾或電腦時 100% 正常運作。
9. **macOS 原生能力與硬體協同優先**：在 Mac (尤其是 Apple Silicon) 環境下，優先評估系統內建功能（如 Apple Vision Framework、`sips`、Metal/MPS、CoreML），拒絕盲目推薦笨重跨平台套件。

---

## 一、 新專案必須建立的標準檔案與目錄結構

```text
my-new-project/
├── .git/hooks/pre-push         # 🛑 阻擋未授權 push 的本地安全鎖 (強制 ALLOW_PUSH=1)
├── .gitignore                  # 🙈 排除 scratch/, logs/, data/state/, .env
│
├── README.md                   # 📖 專案總覽
├── OPERATIONS.md               # 🚀【冷啟動手冊】30秒啟動步驟、Top 3 常用指令、疑難急救
├── AGENTS.md                   # 🤖【跨 Agent 憲法】意圖指令路由表、行為核心鐵律
├── CHANGELOG.md                # 📜【版本日誌】語意化版本與里程碑紀錄 (含發布日期)
├── PROJECT_INIT_STANDARD.md    # 🌟【通用標準】本指南本體
├── run.py (或 run.sh / Makefile)# 🛠️【總指揮中心】封裝 agent-init, doctor, run, save, handoff, publish
│
├── memory/                     # ⚡【動態記憶層】
│   ├── TASKS.md                # 📋 當前 Sprint 任務進度看板與驗收清單 (標記 YYYY-MM-DD)
│   ├── HANDOFF.md              # 🪪 離席交接卡片（外出/上課前 1 分鐘由 AI 更新，帶精確時間戳）
│   └── sessions/               # 🗄️ 跨 Agent 參考用的 1 頁式對話濃縮摘要 (YYYY-MM-DD-topic.md)
│
├── docs/                       # 🏛️【靜態工程資產】
│   ├── STRUCTURE.md            # 🗺️ 專案完整目錄樹地圖與每支程式功能備註
│   ├── CODING_RULES.md         # 🛡️ 開發守則（日誌三要素、軟硬體守衛、scratch 約定、衝突協議）
│   ├── ARCHITECTURE.md         # 🏗️ 系統總體架構圖與數據流向
│   └── adr/                    # 📜 架構決策紀錄 (0001-xxx.md，標記 Accepted / Superseded)
│
├── scratch/                    # 🧪【臨時實驗室】一次性測試腳本專用夾（不入 Git）
├── logs/                       # 📋【診斷日誌】結構化日誌（強制包含 Where + Why + How to Fix）
│
├── data/                       # 📥【資料流核心】(若為資料/內容專案)
│   ├── input/                  # 原始待處理資料 (依子目錄進行慣例路由，如 books/ 與 journals/)
│   ├── output/                 # 正式產出結果 (筆記化格式，如 Markdown 雙鏈)
│   ├── needs_review/           # 🚨 異常隔離區（不卡死主程式，留待人工審核）
│   └── state/                  # 斷點續傳快照與 Dashboard 狀態檔
│
└── src/                        # 💻【業務核心原始碼】
```

---

## 二、 新專案 AI 代理必須嚴格遵守的核心鐵律 (Core Directives)

### 鐵律 0：對話開場喚醒儀式 (Session Warmup)
- 任何 AI 進入專案的第一個動作，必須在終端機執行：
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
- **所有 Git Commit 訊息必須使用【英文】**，嚴格遵循 Conventional Commits 格式：
  - `[YYYY-MM-DD] feat: implement hardware pre-flight guard`
  - `[YYYY-MM-DD] fix: resolve LaTeX formula parsing bug`
  - `[YYYY-MM-DD] wip(handoff): pause session before class`

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
- 在 macOS (尤其是 Apple Silicon) 開發時，AI 嚴禁只盲目推薦跨平台重型套件。必須主動評估並優先建議 macOS 內建/原生功能（如 Apple Vision Framework OCR、Metal/MPS、sips、CoreML 等）。若原生方案效能更高、記憶體更省、體驗更好，必須主動向使用者提出！

---

## 三、 開案一鍵初始化檢查清單 (AI Checklist)

任何 AI Agent 在接收到本指南後，必須按以下清單逐一檢查並向使用者回報：
- [ ] 1. 建立 `.git/hooks/pre-push` 並給予執行權限 (`chmod +x`)。
- [ ] 2. 建立 `memory/`、`docs/`、`scratch/`、`logs/`、`data/` 等目錄結構。
- [ ] 3. 建立 `OPERATIONS.md`，填入該新專案的 30 秒啟動與常用指令。
- [ ] 4. 建立 `AGENTS.md`，填入該新專案的意圖派發清單與開場喚醒指令。
- [ ] 5. 建立 `docs/STRUCTURE.md`，標註當前所有模組職責。
- [ ] 6. 建立 `docs/CODING_RULES.md`，設定該專案的軟硬體門檻與日誌格式。
- [ ] 7. 在 `run.py` 封裝 `agent-init`、`doctor`、`save`、`handoff`、`publish` 等快捷指令。
- [ ] 8. 執行第一次本地 Git 初始化存檔（**使用英文 Commit**）：
  `[YYYY-MM-DD] chore: initialize project standard governance and architecture`。
