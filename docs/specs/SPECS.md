# 功能規格清單 (Specifications)

本目錄收錄系統各項核心功能與架構模組之規格說明。

| 編號 | 標題 | 狀態 | 負責模組 |
|---|---|---|---|
| [SPEC-001](001-textbook-pipeline.md) | 教科書解析管線規格 | Implemented | `services.pipelines.textbook_pipeline` |
| [SPEC-002](002-literature-pipeline.md) | 學術期刊文獻解析管線規格 | Implemented | `adapters.pipelines.literature_pipeline` |
| [SPEC-003](003-epub-exporter.md) | EPUB 3 電子書匯出管線規格 | Implemented | `services.exporter.epub_exporter` |
| [SPEC-004](004-fix-playbook-and-synthesizer.md) | 排版修復手冊與配方合成規格 | Implemented | `adapters.fixes.synthesizer` |
| [SPEC-005](005-unified-profile-and-front-matter.md) | 統一 Profile 規格、共享知識庫與前言分類規格 | Implemented | `domain.profiler.profile_schema` |
