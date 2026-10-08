# 排版轉換品質評估與基準資料集 (evals/README.md)

## 1. 評估目標與維度 (Evaluation Objectives)

本評估模組用於持續驗收書籍與學術文獻轉換之排版品質，杜絕任何退化（Regression）：
1. **排版保真度 (Typesetting Fidelity)**：標題層級真實性、正文段落連續性、跨頁句尾無縫拼接。
2. **圖表結構完整度 (Table & Figure Integrity)**：無殘破 raw OCR 字符、HTML 表格語法閉合、附註獨立性。
3. **數學公式正確率 (Formula Accuracy)**：行內 `$ ... $` 與展示式 `$$ ... $$` 括號閉合率 100%，貨幣符號正確轉義。
4. **雙欄帶狀流動性 (Two-Column Flow)**：學術文獻左右欄文字流向嚴格依序閱讀，無跨欄穿插錯亂。

---

## 2. 7 大物理不變量硬門禁 (Invariant Gates)

由 `QualityInvariantGuard` 強制執行的物理防呆門禁：

```mermaid
flowchart LR
    Output["轉換產出 Markdown"] --> G1["1. 標題非空 (H1)"]
    G1 --> G2["2. 摘要存在 (Abstract)"]
    G2 --> G3["3. 參考文獻獨立 (References)"]
    G3 --> G4["4. LaTeX 括號閉合"]
    G4 --> G5["5. 表格語法無洩漏"]
    G5 --> G6["6. 無孤立頁碼"]
    G6 --> G7["7. 非空白檔案 (>500B)"]
    G7 --> Verdict{"門禁評估結果"}
    Verdict -->|全部通過| Pass["✅ 驗收通過 (data/output/)"]
    Verdict -->|任一失敗| Quarantine["🚨 自動隔離 (data/needs_review/)"]
```

---

## 3. 評估資料集清單 (Benchmark Datasets)

### 3.1 學術文獻基準組 (`data/input/literature/`)
- `2002-01194-001.pdf`：APA 標準雙欄期刊論文（含大量統計公式、三線表格）
- `2008-17521-013.pdf`：APA 標準雙欄期刊論文（含複雜實驗流程與跨欄圖表）
- `Journal of Adolescence...pdf`：Elsevier 雙欄期刊論文（含自定義頁首浮水印）
- 其餘 7 篇涵蓋 IEEE、Springer 與 SpringerOpen 之不同排版樣本。

### 3.2 專書基準組 (`data/input/books/`)
- `Research Methods, Design, and Analysis 13th ed.pdf`：數位原生 PDF，長篇教科書基準（840+ 頁）
- `Group Counseling- Strategies and Skills...pdf`：掃描版書籍 (Scanned PDF)，神經 OCR 與首字下沉基準
- `Research-Methods-in-Psychology-1641401901.epub`：EPUB 參考組，多章節結構對比

---

## 4. 執行評估指令 (Running Evals)

```bash
# 1. 執行排版格式自動化稽核
python3 run.py audit data/output/literature/2002-01194-001/

# 2. 執行全量稽核測試套件
python3 -m unittest tests/test_v39_format_auditor.py tests/test_v40_fix_playbook_and_invariants.py
```
