# 🌟 PROJECT_INIT_STANDARD.md (新專案通用初始化標準指南)

> 💡 **使用方法**：
> 當您未來開立任何新的軟體、資料科學或 AI 專案時，**只需將本文件內容直接複製貼給 AI Agent**，並下達指令：
> 
> *「請閱讀本指南，並嚴格依照本標準在當前工作區中初始化所有必要的資料夾、Markdown 文件、Git 安全鎖與總指揮 run 腳本，完成後向我彙報。」*

---

## 🎯 核心工程哲學 (The Core Philosophy)

1. **零冷啟動成本**：任何時候回到專案，任何人/AI 只要看 `OPERATIONS.md`，30 秒內即可開始跑指令。
2. **防 AI 幻覺與幽靈修復**：拒絕口頭宣稱「已修復」，所有改動必須有實體執行日誌與測試通過證據。
3. **Local-Only 安全保護**：預設封鎖所有遠端 Git Push，代碼存檔在本地，安全有保證。
4. **先更文檔後 Commit**：嚴禁只提交代碼而留下過期文檔，所有紀錄必須強制帶上日期（`YYYY-MM-DD`）。
5. **人機協同守門人 (HITL)**：疑難雜症進隔離區 (`needs_review/`)，避免 AI 自作聰明無限卡死。

---

## 一、 新專案必須建立的標準檔案與目錄結構

```text
my-new-project/
├── .git/hooks/pre-push         # 🛑 阻擋未授權 push 的本地安全鎖 (強制 ALLOW_PUSH=1)
├── .gitignore                  # 🙈 排除 scratch/, logs/, data/state/, .env
│
├── README.md                   # 📖 專案總覽
├── OPERATIONS.md               # 🚀【冷啟動手冊】30秒啟動步驟、Top 3 常用指令、疑難急救
├── AGENTS.md                   # 🤖【跨 Agent 憲法】意圖指令路由表、行為四大鐵律
├── CHANGELOG.md                # 📜【版本日誌】語意化版本與里程碑紀錄
├── run.py (或 run.sh / Makefile)# 🛠️【總指揮中心】封裝 doctor, run, save, handoff, publish
│
├── memory/                     # ⚡【動態記憶層】
│   ├── TASKS.md                # 📋 當前 Sprint 任務進度看板與驗收清單
│   ├── HANDOFF.md              # 🪪 離席交接卡片（外出/上課前 1 分鐘由 AI 更新）
│   └── sessions/               # 🗄️ 跨 Agent 參考用的 1 頁式對話濃縮摘要
│
├── docs/                       # 🏛️【靜態工程資產】
│   ├── STRUCTURE.md            # 🗺️ 專案完整目錄樹地圖與每支程式功能備註
│   ├── CODING_RULES.md         # 🛡️ 開發守則（日誌格式、軟硬體守衛、scratch 約定、衝突協議）
│   ├── ARCHITECTURE.md         # 🏗️ 系統總體架構圖與數據流向
│   └── adr/                    # 📜 架構決策紀錄（標記 Accepted / Superseded）
│
├── scratch/                    # 🧪【臨時實驗室】一次性測試腳本專用夾（不入 Git）
├── logs/                       # 📋【診斷日誌】結構化日誌（Where + Why + How）
│
├── data/                       # 📥【資料流核心】(若為資料/內容專案)
│   ├── input/                  # 原始待處理資料
│   ├── output/                 # 正式產出結果
│   ├── needs_review/           # 🚨 異常隔離區（不卡死主程式，留待人工審核）
│   └── state/                  # 斷點續傳快照與 Dashboard 狀態檔
│
└── src/                        # 💻【業務核心原始碼】
```

---

## 二、 新專案 AI 代理必須嚴格遵守的四大鐵律

### 鐵律 1：Git 本地安全鎖與禁令 (Zero-Push Policy)
- 專案建立第一步：必須安裝 `.git/hooks/pre-push`，任何未帶 `ALLOW_PUSH=1` 的 `git push` 自動阻斷。
- 開發時嚴禁在主分支隨意混亂推送。

### 鐵律 2：代碼與文檔同步存檔 (Doc-Before-Commit)
- 任何 Commit 前，AI 必須主動：
  1. 更新 `memory/TASKS.md` 勾選已完成項目與日期 `[YYYY-MM-DD]`。
  2. 若為中斷交接，更新 `memory/HANDOFF.md` 的時間戳記與接手指令。
  3. 若涉及檔案新增/刪除，更新 `docs/STRUCTURE.md`。
- Commit Message 前綴必須一律帶上日期：`[YYYY-MM-DD] feat: ...`。

### 鐵律 3：決策衝突中斷協議 (Conflict Circuit Breaker)
- AI 動工前必須先查閱 `docs/adr/`。
- 若發現當前需求或做法與既有 `[Status: Accepted]` 的 ADR 衝突，**嚴禁自行決定推翻**，必須主動向使用者發問確認。

### 鐵律 4：草稿隔離規範 (Scratchpad Discipline)
- 所有臨時試跑程式、測試腳本一律放在 `scratch/`。嚴禁污染根目錄與 `src/`。

### 鐵律 5：macOS 原生能力與硬體協同優先原則 (macOS-Native Priority)
- 在 macOS (尤其是 Apple Silicon) 開發時，AI 嚴禁只盲目推薦跨平台重型套件。必須主動評估並優先建議 macOS 內建/原生功能（如 Apple Vision Framework OCR、Metal/MPS、sips、CoreML 等）。若原生方案效能更高、記憶體更省、體驗更好，必須主動向使用者提出！

---

## 三、 開案一鍵初始化檢查清單 (AI Checklist)

任何 AI Agent 在接收到本指南後，必須按以下清單逐一檢查並向使用者回報：
- [ ] 1. 建立 `.git/hooks/pre-push` 並給予執行權限 (`chmod +x`)。
- [ ] 2. 建立 `memory/`、`docs/`、`scratch/`、`logs/`、`data/` 等目錄結構。
- [ ] 3. 建立 `OPERATIONS.md`，填入該新專案的啟動指令。
- [ ] 4. 建立 `AGENTS.md`，填入該新專案的意圖派發清單。
- [ ] 5. 建立 `docs/STRUCTURE.md`，標註當前所有模組職責。
- [ ] 6. 建立 `docs/CODING_RULES.md`，設定該專案的軟硬體門檻與日誌格式。
- [ ] 7. 在 `run.py` 封裝 `doctor`、`save`、`handoff` 等快捷指令。
- [ ] 8. 執行第一次本地 Git 初始化存檔：`[YYYY-MM-DD] chore: initialize project standard structure`。
