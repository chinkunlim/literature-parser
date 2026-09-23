# 📌 會話精要總結 (Executive Summary): 學術期刊雙欄管線開發與 Ollama 邊界分流

- **會話日期**: `2026-09-23` (早晨 ~ 下午)
- **會話 ID**: `e7e0ccf8-a309-4bad-b967-e1ef03284bae`
- **對應完整對話紀錄**: [`2026-09-23-academic-journal-pipeline-and-dual-column-transcript.md`](./2026-09-23-academic-journal-pipeline-and-dual-column-transcript.md)
- **主題類別**: 學術期刊雙欄分流、APA 水印過濾、Ollama 本地大模型分流原則

---

## 🎯 一、 使用者核心需求
1. 在 `inbox/` 放入新學術論文 `2002-01194-001.pdf`，要求精準轉換為高品質 Markdown。
2. 驗證論文結構：
   - 解決從 Method 之後出現類似 review 筆記而非原文的問題（排查是否為 OCR 或提取錯誤）。
   - 保留摘要（Abstract）、作者資訊、雙欄閱讀順序、APA 參考文獻結構。
3. **確立重大 AI 協作原則（Token 與責任邊界劃分）**：
   - **減少雲端 AI (Antigravity) 的 Token 消耗**：Antigravity 主要負責「架構討論、深度除錯、程式開發、人機對話」。
   - **例行轉檔與內容修復交給本地 Ollama (Qwen2.5 / DeepSeek)**：當遇見特殊排版報錯、LaTeX 損壞或輸入異常時，由 Python 自動呼叫本地 Ollama 解決。
   - 若本地 Ollama 也處理不了或信度過低，才隔離並向使用者回報。

---

## 💡 二、 關鍵問題診斷與修復方案
1. **學術期刊雙欄閱讀順序錯亂 (Multi-Column Band Flow)**：
   - **原因**：傳統由上至下掃描會將左欄第 1 行與右欄第 1 行串接，破壞論文正文邏輯。
   - **解法**：研發「帶狀流動 (Band Flow)」演算法，先垂直分割左右欄（Column Detection），左欄讀取完畢後再接續右欄，跨頁橫欄跨幅標題則維持全寬。
2. **APA 浮水印與版權頁首/頁尾過濾**：
   - **解法**：建立正規表達式過濾器，自動剔除諸如 *"American Psychological Association"*, *"DOI: 10.1037/..."* 等頁緣重複雜訊。
3. **論文專屬管道 (Journal Pipeline)**：
   - **解法**：將處理邏輯解耦為書籍架構（Textbook）與期刊架構（Journal），採用 Archetype Strategy Pattern 進行動態指派。

---

## 🛠️ 三、 模組異動與交付成果
- **新增/更新模組**：
  - `src/book_processor/pipelines/journal_pipeline.py`（期刊專用管線）
  - `src/book_processor/extractors/column_segmenter.py`（雙欄排版與帶狀流動）
  - `src/book_processor/filters/academic_noise.py`（APA 浮水印過濾器）
  - `src/guards/ollama_guard.py`（初步構思本地 Ollama 調度模型）
- **交付檔案**：
  - `2002-01194-001.pdf` 論文成功輸出至 `output/`，雙欄流動流暢，無交錯斷句。
