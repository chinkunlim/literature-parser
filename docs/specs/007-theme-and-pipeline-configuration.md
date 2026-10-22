# SPEC-007: 樣式、排版與管線規則外部化規格 (Theme & Pipeline Configuration Specification)

## 1. 概述 (Overview)
本規格定義了將文獻與書籍解析轉換過程中的「字型、調色盤、目錄行為、圖表錨定、表格樣式、教學區塊、Obsidian 雙向導航與品質門檻」全數外部化的標準配置架構，建立單一設定來源 `config/theme.json`，實現免改程式碼即可動態控制輸出排版與視覺呈現。

## 2. 八大分區架構 (Eight-Division Architecture)

| 分區 (Division) | 職責與配置項目 | 預設值範例 |
|---|---|---|
| **typography** | Google Fonts 載入 URL、字型堆疊、正文/標題字體對應、字級與行高、左右齊行、內嵌 CSS | `Inter` (sans), `Merriweather` (serif), `JetBrains Mono` (mono), `16px`, `1.75` |
| **palette** | 60-30-10 出版調色盤、主色、卡片背景、四大語意色（藍/綠/橘/紅）、螢光標記與術語底色 | `#842959` (plum), `#2563eb` (blue), `#059669` (emerald), `#fef08a` (highlight) |
| **layout** | 目錄生成、TOC 預設開闔狀態、TOC 收錄深度、標題與最小生成數、章節首標題補齊、前言獨立切分 | `toc_mode: "close"`, `toc_depth: 3`, `toc_title: "📑 Table of Contents"`, `min: 2` |
| **artifacts** | 圖說渲染模式、圖片最大寬度、裁切四周留白 padding、圖說斜體、子圖歸一化、切圖 DPI | `html_figure`, `max_width: 650`, `pad_pt: 13.0`, `dpi: 300`, `coverage: 0.80` |
| **tables** | 複雜合併儲存格轉 HTML 表格、表格標題格式、數字列點與圓點列點樣式轉換 | `table_html_semantic: true`, `heading: bold-label`, `ordered-list`, `bullet-list` |
| **learning_blocks** | 學習目標圖示與列點、專有名詞位置（章末 vs 原地）、Anki 卡片格式、思考題 Callout 類型 | `lo_emoji: "🎯"`, `gloss_placement: "chapter_end"`, `gloss_format: "anki"`, `[!TIP]` |
| **navigation** | Obsidian 全局 `index.md` 索引生成、章節末前後頁導航列（`« Prev | Next »`） | `generate_obsidian_index: true`, `inject_chapter_navigation: true` |
| **quality** | 驗收合格分數門檻、安全自動修復、Ollama 深度稽核開關、H3 最大字元長度限制 | `pass_threshold: 85.0`, `enable_safe_autofix: true`, `max_heading_chars: 120` |

## 3. 分層繼承策略 (Hierarchical Inheritance)

1. **全域預設母版 (`config/theme.json`)**：
   - 位於專案根目錄，附帶 `config/theme.schema.json` 提供 IDE 智慧補全。
   - 所有未特別自訂的書籍與文獻一律套用此母版。
2. **單書選填覆寫 (`{book_output_dir}/theme.json`)**：
   - 僅宣告需差異調整的鍵值（例如指定代表色或將 `toc_mode` 改為 `"open"`）。
   - 由 `style_loader.load_theme()` 透過遞迴深層合併（Deep Merge）套用，未覆寫鍵無縫繼承全域母版。

## 4. 即時重刷工具 (`scripts/apply_theme.py`)

針對已轉換完成之 Markdown 章節，提供單鍵 CLI 指令快速重刷外觀，毋須重新耗時解析 PDF：
```bash
python3 scripts/apply_theme.py "/path/to/output/My Book"
```
- 自動讀取該目錄之 `theme.json`（若無則套用全局母版）。
- 正則替換各章節內的 `<style>...</style>` 樣式區塊。
- 重新渲染目錄 `<details>` 區塊以套用最新的 `toc_mode`、`toc_depth` 與標題。
- 重寫輸出目錄下的 `style.css` 獨立樣式表。
