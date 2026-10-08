# 協作貢獻指引 (.github/CONTRIBUTING.md)

感謝您對 **Book & Literature Processor** 專案的貢獻！為維持本專案的高工程品質與治理一致性，請遵循以下規範。

---

## 1. 核心開發準則 (Core Directives)

1. **🛑 嚴禁未授權推送 (Zero-Push Rule)**：
   - 本專案預設為 **Local-Only 模式**。
   - 嚴禁未經使用者明確指示執行 `git push`（系統已配置 pre-push hook 阻斷）。
2. **📝 提交前強制文檔同步與全英文 Commit (Doc-Before-Commit & English Protocol)**：
   - 完成新功能：必須先於 `memory/TASKS.md` 勾選並標註日期。
   - 架構更動：必須同步更新 `docs/ARCHITECTURE.md`。
   - 所有 Commit 訊息必須嚴格遵循 **Conventional Commits 英文規範**（例如 `feat: ...`, `fix: ...`, `refactor: ...`）。
3. **🛡️ 軟硬體前置守衛 (Hardware Safeguards)**：
   - 凡呼叫本地大模型（Ollama）之模組，必須通過 `HardwareGuard` 檢驗（可用 RAM ≥ 4GB，低電量電池模式優雅降級為純規則）。
4. **🍎 macOS 原生能力優先 (macOS-Native Priority)**：
   - 優先調用 Apple Vision Framework、`sips`、Core Graphics 與 Metal/MPS。
5. **📦 模組行數上限與職責分離 (God-File Breaker)**：
   - 單一 Python 檔案嚴格限制 $\le 800$ 行；CLI 入口層 $\le 200$ 行；函式長度 $\le 50$ 行。

---

## 2. 本地開發與測試流程 (Local Workflow)

```bash
# 1. 安裝環境與同步依賴
uv sync

# 2. 開發前執行環境檢查
python3 run.py doctor

# 3. 執行標準合規性審計
python3 audit_project.py

# 4. 執行全量單元測試（必須 100% 通過）
python3 -m unittest discover tests
```

---

## 3. 提交 PR 與審查標準 (Pull Request Review)

- 新增解析器或修復模組時，必須隨附相應之單元測試（置於 `tests/`）。
- 嚴禁引入未受控之全域變數或非純函數文字處理（無狀態文字轉換請收攏至 `src/doc_processor/utils/shared_text.py`）。
- 確保所有測試與 `audit_project.py` 檢查為 100% 通過狀態。
