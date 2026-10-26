# 功能規格清單 (Specifications)

本目錄收錄系統各項核心功能與架構模組之規格說明。

| 編號 | 標題 | 狀態 | 負責模組 |
|---|---|---|---|
| [SPEC-001](001-textbook-pipeline.md) | 教科書解析管線規格 | Implemented | `services.pipelines.textbook_pipeline` |
| [SPEC-002](002-literature-pipeline.md) | 學術期刊文獻解析管線規格 | Implemented | `adapters.pipelines.literature_pipeline` |
| [SPEC-003](003-epub-exporter.md) | EPUB 3 電子書匯出管線規格 | Implemented | `services.exporter.epub_exporter` |
| [SPEC-004](004-fix-playbook-and-synthesizer.md) | 排版修復手冊與配方合成規格 | Implemented | `adapters.fixes.synthesizer` |
| [SPEC-005](005-unified-profile-and-front-matter.md) | 統一 Profile 規格、共享知識庫與前言分類規格 | Implemented | `domain.profiler.profile_schema` |
| [SPEC-006](006-conversion-service-and-three-tier-verification.md) | 獨立 Markdown 轉換服務與三層漸進檢驗體系規格 | Implemented | `services.converter.*`, `services.verification.*` |
| [SPEC-007](007-theme-and-pipeline-configuration.md) | 樣式、排版與管線規則外部化規格 | Implemented | `config/theme.json`, `services.style_loader`, `scripts/apply_theme.py` |
| [SPEC-008](008-batch-resilience-and-zero-defect-pipeline.md) | 批次轉檔韌性與全量零缺陷驗證規格 | Implemented | `adapters.core.orchestrator`, `services.utils.text_utils`, `services.parsers.layout.*` |
| [SPEC-009](009-autonomous-layout-and-archive-segregation.md) | 自適應版面剖析、歸檔分流與批次斷點續傳規格 | Implemented | `services.profiler.*`, `services.converter.*`, `adapters.guards.*` |
| [SPEC-010](010-web-comparison-and-feedback-system.md) | 互動式 Web Studio、雙欄 PDF/EPUB 對照編輯與問題反饋回歸保護規格 | Implemented | `web_app.py`, `mcp_server.py`, `web_data_service.py`, `correction_service.py`, `web/` |
