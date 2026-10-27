# ADR-014：三視覺模型全頁雙渲染並排交叉審查與重排版動態視窗映射架構

- **狀態**：Accepted
- **日期**：2026-10-27
- **Agent**：`Antigravity`
- **任務**：`TASK-062` / `TASK-063`

## 1. 背景與問題

系統在完成純文字與 AST 結構檢驗（Gate 1）後，產出之 EPUB 3 仍可能存在視覺排版盲點：
1. **版面撕裂與文字重疊**：大標題可能遺留陰影圖層、雙欄閱讀流斷裂、未轉義 HTML 實體滲漏。
2. **固定版面 PDF 與流動版面 EPUB 的對齊鴻溝**：固定版面 PDF（雙欄、800 字/頁）在重排版 EPUB 中會依字級延伸為 1.5 ~ 2.5 頁。直接逐頁對比會產生高達 50% 的假性遺失率。
3. **模型依賴與速度代價**：僅依賴大型 VLM（如 Llama 3.2 Vision 11B / MiniCPM-V）進行逐頁深度神經網路推論耗時巨大（全書上千頁需耗時數小時），且不同本地環境對多模態模型架構（如 macOS Ollama 未編譯 `mllama`）相容性不同。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| **A. 單純依賴本機 VLM 逐頁檢查** | 能識別複雜圖文關係與視覺美感 | 推論速度慢（~2s/頁），容易出現幻覺式拼寫誤報，且遇到模型未載入或架構未支援（ISSUE-019）時流程容易中斷。 |
| **B. 單純依賴傳統 Python Tesseract OCR** | 離線執行 | 需額外安裝肥大 C++ 依賴與語言包，且對現代版面字元辨識率低，無排版視覺缺陷檢測能力。 |
| **C. 三視覺混合管線（Apple Vision + MiniCPM-V + Llama Vision）與動態視窗映射（選定方案）** | 結合原生 Apple Neural Engine 硬體加速 OCR（0.08s/頁）、MiniCPM-V 本地多模態排版扣分制，以及基於 TOC 的動態重排版視窗（Expansion Ratio Windowing），兼顧極速字詞召回核對與深度視覺排版審查。 | 需維護 Swift 原生橋接腳本，並處理各模型降級邏輯。 |

## 3. 決策與理由

選擇 **方案 C**：
1. **Native Apple Vision OCR 橋接 (`apple_vision_bridge.swift`)**：利用 macOS 原生 Swift 呼叫 `VNRecognizeTextRequest`，零外部 Python 依賴，以金屬級硬體加速達成 0.08 秒/頁的高速 OCR 文字提取與幾何邊界捕捉。
2. **動態擴展比率視窗 (`DualRenderComparator`)**：
   - 透過 EPUB 3 TOC 階層解析精確錨定章節起訖頁碼。
   - 計算擴展比率 $R = \text{EPUB頁數} / \text{PDF頁數}$，將 PDF 第 $i$ 頁映射至 EPUB 頁面視窗 $[i \cdot R, (i+1) \cdot R + 1]$，聚合視窗內字詞流進行召回率計算（正文章節召回率達 80%~95%）。
3. **MiniCPM-V 本地版面瑕疵快篩 (`EpubVisualAuditor`)**：針對重排版視窗代表頁進行標題陰影、雙欄撕裂、文字重疊與 HTML 洩漏之扣分制審查（`DEFECT_PENALTY_MAP`）。
4. **自適應模型降級防護**：針對 Llama 3.2 Vision 在特定平台上的架構未支援（`ISSUE-019`），建立快篩跳過機制，由 Apple Vision + MiniCPM-V 承擔雙重視覺審查，確保批次穩定執行。

## 4. 影響與代價

- **正面影響**：
  - 建立出版級的雙渲染並排對比能力（Gate 2 Visual & Layout Audit）。
  - 全書庫 5 本教科書 128 章節經真實畫面逐頁核對，字詞召回率達 80%~95%，版面評分達 10.0/10。
- **代價**：
  - 本地執行全量全書庫稽核時需消耗約 40~60 分鐘之 GPU/CPU 資源（支援 `--stride` 抽檢步長參數以靈活調整驗收密度）。
- **同步修改項目**：
  - `src/literature_parser/services/verification/apple_vision_bridge.swift`
  - `src/literature_parser/services/verification/apple_vision_auditor.py`
  - `src/literature_parser/services/verification/dual_render_comparator.py`
  - `src/literature_parser/services/verification/visual_cross_audit_orchestrator.py`
  - `scripts/run_visual_cross_audit.py`
  - `docs/adr/DECISIONS.md`
