---
name: document-processor
description: Master orchestrator skill for converting textbooks and academic literature into structured Markdown. Automatically routes between textbook-processor and literature-processor with hardware guards and dual verification.
---

# 📚 Document Processor Skill (全域文檔處理總調度技能)

本技能為專案之**總入口調度技能 (Master Orchestrator)**。負責接收所有轉檔需求，執行軟硬體安全前置健檢，並根據輸入特徵自動路由至對應的專業子技能。

---

## 🏛️ 技能分層架構 (Skill Hierarchy)

```text
┌───────────────────────────────────────────────────────────┐
│        document-processor (總調度技能 / Master Skill)        │
│  • 前置軟硬體健檢 (Doctor Audit: RAM >= 4GB / SSD >= 10GB) │
│  • 慣例路由與文檔分類 (Routing: Textbook vs Literature)   │
│  • 本地 Ollama 喚醒與確定性 Prompt 注入                   │
│  • 瑕疵與低信度 (< 0.80) 自動隔離至 data/needs_review/     │
└─────────────────────────────┬─────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│    textbook-processor     │   │   literature-processor    │
│    (長篇教科書子技能)     │   │     (學術文獻子技能)      │
│  • 章節極速拆分 (TOC)     │   │  • 單篇原子性處理 (No TOC) │
│  • 跨頁斷句縫合 (Stitch)  │   │  • 雙欄帶狀流動 (Band Flow)│
│  • 專有名詞與 Anki 卡片   │   │  • 摘要與作者機構結構化   │
│  • 學習目標與案例對話     │   │  • APA/IEEE 參考文獻解析   │
└───────────────────────────┘   └───────────────────────────┘
```

---

## 🚀 執行規範 (Execution Protocol)

AI Agent 接到任何轉檔指示時，**嚴禁口頭指示使用者手動執行**，必須主動調用終端執行：
```bash
# 處理書籍 (自動調派 textbook-processor)
python run.py process data/input/books/<filename>

# 處理學術文獻 (自動調派 literature-processor)
python run.py process data/input/literature/<filename>
```
