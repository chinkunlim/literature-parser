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
