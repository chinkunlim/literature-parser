# 🌟 PROJECT_INIT_STANDARD.md (新專案通用初始化標準指南 - 企業級規範)

> 💡 **使用方法 (How to Use)**：
> 當您未來開立任何新的軟體、資料科學、AI Agent 或後端專案時，**只需將本文件內容直接複製貼給 AI Agent**，並下達指令：
> 
> *「請閱讀本指南，並嚴格依照本標準在當前工作區中初始化所有必要的資料夾、Markdown 文件、Git 安全鎖、軟硬體守衛與總指揮 run 腳本，完成後向我彙報。」*

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
16. **開案前置軟硬體基線探針 (Hardware Baseline Probe & Guard)**：開案初期必須自動先寫 Python 探針（`src/guards/hardware.py`），精準探測主機 CPU 核心、Apple Silicon 架構、RAM、GPU/MPS、SSD 與電池狀態；開發時兼顧「充分榨乾原生硬體效能」與「嚴格防 OOM/電池耗盡安全守護」。
17. **開案標配一體化看門狗程式 (Scaffold Autonomous Watchdog)**：專案初始化時必須標配產生守望看門狗（`run.py watchdog`），同時盯住輸入任務隊列與本機硬體健康，實現有任務自動安全啟動。
18. **SOLID 物件導向架構約束 (SOLID Principles)**：嚴格實施單一職責（SRP）、開放封閉（OCP）、里氏替換（LSP）、介面隔離（ISP）與依賴反轉（DIP），杜絕千行巨石檔案。
19. **純函數運算與副作用邊界隔離 (Pure Functions & Side-Effect Isolation)**：核心演算法與資料轉換一律寫成無 I/O、無全域狀態的「純函數」；磁碟/網路等副作用收攏於邊界調度器。
20. **工業級強制型別提示與資料契約 (Type Hints & Dataclasses)**：100% 涵蓋 Type Hints (PEP 484/585)；跨模組業務物件禁止濫用無型別 `dict`，一律使用 `@dataclass(frozen=True)` 或 `Pydantic` 定義契約。
21. **防衛性編程與原子性檔案 I/O (Defensive Programming & Atomic Writes)**：嚴禁裸抓異常（No bare `except:`）；大檔寫入必須採用「臨時檔寫入 + `os.replace` 原子替換」，杜絕斷電損壞。
22. **零硬編碼機密與 12-Factor 環境配置 (Zero Hardcoded Secrets & 12-Factor Config)**：嚴禁程式碼寫死金鑰；一律依賴 `.env` 注入，專案標配提交 `.env.example` 樣板。
23. **CODING_RULES 雙層繼承架構規範 (Universal Base + Domain Overlay)**：開發規範統一採雙層結構：第一部為所有專案 100% 通用的高品質軟體工程基線；第二部為本專案專屬之領域擴充。新專案繼承第一部，領域規則只擴充在第二部，通用基線永不被污染。
24. **全生命週期同步與存檔時機矩陣 (Lifecycle Synchronization & Archiving Matrix)**：明確定義「何時該更哪個 MD、何時該 Commit、何時該備份會話與生成摘要」，告別混亂與碎片化。

---

## 一、 新專案必須建立的標準檔案與目錄結構 (專業企業級佈局)

```text
my-new-project/
├── .git/hooks/pre-push         # 🛑 阻擋未授權 push 的本地安全鎖 (強制 ALLOW_PUSH=1)
├── .gitignore                  # 🙈 排除 scratch/, logs/, data/state/, data/needs_review/, .env, __pycache__/
├── pyproject.toml              # 📦 現代 Python 打包、依賴管理與工具配置 (ruff, mypy, pytest)
├── .env.example                # 🔑 12-Factor 環境變數配置範本 (嚴禁提交真實 .env)
│
├── README.md                   # 📖 專案總覽、架構速覽與快速上手
├── OPERATIONS.md               # 🚀【冷啟動手冊】30秒啟動步驟、Top 常用指令、疑難急救
├── AGENTS.md                   # 🤖【跨 Agent 憲法】意圖指令路由表、行為核心鐵律、同步時機矩陣
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
├── docs/                       # 🏛️【靜態工程資產】(提案、架構與歷史議題全部收納於此，不散落根目錄)
│   ├── STRUCTURE.md            # 🗺️ 專案完整目錄樹地圖與每支程式功能備註
│   ├── CODING_RULES.md         # 🛡️ 開發守則（雙層架構：第一部通用基線 + 第二部領域擴充）
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
│   └── state/                  # 💾 斷點續傳快照與狀態檔
│
├── tests/                      # 🧪【自動化測試體系】
│   ├── __init__.py             # 動態注入 sys.path，確保任何環境直跑 unittest/pytest
│   ├── unit/                   # 單元測試 (純函數、模組邏輯，毫秒級無 I/O)
│   └── integration/            # 整合測試 (管線端到端串接、守衛驗證)
│
└── src/                        # 💻【分層業務核心原始碼】(Clean Architecture)
    └── <package_name>/
        ├── core/               # 核心領域模型、不變量校驗 (Invariants)
        ├── guards/             # 軟硬體前置守衛、模型探活與輸入/輸出攔截器
        ├── parsers/ (或 adapters/) # 實體數據讀寫、PDF/EPUB 解碼、外部 API 轉接
        ├── pipelines/ (或 services/)# 應用層場景調度、管線串接
        └── utils/              # 通用無副作用小工具與日誌器
```

---

## 二、 全生命週期同步與存檔時機矩陣 (The 6 Golden Triggers)

為徹底杜絕「何時該改 MD、何時該 Git Commit、何時該歸檔對話」的模糊不清，所有專案與 AI 必須依循以下確定性矩陣運作：

| 觸發節點 (Trigger Event) | 具體情境說明 (When it Happens) | 必須同步的 Markdown 文件 | Git Commit 動作與指令 | 對話備份+摘要動作 (Session Archiving) |
| :--- | :--- | :--- | :--- | :--- |
| **1. 開場喚醒 / 接收需求** | 開啟新對話，或使用者提出新任務 | **唯讀讀取**：執行 `run.py agent-init` 讀取 `HANDOFF.md` 與 `TASKS.md` | ❌ 不 Commit | ❌ 不備份（剛開場尚未有新結論） |
| **2. 架構調整 / 檔案增刪** | 新增/刪除檔案、調整模組目錄、重構檔案結構 | **即時更新** `docs/STRUCTURE.md`；若有架構重大決策，更新 `docs/adr/` 與 `docs/ARCHITECTURE.md` | 隨該功能一併提交，或執行 `run.py save "<English_message>"` | ❌ 不備份 |
| **3. 治理標準 / 規則改進** | 使用者提出新流程規範、命名限制或 coding 規則 | 1. 更新 `docs/CODING_RULES.md`<br>2. 更新 `AGENTS.md`<br>3. **同步更新** `PROJECT_INIT_STANDARD.md` | 執行 `run.py save "docs: update ..."` | ❌ 不備份 |
| **4. 完成單項功能 / 步驟** | 功能實作完成、Bug 修復、且單元測試通過 (Proof of Execution) | **即時更新** `memory/TASKS.md`，將該任務勾選並標註 `[x] [YYYY-MM-DD] ...` | **小步快跑 Commit**：執行 `run.py save "<English_conventional_msg>"` | ❌ 不備份（保持對話流暢，避免碎裂檔） |
| **5. 使用者離席 / 中途暫停** ⭐ | 使用者說「要去上課」、「先暫停」、「等下再弄」 | 1. 刷新 `memory/HANDOFF.md`（更新當前時間戳 + 接手指令）<br>2. 核對 `memory/TASKS.md` 狀態 | **離席專用 Commit**：執行 `run.py handoff "<English_reason>"` | **⭐ 立即執行**：呼叫 `run.py archive-sessions`，自動生成本次主題高密度 `-summary.md` 並同步 `-transcript.md`！ |
| **6. 里程碑發布 / 階段結案** ⭐ | Sprint 全數完成驗收、發布新版本號、或切換至全新大專題 | 1. 更新 `CHANGELOG.md` 登錄新版號與日期<br>2. 在 `memory/TASKS.md` 歸檔當前 Sprint | **發布專用 Commit**：執行 `run.py publish "<English_release_notes>"` | **⭐ 立即執行**：呼叫 `run.py archive-sessions`，執行全量會話雙軌雙封存！ |

---

## 三、 CODING_RULES 雙層架構標準 (Universal Base + Domain Overlay)

為讓代碼規範在任何新專案中皆可直接繼承，同時允許個別專案自由擴充特化規範，所有專案的 `docs/CODING_RULES.md` 必須嚴格採雙層架構：

### 1. 第一部：通用軟體工程基線 (Universal Core Standards)
- **特性**：所有專案 **100% 通用**，嚴禁寫入特定業務或領域偏好。任何新專案直接拷貝繼承。
- **涵蓋範疇**：
  1. SOLID 物件導向設計準則（SRP/OCP/LSP/ISP/DIP，單檔 < 300 行，單函式 < 50 行）。
  2. 純函數運算與副作用邊界隔離（核心邏輯無 I/O、衛語句提前返回、最大嵌套 $\le 3$）。
  3. 強型別標註與 Data Contract（100% Type Hints，以 `@dataclass(frozen=True)` 取代無型別字典）。
  4. 防衛性編程與原子性檔案寫入（`NamedTemporaryFile` + `os.replace` 原子置換）。
  5. 異常處理禁忌（嚴禁裸 `except:`、嚴禁靜默失敗、強制 `raise ... from err` 保留呼叫鏈）。
  6. 拒絕幽靈修復原則（Proof of Execution，提供日誌或測試通過證據）。
  7. 結構化診斷日誌三要素（Where + Why + How to Fix）。
  8. 零硬編碼絕對路徑（一律採 `Path(__file__).resolve().parent` 動態推導）。
  9. 臨時實驗室隔離規範（`scratch/` 不入 Git）。
  10. 提交前文檔同步與全英文 Commit 規範。
  11. 決策衝突阻斷協議（ADR Circuit Breaker）。
  12. 12-Factor 環境變數配置隔離（`.env.example` 樣板）。

### 2. 第二部：本專案專屬領域擴充 (Project Domain Extensions)
- **特性**：針對該專案技術棧與業務領域所設定的特化規則。
- **範例與擴充方式**：
  - **書籍與文獻處理專案**：macOS 原生能力與 Apple Vision 優先、4GB RAM 軟硬體前置守衛、Ollama 自動除錯與固定提示詞、LaTeX 括號閉合驗證、`data/needs_review/` 隔離區、`literature` 命名規範。
  - **Web 全端專案**：React Server Components 邊界、Tailwind CSS 設計規範、Zod 輸入校驗、Prisma 遷移規範。
  - **後端 API 專案**：FastAPI 依賴注入規格、SQLAlchemy 異步 Session 生命週期、Pydantic v2 Schema 驗證。
  - **原則**：領域擴充只能追加在第二部，絕不反向污染第一部的通用條款！

---

## 四、 專案全自動化操作與觸發時機規範 (The 8 Autonomous Triggers)

為確保專案在無人值守或 AI 協同開發時具備極致的穩定性與自動化，以下 8 大操作必須設定確定性自動觸發時機：

| 編號 | 自動化操作項目 | 具體觸發時機 (When to Trigger) | 自動執行的動作 (Automated Action) |
| :--- | :--- | :--- | :--- |
| **1** | **存檔前自動測試門禁** (Pre-Save Test Gate) | 每次執行 `run.py save` 進行本地代碼提交時 | 自動秒級執行 `python -m unittest discover tests`；若有失敗立即阻斷 Commit 並顯示報錯，全數通過才放行。 |
| **2** | **發布前全流程自動門禁** (Pre-Publish Pipeline) | 每次執行 `run.py publish` 發布正式里程碑時 | 依序自動執行：(1) 全量單元測試 ➔ (2) 會話雙軌歸檔 (`archive-sessions`) ➔ (3) 清理過期暫存檔 ➔ (4) Squash Merge 到 main。 |
| **3** | **Ollama 斷線背景自動喚醒** (Auto-Wake Ollama) | 需要調用模型但 Port 11434 離線時 | 自動背景啟動 `ollama serve`，等待 3 秒重試；若成功則無縫對接，若失敗自動切換為純規則優雅降級。 |
| **4** | **硬體受限自動平滑降級** (Hardware Degradation) | 啟動高算力處理前（RAM < 4GB、低電量電池模式、SSD < 10GB） | 自動關閉本地大模型深層掃描，切換為輕量純規則 Regex；若磁碟空間不足則拒絕大批次切圖並於日誌發出警報。 |
| **5** | **看門狗來檔自動轉檔** (Watchdog Ingestion) | 常駐 `run.py watchdog` 偵測到 `data/input/` 目錄出現新檔案時 | 先巡檢軟硬體安全 ➔ 自動識別書籍或文獻 ➔ 派發至專屬管線轉檔 ➔ 輸出至 `data/output/` ➔ 標記已處理防重複。 |
| **6** | **瑕疵自動自我修復與隔離** (Self-Healing & Quarantine) | LaTeX 括號破損、OCR 置信度 < 0.80、或目錄不符 `manifest.json` 時 | 打包上下文自動呼叫模型修復 1 次；若修復失敗或處於降級狀態，自動拋入 `data/needs_review/` 隔離存檔，主流程不卡死。 |
| **7** | **過期暫存與當機殘留自動清理** (Temp Auto-Pruning) | 每次執行 `run.py doctor`、`run.py save` 或 `run.py publish` 時 | 自動掃描並刪除上次程式當機或中斷殘留的 `*.tmp.*` 原子寫入暫存檔，保持磁碟乾淨。 |
| **8** | **依賴異動環境自動同步** (Dependency Auto-Sync) | `pyproject.toml` 被修改，或執行時捕捉到 `ModuleNotFoundError` 時 | AI 自動執行 `uv sync`，重新對齊虛擬環境依賴，杜絕缺套件報錯。 |

---

## 五、 開案一鍵初始化檢查清單 (AI Checklist)

任何 AI Agent 在接收到本指南後，必須按以下清單逐一檢查並主動執行，最後向使用者回報：
- [ ] 1. 建立 `.git/hooks/pre-push` 並給予執行權限 (`chmod +x`)。
- [ ] 2. 建立 `memory/`、`docs/`、`scratch/`、`logs/`、`data/input/`、`data/output/`、`data/needs_review/`。
- [ ] 3. **主動撰寫 Python 軟硬體基線探針與安全守衛模組 (`src/guards/hardware.py` / `src/guards/ollama_guard.py`)**。
- [ ] 4. 建立 `pyproject.toml` 與 `.env.example`，鎖定環境與依賴版本。
- [ ] 5. 建立 `tests/` 測試目錄結構 (`__init__.py`, `unit/`, `integration/`)，確保測試直跑。
- [ ] 6. 建立 `OPERATIONS.md`，填入該新專案的 30 秒啟動與常用指令。
- [ ] 7. 建立 `AGENTS.md`，填入該新專案的意圖派發清單、同步時機矩陣與開場喚醒指令。
- [ ] 8. 建立 `docs/STRUCTURE.md`，標註當前所有模組職責。
- [ ] 9. 建立 `docs/CODING_RULES.md`，落實雙層架構（第一部通用基線 + 第二部領域擴充）。
- [ ] 10. 建立 `.agent/skills/` 分層技能體系（總入口 + 專屬子技能）。
- [ ] 11. 在 `run.py` 封裝 `agent-init`、`doctor`、`process`、`save`、`handoff`、`publish`、`watchdog`、`archive-sessions` 等快捷指令。
- [ ] 12. 主動執行第一次本地 Git 初始化存檔（**使用英文 Commit**）：
  `[YYYY-MM-DD] chore: initialize project standard governance and architecture`。
