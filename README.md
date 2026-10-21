# literature-parser

> Enterprise-grade PDF & EPUB Structured Markdown & Image Extractor with Neural Layout OCR, LaTeX Math & Local Ollama AI Verification.

本專案專注於將教科書（Textbooks）與學術文獻/期刊論文（Academic Literature / Journals）從 PDF 與 EPUB 高精度解析為結構化 Markdown、提取圖表與數學公式（LaTeX），並具備本地 Ollama 自我修復、硬體守衛與 EPUB 3 匯出功能。

---

## 快速開始

### 1. 環境前置檢查
本專案依賴純本地 Python 工具鏈與可選的本地 OCR / PDF 轉換工具：

```bash
# 系統前置軟硬體與 Ollama 健康檢查
uv run literature-parser doctor
```

系統建議工具（選配，用於掃描版 PDF OCR）：
```bash
brew install poppler tesseract
```

### 2. 環境與依賴
專案採用 `uv` 管理環境與虛擬隔離環境：
```bash
python3 scripts/agentctl.py setup --install
```

環境設定檔複製自 `.env.example`（設定檔與資料夾位於專案目錄外之 `DATA_DIR`）：
```bash
cp .env.example .env
```

---

## 常用指令 (CLI)

本專案提供統一命令行入口 `literature-parser`（亦相容 `book-processor` 與 `doc-processor`）：

### 處理文獻或書籍
```bash
# 處理單一學術文獻或書籍
uv run literature-parser process path/to/document.pdf --type journal
uv run literature-parser process path/to/textbook.pdf --type book

# 批次遞迴處理整個目錄
uv run literature-parser batch path/to/folder/ --type journal

# 匯出結構化 Markdown 為標準 EPUB 3 電子書
uv run literature-parser epub path/to/output_dir/ --type book
```

### 驗證與自動修復
```bash
# 執行 Markdown 排版格式與數學符號稽核
uv run literature-parser audit path/to/chapter.md --ollama --fix

# 查看或套用專案排版修復配方 (Fix Playbook)
uv run literature-parser fix list
uv run literature-parser fix apply clean_orphan_page_numbers path/to/chapter.md
```

### 監控與儀表板
```bash
# 查看全域文獻處理進度快照
uv run literature-parser status

# 生成並瀏覽 HTML 視覺化進度看板
uv run literature-parser dashboard
```

---

## 執行測試與品質檢查

```bash
# 執行全套單元與整合測試
uv run python -m unittest discover -s tests -v

# 執行架構分層、型別、註解與秘密審查
python3 scripts/agentctl.py check
```

---

## 檔案與資料分離原則 (Data Isolation)
所有書籍輸入、產出 Markdown、斷點資訊與 Log 均置於專案外的 `DATA_DIR`（預設為 `../../projects-data/literature-parser`）：
- `DATA_DIR/input/`：原始書籍與論文（唯讀）
- `DATA_DIR/output/`：轉換產出之 Markdown 與圖像
- `DATA_DIR/needs_review/`：低信心度或需人工複審之段落隔離區
- `DATA_DIR/state/`：斷點清單與處理進度
- `DATA_DIR/logs/`：結構化執行紀錄（`process.log`）

---

## 安全性與隱私 (Security & Privacy)
- **零資料上雲**：所有文字處理、版面辨識與大模型驗證均在本地執行，Ollama 服務預設僅綁定 `http://127.0.0.1:11434`。
- **機密隔離**：專案程式碼內嚴禁硬編碼任何 API Key，機密與金鑰統一存放於本地 `.env`。

---

## 文件索引

- [`AGENTS.md`](AGENTS.md) — Agent 規則與「文件放哪裡」對照表
- [`.agents/handoff/LATEST.md`](.agents/handoff/LATEST.md) — 交接看板
- [`docs/adr/DECISIONS.md`](docs/adr/DECISIONS.md) — 架構決策紀錄 (ADR)
- [`docs/known-issues/KNOWN_ISSUES.md`](docs/known-issues/KNOWN_ISSUES.md) — 已知問題庫
- [`docs/specs/SPECS.md`](docs/specs/SPECS.md) — 功能規格清單
- [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) — 系統架構與分層設計
- [`docs/standards/PROJECT_RULES.md`](docs/standards/PROJECT_RULES.md) — 本專案特有規則
- [`CHANGELOG.md`](CHANGELOG.md) — 版本變更紀錄
