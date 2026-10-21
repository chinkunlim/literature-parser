# 001. 雙欄學術論文排版與粉碎數學公式修復

- **狀態**：Open (Mitigated)
- **嚴重程度**：Medium
- **發現日期**：2026-09-20
- **相關模組**：`src/literature_parser/services/parsers/digital_pdf.py`, `src/literature_parser/services/parsers/math_latex.py`

## 問題現象
部分兩欄學術論文在 PDF 文字流解析時，行內數學符號、希臘字母容易被撕裂並插入相鄰正文單詞中，或是坐標軸數字外洩污染正文。

## 根本原因
PDF 底層文字排版並非語意段落，而是散落的文字定位指令。當多欄排版與向量圖形坐標相近時，單純基於幾何投影容易混淆文字邊界。

## 緩解與解決方案
- 引入 `CoordinateCalibrator` 幾何校準。
- 在 `math_latex.py` 中引入連續符號貪婪聚集演算法。
- 透過 `APAStatsNormalizer` 針對統計檢定數值進行正則標準化修復。
