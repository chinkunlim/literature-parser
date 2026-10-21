# 架構重大決策記錄 (DECISIONS.md - ADR)

本文件整合本專案所有架構決策記錄（原 `docs/adr/`）。

### 0001-ollama-hardware-guard-and-auto-verify.md

# ADR-0001: Ollama 自動除錯觸發與軟硬體前置攔截守衛

- **日期**：2026-09-23
- **狀態**：[Status: Accepted]
- **決策者**：使用者 & Antigravity

---

## 背景與問題陳述 (Context)

在先前的專案實作中，Ollama 本地大模型驗證存在以下重大缺陷：
1. **假修復（Ghost Fix）**：程式碼中存在 `OllamaVerifier` 實作，但預設參數為 `use_ollama: bool = False`，導致日常轉檔中從未實際調用，AI 聲稱已修正但實際上並未運作。
2. **缺乏硬體保護**：本地大模型若在可用 RAM 不足（< 4GB）時啟動，會導致 macOS 嚴重記憶體交換（Swap）甚至死機；若在電池模式下高並發運行，會瞬間耗盡電力。
3. **缺乏輸入與輸出自動攔截機制**：輸入格式與 JSON 描述不符、或輸出 LaTeX 公式毀損時，缺乏自動喚起 Ollama 進行自我修復的機制。

---

## 決策內容 (Decision)

1. **全面改由守衛自動決策**：
   - 移除原先硬編碼的 `use_ollama=False` 預設。
   - 改由 `src/guards/ollama_guard.py` 與 `src/guards/hardware.py` 在執行期動態評估：
     - **硬體安全（RAM ≥ 4GB 且非低電量電池模式）**：預設自動喚醒 Ollama 進行語義與公式深度驗證。
     - **硬體受限或無 Ollama**：自動優雅降級為純規則檢查，並在輸出 Markdown 中記錄，主流程絕不崩潰。
2. **強制兩大自動喚醒 Hook**：
   - **Hook 1 (Input Guard)**：比對輸入檔案與 manifest.json，若結構缺失自動呼叫 Ollama 分析。
   - **Hook 2 (Output Self-Healing Guard)**：LaTeX 語法錯誤或文本異常時，自動將 `(上下文, 錯誤訊息)` 派送給 Ollama 進行單次自動修復嘗試。
3. **提供獨立驗收指令**：
   - 建立 `run.py test-ollama-auto-trigger`，透過注入受損測試檔案驗收自動喚起機制。

---

## 後果與影響 (Consequences)

### 正面影響 (Pros)
- 徹底杜絕「死代碼」與「宣稱修復但未啟動」的隱形巨坑。
- 保護使用者的筆電硬體與電池安全，避免外出時被大模型吸乾電量。
- 具備自動容錯與自我修復能力，大幅降低人工微調 LaTeX 的時間。

### 負面影響 / 限制 (Cons)
- 首次冷啟動時需花費數秒進行硬體與 Ollama 探活檢查。

### 0002-domain-split-book-and-paper.md

# ADR-0002: 書籍與期刊領域解耦與 data/ 實體目錄路由

- **日期**：2026-09-23
- **狀態**：[Status: Accepted]
- **決策者**：使用者 & Antigravity

---

## 背景與問題陳述 (Context)

使用者需要將不同類型的電子檔（書籍、學術期刊、論文）轉換為方便做筆記的 Markdown 格式（如 Obsidian 雙鏈筆記）：
1. **版面結構迥異**：書籍以多章節、單欄、深度樹狀目錄為特徵；期刊論文以雙欄排版、摘要 (Abstract)、引用文獻 (Citations/BibTeX) 為特徵。
2. **AI 自動猜測的不可靠性**：如果讓 AI 或規則去啟發式猜測檔案類型，極易發生判斷失誤，導致拿雙欄切割器去切整本教材，或拿書籍章節拆分器去處理 6 頁論文。
3. **未來的擴充需求**：未來可能還會增加投影片（Slides/PPT）、網頁剪藏等格式，程式如果未良好解耦，每次擴充都會引發嚴重的代碼回歸與衝突。

---

## 決策內容 (Decision)

1. **實體路徑即路由 (Convention-based Routing)**：
   - 在 `data/input/` 下實體劃分 `books/` 與 `journals/`。
   - 使用者將檔案丟入對應資料夾，程式透過輸入路徑直接確定調用 `BookPipeline` 或是 `JournalPipeline`，達到 100% 零猜測誤差。
2. **雙軌核心與共享基礎庫**：
   - 在 `src/book_processor/pipelines/` 徹底分離 `textbook_pipeline.py` 與 `journal_pipeline.py`。
   - 共享底層的核心 OCR、LaTeX 正規化工具與安全守衛。
3. **人機隔離防呆區 (`data/needs_review/`)**：
   - 任何無法透過自動化或 Ollama 自我修復的疑難頁面，自動拋入隔離區，主轉檔流程不停滯。

---

## 後果與影響 (Consequences)

### 正面影響 (Pros)
- 徹底消除分類猜測錯誤與 Token 浪費。
- 未來擴充新電子檔類型（如 `data/input/slides/`）時，只需新增對應適配器，既有書籍與論文程式碼完全不受影響。
- 產出目錄結構清晰，直接對接 Obsidian 筆記庫。

### 負面影響 / 限制 (Cons)
- 使用者存放檔案時需手動放至正確的子資料夾。

