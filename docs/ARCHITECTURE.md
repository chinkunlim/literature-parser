# 🏗️ docs/ARCHITECTURE.md (系統架構與數據流向)

---

## 系統總體架構圖

本系統採用 **管道-過濾器架構 (Pipes and Filters)** 結合 **領域策略模式 (Domain Strategy Pattern)**，將「輸入轉換」、「領域解析」、「AI 增強」與「筆記匯出」徹底解耦。

```mermaid
flowchart TD
    subgraph Input_Layer ["1. 輸入與實體路由 (Input Routing)"]
        InBook["data/input/books/<br>(PDF / EPUB)"] -->|路由至| BookDomain["書籍專用處理器<br>(Textbook Pipeline)"]
        InJournal["data/input/journals/<br>(Academic PDF)"] -->|路由至| PaperDomain["期刊專用處理器<br>(Journal Pipeline)"]
    end

    subgraph Guard_Layer ["2. 前置防線與守衛 (Guards)"]
        HardwareGuard["硬體守衛 (hardware.py)<br>- RAM ≥ 4GB<br>- 電池狀態 (AC/Battery)<br>- 磁碟空間 ≥ 10GB"]
        InputValidator["輸入校驗 (validator.py)<br>- 檔案 vs manifest.json<br>- 異常自動呼喚 Ollama"]
        HardwareGuard --> BookDomain
        HardwareGuard --> PaperDomain
        InputValidator --> BookDomain
        InputValidator --> PaperDomain
    end

    subgraph Core_Engine ["3. 核心處理與雙引擎 (Core Processing)"]
        BookDomain --> Splitter["目錄提取與章節切分"]
        BookDomain --> Stitcher["跨頁連續性縫合 (Stitcher)"]
        PaperDomain --> TwoCol["雙欄版面切割與還原"]
        PaperDomain --> MetaRef["Abstract 與 BibTeX 解析"]
        
        Splitter --> SharedEngine["共享核心：Neural OCR + LaTeX 規範化"]
        Stitcher --> SharedEngine
        TwoCol --> SharedEngine
        MetaRef --> SharedEngine
    end

    subgraph Verification_Layer ["4. 檢驗與自我修復 (Self-Healing)"]
        SharedEngine --> Healer["輸出語法異常攔截"]
        Healer -->|正常| Clean["格式驗證通過"]
        Healer -->|異常且硬體允許| OllamaAudit["Ollama AI 自動除錯與修復"]
        OllamaAudit -->|修復成功| Clean
        OllamaAudit -->|修復失敗/疑難| Quarantine["data/needs_review/<br>(隔離檢驗區)"]
    end

    subgraph Export_Layer ["5. 筆記化輸出與儀表板 (Export & Dashboard)"]
        Clean --> ObsidianBook["data/output/books/<br>(Obsidian 雙鏈筆記)"]
        Clean --> ObsidianJournal["data/output/journals/<br>(論文結構筆記)"]
        Clean --> StatusDB["data/state/status.json<br>(即時進度快照)"]
        StatusDB --> Dashboard["dashboard/<br>(預留視覺化儀表板)"]
    end
```

---

## 核心設計原則

1. **路徑即路由 (Path-as-Routing)**：
   - 書籍放在 `data/input/books/`，期刊放在 `data/input/journals/`。由路徑直接決定調用哪個 Pipeline，完全免除 AI 猜測的誤差與 Token 浪費。
2. **優雅降級 (Graceful Degradation)**：
   - 系統依賴 Ollama 進行自我除錯，但在無 Ollama、無 GPU 加速或低電量情況下，自動退化為純規則檢驗，保證主轉檔流程絕不崩潰。
3. **人機隔離防呆 (Human-in-the-Loop Quarantine)**：
   - 遇到難啃的異常公式或版面，自動丟入 `data/needs_review/`，避免讓 AI 無限重試耗盡電力與記憶體。
4. **狀態解耦 (Stateless Core, Stateful State)**：
   - 核心處理器不維護全域動態變數，所有狀態（如當前處理到第幾頁、進度百分比）集中寫入 `data/state/`，支援隨時中斷、隨時恢復（斷點續傳），並為未來的 `dashboard/` 奠定資料基礎。
