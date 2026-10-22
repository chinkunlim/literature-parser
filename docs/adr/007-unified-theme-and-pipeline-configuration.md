# ADR-007：全專案樣式排版與管線規則集中外部化 (Unified Theme and Pipeline Configuration)

- **狀態**：Accepted
- **日期**：2026-10-22
- **Agent**：`antigravity`
- **任務**：`TASK-021` / `TASK-022`

## 1. 背景與問題

在過去的轉檔流程中，字型堆疊（Google Fonts 載入 URL、無襯線與襯線字體家族）、出版級 60-30-10 調色盤（主色、卡片背景色、語意藍/綠/橘/紅、術語標籤色）、目錄結構（TOC 預設開闔、層級深度、自訂標題）、圖表錨定邊距、表格解析行為與 Obsidian 導航等規則，分散散落於 Python 原始碼（如 `book_style.py`、`literature_style.py`、`layout_detector.py`）與各個常數中。
使用者若想調整輸出字型或顏色主題，必須深入 Python 原始碼修改程式碼；且對於已轉檔完成的龐大教科書章節，缺乏快速抽換樣式表的途徑，過去需要重新執行整本 PDF 的昂貴解析才能更新外觀。

## 2. 評估過的方案

| 方案 | 優點 | 缺點 |
|---|---|---|
| **方案 A：純程式碼硬編碼（既有做法）** | 執行效率最高，不需磁碟讀取或 JSON 解析開銷。 | 使用者無法自訂外觀；每次微調樣式皆需修改程式碼並重新執行單元測試；缺乏通用性。 |
| **方案 B：每本書強制產生完全獨立設定檔** | 單書完全隔離，可自由針對單書極致客製。 | 缺乏全局母版；使用者每次轉檔都需重複維護一份龐大設定；修改全局共同風格時需逐一修改每本書。 |
| **方案 C：全域母版 ＋ 單書選填覆寫 ＋ 獨立重刷 CLI（採納方案）** | 1. 於 `config/theme.json` 集中提供 8 大分區母版，開箱即用。<br>2. 支援單書 `{output_dir}/theme.json` 局部覆寫，未覆寫鍵 100% 繼承母版。<br>3. 提供 `scripts/apply_theme.py` 毫秒級重刷已轉換之 Markdown 樣式。<br>4. 附帶 `config/theme.schema.json` 支援 IDE 智慧補全。 | 需維護設定檔結構與深層合併（Deep Merge）邏輯。 |

## 3. 決策與理由

**決定採用方案 C**：
1. **單一設定來源**：在專案根目錄建立 `config/theme.json`，按 `typography`、`palette`、`layout`、`artifacts`、`tables`、`learning_blocks`、`navigation`、`quality` 八大語意分區集中收納。
2. **階層繼承機制**：由 `src/literature_parser/services/style_loader.py` 的 `load_theme()` 統一載入，具備內建安全預設值 ➔ 全域 `config/theme.json` ➔ 單書目錄 `theme.json` 三層覆寫。
3. **無痛相容性**：`load_style()` 同步輸出結構化分組與扁平鍵值，現存既有程式碼與外掛模組無需更動任何調用。
4. **一鍵快速重刷**：建立 `scripts/apply_theme.py`，正則匹配替換 `<style>` 區塊並同步更新 `style.css`，免去重新解析 PDF 的昂貴運算。

## 4. 影響與代價

- **正面影響**：
  - 使用者完全不需接觸 Python 程式碼即可任意切換字型、深色/淺色主題與目錄深度。
  - 對於轉好的大型書籍，調整樣式或目錄僅需不到 0.01 秒即可完成全局更新。
- **代價與維護注意事項**：
  - 新增排版行為或風格屬性時，需同步在 `config/theme.json` 與 `config/theme.schema.json` 登記預設值。
  - 需確保 `load_style()` 繼續維持向後相容。
