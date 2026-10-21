# 本專案專屬規則 (PROJECT_RULES)

> 規則分兩層：`docs/standards/` 的其他文件是**所有專案通用**的規範（由專案模板提供，`agentctl update` 會更新）；
> 本檔是**只適用這個專案**的規則，由這個專案自己維護，模板更新時不會被覆蓋。每次開工都要讀。

## 1. 領域知識與術語

- **文獻 (Literature / Journal)**：指學術論文 PDF，具有雙欄排版、IMRAD 架構（Introduction, Method, Results, Discussion）、作者資訊與懸掛縮排參考文獻。
- **書籍 (Book / Textbook)**：指教科書 PDF / EPUB，具有多章節、目錄（TOC）、學習目標（Learning Objectives）、專有名詞（Glossary）與章末總結（End-of-Chapter）。
- **斷點紀錄 (Checkpoint)**：記錄章節處理與驗證狀態的清單檔，確保中斷後可優雅恢復（Resume）。
- **修復手冊 (Fix Playbook / Synthesizer)**：存放確定性排版修復規則與由本地 Ollama 演繹之代碼修復配方。

## 2. 本專案特有的規則

- **硬體守衛優先 (Hardware Guard)**：所有啟動本地 Ollama 大模型推理或密集 OCR 運算的任務，必須事先通過 RAM（≥ 2.0GB/4.0GB）與電源狀態（電池低電量防護）檢查，資源不足時應優雅降級或中止。
- **純本地離線保證**：本地大模型服務僅綁定 `http://127.0.0.1:11434`，絕不將資料傳送至外部非授權端點。
- **分層架構隔離**：`orchestrator`、`verifier`、`synthesizer`、`literature_pipeline` 與 `validator` 呼叫外部硬體/Ollama 工具，均定義於 `adapters` 層，`services` 業務邏輯層嚴格禁止逆向引用 `adapters`。
- **組態與知識庫集中**：期刊與出版商配置、標題映射表統一收斂於 `src/literature_parser/config/resources/`，由 `ConfigManager` 提供階層式載入。

## 3. 和通用規範不同的例外

- 無例外。所有程式檔均嚴格遵守 `[quality]` 設定與標準分層規範。

## 4. 禁止事項

- **嚴禁污染輸入目錄**：永遠不要修改 `DATA_DIR/input/` 的原始書籍與論文檔案（嚴格唯讀）。
- **禁止在原始碼內寫入 Log 檔案**：Log 檔案一律輸出至 `DATA_DIR/logs/`，禁止在專案目錄內直接產生 `.log` 檔案。
