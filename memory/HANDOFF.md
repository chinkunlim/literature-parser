# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-25 12:36
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **全專案代碼深度解耦、模組重構與 PromptRegistry 統一架構實裝**：
  1. **統一 Ollama 提示詞中樞 (`src/guards/prompts.py`)**：
     - 實作強型別 `PromptRegistry` 類別，統一收攏 LaTeX 公式修復、Manifest 結構校驗、語義排版格式稽核、修復配方合成、自我修復重試、雙欄展開與引用解析提示詞。
     - 與專案最新修復規則（KaTeX `\$` 貨幣轉義、Python 正則 `\g<1>` 反向引用、APA 表格附註 `<tfoot><tr class="table-notes">`、雙欄閱讀流）緊密對齊。
  2. **模組化重構龐大命令中心 (`run.py` ➔ `src/cli/*`)**：
     - 建立 `src/cli/` 專用領域子套件：
       - `common.py`: 根目錄錨定、過期暫存清理、文檔時間戳同步。
       - `cli_audit.py`: 文獻排版格式全維度稽核與 AI 複核。
       - `cli_fix.py`: 修復手冊清單、套用、沙盒測試與 Ollama 合成。
       - `cli_git.py`: agent-init, save, handoff, end-session, publish, archive-sessions。
       - `cli_process.py`: process, batch 單檔與批次轉檔管線派發。
       - `cli_project.py`: doctor, watchdog, init-project, obsidian-link, status, dashboard, test-ollama-auto-trigger。
     - `run.py` 精簡至 200 行極簡 CLI 派發器。
  3. **提取跨模組共用純函數文字與正則工具 (`src/doc_processor/utils/shared_text.py`)**：
     - 統一集中孤立頁碼、KaTeX 貨幣轉義、OCR 統計符號修復、稿件水印過濾、黏連引用等純函數清洗轉換。
     - `FixPlaybook` 與 `FormatAuditor` 同步繼承引用，消除代碼重複。
  4. **解耦 1,206 行版面特徵解析巨石 (`layout_detector.py` ➔ 662 行)**：
     - 抽取 `VectorFigureParser`（向量圖表與研究符號圖式抽取）至 `src/doc_processor/parsers/layout/vector_figure_parser.py`。
     - 抽取 `EndOfChapterParser`（章末練習題、詞彙索引與延伸閱讀解析器）至 `src/doc_processor/parsers/layout/eoc_parser.py`。
     - `LayoutDetector` 各方法直接委派，保持 100% 向後相容。
  5. **全套測試與文獻稽核 100% 通過**：
     - 全套 229/229 單元測試 100% 通過（5.06 秒）。
     - 全量 10 篇學術文獻全維度稽核 100% 通過（96%~100% 分數）。

#### 2. 目前專案狀態與代碼位置
- 分支：`main`
- 狀態：所有模組、功能、文檔 100% 同步，代碼庫極致整潔，無任何 God class / God file，已完整通過全量測試。

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
