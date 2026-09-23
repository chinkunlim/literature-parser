# 🛡️ docs/CODING_RULES.md (開發守則與工程約束)

> 適用對象：全體開發者與 AI Agent。本檔案定義專案不可逾越的工程底線與規範。

---

## 1. 拒絕幽靈修復原則 (Proof of Execution)

1. **嚴禁口頭宣告「已修復」**：
   - AI Agent 修改任何功能或修正 Bug 後，必須提供具體的執行輸出（Terminal Output）、測試結果日誌或截圖說明。
2. **呼叫鏈連動驗證 (Call-Chain Integrity)**：
   - 實作任何功能模組時，必須確認主業務流程（Main Pipeline）中有真實呼叫該函式，嚴禁寫成永遠不會被觸發的死代碼（Dead Code）。

---

## 2. 軟硬體守衛規範 (Hardware Pre-flight Checks)

在啟動任何高算力處理（特別是本地 Ollama 大模型調用或大批次 OCR）前，程式必須強制呼叫 `src/guards/hardware.py` 進行檢查：

1. **記憶體安全餘裕 (RAM Guard)**：
   - 門檻：系統可用 RAM 必須 **≥ 4.0 GB**。
   - 處置：若低於門檻，禁止載入本地大模型，必須在 Log 印出警報並自動啟動降級流程，避免造成 macOS 頻繁 Swap 甚至凍結。
2. **電源狀態防護 (Battery Guard)**：
   - 門檻：筆電處於電池模式（Battery Mode）且電量 < 50%。
   - 處置：終端機提示警告，預設自動跳過或降級本地大模型檢驗，防止在無電源環境下電量耗盡。除非使用者明確加上 `--ignore-battery` 參數方得覆寫。
3. **磁碟剩餘空間 (Disk Guard)**：
   - 門檻：可用磁碟空間必須 **≥ 10.0 GB**。
   - 處置：若低於門檻，拒絕啟動大批次 PDF 切割與高解析圖檔轉存。

---

## 3. Ollama 自動除錯與輸入校驗守則 (Mandatory Auto-Ollama Rules)

告別過去預設關閉的漏洞，Ollama 調用遵循以下鐵律：

### ① 輸入校驗防線 (Input Guard)
- 當處理書籍或期刊時，若目錄中含有 `manifest.json` 或 `metadata.json`，程式必須核對實體檔案與 JSON 描述。
- **Ollama 觸發時機**：若欄位缺失、章節數不符或檔案型態異常，在硬體允許下**自動啟動 Ollama 進行語義修復診斷**，產出修復建議報告。

### ② 輸出異常自我修復防線 (Output & Self-Healing Guard)
- **Ollama 觸發時機**：
  - 提取的 LaTeX 公式編譯報錯或語法損壞。
  - OCR 輸出為空或置信度過低。
  - 章節文本長度出現明顯異常中斷。
- **嚴禁行為**：在 `try...except` 區塊中嚴禁只寫 `pass` 或只印出錯誤名稱。
- **處置**：必須將 `(異常上下文, 原始文字, 錯誤訊息)` 打包，自動呼叫 Ollama 進行一次「自動修復嘗試 (Auto-Repair Attempt)」。若修復成功則替換；若修復失敗則將該片段拋入 `data/needs_review/` 隔離區。

### ③ 固定提示詞與無人值守原則 (Pre-defined Prompts & Autonomous Execution)
- **程式啟動後無人介入**：一旦 Python 轉檔管線啟動，AI Agent（如 Antigravity / Claude）無法在執行期即時介入。
- **Prompt 集中預設**：所有呼叫 Ollama 的 System Prompt 與模板，必須在 `src/guards/prompts.py` 中集中以常數預先定義好（包含嚴格的格式限制與 JSON 輸出規範），嚴禁在執行期動態拼湊隨意字串。

---

## 4. 結構化診斷日誌規範 (Structured Diagnostic Logging)

所有日誌輸出嚴禁只印出抽象的 `Error: Exception`，必須統一採用 `src/utils/logger.py`，強制包含「三要素」：

```python
from src.utils.logger import get_diagnostic_logger
logger = get_diagnostic_logger("pipeline")

# 範例
logger.error(
    where="[Chapter 3 / Formula #12]",
    why="Ollama 服務在 localhost:11434 回應連線超時 (Timeout > 30s)",
    how_to_fix="請確認 Ollama 是否背景當機，或在終端機執行 'brew services restart ollama'"
)
```

---

## 5. 臨時實驗室規範 (Scratchpad Policy)

- 所有一次性測試腳本、臨時驗證程式，**一律存放在 `scratch/` 目錄下**（如 `scratch/test_math.py`）。
- **嚴禁**在根目錄或 `src/` 下建立未命名的測試檔。`scratch/` 目錄已被加入 `.gitignore`，不提交至 Git。

---

## 6. 先更文檔後 Commit 鐵律 (Doc-Before-Commit Protocol)

- 所有 AI Agent 準備執行 `git commit` 前，必須先：
  1. 在 `memory/TASKS.md` 勾選已完成項目並打上日期 `[YYYY-MM-DD]`。
  2. 若為中斷交接，必須更新 `memory/HANDOFF.md` 的時間戳記與接手指令。
  3. 若涉及檔案新增/刪除，必須更新 `docs/STRUCTURE.md`。
- Commit 訊息前綴必須一律帶上日期：`[YYYY-MM-DD] feat: ...` 或 `[YYYY-MM-DD] wip(handoff): ...`。

---

## 7. 決策衝突阻斷協議 (Decision Conflict Circuit Breaker)

- 任何 AI Agent 在規劃或修改程式碼時，必須先檢索 `docs/adr/` 中所有 `[Status: Accepted]` 的決策。
- 若發現當前需求或做法與既有 ADR 衝突，**嚴禁自行決定推翻**，必須立即向使用者主動發問，經使用者確認後始得修改。

---

## 8. macOS 原生能力與硬體加速優先準則 (macOS-Native Optimization)

在 Apple Silicon (M1/M2/M3/M4/M5) 環境中開發時，AI 必須主動評估並優先建議 macOS 的內建技術生態：

1. **文字辨識與 OCR 評估**：
   - 優先評估調用系統原生 **Apple Vision Framework**。透過 Python PyObjC (`Vision.VNRecognizeTextRequest`) 或 Swift CLI 調用，可直接利用 Apple Neural Engine (ANE)，省去下載 2GB+ 的 PaddleOCR/PyTorch 權重，且辨識速度快、極度省電。
2. **影像處理與格式轉換**：
   - 優先評估內建命令列工具 **`sips`**（Scriptable Image Processing System）與 Core Graphics，避免額外安裝肥大依賴。
3. **運算加速與記憶體共享**：
   - 充分利用 Apple Silicon 統一記憶體架構（Unified Memory），模型載入與加速優先使用 **Metal Performance Shaders (MPS)** 與 **CoreML**。
4. **主動建議責任**：
   - 若某項任務有表現更優、資源消耗更低的 macOS 原生解法，AI 有義務主動向使用者提出架構建議，而非默默採用通用但笨重的第三方套件。

---

## 9. 零硬編碼絕對路徑與專案可攜性規範 (Zero Hardcoded Absolute Paths)

為保證整個專案資料夾被任意移動（例如從 Desktop 移到 Documents、隨身碟、或另一台電腦）時**絕不崩潰**，所有代碼必須嚴格遵守以下路徑規範：

1. **嚴禁寫死系統使用者絕對路徑**：
   - 嚴禁在程式碼、配置檔或測試腳本中寫死 `/Users/username/...` 或 `C:\Users\...`。
2. **統一使用動態相對錨定**：
   - 所有內部檔案路徑定位，必須以當前程式檔案位置動態推導專案根目錄：
     ```python
     # 標準範例：保證搬移目錄後 100% 正常
     PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
     CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"
     ```
3. **終端機執行彈性**：
   - 無論使用者是在專案根目錄下指令，還是從深層子目錄呼叫 `python ../run.py`，程式皆能精準找到對應的 `data/`、`logs/` 與 `memory/` 目錄。
