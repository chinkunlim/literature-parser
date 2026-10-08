# 書籍與文檔排版轉換系統標準作業流程指南 (WORKFLOW_GUIDE.md)

## 1. 系統定位
本手冊整合原 `OPERATIONS.md` 與標準 Agent 執行流程，提供書籍、PDF、EPUB 轉 Markdown 與數學公式/表格/圖形提取之標準作業流程（SOP）。

# 🚀 OPERATIONS.md (專案操作速查手冊)

> 💡 **專為「3 個月後的自己」與「剛喚醒的 AI Agent」設計**。無論何時重啟專案，請先閱讀此手冊，30 秒內即可快速上手，無需重新通讀原始碼！

---

## 1. 喚醒三部曲 (30 秒冷啟動)

每當重新啟動專案，請按以下順序執行：

```bash
# 步驟 1：確認本地 Ollama 服務（若未啟動可手動點擊 App 或啟動服務）
brew services start ollama   # 或直接打開 macOS 上的 Ollama 應用程式

# 步驟 2：執行系統軟硬體與環境前置健檢 (Doctor)
uv run python run.py doctor
```
> 若所有檢查均顯示 `[PASS]` 或 `[OK]`，即可開始進行書籍或論文處理。

---

## 2. 最常用的日常指令 (Top 4 Commands)

### ① 處理書籍 (Book Pipeline)
將 PDF 或 EPUB 放入 `data/input/books/`，執行：
```bash
uv run python run.py process data/input/books/your_book.pdf
```
*系統將自動執行：目錄解析 ➔ 章節拆分 ➔ 雙頁文意縫合 ➔ OCR/LaTeX 處理 ➔ Ollama 驗證 ➔ 輸出至 `data/output/books/`。*

### ② 處理學術文獻 / 論文 (Literature Pipeline)
將論文 PDF 放入 `data/input/literature/`，執行：
```bash
uv run python run.py process data/input/literature/nature_paper.pdf
```
*系統將自動執行：雙欄帶狀排版流動 ➔ 摘要 (Abstract) 提取 ➔ APA/IEEE 參考文獻結構化解析 ➔ 輸出至 `data/output/literature/`。*

### ③ 執行 Ollama 自動喚醒與自我除錯測試 (自檢驗收)
```bash
uv run python run.py test-ollama-auto-trigger
```

### ④ 匯出為標準 EPUB 3 電子書 (EPUB Export)
```bash
# 將單篇文獻或 Markdown 轉為 EPUB 3
uv run python run.py epub data/output/literature/2002-01194-001/

# 將整本教科書所有章節打包為一本完整電子書
uv run python run.py epub data/output/books/Research_Methods/

# 於轉檔時直接一鍵產出 Markdown 與 EPUB 雙版本
uv run python run.py process data/input/literature/paper.pdf --epub
```

### ⑤ 日常本地存檔、結束對話與離席交接 (Git Local-Only)
```bash
# 一般進度存檔（自動更新文檔時間戳並 commit）
uv run python run.py save "完成雙欄排版修正"

# 結束對話（自動執行三部曲：1. 雙軌歸檔 2. 檢核所有 md 包含 .agent/skills/ 3. 測試與 commit）
uv run python run.py end-session "完成對話任務與文檔同步"

# 要去上課或外出中斷（自動更新 memory/HANDOFF.md 並 commit）
uv run python run.py handoff "去上課暫存進度"
```

### ⑤ 全自動對話雙軌封存 (Session Archiving)
```bash
# 自動掃描當前與歷史會話 (嚴格過濾本專案)，更新 memory/sessions/ 雙軌總結與紀錄
uv run python run.py archive-sessions
```

### ⑥ 軟硬體一體化看門狗 (Integrated Watchdog)
```bash
# 常駐監聽 data/input/ 新檔案，同時守衛 RAM、SSD 與電池安全，來檔即轉
uv run python run.py watchdog
```

---

## 3. 開發存檔與會話封存六大節奏 (The 6 Golden Triggers)

| 時機點 | 觸發事件 | 該改哪個 MD？ | Git 指令 | 會話歸檔 (`archive-sessions`) |
| :--- | :--- | :--- | :--- | :--- |
| **1. 開場喚醒** | 接收新任務 | 唯讀讀取 `HANDOFF.md`, `TASKS.md` | ❌ 不 Commit | ❌ 不歸檔 |
| **2. 架構異動** | 檔案/模組增刪 | 即時更新 `docs/ARCHITECTURE.md` | `run.py save "<msg>"` | ❌ 不歸檔 |
| **3. 規則調整** | 流程/約束更新 | 更新 `CODING_RULES.md`, `WORKFLOW_GUIDE.md` | `run.py save "<msg>"` | ❌ 不歸檔 |
| **4. 功能完成** | 單元測試通過 | 勾選 `memory/TASKS.md` | `run.py save "<msg>"` | ❌ 不歸檔 |
| **5. 離席暫停** ⭐ | 上課/外出/暫停 | 刷新 `memory/HANDOFF.md` | `run.py handoff "<reason>"` | **⭐ 立即執行** |
| **6. 里程碑結案** ⭐| 版本發布/大交接 | 更新 `CHANGELOG.md`, `TASKS.md` | `run.py publish "<notes>"` | **⭐ 立即執行** |

---

## 4. 常見狀況與疑難排解 (Troubleshooting)

### Q1: 終端機顯示 `[Warning] Battery Mode Detected` 或 `Low Battery`？
- **原因**：筆電處於電池模式且電量偏低。
- **處理**：系統會自動**降級/跳過重度 Ollama 模型**，改用輕量語法規則檢查，防止筆電瞬間斷電。如需強制執行，請插上電源線，或帶入參數 `--ignore-battery`。

### Q2: 提示 `[RAM Guard] Available Memory < 4.0GB`？
- **原因**：macOS 可用記憶體不足，若啟動本地大模型可能導致系統瘋狂 Swap 甚至凍結。
- **處理**：請先關閉其他高耗能應用程式（如 Docker、瀏覽器分頁），或待釋放記憶體後再行執行。

### Q3: 提示 `Ollama connection refused` 或模型未下載？
- **原因**：Ollama 守衛探活失敗，或指定模型尚未 Pull。
- **處理**：
  1. 執行 `curl http://localhost:11434/api/tags` 確認服務是否運行。
  2. 執行 `ollama pull qwen2.5:7b`（或專案指定模型）。
  3. 系統具備**優雅降級（Graceful Fallback）**，未開 Ollama 仍會繼續轉檔，並在輸出 Markdown 頂部標註 `[未經 AI 複檢]`。

### Q4: 某些公式或排版解析失敗，主流程中斷了嗎？
- **安心機制**：主流程**絕不會**因單一頁面錯誤而崩潰！有疑慮的段落會自動丟入 `data/needs_review/` 隔離區，其餘章節繼續正常處理。您可於事後人工查看該目錄進行微調。

---

## 5. 專案目錄地圖版本說明 (Directory Maps)

- **【精簡摘要版】**：請見本手冊與 [README.md](README.md)，供 30 秒快速冷啟動時掌握核心骨幹。
- **【完整詳細版】**：請直接參閱 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，全景收錄全專案每一個檔案的功能職責、依賴關係、設計備註與防重構約束。

