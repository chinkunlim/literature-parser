# 🗄️ 會話深度紀要：專案治理、企業級標準、雙層代碼規範與自動化體系建立

- **對應完整對話紀錄**：[2026-09-23-project-architecture-and-governance-transcript.md](2026-09-23-project-architecture-and-governance-transcript.md)
- **會話 ID**：`d934528e-eb4f-4097-8457-50cc94bfb932`
- **會議/會話日期**：2026-09-23 至 2026-09-24
- **參與角色**：使用者 (Developer) & Antigravity (AI Assistant)
- **主題**：解決專案長期痛點、剔除歷史過渡冗餘、落實軟硬體守衛與自動觸發、建立雙層代碼規範與 30 大核心工程鐵律、一鍵開案 CLI 腳手架 (`run.py init-project`)

---

## 一、 背景與原始痛點回溯

1. **檔案混亂與職責重疊**：
   - 早期留存過多重複 Markdown 檔案，缺乏「臨時檔案（Scratchpad）」與「長期資產（Docs）」的生命週期區分。
   - 單一決策檔案過大造成 Token 消耗與記憶污染。
2. **開發過程的中斷（如去上課、外出）**：
   - 使用者中途需離開去上課，回來時 AI 上下文重置，無法無縫接續。
3. **「幽靈修復」與軟硬體失衡**：
   - 過去宣稱修復，但預設關閉大模型；缺乏對可用 RAM、電池模式、SSD 空間的保護，容易卡頓凍結。
4. **規則無法通用至其他專案**：
   - 使用者希望這套標準在開立任何新專案時皆能 100% 複製沿用，且個別專案有自己規則時能無污染擴充。

---

## 二、 核心架構決策與共識落地

### 1. 跨專案通用開案標準 (`PROJECT_INIT_STANDARD.md` 升級至 30 大鐵律)
- 將標準全面昇華為 **30 大核心工程鐵律**，包含 SOLID 物件導向、純函數與副作用邊界隔離、強型別 Data Contract、防衛性編程與原子性檔案寫入、12-Factor 配置、雙層代碼規範、六大同步矩陣、八大自動化防線、秒級測試迴圈與離線主權。

### 2. 雙層代碼規範架構 (`docs/CODING_RULES.md`)
- **第一部：通用軟體工程基線 (Universal Core Standards)**：所有專案 100% 通用，定義現代高品質軟體工程不可逾越的底線，零污染繼承。
- **第二部：本專案專屬領域擴充 (Project Domain Extensions)**：特定技術棧與業務約束（如 Apple Vision、4GB RAM 守衛、Ollama 修復、`literature` 命名）。

### 3. 全生命週期六大黃金時機同步矩陣 (The 6 Golden Triggers)
- 規範開場喚醒、架構異動、規則改進、功能完成、離席暫停與里程碑結案時，何時同步哪個 MD、何時執行 Git Commit、何時自動進行會話雙軌封存。

### 4. 專案全自動化八大防線 (The 8 Autonomous Triggers)
- 存檔自動測試門禁、發布全流程門禁、Ollama 背景自動喚醒、硬體受限平滑降級、看門狗來檔自動轉檔、瑕疵自動修復隔離、過期暫存自動清理、環境依賴自動同步。

### 5. 一鍵開案 CLI 腳手架實裝 (`run.py init-project`)
- 在總指揮腳本實作 `init-project <dir>`，可在 3 秒內自動建立符合 30 大鐵律的完整專案目錄（14 個目錄）、Git 安全鎖、軟硬體守衛、雙層代碼規範、測試與 run.py 總指揮。

### 6. 整潔根目錄與單一真理來源
- 根目錄過渡資料夾（`inbox/`, `processed/`, `output/`）與過渡腳本（`verify_accuracy.py` 等）徹底清除。
- 歷史遺留的根目錄 `skills/` 資料夾徹底移除，確立 `.agent/skills/` 為官方原生唯一標準。

---

## 三、 本次重大產出清單

1. **規範文檔**：`PROJECT_INIT_STANDARD.md` (30 大鐵律), `OPERATIONS.md`, `AGENTS.md`, `CHANGELOG.md` (登錄 v1.0.0-rc2), `docs/STRUCTURE.md`, `docs/CODING_RULES.md` (雙層結構), `memory/TASKS.md`, `memory/HANDOFF.md`。
2. **關鍵程式**：
   - `run.py`（支援 `doctor`, `process`, `save` 帶測試門禁, `handoff`, `publish` 帶自動封存與 Tag, `watchdog`, `archive-sessions`, `init-project`）。
   - `src/guards/hardware.py`、`src/guards/ollama_guard.py`、`src/guards/validator.py`、`src/utils/logger.py`。
   - `.git/hooks/pre-push` 物理安全鎖。
3. **驗證數據**：171 個單元測試在 **0.11 秒** 內全數通過 (100% PASS)。
