# 🗄️ 會話雙軌歸檔總結：架構深度解耦、PromptRegistry 提示詞中樞與防重構治理標準實裝

- **會話日期**：2026-09-24 ~ 2026-09-25
- **會話識別碼 (Conversation ID)**：`c6a41fa0-96ad-4c71-adce-cc411951f419`
- **對應完整對話紀錄 (Transcript)**：[`2026-09-24-uv-run-python-runpy-agent-init-additional-meta-transcript.md`](file:///Users/limchinkun/Desktop/books/memory/sessions/2026-09-24-uv-run-python-runpy-agent-init-additional-meta-transcript.md)

---

## 1. 核心需求與背景 (User Requirements & Context)

1. **圖表語義定位與段落縫合**：解決 Figure 2 穿插在跨頁指示說明段落中間導致段落截斷的問題，要求所有圖表放置於首次提及之完整段落後。
2. **學術文獻批次分析與 Profile 萃取**：分析 `data/input/literature/` 所有文獻格式，生成精準物理座標與版面配置 `document_profile.json`。
3. **文獻排版瑕疵修復與格式對齊**：修正全量文獻輸出排版，解決空標題、側欄干擾、黏連參考文獻、OCR 統計符號亂碼等問題。
4. **格式深度稽核工具與防呆機制**：開發專門的格式稽核器 (`FormatAuditor`)，支援 Ollama 語義複核，並建立「零容忍物理硬不變量門禁 (`QualityInvariantGuard`)」，杜絕「有錯還報對」之假陽性。
5. **修復手冊庫 (`FixPlaybook`) 與 Ollama 程式合成沙盒 (`OllamaRecipeSynthesizer`)**：建立專案修復程式手冊庫，並允許 Ollama 自主撰寫 Python 修復腳本，透過 AST 靜態語法檢查與沙盒隔離測試，再晉升為正式手冊。
6. **全專案架構解耦與防重構標準**：
   - 提取跨模組共用純函數工具至 `shared_text.py`。
   - 集中 Ollama 提示詞至強型別 `PromptRegistry`（`src/guards/prompts.py`）。
   - 將 1,820 行巨石 `run.py` 拆解為 `src/cli/` 子套件，使 `run.py` 控制在 200 行以內。
   - 解耦 1,206 行 `layout_detector.py`，拆分出 `vector_figure_parser.py` 與 `eoc_parser.py`。
   - 明確文檔分級標準：`docs/STRUCTURE.md`（完整詳細版 SSOT）與 `README.md` / `OPERATIONS.md`（精簡摘要版）。

---

## 2. 重大架構與技術決策 (Major Architectural Decisions)

1. **PromptRegistry 單一真理來源**：所有大模型提示詞統一集中於 `src/guards/prompts.py` 中的 `PromptRegistry` 類別，杜絕各模組硬編碼提示詞，並嚴格連結專案修正規格（KaTeX `\$`、正則 `\g<1>`、APA 表格附註、雙欄閱讀流）。
2. **命令調度模組化架構 (`src/cli/`)**：`run.py` 僅保留極簡 CLI 派發器（$\le 200$ 行），其餘業務命令收斂至 `src/cli/common.py`、`cli_audit.py`、`cli_fix.py`、`cli_git.py`、`cli_process.py` 與 `cli_project.py`。
3. **版面解析子模組專責化**：版面總協調器 `layout_detector.py` 行數降至 662 行，專責向量圖抽取委派給 `VectorFigureParser`，章末習題與雙欄解交錯委派給 `EndOfChapterParser`。
4. **純文字共用工具集中化**：建立 `src/doc_processor/utils/shared_text.py`，收攏孤立頁碼、KaTeX 貨幣轉義、OCR 統計符號修復、稿件水印過濾、黏連引用等純函數清洗轉換。
5. **零容忍物理硬不變量防線**：建立 `QualityInvariantGuard`，以 7 大物理不變量（標題非空、摘要存在、參考文獻獨立、LaTeX 括號閉合、無表格洩漏、無孤立頁碼、非空白檔案）防呆，一票否決假陽性。
6. **修復手冊與漸進式 AST 沙盒**：`FixPlaybook` 內建 8 大專用修復配方；AI 合成修復程式經 AST 語法檢驗與沙盒回歸測試後暫存於 `fixes/staged/`，經審查後始可轉正至 `fixes/promoted/`。
7. **文檔分級雙軌標記**：`docs/STRUCTURE.md` 標註為【完整詳細版】；`README.md` 與 `OPERATIONS.md` 標註為【精簡摘要版】。

---

## 3. 程式碼與檔案具體變更 (Concrete File Changes)

- **新增核心模組**：
  - `src/guards/prompts.py`: 統一 `PromptRegistry` 集中管理 12 大 Ollama 提示詞。
  - `src/cli/`: `__init__.py`, `common.py`, `cli_audit.py`, `cli_fix.py`, `cli_git.py`, `cli_process.py`, `cli_project.py`。
  - `src/doc_processor/utils/shared_text.py`: 跨模組共用純函數文字與正則清洗工具。
  - `src/doc_processor/parsers/layout/vector_figure_parser.py`: 向量圖表與研究流程圖專責抽取。
  - `src/doc_processor/parsers/layout/eoc_parser.py`: 章末練習題、詞彙索引與延伸閱讀專責解析。
  - `src/doc_processor/verification/format_auditor.py`: 8 維度文獻排版格式深度稽核器。
  - `src/doc_processor/fixes/playbook.py`: 專案專屬修復手冊庫。
  - `src/doc_processor/fixes/synthesizer.py`: Ollama 程式修復合成器與 AST 靜態沙盒。
  - `src/doc_processor/core/invariants.py`: 物理硬不變量安全守衛 (`QualityInvariantGuard`)。
- **重構與精簡模組**：
  - `run.py`: 由 1,820 行精簡至 200 行極簡調度器。
  - `src/doc_processor/parsers/layout_detector.py`: 由 1,206 行解耦降至 662 行。
  - `src/doc_processor/verification/ollama_verifier.py`: 提示詞全部重構改用 `PromptRegistry`。
  - `src/doc_processor/parsers/layout/table_llm_fixer.py`: 改用 `PromptRegistry.table_reconstruction_prompt`。
  - `src/doc_processor/profiler/ollama_profiler.py`: 改用 `PromptRegistry.book_features_detection_prompt`。
- **新增單元測試**：
  - `tests/test_v37_semantic_figure_table_placement.py`
  - `tests/test_v38_literature_batch_profiling.py`
  - `tests/test_v39_format_auditor.py`
  - `tests/test_v40_fix_playbook_and_invariants.py`
  - `tests/test_v41_ollama_synthesizer.py`
  - `tests/test_v42_modular_refactoring.py`
- **治理文檔與結構地圖全面更新**：
  - `docs/STRUCTURE.md`（完整詳細版，逐一詳列所有資料夾、檔案與公開類別職責）
  - `README.md` & `OPERATIONS.md`（精簡摘要版，增添分級徽章與雙向導航連結）
  - `docs/CODING_RULES.md`（雙層架構，增列行數熔斷、上帝類別防範、PromptRegistry、AST 沙盒與硬不變量規範）
  - `AGENTS.md`（增列第 12 至 16 條核心鐵律）
  - `PROJECT_INIT_STANDARD.md`（擴充核心哲學第 31 至 36 條）
  - `.agent/skills/`（全面更新總調度技能與兩大領域子技能）

---

## 4. 驗證與測試結果 (Verification & Quality)

- **單元測試全數通過**：`uv run python -m unittest discover tests/`：**229/229 測試 100% 通過**（耗時約 5.1 秒）。
- **全量文獻稽核全數通過**：`uv run python run.py audit --all`：**10 篇學術文獻 100% PASS**（得分率 96.0% ~ 100.0%）。
- **Python 語法靜態編譯**：所有 Python 原始碼均通過 `python -m py_compile` 驗證，0 語法錯誤。

---

## 5. 目前狀態與接手引導 (Current State & Next Steps)

- **專案狀態**：本專案代碼風格優異、架構模組職責清晰、無任何 God Class / God File，所有文檔均已完整同步。
- **下次喚醒第一步**：
  ```bash
  uv run python run.py agent-init
  ```
  系統會自動簡報守則與交接狀態，直接接續下一步任務！
