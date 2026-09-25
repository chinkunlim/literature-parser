# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-25 08:42
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **全面巡檢與修復全量 10 篇學術文獻版面瑕疵 (10 Literature Documents Full Verification & Audit)**：
  1. **劍橋大學出版社 (CUP) 不對稱側邊欄分離 (`DigitalPDFParser.has_p1_side_rail` & `p1_rail_split_x`)**：
     - 檢測首頁極窄側邊欄（寬度 $< 33\%$），動態將分欄分割線置於側邊欄右側邊界 (`split_x = 0.33 pw`)，徹底解決 `11 Pliatsikas` 首頁左側邊欄期刊/作者資訊與右側主內文水平粘連交錯之問題。
     - 頁眉過濾擴充 Cambridge UP 標識與網址，成功識別並萃取出標準 Markdown 標題 `# Understanding structural plasticity in the bilingual brain: The Dynamic Restructuring Model` 與 `## Abstract`。
  2. **論文標題層級相容與跨行縫合 (`LiteraturePipeline` & `LiteratureMetadataExtractor`)**：
     - 將 H1 標題提升正則擴展為 `#{1,3}`，修復 `Universal_consciousness` 輸出空白標題問題。
     - 支援跨行長標題合併（如 `05 Hartshorne` 之 `Evidence from` + `2/3 million English speakers`），並確保 H1 正式標題優先於快速元數據抽取候選。
  3. **參考文獻格式相容與粘連分離 (`IMRADResolver` & `ReferenceParser`)**：
     - 新增支援 Annual Reviews 之 `LITERATURE CITED` / `Literature Cited` 分隔符識別。
     - 預先拆分粘連在致謝末尾之 `**References**`（如 Elsevier/NIH 論文的 `award). **References** FirstAuthor...`），解除內聯粘連並獨立為標準 `## References` 清單。
     - 支援無括號年代與分號結尾之引用條目（如 `Abrahamsson N. 2012;`）。
  4. **指引建議清單降級處理 (`DigitalPDFParser.is_section_num`)**：
     - 針對 APA 臨床實踐指引（如 `3 Psychotherapy`）中的 28 條建議，自動識別並保留為有序列表條目，避免膨脹為 28 個 `## ` 標題，TOC 成功精簡至標準 5 個核心區塊。
  5. **10 篇文獻全量自動化審計與單元測試 100% 通過**：
     - 197 項單元測試 100% 通過。
     - 10 篇文獻重跑並全數通過版面稽核檢查（`04 Bialystok`, `05 Hartshorne`, `08 Kroll`, `11 Pliatsikas`, `115319`, `2002-01194-001`, `2008-17521-013`, `3 Psychotherapy`, `Journal of Adolescence`, `Universal_consciousness`）。

#### 2. 目前專案狀態與代碼位置
- 分支：`main`
- 狀態：所有 10 篇文獻轉檔結果皆已達到黃金標準；代碼庫全量測試 100% 通過，文檔同步完畢。

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

