# 🛡️ docs/CODING_RULES.md (開發守則與工程約束 - 雙層通用架構)

> **💡 架構說明 (Two-Tier Architecture)**：
> 1. **第一部：通用軟體工程基線 (Universal Core Standards)**：所有軟體、腳本與 AI 專案 **100% 通用**，定義高品質代碼的不可逾越底線，可直接跨專案移植。
> 2. **第二部：本專案領域擴充規範 (Project Domain Extensions)**：本專案專屬之業務與技術約束（如文獻書籍處理、LaTeX、Apple Vision、本地 Ollama 守衛）。
>
> 🔄 **個別專案如何擴充？**
> 未來開立任何新專案時，直接原封不動拷貝「第一部」；若新專案有自己的領域特性（如 React/Next.js 前端規範、FastAPI 後端規範、PyTorch 訓練規範），**一律於「第二部」往下擴充**，確保通用工程核心乾淨獨立、永不被特定領域污染！

---

# 🌐 第一部：通用軟體工程基線 (Universal Core Standards)
> 本部分適用於任何語言與架構的現代軟體工程專案。

---

## 1. SOLID 物件導向設計準則 (SOLID Principles)

所有模組與類別開發，必須嚴格遵守物件導向五大原則，杜絕千行巨石檔案（God Classes）：

## 1. SOLID 物件導向設計準則 (SOLID Principles)

所有模組與類別開發，必須嚴格遵守物件導向五大原則，杜絕千行巨石檔案（God Classes / God Files）：

1. **S - 單一職責原則 (Single Responsibility Principle, SRP)**：
   - 一個類別或模組**只應有一個引起它變更的原因**。
   - 職責必須單一且聚焦。單一類別建議不超過 300 行；單一函式建議不超過 50 行。
2. **O - 開放封閉原則 (Open/Closed Principle, OCP)**：
   - 模組應**對擴充開放，對修改封閉**。
   - 善用抽象基底類別（`ABC`）與介面，新增功能透過新增實作類別達成，嚴禁在核心管線中撰寫長串 `if...elif...elif` 條件判斷。
3. **L - 里氏替換原則 (Liskov Substitution Principle, LSP)**：
   - 所有子類別必須能無縫替代父類別而無需調用端做特殊判斷，子類別絕不拋出父類別介面未定義的破壞性異常。
4. **I - 介面隔離原則 (Interface Segregation Principle, ISP)**：
   - 介面與抽象基底類別應當保持精煉，客戶端不應被迫依賴它們用不到的方法。拆分為精簡的 Protocols 或 Mixins。
5. **D - 依賴反轉原則 (Dependency Inversion Principle, DIP)**：
   - 高層業務邏輯不得直接依賴低層實體細節，雙方必須共同依賴抽象介面，透過建構子注入（Dependency Injection）達成極致解耦與單元測試可 Mock 性。

---

## 2. 單一檔案行數上限與 God-File 阻斷機制 (God-File Circuit Breaker)

為了防止專案隨迭代再次膨脹出難以維護的「千行上帝檔案」（如舊版 1,820 行 `run.py`、1,206 行 `layout_detector.py`）：
1. **建議行數門檻**：一般 Python 業務模組行數建議維持在 **$\le 500$ 行**。
2. **絕對硬性上限**：單一 Python 檔案**絕對上限為 800 行**。一旦超過 800 行，必須強制依照職責拆分為子模組（例如拆出專用子套件如 `src/cli/`，或子解析器如 `vector_figure_parser.py`、`eoc_parser.py`）。
3. **入口派發器精簡原則**：專案總進入點或 CLI 派發器（如 `run.py`）**嚴禁**承載深層業務邏輯，僅允許保留參數解析與模組分發，行數嚴格控制在 **$\le 200$ 行**。

---

## 3. 共用模組提取原則 (Shared Utilities Extraction Rule)

1. **消除代碼重複 (DRY Protocol)**：
   - 凡是跨 **2 個（含）以上**模組使用之純文字轉換、正規表達式或通用資料結構，**必須提取至通用模組**（如 `src/doc_processor/utils/shared_text.py`），嚴禁複製貼上或重複定義。
2. **純函數式封裝**：
   - 提取的共用模組必須保持純函數（Pure Functions）特性，接受字串或數值輸入，回傳轉換後字串與修復計數（如 `Tuple[str, int]`），零副作用，供所有驗證器與修復手冊直接調用。

---

## 4. 函數設計與純邏輯分離原則 (Pure Functions & Side-Effect Isolation)

為了達到極致的可測試性與確定性，專案核心邏輯必須落實「純運算」與「外部副作用」的嚴格隔離：

1. **核心演算法純函數化 (Pure Functions)**：
   - 文本清洗、數學計算、資料轉換、正則匹配、結構組裝等核心運算，**一律寫成純函數 (Pure Functions)**。
   - **純函數鐵律**：相同的輸入必產生完全相同的輸出；**零 I/O 操作**、**不讀寫磁碟**、**不存取全域變數**、**不呼叫網路或外部子程序**。保證單元測試毫秒級完成且 100% 穩定重現。
2. **副作用外推至系統邊界 (Push Side-Effects to the Boundary)**：
   - 所有磁碟讀寫、網路請求、外部子程序呼叫等「副作用（Side Effects）」，一律集中在最外層的 Controller、Runner 或專屬 Adapter 中，不滲透進資料轉換核心。
3. **防禦式衛語句 (Guard Clauses)**：
   - 函式開頭優先處理不合規條件並提早返回（Early Return），嚴禁多層巢狀 `if...else`（巢狀深度嚴格控制在 3 層以內）：
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

## 5. 強型別標註與資料契約規範 (Type Hints & Data Contracts)

動態型別不等於隨意編程。專案全體程式碼必須具備工業級型別安全：

1. **強制完整 Type Hints (PEP 484 / PEP 585)**：
   - 所有公開函式與類別方法之參數與回傳值，**必須 100% 標註明確型別**（支援 Python 3.10+ 現代語法，如 `str | None`、`list[Path]`、`tuple[int, ...]`）。
2. **嚴禁濫用無型別 dict 傳遞業務實體**：
   - 禁止在不同模組間傳遞意義不明的深層 `dict`（如 `data["info"]["sub"]["field"]`）。
   - 複雜領域物件一律使用 **`@dataclass(frozen=True)`** 或 **`Pydantic BaseModel`** 定義強型別契約，保證不可變性（Immutability）、屬性自動校驗與 IDE 自動補全支援。

---

## 6. 防衛性編程與原子性檔案 I/O (Defensive Programming & Atomic Writes)

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

## 7. 異常處理禁忌與反模式清單 (Exception Handling Anti-Patterns)

1. **🛑 絕對禁止裸抓異常 (No Bare Except)**：
   - **嚴禁**使用 `except:` 或 `except Exception: pass`！這會吞掉鍵盤中斷（`KeyboardInterrupt`）與系統記憶體中斷（`MemoryError`）。
   - 必須明確捕捉具體例外（如 `except (json.JSONDecodeError, FileNotFoundError) as err:`）。
2. **🛑 嚴禁靜默失敗 (No Silent Failures)**：
   - 捕捉例外後必須明確做兩件事之一：**「記錄診斷日誌並向外拋出領域例外」**，或**「進行合法的優雅降級並記錄原因」**。
3. **保留原始呼叫鏈 (Exception Chaining)**：
   - 包裝新例外時，必須使用 `raise CustomDomainError("...") from err`，完整保留原始堆疊追蹤資訊（Traceback）。

---

## 8. 拒絕幽靈修復原則 (Proof of Execution)

1. **嚴禁口頭宣告「已修復」**：
   - AI Agent 修改任何功能或修正 Bug 後，必須提供具體的執行輸出（Terminal Output）、測試結果日誌或截圖說明。
2. **呼叫鏈連動驗證 (Call-Chain Integrity)**：
   - 實作任何功能模組時，必須確認主業務流程中有真實呼叫該函式，嚴禁寫成永遠不會被觸發的死代碼（Dead Code）。

---

## 9. 結構化診斷日誌規範 (Structured Diagnostic Logging)

所有日誌輸出嚴禁只印出抽象的 `Error: Exception`，必須統一採用結構化日誌，強制包含「三要素」：

```python
from src.utils.logger import get_diagnostic_logger
logger = get_diagnostic_logger("pipeline")

# 範例
logger.error(
    where="[Chapter 3 / Formula #12]",
    why="服務回應連線超時 (Timeout > 30s)",
    how_to_fix="請確認服務是否背景當機，或在終端機重啟該服務"
)
```

---

## 10. 零硬編碼絕對路徑與專案可攜性 (Zero Hardcoded Absolute Paths)

為保證整個專案資料夾被任意移動（從 Desktop 移到 Documents、隨身碟、或另一台電腦）時**絕不崩潰**：
1. **嚴禁寫死系統絕對路徑**：嚴禁在代碼、配置或測試中寫死 `/Users/...` 或 `C:\...`。
2. **統一使用動態相對錨定**：
   ```python
   PROJECT_ROOT = Path(__file__).resolve().parent.parent
   CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"
   ```
3. **終端機執行彈性**：無論是在專案根目錄下指令，還是從子目錄呼叫，程式皆能精準找到根目錄與相依資料夾。

---

## 11. 臨時實驗室規範 (Scratchpad Policy)

- 所有一次性測試腳本、臨時驗證程式，**一律存放在 `scratch/` 目錄下**（如 `scratch/test_math.py`）。
- **嚴禁**在根目錄或 `src/` 下建立未命名的測試檔。`scratch/` 目錄已被加入 `.gitignore`，不提交至 Git。

---

## 12. 先更文檔後 Commit 鐵律與全英文規範 (Doc-Before-Commit & English Protocol)

- 所有 AI Agent 準備執行 `git commit` 前，必須先同步更新相關文檔：
  1. 在 `memory/TASKS.md` 勾選已完成項目並打上日期 `[YYYY-MM-DD]`。
  2. 若為中斷交接，必須更新 `memory/HANDOFF.md` 的時間戳記與接手指令。
  3. 若涉及檔案新增/刪除/結構異動，必須更新 `docs/STRUCTURE.md`。
- **Commit 訊息規範**：一律使用英文 Conventional Commits 格式，並帶上日期前綴，例如：`[YYYY-MM-DD] feat: ...`。

---

## 13. 決策衝突阻斷協議 (Decision Conflict Circuit Breaker)

- 任何 AI Agent 在規劃或修改程式碼時，必須先檢索 `docs/adr/` 中所有 `[Status: Accepted]` 的決策。
- 若發現當前需求或做法與既有 ADR 衝突，**嚴禁自行決定推翻**，必須立即向使用者主動發問確認。

---

## 14. 12-Factor 環境變數配置隔離 (Zero Hardcoded Secrets & Config Isolation)

- 嚴禁在程式碼中寫死金鑰、密鑰或環境特定參數。
- 專案根目錄標配提交 `.env.example` 宣告所需變數範本，真實環境變數注入經由 `.env` 或系統環境變數讀取。

---
---

# 📦 第二部：本專案專屬領域擴充 (Project Domain Extensions)
> 本部分為針對「書籍與文獻 Markdown 高精度轉檔專案」之特化規範。
> **💡 提示：其他專案開案時，請將本部分替換為該專案之領域技術規範。**

---

## 15. macOS 原生能力與硬體加速優先準則 (macOS-Native Optimization)

在 Apple Silicon (M1/M2/M3/M4/M5) 環境中開發時，AI 必須主動評估並優先建議 macOS 的內建技術生態：

1. **文字辨識與 OCR 評估**：
   - 優先評估調用系統原生 **Apple Vision Framework** (`Vision.VNRecognizeTextRequest`)。調用 Apple Neural Engine (ANE)，省去下載 2GB+ 外部模型權重，近乎零記憶體負擔且極速省電。
2. **影像處理與格式轉換**：
   - 優先評估內建命令列工具 **`sips`**（Scriptable Image Processing System）與 Core Graphics，避免額外安裝肥大第三方套件。
3. **運算加速與記憶體共享**：
   - 充分利用 Apple Silicon 統一記憶體架構（Unified Memory），模型載入與加速優先使用 **Metal Performance Shaders (MPS)** 與 **CoreML**。
4. **主動建議責任**：
   - 若某項任務有表現更優、資源消耗更低的 macOS 原生解法，AI 有義務主動向使用者提出架構建議，而非默默採用跨平台通用但笨重的第三方套件。

---

## 16. 軟硬體前置守衛與安全餘裕 (Hardware Pre-flight Checks)

在啟動任何高算力處理（本地 Ollama 大模型調用或大批次 OCR）前，程式必須強制呼叫 `src/guards/hardware.py` 檢查：

1. **記憶體安全餘裕 (RAM Guard)**：可用 RAM 必須 **≥ 2.0 GB (AC 電源模式) / ≥ 4.0 GB (電池模式)**。同時感知 macOS `memorystatus_vm_pressure_level`，非 critical 級別才放行，低於門檻禁止載入本地大模型，自動啟動純規則降級流程。
2. **電源狀態防護 (Battery Guard)**：若處於電池模式且電量 < 50%，預設自動跳過或降級本地大模型檢驗，防止電量耗盡。
3. **磁碟剩餘空間 (Disk Guard)**：可用磁碟空間必須 **≥ 10.0 GB**，低於門檻拒絕啟動批次切圖與轉存。

---

## 17. Ollama 提示詞中樞集中化原則 (PromptRegistry Single-Source-of-Truth)

1. **🛑 絕對禁止散落硬編碼 Prompt (Zero Hardcoded Prompts)**：
   - 嚴禁在各業務模組、驗證器或工具中直接字串拼接或硬編碼 Prompt。
   - 所有 LLM Prompt 必須統一宣告於 `src/guards/prompts.py` 之 **`PromptRegistry`** 靜態方法中，對外提供強型別簽名（如 `get_latex_healer`、`get_table_reconstruction`、`get_structured_format_audit`）。
2. **緊密對齊專案最新排版修復規則**：
   - 所有與文本、數學、排版相關之 Prompt，必須強制融入專案最新修復規則：
     - **KaTeX 貨幣轉義**：金額貨幣符號轉義為 `\$25`，嚴禁使用 `$` 引發公式衝突。
     - **正則替換安全反向引用**：在代碼合成提示詞中明確要求使用 `\g<1>` 或具名群組，嚴禁使用不可靠的 `\1` 或 `$1`。
     - **APA 表格附註結構**：統一規範將表格附註收斂至 `<tfoot><tr class="table-notes"><td colspan="N">...</td></tr></tfoot>`。
     - **雙欄閱讀流**：先由上至下讀完左欄（Column 1），再由上至下讀完右欄（Column 2）。

---

## 18. 修復手冊庫與 AI 自動合成隔離規範 (Playbook & Staged Synthesis Workflow)

1. **專屬修復手冊庫 (`FixPlaybook`)**：
   - 負責管理、查詢、測試與套用純函數修復配方，支援症狀正則匹配與自動推薦。
2. **AI 代碼合成沙盒隔離 (`OllamaRecipeSynthesizer`)**：
   - 當遇未知排版瑕疵由 Ollama 合成修復代碼時，新生成之配方必須先進入 `src/doc_processor/fixes/staged/` 暫存隔離區。
   - **AST 靜態沙盒校驗**：強制檢查是否為純函數、禁止一切危險 AST 節點（`import os`, `import subprocess`, `eval`, `exec`, `open`）。
   - **自帶單元測試驗證**：必須內建 `TEST_CASES` 且在獨立沙盒內 100% 執行通過。
   - **嚴格審核升級機制**：唯有通過 `run.py fix review` 檢閱、`run.py fix test <id>` 測試通過後，經手動 `run.py fix promote <id>` 方可升級至正式手冊庫 `promoted/`。

---

## 19. 零容忍防呆不變量門禁 (Zero-Tolerance Invariant Gate)

1. **防止「有錯還報對」**：
   - 專案設有獨立於大模型之外的絕對物理門禁 `QualityInvariantGuard.verify_hard_invariants`。
   - 包含 7 大核心不變量：
     1. 標題非空且長度合規。
     2. 摘要必須存在且未被吞噬。
     3. 參考文獻必須獨立為二級標題。
     4. 所有 LaTeX 公式括號必須嚴格閉合。
     5. 表格代碼不得外洩至正文。
     6. 不得殘留正文孤立純數字頁碼行。
     7. 輸出內容不得為空。
   - **一票否決制**：任何一項違背，稽核器一律強制給予 `FAILED`，分數立即扣除，杜絕偽陽性。

---

## 20. 疑難瑕疵全自動隔離規範 (Mandatory Quarantine Protocol)

任何由 Ollama、OCR 或解析器產生的瑕疵，嚴禁中斷主批次管線或默默吞掉錯誤，必須一律隔離至 `data/needs_review/`：
1. **觸發條件**：Ollama 失敗/超時、修復後仍未通過校驗、置信度評估 `< 0.80`、雙欄排版出現未決斷層。
2. **隔離格式**：自動寫入 `data/needs_review/<category>_<hash>.md`，包含：時間戳、原始片段、診斷原因、AI 置信度評估與人類人工處理建議。

---

## 21. 領域命名標準化規範 (`literature`)

- 論文、期刊、報告統一使用 **`literature`** 作為目錄與管線命名（`data/input/literature/`, `src/pipelines/literature/`, `.agent/skills/literature-processor`）。
- 嚴禁使用混淆的 `journal` 或 `paper`。

