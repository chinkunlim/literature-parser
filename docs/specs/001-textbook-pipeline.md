# 001. 教科書解析管線規格 (Textbook Pipeline Specification)

## 1. 概述
`TextbookPipeline` 專門負責多章節大型教科書之解析，具備目錄（TOC）導航抽取、章節物理切分、學習目標識別與 Anki 卡片匯出功能。

## 2. 核心功能
- **目錄剖析與章節拆分**：利用 PDF Outline 或正文特徵自動識別 Chapter 範圍，執行無損切分。
- **邊欄與專有名詞提取**：自動辨識 Margin Glossaries，轉換為側欄卡片。
- **學習目標與章末總結**：抽取 Learning Objectives (LO) 與 End of Chapter (EOC) 練習題。
- **EPUB 與 Obsidian 整合**：生成雙向導航標籤與出版商特化 CSS 樣式。
