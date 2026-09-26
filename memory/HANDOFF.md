# 🪪 memory/HANDOFF.md (離席交接卡片)

> 💡 本檔案供「去上課、外出、會話結案、或切換至不同 AI Agent」時無縫交接使用。
> 每次離開前由 AI 自動更新；接手之 AI 請直接從最頂部的交接卡開始執行。

---

### 🕒 最新交接時間：2026-09-26 08:14
 
#### 1. 剛剛完成了什麼？ (Session Accomplishments)
- **實裝標準 EPUB 3 電子書自適應生成架構 (`EpubExporter`) 與多格式發布管線**：
  1. **建立多格式匯出模組 (`src/doc_processor/exporter/`)**：
     - `EpubExporter`: 統一跨書籍與學術文獻的 EPUB 3 匯出控制器，具備自適應引擎選擇（Pandoc 優先 + 純 Python 回退）。
     - `PurePythonEpubBuilder`: 零依賴 EPUB 3 封裝引擎，嚴格遵循 IDPF 規範（未壓縮 mimetype 第一位、container.xml、content.opf、雙導航 nav.xhtml 與 toc.ncx、CSS 樣式表、圖片打包與 MathML 宣告）。
     - `MarkdownToXHTML`: 實裝 HTML 標籤棧追蹤器（Tag-Stack Tracker），保證多行 HTML 區塊與巢狀標籤不被破壞；修正 void tags 自閉合 (`<img />`, `<br />`, `<hr />`)、布林屬性規範化 (`<details open="open">`) 與 XML 特殊字符轉義。
     - `LaTeXToMathML`: 支援 LaTeX 公式轉 MathML（`<math>`），並嚴格保護貨幣符號（`&#36;15.50`）。
     - `epub_styles.py`: 提供 EPUB 3 專屬排版樣式表，支援閱讀器深淺色模式自適應、響應式表格與圖說美化。
  2. **支援教科書整本多章節合併與單章獨立匯出**：
     - 自動遍歷 `chapters/` 將所有章節整合進同一本電子書，具備完整層級導航與 Spine 順序。
  3. **CLI 總入口整合 (`run.py epub`)**：
     - 新增獨立指令 `uv run python run.py epub <path>`。
     - 於 `process` 與 `batch` 深度整合 `--epub` 參數，轉檔完成後自動輸出 EPUB 3。
  4. **全套測試 100% 通過**：
     - 新增 `tests/test_v42_epub_exporter.py`，全套 240/240 單元測試 100% 通過（5.4 秒）。
     - 實際驗證 `2002-01194-001.epub` 與 `2008-17521-013.epub` 完整打包且 XML 驗證無誤。

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
