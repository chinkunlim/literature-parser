# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-25 04:38
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **文獻全自動幾何座標分析與 Profile 生成機制上線 (Universal Profiling)**：
  1. 實作 `CoordinateCalibrator.calibrate_literature_geometry` 與 `calibrate_and_save_literature_profile`，自動掃描每篇文獻之頁面維度、邊界、Header/Footer 截斷點、單雙欄判定與正文起始 Y 座標。
  2. 擴充出版商識別器 `PublisherDetector`，新增 AIP (`10.1063`)、Annual Reviews (`10.1146`)、Cambridge University Press (`10.1017`) 原型與設定檔。
  3. 實作單欄稿件保護 (`is_single_col_doc`)，杜絕單欄稿件被割裂為雙欄。
  4. 實作 NIH/HHS Author Manuscript 浮水印清除器與附錄段落（Author Note, Acknowledgments, Declarations, Funding 等）統一定位於 References 前。
  5. 增強標題與首頁引言識別（解決無顯式 Abstract 標題導致開頭段落遺失問題）。
  6. 解決 KaTeX 貨幣符號轉義（`$12.00` ➔ `&#36;12.00`）與不對稱雙錢號問題。
  7. 全量批次處理 `data/input/literature/` 全部 10 篇學術文獻，**10 篇 100% 全部通過（PASS）驗證**！
  8. 新增 `tests/test_v38_universal_literature_profiling.py`，全套 197 項單元測試 100% 通過。

#### 2. 目前專案狀態與代碼位置
- 分支：`main`
- 狀態：所有模組、功能、文檔 100% 同步，代碼庫極致整潔，已完整提交至本地 Git。

#### 3. 下一個 AI 回來接手時的第 1 步指令 (Next Steps)
```bash
# 開場喚醒儀式（自動讀取本卡片與 AGENTS.md 守則）
uv run python run.py agent-init

# 系統軟硬體與環境前置健檢
uv run python run.py doctor

# 檢視全域處理進度快照
uv run python run.py status
```
接手者請直接向使用者簡報目前狀態，並依使用者下一步指令進行處理！

