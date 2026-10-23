# ISSUE-009：邊欄名詞解釋缺乏幾何寬度限制誤食主文大標題

- **狀態**：🟢 已根治 (Resolved)
- **發現日期**：2026-10-23
- **Agent**：`antigravity`
- **任務**：`TASK-039`

## 1. 現象

在轉檔 `Career Counseling` Chapter 1 時，正文的二級標題 `Criteria for Choosing Assessments`（字體大、跨度 386 pt）連同下方 15 行主文內容，被完全移出正文，並以邊欄詞彙（Margin Glossary）的形式被打包進區塊中，造成內文遺失與標題大綱結構破損。

- **錯誤訊息**：
  `QualityInvariantGuard: Missing major heading 'Criteria for Choosing Assessments'; heading sequence broken`
- **重現步驟**：
  在 `gloss_placement == "chapter_end"` 之書籍中呼叫 `MarginParser.extract_margin_glossaries()`。
- **影響範圍**：
  採用章末詞彙表排版（非邊欄詞彙）之教科書，以及包含靠左對齊但向右延展之主文標題。

## 2. 根本原因

1. `src/literature_parser/services/parsers/layout/margin_parser.py` 未嚴格依據章節與書籍設定（`gloss_placement`）判斷是否需要啟用邊欄抽取；即使書籍配置為 `gloss_placement == "chapter_end"`，邊欄抽取器仍持續運作。
2. 抽取邊欄項目時，僅檢查了文字區塊的左邊界（`left`），未對右邊界（`right`）或寬度進行幾何封頂。這導致寬度高達 386 pt 的全版面標題與正文段落，只要其左側位於邊欄起點附近，就被整塊吸入邊欄詞彙群中。

## 3. 修正或規避方式

1. **依據配置守衛執行**：
   在 `MarginParser` 開頭加入章節設定檢驗，若當前書籍或章節之 `gloss_placement != "margin"`，直接返回空串列，不進行邊欄抽取。
2. **幾何邊界雙重約束**：
   引入嚴格的幾何寬度與右邊界限制：
   ```python
   margin_bound = profile.geometry.margin_bound if profile else 150.0
   if element.bbox.x1 > margin_bound + 40 or element.bbox.width > 200.0:
       continue  # 屬於主文內容，禁止作為邊欄詞彙抽取
   ```
   確保只有真正狹窄、貼附在邊界內的專有名詞定義才會被收錄。

## 4. 防回歸

已於單元測試 `tests/test_v53_regex_bullet_and_watermark_filters.py` 中增加邊界約束檢驗，並於 `Career Counseling` Chapter 1 實測確認 `Criteria for Choosing Assessments` 完美保留在正文 H2 大綱中。
