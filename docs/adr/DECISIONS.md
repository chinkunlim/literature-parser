# 架構決策紀錄 (Architecture Decision Records)

本目錄記錄系統演進過程中的重要架構決策。

| 編號 | 標題 | 狀態 | 日期 |
|---|---|---|---|
| [ADR-001](001-ollama-hardware-guard-and-auto-verify.md) | 本地 Ollama 離線硬體防護與自我修復管線 | Accepted | 2026-09-23 |
| [ADR-002](002-domain-split-book-and-paper.md) | 教科書與學術期刊管道與實體路徑分離 | Accepted | 2026-09-23 |
| [ADR-003](003-external-tools-in-adapters-layer.md) | 呼叫外部工具與模型之核心協調器收斂至 Adapters 分層 | Accepted | 2026-10-21 |
| [ADR-004](004-hierarchical-profile-and-front-matter-isolation.md) | 四階層 Profile 繼承體系、前言獨立切分與純淨 Chapter 1 | Accepted | 2026-10-22 |
| [ADR-005](005-modular-conversion-and-three-tier-verification.md) | 獨立 MarkdownConversionService、CSS 雙出與三層漸進檢驗體系 | Accepted | 2026-10-22 |
| [ADR-006](006-dual-engine-and-pipelined-concurrency.md) | PyMuPDF 原生雙引擎解析與 CPU-GPU 流水線重疊並行架構 | Accepted | 2026-10-22 |
| [ADR-007](007-unified-theme-and-pipeline-configuration.md) | 全專案樣式排版與管線規則集中外部化 (Unified Theme and Pipeline Configuration) | Accepted | 2026-10-22 |
| [ADR-008](008-convention-input-routing-and-naming-hygiene.md) | 輸入目錄約定分流路由與產出目錄連字號命名衛生規範 | Accepted | 2026-10-22 |
| [ADR-009](009-geometric-bounds-and-non-backtracking-regex.md) | 版面元件解析之嚴格幾何邊界收斂與線性時間跨頁流向縫合 | Accepted | 2026-10-23 |
| [ADR-010](010-archive-segregation-and-batch-resilience.md) | 處理完成文檔嚴格分流歸檔與全書庫斷點續傳機制 | Accepted | 2026-10-25 | TODO |
