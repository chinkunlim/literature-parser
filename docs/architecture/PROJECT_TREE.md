# 專案完整檔案與資料夾結構樹 (PROJECT_TREE)

> ⚠️ 本檔案由 `python3 scripts/agentctl.py tree` 自動產生，請勿手動編輯。

```text
literature-parser/
├── .agents/                                # 【AI Agent 框架層】專案設定、共用函式庫、Skills、任務卡與交接紀錄
│   ├── bin/                                # [框架腳本] commit、任務、收尾、doctor、update…（由 agentctl 呼叫）
│   │   ├── agent_task.py
│   │   ├── agentctl.py
│   │   ├── audit_trail.py
│   │   ├── auto_commit.py
│   │   ├── build_graph.py
│   │   ├── check_staged.py
│   │   ├── conversations.py
│   │   ├── doctor.py
│   │   ├── finish.py
│   │   ├── setup_env.py
│   │   ├── sync_agent_adapters.py
│   │   ├── update_framework.py
│   │   └── update_tree.py
│   ├── handoff/                            # [交接紀錄] 頂部即時狀態看板 + 歷史交接時間軸，開工前必讀
│   │   ├── ARCHIVE.md                      # [歷史交接歸檔] 超過 20 筆之舊交接紀錄自動歸檔
│   │   └── LATEST.md                       # [即時交接看板] 目前分支、進行中/待接手任務、已完成與待辦事項
│   ├── hooks/                              # [版本控管的 git hooks] 由 core.hooksPath 啟用（pre-commit、pre-push）
│   │   ├── pre-commit
│   │   └── pre-push
│   ├── lib/                                # 框架共用 Python 函式庫 (設定載入、目錄樹註解)
│   │   ├── framework_install.py
│   │   ├── project_config.py
│   │   └── tree_annotations.py
│   ├── skills/                             # 按任務觸發的模組化 Agent Skills (SKILL.md + scripts/*.py)
│   │   ├── adr-issue-tracker/              # [Skill] ADR 與 Known Issues 自動編號與索引
│   │   │   ├── scripts/
│   │   │   │   └── tracker_cli.py
│   │   │   └── SKILL.md
│   │   ├── api-adapter-scaffold/           # [Skill] 外部 API 防腐層產生器
│   │   │   ├── scripts/
│   │   │   │   └── scaffold_adapter.py
│   │   │   └── SKILL.md
│   │   ├── code-review-guard/              # [Skill] 註解、分層、秘密與函式大小靜態審查
│   │   │   ├── scripts/
│   │   │   │   └── review_guard.py
│   │   │   └── SKILL.md
│   │   ├── frontend-design/                # [Skill] Web App 響應式架構、無障礙檢查與視覺品味 (Anti-Slop) 審查
│   │   │   ├── scripts/
│   │   │   │   ├── frontend_tool.py
│   │   │   │   └── taste_auditor.py
│   │   │   └── SKILL.md
│   │   ├── legacy-migration/
│   │   │   ├── scripts/
│   │   │   │   └── migration_status.py
│   │   │   ├── FLASK_TO_FASTAPI.md
│   │   │   └── SKILL.md
│   │   ├── session-closeout/               # [Skill] 收尾：測試、對話紀錄（逐字稿＋摘要）、交接、Commit
│   │   │   ├── scripts/
│   │   │   │   └── closeout_runner.py
│   │   │   └── SKILL.md
│   │   ├── tdd-bugfix/                     # [Skill] 測試驅動開發與離線 Fixture 產生
│   │   │   ├── scripts/
│   │   │   │   └── tdd_runner.py
│   │   │   └── SKILL.md
│   │   └── catalog.json                    # [Skills 目錄] 各 skill 的分層 (core/stack/optional)、觸發時機與指令
│   ├── tasks/                              # [任務卡] 建立、接手、交接、完成 (agentctl task)
│   │   ├── TASK-001-1-uv-pnpm-env-example-brewfile.json
│   │   ├── TASK-002-2-config.json
│   │   ├── TASK-003-3-domain.json
│   │   ├── TASK-004-4-adapters-api-i-o.json
│   │   ├── TASK-005-5-services.json
│   │   ├── TASK-006-6-entrypoints-cli-http.json
│   │   ├── TASK-007-7-web-html-css-js.json
│   │   ├── TASK-008-8.json
│   │   ├── TASK-009-9-readme.json
│   │   ├── TASK-010-10.json
│   │   ├── TASK-011-md.json
│   │   ├── TASK-012-task.json
│   │   ├── TASK-013-profile-json-schema.json
│   │   ├── TASK-014-front-matter-markdown.json
│   │   ├── TASK-015-markdown.json
│   │   ├── TASK-016-markdownconversionservice-css.json
│   │   ├── TASK-017-markdown.json
│   │   ├── TASK-018-markdown.json
│   │   ├── TASK-019-optimize-literature-and-textbook.json
│   │   ├── TASK-020-implement-marker-style-layout-fr.json
│   │   └── TASK-021-externalize-typography-palette-t.json
│   ├── framework.lock                      # [框架鎖定檔] 框架版本與檔案雜湊，供 update_framework 判斷是否被修改
│   └── project.toml                        # [專案設定・各專案自訂] 語言、分層、品質門檻、指令、業務規則
├── .cursor/                                # [Agent 轉接] Cursor 規則 (自動產生)
│   └── rules/
│       └── 00-project-constitution.mdc
├── .github/                                # 【自動化護欄層】CI、PR 範本與 Copilot 入口
│   ├── workflows/                          # CI/CD 自動化檢查工作流程
│   │   └── ci.yml                          # 金鑰掃描、目錄樹檢查、程式審查與離線測試
│   └── copilot-instructions.md             # [Agent 轉接檔] GitHub Copilot 入口 (自動產生)
├── .vscode/
│   ├── extensions.json
│   ├── launch.json
│   └── settings.json
├── .windsurf/                              # [Agent 轉接] Windsurf 規則 (自動產生)
│   └── rules/
│       └── 00-project-constitution.md
├── config/
│   ├── theme.json
│   └── theme.schema.json
├── docs/                                   # 【工程知識庫】架構、規格、決策、已知問題、維運、規範
│   ├── adr/                                # [架構決策庫] 一決定一檔案
│   │   ├── 001-ollama-hardware-guard-and-auto-verify.md
│   │   ├── 002-domain-split-book-and-paper.md
│   │   ├── 003-external-tools-in-adapters-layer.md
│   │   ├── 004-hierarchical-profile-and-front-matter-isolation.md
│   │   ├── 005-modular-conversion-and-three-tier-verification.md
│   │   ├── 006-dual-engine-and-pipelined-concurrency.md
│   │   ├── _TEMPLATE.md                    # ADR 範本 (tracker_cli 會套用)
│   │   └── DECISIONS.md                    # 架構決策總表
│   ├── architecture/                       # [系統架構與資料模型]
│   │   ├── ARCHITECTURE.md                 # 系統架構總覽 (手動) 與自動報告索引
│   │   └── PROJECT_TREE.md                 # 完整檔案結構樹 (自動產生)
│   ├── known-issues/                       # [已知問題庫] 一問題一檔案
│   │   ├── 001-two-column-and-math-shattering.md
│   │   ├── 002-table-banner-and-styling.md
│   │   ├── 003-external-pdf-tools-fallback.md
│   │   ├── 004-chapter1-bookmark-misattribution-and-front-matter-pollution.md
│   │   ├── _TEMPLATE.md                    # 已知問題範本 (tracker_cli 會套用)
│   │   └── KNOWN_ISSUES.md                 # 已知問題總表 (🔴/🟡/🟢)
│   ├── migration/                          # [遷移紀錄] 舊專案搬移清單、批次與完成標準
│   │   └── MIGRATION.md
│   ├── specs/                              # [功能規格書] PRD / API Contract
│   │   ├── 001-textbook-pipeline.md
│   │   ├── 002-literature-pipeline.md
│   │   ├── 003-epub-exporter.md
│   │   ├── 004-fix-playbook-and-synthesizer.md
│   │   ├── 005-unified-profile-and-front-matter.md
│   │   ├── 006-conversion-service-and-three-tier-verification.md
│   │   ├── 007-theme-and-pipeline-configuration.md
│   │   ├── _TEMPLATE.md                    # 規格範本
│   │   └── SPECS.md                        # 規格清單
│   ├── standards/                          # [工程規範] 依任務載入 (Progressive Disclosure)
│   │   ├── ARCHITECTURE_RULES.md           # 分層依賴與系統架構守則
│   │   ├── CODING_PRINCIPLES.md            # 註解規範、Karpathy 原則、SOLID、DRY、Atomic
│   │   ├── ENVIRONMENT_AND_DEPENDENCIES.md # uv / pnpm / Brewfile / 127.0.0.1 環境與依賴規範
│   │   ├── GIT_AND_VERSIONING.md           # Local Git、變更片段、發布與收尾規範
│   │   ├── LOCAL_AI_ENVIRONMENT.md
│   │   ├── MULTI_AGENT_COLLABORATION.md    # Agent 輪流接力：開工、交接、收尾與溯源
│   │   ├── PROJECT_RULES.md
│   │   └── TESTING_AND_QUALITY.md          # 測試金字塔與 DoD 驗收清單
│   ├── PROMPT_TEMPLATES.md
│   └── TEMPLATE_FEEDBACK.md
├── evals/
│   └── EVALS.md
├── scripts/                                # 【專案腳本】agentctl.py 是框架的單一入口；其餘放本專案自己的腳本
│   ├── agentctl.py                         # [單一入口] 轉呼叫 .agents/bin/agentctl.py
│   └── apply_theme.py
├── src/                                    # 【核心原始碼層】分層與依賴方向定義於 .agents/project.toml
│   └── literature_parser/
│       ├── adapters/
│       │   ├── core/
│       │   │   ├── __init__.py
│       │   │   ├── chapter_converter.py
│       │   │   └── orchestrator.py
│       │   ├── fixes/
│       │   │   ├── promoted/
│       │   │   │   └── __init__.py
│       │   │   ├── staged/
│       │   │   │   └── __init__.py
│       │   │   ├── __init__.py
│       │   │   ├── playbook.py
│       │   │   └── synthesizer.py
│       │   ├── guards/
│       │   │   ├── __init__.py
│       │   │   ├── hardware.py
│       │   │   ├── ollama_guard.py
│       │   │   └── validator.py
│       │   ├── parsers/
│       │   │   ├── layout/
│       │   │   │   ├── __init__.py
│       │   │   │   └── table_llm_fixer.py
│       │   │   ├── literature/
│       │   │   │   ├── __init__.py
│       │   │   │   └── metadata_extractor.py
│       │   │   └── pdf_engine.py
│       │   ├── pipelines/
│       │   │   ├── __init__.py
│       │   │   └── literature_pipeline.py
│       │   ├── profiler/
│       │   │   ├── __init__.py
│       │   │   └── ollama_profiler.py
│       │   ├── utils/
│       │   │   ├── __init__.py
│       │   │   └── system.py
│       │   ├── verification/
│       │   │   ├── __init__.py
│       │   │   ├── format_auditor.py
│       │   │   ├── layout_healer.py
│       │   │   ├── ollama_healer.py
│       │   │   ├── ollama_verifier.py
│       │   │   ├── review_manager.py
│       │   │   ├── rules.py
│       │   │   ├── verifier.py
│       │   │   └── visual_auditor.py
│       │   └── __init__.py
│       ├── config/
│       │   ├── resources/
│       │   │   ├── archetypes/
│       │   │   │   ├── literature.json
│       │   │   │   └── textbook.json
│       │   │   ├── profiles/
│       │   │   │   ├── global_profile.json
│       │   │   │   ├── literature_aip.json
│       │   │   │   ├── literature_annual_reviews.json
│       │   │   │   ├── literature_apa.json
│       │   │   │   ├── literature_cup.json
│       │   │   │   ├── literature_elsevier.json
│       │   │   │   ├── literature_sage.json
│       │   │   │   ├── literature_springer.json
│       │   │   │   ├── literature_wiley.json
│       │   │   │   ├── publisher_cengage.json
│       │   │   │   └── publisher_pearson.json
│       │   │   ├── publishers/
│       │   │   │   ├── apa.json
│       │   │   │   ├── elsevier.json
│       │   │   │   ├── ieee.json
│       │   │   │   ├── springer.json
│       │   │   │   └── wiley.json
│       │   │   └── shared_knowledge/
│       │   │       ├── front_matter_taxonomy.json
│       │   │       ├── literature_sections.json
│       │   │       ├── pedagogical_blocks.json
│       │   │       └── symbol_mappings.json
│       │   ├── __init__.py
│       │   ├── env.py
│       │   ├── logging_setup.py
│       │   ├── processor_config.py
│       │   └── settings.py
│       ├── domain/
│       │   ├── profiler/
│       │   │   ├── __init__.py
│       │   │   ├── model_advisor.py
│       │   │   └── profile_schema.py
│       │   └── __init__.py
│       ├── entrypoints/
│       │   ├── project_cli/
│       │   │   ├── __init__.py
│       │   │   ├── cli_audit.py
│       │   │   ├── cli_fix.py
│       │   │   ├── cli_git.py
│       │   │   ├── cli_process.py
│       │   │   ├── cli_project.py
│       │   │   └── common.py
│       │   ├── __init__.py
│       │   ├── cli.py
│       │   ├── doc_cli.py
│       │   └── run.py
│       ├── services/
│       │   ├── concurrency/
│       │   │   ├── __init__.py
│       │   │   ├── m5_worker_pool.py
│       │   │   └── pipelined_processor.py
│       │   ├── converter/
│       │   │   ├── strategies/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── base_strategy.py
│       │   │   │   ├── book_strategy.py
│       │   │   │   └── literature_strategy.py
│       │   │   ├── __init__.py
│       │   │   ├── element_cropper.py
│       │   │   ├── layout_frame.py
│       │   │   ├── markdown_converter.py
│       │   │   └── models.py
│       │   ├── core/
│       │   │   ├── __init__.py
│       │   │   ├── analyzer.py
│       │   │   ├── checkpoint.py
│       │   │   ├── global_state.py
│       │   │   ├── image_manager.py
│       │   │   ├── invariants.py
│       │   │   ├── learner.py
│       │   │   ├── logger.py
│       │   │   ├── splitter.py
│       │   │   └── watchdog.py
│       │   ├── exporter/
│       │   │   ├── __init__.py
│       │   │   ├── epub_exporter.py
│       │   │   ├── epub_math.py
│       │   │   └── epub_styles.py
│       │   ├── fingerprinting/
│       │   │   ├── __init__.py
│       │   │   ├── document_classifier.py
│       │   │   └── publisher_detector.py
│       │   ├── guards/
│       │   │   ├── __init__.py
│       │   │   └── prompts.py
│       │   ├── parsers/
│       │   │   ├── layout/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── callout_parser.py
│       │   │   │   ├── concept_map_parser.py
│       │   │   │   ├── eoc_parser.py
│       │   │   │   ├── list_parser.py
│       │   │   │   ├── margin_parser.py
│       │   │   │   ├── table_parser.py
│       │   │   │   └── vector_figure_parser.py
│       │   │   ├── literature/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── figure_formatter.py
│       │   │   │   ├── imrad_resolver.py
│       │   │   │   └── reference_parser.py
│       │   │   ├── math/
│       │   │   │   ├── __init__.py
│       │   │   │   └── apa_stats_normalizer.py
│       │   │   ├── __init__.py
│       │   │   ├── digital_pdf.py
│       │   │   ├── epub_parser.py
│       │   │   ├── layout_detector.py
│       │   │   ├── math_latex.py
│       │   │   └── scanned_pdf.py
│       │   ├── pipelines/
│       │   │   ├── __init__.py
│       │   │   ├── base_pipeline.py
│       │   │   └── textbook_pipeline.py
│       │   ├── profiler/
│       │   │   ├── __init__.py
│       │   │   ├── coordinate_calibrator.py
│       │   │   └── special_block_scanner.py
│       │   ├── utils/
│       │   │   ├── __init__.py
│       │   │   ├── anki_exporter.py
│       │   │   ├── app_logger.py
│       │   │   ├── obsidian_linker.py
│       │   │   ├── shared_text.py
│       │   │   └── text_utils.py
│       │   ├── verification/
│       │   │   ├── __init__.py
│       │   │   ├── layout_auditor.py
│       │   │   ├── lexical_auditor.py
│       │   │   ├── models.py
│       │   │   ├── quality_engine.py
│       │   │   └── semantic_auditor.py
│       │   ├── __init__.py
│       │   ├── audit_project.py
│       │   ├── book_style.py
│       │   ├── config_manager.py
│       │   ├── literature_style.py
│       │   └── style_loader.py
│       └── __init__.py
├── tests/                                  # 【測試層】單元與整合測試
│   ├── __init__.py
│   ├── test_apa_stats_normalizer.py
│   ├── test_archetype_pipeline_and_knowledge.py
│   ├── test_element_cropper.py
│   ├── test_fingerprinting.py
│   ├── test_journal_conversion.py
│   ├── test_layout_submodules.py
│   ├── test_m5_concurrency.py
│   ├── test_markdown_converter.py
│   ├── test_quality_engine.py
│   ├── test_v21_features.py
│   ├── test_v22_features.py
│   ├── test_v23_layout_features.py
│   ├── test_v24_ch02_layout.py
│   ├── test_v25_layout_healer.py
│   ├── test_v26_exhibits_and_columns.py
│   ├── test_v27_profile_and_layout.py
│   ├── test_v28_advanced_features.py
│   ├── test_v29_special_block_scanner.py
│   ├── test_v30_code_hardening.py
│   ├── test_v31_table_semantic_healer.py
│   ├── test_v32_syntax_and_table_integrity.py
│   ├── test_v33_obsidian_linker.py
│   ├── test_v34_global_state.py
│   ├── test_v35_literature_pipeline.py
│   ├── test_v36_literature_layout_refinement.py
│   ├── test_v37_semantic_figure_table_placement.py
│   ├── test_v38_universal_literature_profiling.py
│   ├── test_v39_format_auditor.py
│   ├── test_v40_fix_playbook_and_invariants.py
│   ├── test_v41_ollama_synthesizer.py
│   ├── test_v42_epub_exporter.py
│   ├── test_v43_input_segregation_and_naming.py
│   ├── test_v44_profile_schema_and_inheritance.py
│   ├── test_v45_front_matter_and_pure_chapter1.py
│   ├── test_v46_speed_and_quality_optimization.py
│   ├── test_v47_marker_layout_framing_and_anchoring.py
│   └── test_v48_theme_configuration_and_override.py
├── web/
│   ├── app.js
│   ├── dashboard.html
│   ├── index.html
│   ├── styles.css
│   └── WEB.md
├── .editorconfig
├── .env.example                            # [設定範本] 環境變數清單與預設值說明
├── .gitignore                              # [版控排除] 排除依賴、機密 .env、憑證與執行期快取
├── .python-version                         # [Python 版本釘選] 供 uv / pyenv / mise 自動讀取
├── AGENTS.md                               # [AI 協作憲法・唯一規則來源] 所有 AI Agent 共用的開發原則與 Skills 路由
├── CHANGELOG.md                            # [版本歷史] commit 寫入 Unreleased；agentctl finish --tag 發布版本
├── CLAUDE.md                               # [Agent 轉接檔] Claude Code 入口，匯入 AGENTS.md (自動產生)
├── GEMINI.md                               # [Agent 轉接檔] Gemini CLI 入口，指向 AGENTS.md (自動產生)
├── LICENSE
├── pyproject.toml                          # [PEP 621 單一真相來源] Python 中繼資料、依賴分組、pytest 與 ruff 設定
└── README.md                               # [唯一 README] 專案入口、快速開始與文件索引
```
