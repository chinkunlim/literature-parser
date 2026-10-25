# ADR-010：處理完成文檔嚴格分流歸檔與全書庫斷點續傳機制

- **狀態**：Accepted
- **日期**：2026-10-25
- **Agent**：`antigravity`
- **任務**：`TASK-044`

## 1. 背景與問題

隨著全書庫無人值守多工批次轉檔的落地，系統在面對數百頁教科書與密集學術文獻時面臨兩個關鍵架構挑戰：
1. **處理完成實體檔案之分流歸檔**：
   原有流程將完成檔案放於單一 `input/processed/` 根目錄，未能依領域（教科書 vs. 學術文獻）分流，且易與包含 `literature-parser` 專案名稱之實體路徑發生字串混淆。
2. **長時批次作業之斷點續傳韌性**：
   轉檔 5 本大部頭書（2,431 頁、128 個章節）需花費數小時。若遇系統重啟或暫停，若強制從第 1 頁重新解析，會浪費大量 M5 核心運算資源；需提供確定性的斷點續傳機制。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| **A. 單一 processed 目錄 + 無斷點控制** | 實作簡單 | 領域檔案混雜無法分流；任何中斷需從頭開始，批次耗時過長 |
| **B. 獨立 processed-books / processed-literature + CLI 顯式 `--resume` 斷點續傳** (採用) | 嚴格維持架構單向分流；已通過出版級驗收之章節可即時略過，容災復原時間縮短為秒級 | 需在 `CheckpointManager` 嚴密處理多工競爭與檔案存在性檢查 |

## 3. 決策與理由

1. **實體路徑嚴格分流**：
   - 書籍歸檔至 `DATA_DIR/input/processed/processed-books/`
   - 學術論文歸檔至 `DATA_DIR/input/processed/processed-literature/`
   - 採用 `p.relative_to(app_cfg.input_dir)` 進行相對路徑解析，徹底杜絕因專案資料夾名稱包含 `"literature"` 而產生假陽性誤判。
   - 所有輸入掃描邏輯（`discover_books` 與 `rglob`）一律嚴格排除 `processed*` 子目錄。
2. **CLI 支援顯式 `--resume` 斷點續傳**：
   - 在 `run.py`、`doc_cli.py` 與 `cli_process.py` 增設 `--resume` 旗標。
   - 當開啟 `--resume` 時，檢查 `CheckpointManager.is_chapter_verified(name)`，若章節狀態為 `VERIFIED` 且實體 PDF/Markdown 齊備，即刻略過並保留原有產物，直接接續待處理章節。
3. **檢查點狀態之磁碟實體校驗**：
   - `is_chapter_verified` 強化為結合磁碟上章節 PDF 之實際存在性檢驗，避免多 Worker 平行回寫 JSON 時之競態覆蓋。

## 4. 影響與代價

- **正面影響**：
  - 全書庫 5 本大部頭書籍 128 章節可順暢分批或接續運行，成功達成 100% 驗收歸檔與原輸入目錄完全清空。
  - 學術文獻目錄保持乾淨獨立，為後續論文批次化提供清晰邊界。
- **代價與維護注意事項**：
  - 測試套件需維護 mock 路徑之相對解析，測試已增設 `tests/test_archive_paths.py`。
