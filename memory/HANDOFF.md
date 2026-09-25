# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-25 08:31
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **修復學術文獻版面與排版瑕疵 (Universal Literature Layout Defect Fixes)**：
  1. **首頁頁眉與標題保護 (`DigitalPDFParser._is_running_header`)**：限制作者與論文標題頁眉過濾僅在第 2 頁及之後生效，並豁免 14pt 以上字體，完整保護首頁論文標題（例如 `2008-17521-013.md` 的 `# Test-Retest Characteristics of the Balloon Analogue Risk Task (BART)`）。
  2. **首頁雙欄基線避難所 (`page_1_body_start_y`)**：改用 `page_1_body_start_y` (或 0.45 ph) 作為首頁單欄避難所閾值，修復摘要被誤判為雙欄而交錯碎裂之瑕疵，保持單一區塊引用與統計公式完整性。
  3. **作者姓名與摘要候選區清洗 (`LiteratureMetadataExtractor`)**：徹底剔除作者姓名中夾帶之 "Acknowledgments" / "Author Note" 前綴，過濾前置摘要中的期刊卷期與 DOI 字串。
  4. **多行表格附註隔離機制 (`TableParser.fn_start_top`)**：精準捕獲以小數點或 "Note." 開頭的多行表格註釋（如 Elsevier 表格），完整隔離至 `<tfoot><tr class="table-notes">`，消除洩漏至內文之孤兒文字行。
  5. **Elsevier 統計公式與 OCR 分隔符正規化 (`IMRADResolver._fix_ocr_stats`)**：修復 `*t* ð 24 Þ = 2: 06` ➔ `$t(24) = 2.06$`、`M = 4: 46` ➔ `$M = 4.46$`、`s. d. =2.02` ➔ `$SD = 2.02$`、`p o 0: 01` ➔ `$p < 0.01$`。
  6. **真圖 (Raster Images) 標題捕獲與語義定位**：捕獲真圖完整圖說，且所有圖表均精確錨定在第一次提及之完整段落之後，原位置斷句無縫縫合。
  7. **全套測試與驗證 100% 通過**：197 項單元測試 100% 通過，全量驗證 `2002-01194-001.pdf`、`2008-17521-013.pdf`、`Journal of Adolescence` 達成 [SUCCESS (PASS)]。

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

