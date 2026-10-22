# 005. 統一 Profile 規格、共享知識庫與前言分類規格 (Unified Profile & Shared Knowledge Specification)

## 1. 概述
本規格定義文獻與書籍通用之強型別領域模型 `DocumentProfile`、四階層樣式繼承架構、全域共享知識庫（Shared Knowledge Repository）以及閉環自我修復協定。

## 2. 四階層樣式繼承體系 (Four-Tier Inheritance)
1. **階層 1：全局原形基準 (Archetype Defaults)**：
   - 來源：`config/resources/archetypes/textbook.json` 與 `literature.json`。
   - 提供全域基礎字級階層、通用頁首頁尾比例與邊界。
2. **階層 2：出版社模板與噪音規則 (Publisher Rules)**：
   - 來源：`config/resources/publishers/<pub>.json` 與 `profiles/literature_<pub>.json`。
   - 包含出版社專屬頁首浮水印正則、著作權聲明與版面模板（如 APA, Elsevier, Pearson, Wiley, Springer）。
3. **階層 3：全域共享知識庫 (Shared Knowledge Repository)**：
   - `front_matter_taxonomy.json`：前置頁面標準分類與正則清單（Cover, Publish, TOC, Preface...）。
   - `pedagogical_blocks.json`：學科專門教學區塊定義（Margin Glossary, Dialogue, Case Study, Worked Example, Ethics...）。
   - `literature_sections.json`：學術文獻 IMRAD 標題晉升映射表。
   - `symbol_mappings.json`：Unicode 至 LaTeX 特殊數學符號轉換對照表。
4. **階層 4：個別文件實例 Profile (Instance Canonical Profile)**：
   - 來源：`DATA_DIR/output/<Type>/<Doc-Title>/profile.json`。
   - 實例檔案一律命名為標準 `profile.json`，並為相容性自動維護 `book_profile.json` 或 `document_profile.json` 鏡像。

## 3. 強型別領域模型 (`DocumentProfile`)
- `ProfileMetadata`：文件分類 (`book`/`literature`)、模式 (`digital`/`scanned`)、標題、出版社、版本與前置頁清單 (`front_matter_sections`)。
- `ProfileGeometry`：版面尺寸、`header_cutoff_y`、`footer_cutoff_y`、雙欄中縫 (`gutter_split_x`)、奇偶頁非對稱結構（`PageAsymmetry`）與雙欄跨欄橫幅（`has_spanning_boxes`）。
- `ProfileTypography`：H1/H2/H3 字級閾值、內文字級、Unicode-LaTeX 對照、首字下沉（`has_drop_caps`）與圖表標題正則（`caption_patterns`）。
- `ProfileSpecialBlocks`：動態命中之教學區塊清單（`active_blocks`）與樣式規則（`block_rules`）。

## 4. 閉環自我修復 (Closed-Loop Layout Healing)
- 當品質稽核器或本地 AI 驗證器在轉檔後偵測到排版噪點（如 `LEAKED_HEADER` 或 `LEAKED_FOOTER`）時，調用 `CoordinateCalibrator.adjust_geometry_from_feedback()`。
- 動態微調切分閾值，同步寫入本機 `profile.json` 與鏡像檔案，實現「偵測到一次排版雜訊，即全書自動校正」的閉環修復。
