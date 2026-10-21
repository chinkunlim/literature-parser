# 系統部署與維運手冊 (docs/DEPLOYMENT.md)

## 1. 運行環境要求 (Prerequisites)

- **作業系統**：macOS 14 (Sonoma) 或更高版本（針對 Apple Silicon M-Series 晶片優化）。
- **Python 環境**：Python 3.11+（由 `uv` 自動鎖定與管理）。
- **套件管理器**：[uv](https://github.com/astral-sh/uv) (v0.5.0+) 與 [Homebrew](https://brew.sh/)。
- **本地大模型服務**：[Ollama](https://ollama.ai/) (建議模型：`qwen2.5:7b` 或 `llama3.1:8b`)。
- **外部二進位工具**：
  - `pandoc`：EPUB 3 匯出引擎（選用，若缺失自動回退至內建 `PurePythonEpubBuilder`）。
  - `poppler`：PDF 渲染與底層文字座標提取工具。

---

## 2. 一鍵冷啟動流程 (Quick Start)

### 步驟 1：克隆專案與同步 Python 依賴
```bash
# 進入專案目錄
cd /Users/limchinkun/Desktop/books

# 使用 uv 秒級建立虛擬環境並安裝鎖定依賴
uv sync
```

### 步驟 2：確認並啟動本地 Ollama 服務
```bash
# 啟動 Ollama 本地服務（若已開啟 Ollama.app 則可略過）
brew services start ollama
# 或直接在終端機啟動：
ollama serve

# 拉取專案推薦模型（用於排版語義修復與標題格式化）
ollama pull qwen2.5:7b
```

### 步驟 3：執行環境完整健檢 (Doctor Check)
```bash
python3 run.py doctor
```
檢查項目涵蓋：
- [x] Python 執行時版本與虛擬環境狀態
- [x] 系統可用 RAM（AC 電源 ≥ 2.0GB / 電池模式 ≥ 4.0GB）
- [x] 磁碟可用空間（SSD ≥ 10GB）
- [x] 電池供電狀態與剩餘電量
- [x] Ollama 守衛探活與預設模型可用性
- [x] 臨時檔案 (`scratch/*.tmp.*`) 清理狀態

---

## 3. 日常作業命令 (Operational Commands)

### 3.1 轉換教科書
```bash
python3 run.py process data/input/books/sample_book.pdf [--epub]
```
- 自動辨識目錄、章節切分、文意雙頁縫合，並於 `data/output/books/` 產出章節 Markdown。
- 附帶 `--epub` 參數時自動呼叫 `EpubExporter` 生成標準 EPUB 3 電子書。

### 3.2 轉換學術文獻 / 論文
```bash
python3 run.py process data/input/literature/paper.pdf [--epub]
```
- 自動辨識雙欄閱讀流、抽取摘要、結構化參考文獻與圖表首引後排。

### 3.3 文獻排版格式深度稽核
```bash
# 全維度格式檢查（8 維度格式掃描）
python3 run.py audit data/output/literature/paper_id/

# 啟用 Ollama 語義複檢與自動修復
python3 run.py audit data/output/literature/paper_id/ --ollama --fix
```

### 3.4 EPUB 3 電子書打包
```bash
# 打包單篇文獻或 Markdown 文件
python3 run.py epub data/output/literature/paper_id/

# 打包整本教科書所有章節
python3 run.py epub data/output/books/book_title/ --output my_book.epub
```

### 3.5 智慧看門狗常駐監聽
```bash
# 常駐監控 data/input/ 來檔即轉，內建 RAM/SSD/電池守衛
python3 run.py watchdog
```

---

## 4. 自動化審計與 CI 流程 (Compliance & CI)

本專案配置標準合規審計工具 `audit_project.py` 與 GitHub Actions CI 流程：

```bash
# 執行專案目錄規範與治理文件審計（必須 100% 通過）
python3 audit_project.py
# 或透過 Makefile 執行
make audit

# 執行全量單元測試（包含 240+ 項測試）
python3 -m unittest discover tests
# 或透過 Makefile 執行
make test
```
