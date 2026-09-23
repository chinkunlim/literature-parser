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

---

## 10. 疑難瑕疵全自動隔離規範 (Mandatory Quarantine Protocol)

任何由 Ollama、OCR 或解析器產生的瑕疵，嚴禁中斷主批次管線或默默吞掉錯誤，必須一律隔離至 `data/needs_review/`：
1. **觸發條件**：
   - Ollama 呼叫失敗、連線超時、或語法修復後仍未通過括號閉合校驗。
   - 提取置信度評估低於門檻（`< 0.80`）。
   - 雙欄排版出現未決斷層。
2. **隔離檔案格式**：
   - 自動寫入 `data/needs_review/<category>_<hash>.md`，包含：時間戳、原始片段、診斷原因、AI 置信度評估與人類人工處理建議。

---

## 11. 會話雙軌歸檔規範 (Dual-Track Session Archiving Protocol)

每當會話需要中斷交接（`run.py handoff`）或重大里程碑結案時，AI 必須執行雙軌歸檔：
1. **配對結構**：
   - `memory/sessions/YYYY-MM-DD-<topic>-summary.md`：**高密度摘要**（供人類或新 AI 30 秒快速掌握進度與架構決定）。
   - `memory/sessions/YYYY-MM-DD-<topic>-transcript.md`：**完整對話紀錄**（供事後深挖問答細節）。
2. **自動化時機**：
   - 建議於每次「離席交接（Handoff）」與「發布結案（Publish）」時執行，避免每個單發 prompt 產生過多碎裂小檔案。

---

## 12. SOLID 物件導向設計實戰落地準則 (SOLID Principles)

所有模組與類別開發，必須嚴格遵守物件導向五大原則，杜絕千行巨石檔案（God Classes）：

1. **S - 單一職責原則 (Single Responsibility Principle, SRP)**：
   - 一個類別或模組**只應有一個引起它變更的原因**。
   - 範例：文字解析器（`TextParser`）、表格提取器（`TableExtractor`）與品質檢驗器（`Verifier`）必須分屬不同模組，禁止混寫在同一檔案中。
   - **程式碼長度門檻**：單一類別建議不超過 300 行；單一函式建議不超過 50 行。
2. **O - 開放封閉原則 (Open/Closed Principle, OCP)**：
   - 模組應**對擴充開放，對修改封閉**。
   - 範例：新增新出版商（如 IEEE 或 Nature）時，應建立繼承自 `BasePublisher` 的新子類別或擴充配置檔，**嚴禁**在主流程中使用無限增長的 `if publisher == "apa": ... elif ...:` 巨型條件分支。
3. **L - 里氏替換原則 (Liskov Substitution Principle, LSP)**：
   - 所有子類別（如 `LiteraturePipeline`, `TextbookPipeline`）必須能無縫替代父類別（`BasePipeline`）而無需調用端做特殊判斷，子類別絕不拋出父類別介面未定義的破壞性異常。
4. **I - 介面隔離原則 (Interface Segregation Principle, ISP)**：
   - 介面與抽象基底類別應當保持精煉，客戶端不應被迫依賴它們用不到的方法。
   - 範例：將「純文字提取」與「視覺圖片渲染」拆分為 `ITextExtractable` 與 `IRenderable`，不強迫純文字管線實作圖片方法。
5. **D - 依賴反轉原則 (Dependency Inversion Principle, DIP)**：
   - 高層業務邏輯（如 `PipelineOrchestrator`）不得直接依賴低層實體細節（如具體的 `DigitalPDFParser`），雙方必須共同依賴抽象介面（如 `BaseParser`），透過建構子注入（Dependency Injection）達成極致解耦與單元測試可 Mock 性。

---

## 13. 函數設計與純邏輯分離原則 (Pure Functions & Side-Effect Isolation)

為了達到極致的可測試性與確定性，專案核心邏輯必須落實「純運算」與「外部副作用」的嚴格隔離：

1. **核心演算法純函數化 (Pure Functions)**：
   - 文本清洗、LaTeX 標籤轉換、Markdown 語法組裝、正則匹配、資料映射等核心運算，**一律寫成純函數 (Pure Functions)**。
   - **純函數鐵律**：相同的輸入必產生完全相同的輸出；**零 I/O 操作**、**不讀寫磁碟**、**不存取全域變數**、**不呼叫網路或外部子程序**。這保證了單元測試可以在毫秒級完成且 100% 穩定重現。
2. **副作用外推至系統邊界 (Push Side-Effects to the Boundary)**：
   - 所有磁碟讀寫、網路請求、Ollama 模型調用、作業系統子程序呼叫等「副作用（Side Effects）」，一律集中在最外層的 Controller、Runner 或專屬 Adapter 中，不滲透進資料轉換核心。
3. **防禦式衛語 (Guard Clauses)**：
   - 函式開頭優先處理不合規條件並提早返回（Early Return），嚴禁多層巢狀 `if...else`（巢狀深度不得超過 3 層）：
     ```python
     def process_block(block: Block) -> ProcessedBlock:
         if not block.is_valid:
             return ProcessedBlock.empty()
         if block.is_noise:
             return ProcessedBlock.skipped()
         # 主邏輯平鋪直敘展開，無深層縮排
         return transform(block)
     ```

---

## 14. 強型別標註與資料契約規範 (Type Hints & Data Contracts)

動態型別不等於隨意編程。專案全體程式碼必須具備工業級型別安全：

1. **強制完整 Type Hints (PEP 484 / PEP 585)**：
   - 所有公開函式與類別方法之參數與回傳值，**必須 100% 標註明確型別**（支援 Python 3.10+ 現代語法，如 `str | None`、`list[Path]`、`tuple[int, ...]`）。
2. **嚴禁濫用無型別 dict 傳遞業務實體**：
   - 禁止在不同模組間傳遞意義不明的深層 `dict`（如 `data["info"]["sub"]["field"]`）。
   - 複雜領域物件一律使用 **`@dataclass(frozen=True)`** 或 **`Pydantic BaseModel`** 定義強型別契約，保證不可變性（Immutability）、屬性自動校驗與 IDE 自動補全支援。

---

## 15. 防衛性編程與原子性檔案 I/O (Defensive Programming & Atomic Writes)

1. **原子性檔案寫入 (Atomic Writes)**：
   - 為防止寫入大檔案期間電腦斷電、使用者強制中斷或記憶體耗盡導致磁碟留下一半損壞的殘缺檔案，所有重要產出寫入**必須採用原子替換原則**：
     ```python
     def atomic_write_text(filepath: Path, content: str, encoding: str = "utf-8") -> None:
         """Writes content to a temporary file in the same directory, then atomically replaces target."""
         tmp_file = filepath.with_suffix(f"{filepath.suffix}.tmp.{os.getpid()}")
         try:
             tmp_file.write_text(content, encoding=encoding)
             os.replace(tmp_file, filepath)  # 原子性替換，永無損壞中間狀態
         except Exception:
             if tmp_file.exists():
                 tmp_file.unlink()
             raise
     ```
2. **邊界前置快速失敗 (Fail-Fast at Boundary)**：
   - 檔案存在性、權限、數值合理性必須在模組入口第一行檢查完畢，有問題立即拋出明確的語意化例外，禁止將錯誤延遲到深層調用才暴雷。

---

## 16. 異常處理禁忌與反模式清單 (Exception Handling Anti-Patterns)

1. **🛑 絕對禁止裸抓異常 (No Bare Except)**：
   - **嚴禁**使用 `except:` 或 `except Exception: pass`！這會吞掉鍵盤中斷（`KeyboardInterrupt`）與系統記憶體中斷（`MemoryError`）。
   - 必須明確捕捉具體例外（如 `except (json.JSONDecodeError, FileNotFoundError) as err:`）。
2. **🛑 嚴禁靜默失敗 (No Silent Failures)**：
   - 捕捉例外後必須明確做兩件事之一：**「記錄診斷日誌並向外拋出領域例外」**，或**「進行合法的優雅降級並記錄原因」**。
3. **保留原始呼叫鏈 (Exception Chaining)**：
   - 包裝新例外時，必須使用 `raise CustomDomainError("...") from err`，完整保留原始堆疊追蹤資訊（Traceback）。
