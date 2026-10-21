# 專案遷移計畫 (MIGRATION)

> 舊專案的檔案目前在 `legacy/`（原封不動）。依下方批次逐一搬到新結構，**每一批都要符合新專案的所有規範**，全部完成後刪除 `legacy/`。

## 1. 來源

- **舊專案位置**：`/Users/limchinkun/Desktop/projects/Old/books`
- **舊專案遠端**：`https://github.com/chinkunlim/book-processor.git`
- **遷移時的最後 commit**：`1ff162d`
- **git 歷史**：已保留（新 repo 由舊 repo clone；舊檔案以 `git mv` 移到 `legacy/`，`git log --follow` 可追溯）
- **模式**：開發模式：Flask 必須全部改寫成 FastAPI（對照表：[`FLASK_TO_FASTAPI.md`](../../.agents/skills/legacy-migration/FLASK_TO_FASTAPI.md)）（舊專案未使用 Flask）
- **建立時間**：2026-10-21 04:12 UTC
- **檔案數**：209

## 2. 完成標準

### 每一批

每一批都必須做到（做到才可 `agentctl task done`）：

1. **兩個 commit：先搬、再整理**（保證 `git log --follow` 與 blame 追得到舊歷史）：
   - 第一個 commit 只用 `git mv legacy/舊路徑 新路徑` 搬移，內容一個字都不改：`agentctl commit --bump none -m "refactor(migration): move <檔名> from legacy"`。pre-commit 只對「從 legacy/ 原樣搬入」的檔案暫時放行註解、大小、分層與 print 問題（秘密與禁用套件仍會擋）。
   - 下一個 commit 必須把這批檔案全部整理到符合規範（第 2 點），否則任何 commit 與 `agentctl check` 都過不了，所以一批只搬少量檔案。
2. 依新規範修改：
   - **註解**：檔案開頭用途說明；每個函數/類別的說明、每個參數（`Args:` / `@param`）與回傳值（[`CODING_PRINCIPLES.md`](../standards/CODING_PRINCIPLES.md) §0）。
   - **型別**：Python 參數與回傳值都有型別，`uv run mypy` 通過（strict）。
   - **分層**：放到正確的層；環境變數只在 `config` 層讀取，其他層改收 `AppConfig` 參數（[`ARCHITECTURE_RULES.md`](../standards/ARCHITECTURE_RULES.md)）。
   - **函式大小**：符合 `[quality]` 門檻。
   - **Log**：除了 entrypoints，`print` 一律改成模組 logger；關鍵步驟、外部呼叫與例外都要記 log（[`CODING_PRINCIPLES.md`](../standards/CODING_PRINCIPLES.md) §0.4）。
   - **秘密**：金鑰移到 `.env`，`.env.example` 只留變數名稱。
   - **依賴**：只用 `uv add` / `pnpm add`（[`ENVIRONMENT_AND_DEPENDENCIES.md`](../standards/ENVIRONMENT_AND_DEPENDENCIES.md)）。
   - **本機服務**：綁 `127.0.0.1`，網址不用 `localhost`。
   - **測試**：搬移的程式要有測試（沿用舊測試或補寫，[`TESTING_AND_QUALITY.md`](../standards/TESTING_AND_QUALITY.md)）。
3. `python3 scripts/agentctl.py check` 與專案測試全部通過。
4. 下方「檔案清單」把這批的 ☐ 改成 ☑；過程中的重要決策寫 ADR、發現的舊 bug 寫 known-issue。
5. `python3 scripts/agentctl.py commit --agent <名字> --task TASK-NNN`，再 `agentctl task done TASK-NNN --summary ...`。

### 整個遷移

全部完成才算遷移成功（`python3 scripts/agentctl.py migration --verify` 會逐項檢查）：

- [ ] `legacy/` 已刪除（所有檔案都搬到新結構或確認不需要）。
- [ ] 舊資料已依 §4.5 複製到 `DATA_DIR`，程式透過 config 讀取路徑，專案資料夾內沒有資料檔。
- [ ] 沒有 `requirements.txt`、`package-lock.json`、`yarn.lock`、`Pipfile`：依賴只在 `pyproject.toml` + `uv.lock`、`package.json` + `pnpm-lock.yaml`。
- [ ] `python3 scripts/agentctl.py check` 全部通過（註解、分層、秘密、lint、mypy strict、目錄樹）。
- [ ] 專案測試全部通過。
- [ ] 所有遷移任務卡都是 `done`。
- [ ] 模板的範例程式（`greeting` 相關的 services / domain / cli / api / 資料表 `greetings` 與其 Alembic revision、測試）已刪除或換成真正的程式。
- [ ] `README.md` 改寫為這個專案的說明；`docs/architecture/ARCHITECTURE.md` 有系統概覽；主要功能在 `docs/specs/` 有規格。
- [ ] 舊專案已知的問題記在 `docs/known-issues/`；遷移中的重要決策記在 `docs/adr/`。
- [ ] `.env.example` 列出所有需要的變數（只有名稱）。
- [ ] 最後執行 `agentctl closeout`（本機對話紀錄＋交接看板記下遷移完成）。

## 3. 批次

| 順序 | 任務 | 內容 | 檔案數 |
|---|---|---|---|
| 1 | `TASK-001` | 依賴與設定檔轉換（uv / pnpm / .env.example / Brewfile） | 4 |
| 2 | `TASK-002` | config 層（設定、環境變數讀取） | 2 |
| 3 | `TASK-003` | domain 層（資料模型、純邏輯） | 1 |
| 4 | `TASK-004` | adapters 層（外部 API、資料庫、檔案 I/O） | 8 |
| 5 | `TASK-005` | services 層（業務流程） | 70 |
| 6 | `TASK-006` | entrypoints 層（CLI、HTTP、排程入口） | 9 |
| 7 | `TASK-007` | web 前端（HTML / CSS / JS） | 1 |
| 8 | `TASK-008` | 測試 | 29 |
| 9 | `TASK-009` | 文件（README、規格、決策、已知問題） | 54 |
| 10 | `TASK-010` | 其他（資料、資源、需人工判斷） | 31 |

## 4. 依賴轉換

舊專案有 pyproject.toml / setup.py / Pipfile：把其中的依賴逐一用 uv add 加入，再比對版本：

```bash
uv tree
```

舊 `.env.example` 的變數（加到新 `.env.example`，只寫名稱）：`OLLAMA_HOST`、`OLLAMA_DEFAULT_MODEL`、`MIN_RAM_AVAILABLE_GB`、`MIN_DISK_FREE_GB`、`ALLOW_BATTERY_MODE`、`ALLOW_PUSH`

## 4.5 資料搬到 DATA_DIR（資料不進新專案）

舊專案的資料**沒有**搬進 `legacy/`，也不在新專案資料夾內；唯一的副本仍在舊專案（未被修改）。確認 `.env` 的 `DATA_DIR` 後，**在新專案資料夾內**依序執行（目標是相對於新專案的路徑）：

`data`（3532 個檔案）→ `../../projects-data/literature-parser/input/data/`：

```bash
mkdir -p ../../projects-data/literature-parser/input/data/ && rsync -a "/Users/limchinkun/Desktop/projects/Old/books/data/" ../../projects-data/literature-parser/input/data/
```

複製完成並確認新專案能讀到資料後，再決定是否刪除舊專案的資料（請自行確認，工具不會刪除）。

## 5. 風險

- 🟡 `legacy/memory/sessions/2026-09-18-initial-textbook-pipeline-development-transcript.md` 大小 5 MB：確認是否該放進 git（資料檔可改放外部儲存）。
- 🟡 舊的 git 歷史仍含 3532 個資料檔（repo 體積大、可能有著作權資料）：若要推送到 GitHub，先評估用 `git filter-repo` 清除歷史中的資料檔。

## 6. 檔案清單

| 狀態 | 舊檔案 | 建議位置 | 批次 |
|---|---|---|---|
| ☑ | `legacy/.env.example` | `pyproject.toml / package.json / .env.example（轉換後刪除舊檔）` | deps |
| ☑ | `legacy/.gitignore` | `pyproject.toml / package.json / .env.example（轉換後刪除舊檔）` | deps |
| ☑ | `legacy/.python-version` | `pyproject.toml / package.json / .env.example（轉換後刪除舊檔）` | deps |
| ☑ | `legacy/pyproject.toml` | `pyproject.toml / package.json / .env.example（轉換後刪除舊檔）` | deps |
| ☑ | `legacy/src/doc_processor/config.py` | `src/literature_parser/config/` | config |
| ☑ | `legacy/src/doc_processor/config_manager.py` | `src/literature_parser/config/` | config |
| ☑ | `legacy/src/doc_processor/profiler/model_advisor.py` | `src/literature_parser/domain/` | domain |
| ☑ | `legacy/src/doc_processor/parsers/layout/table_llm_fixer.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/doc_processor/parsers/literature/metadata_extractor.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/doc_processor/profiler/ollama_profiler.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/doc_processor/utils/system.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/doc_processor/verification/ollama_healer.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/doc_processor/verification/ollama_verifier.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/guards/hardware.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/src/guards/ollama_guard.py` | `src/literature_parser/adapters/` | adapters |
| ☑ | `legacy/audit_project.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/book_style.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/concurrency/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/concurrency/m5_worker_pool.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/analyzer.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/checkpoint.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/global_state.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/image_manager.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/invariants.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/learner.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/logger.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/orchestrator.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/splitter.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/core/watchdog.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/exporter/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/exporter/epub_exporter.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/exporter/epub_styles.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fingerprinting/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fingerprinting/document_classifier.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fingerprinting/publisher_detector.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fixes/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fixes/playbook.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fixes/promoted/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fixes/staged/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/fixes/synthesizer.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/literature_style.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/digital_pdf.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/epub_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/callout_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/concept_map_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/eoc_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/list_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/margin_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/table_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout/vector_figure_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/layout_detector.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/literature/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/literature/figure_formatter.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/literature/imrad_resolver.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/literature/reference_parser.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/math/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/math/apa_stats_normalizer.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/math_latex.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/parsers/scanned_pdf.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/pipelines/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/pipelines/base_pipeline.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/pipelines/literature_pipeline.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/pipelines/textbook_pipeline.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/profiler/coordinate_calibrator.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/profiler/special_block_scanner.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/style_loader.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/utils/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/utils/anki_exporter.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/utils/obsidian_linker.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/utils/shared_text.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/utils/text_utils.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/__init__.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/format_auditor.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/layout_healer.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/review_manager.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/rules.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/verifier.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/doc_processor/verification/visual_auditor.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/guards/prompts.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/guards/validator.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/src/utils/logger.py` | `src/literature_parser/services/` | services |
| ☑ | `legacy/run.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/__init__.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/cli_audit.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/cli_fix.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/cli_git.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/cli_process.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/cli_project.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/cli/common.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/src/doc_processor/cli.py` | `src/literature_parser/entrypoints/` | entrypoints |
| ☑ | `legacy/dashboard/index.html` | `web/` | web |
| ☑ | `legacy/tests/__init__.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_apa_stats_normalizer.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_archetype_pipeline_and_knowledge.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_fingerprinting.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_journal_conversion.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_layout_submodules.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_m5_concurrency.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v21_features.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v22_features.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v23_layout_features.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v24_ch02_layout.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v25_layout_healer.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v26_exhibits_and_columns.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v27_profile_and_layout.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v28_advanced_features.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v29_special_block_scanner.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v30_code_hardening.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v31_table_semantic_healer.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v32_syntax_and_table_integrity.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v33_obsidian_linker.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v34_global_state.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v35_literature_pipeline.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v36_literature_layout_refinement.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v37_semantic_figure_table_placement.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v38_universal_literature_profiling.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v39_format_auditor.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v40_fix_playbook_and_invariants.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v41_ollama_synthesizer.py` | `tests/` | tests |
| ☑ | `legacy/tests/test_v42_epub_exporter.py` | `tests/` | tests |
| ☑ | `legacy/.agent/skills/document-processor/SKILL.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/.agent/skills/literature-processor/SKILL.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/.agent/skills/textbook-processor/SKILL.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/.github/CONTRIBUTING.md` | `docs/standards/PROJECT_RULES.md（只留本專案特有的規則；通用規則已在 AGENTS.md / standards）` | docs |
| ☑ | `legacy/.github/SECURITY.md` | `README.md 的安全說明，或 docs/standards/PROJECT_RULES.md` | docs |
| ☑ | `legacy/AGENTS.md` | `docs/standards/PROJECT_RULES.md（只留本專案特有的規則；通用規則已在 AGENTS.md / standards）` | docs |
| ☑ | `legacy/CHANGELOG.md` | `CHANGELOG.md（舊版本紀錄貼在 0.1.0 下方，保留原日期）` | docs |
| ☑ | `legacy/DECISIONS.md` | `docs/adr/（每個決策拆成一個 NNN-*.md，用 adr-issue-tracker）` | docs |
| ☑ | `legacy/KNOWN_ISSUES.md` | `docs/known-issues/（每個問題一個 NNN-*.md）` | docs |
| ☑ | `legacy/README.md` | `README.md（改寫成新專案的說明）` | docs |
| ☑ | `legacy/WORKFLOW_GUIDE.md` | `docs/standards/PROJECT_RULES.md（只留本專案特有的規則；通用規則已在 AGENTS.md / standards）` | docs |
| ☑ | `legacy/conversations/raw/001_pdf_epub_extraction_and_sample_slicing.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/002_research_methods_conversion_and_tuning.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/003_table_recognition_and_dual_column_layout.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/004_journal_article_latex_table_healer.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/005_agent_init_startup_sequence_and_refactor.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/006_project_architecture_and_governance.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/007_full_feature_enhancements_and_books_conversion.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/008_literature_style_decoupling_and_verification.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/raw/009_epub_exporter_and_multi_format_pipeline.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/001_pdf_epub_extraction_and_sample_slicing_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/002_research_methods_conversion_and_tuning_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/003_table_recognition_and_dual_column_layout_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/004_journal_article_latex_table_healer_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/005_agent_init_startup_sequence_and_refactor_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/006_project_architecture_and_governance_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/007_full_feature_enhancements_and_books_conversion_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/008_literature_style_decoupling_and_verification_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/conversations/summaries/009_epub_exporter_and_multi_format_pipeline_summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/docs/ARCHITECTURE.md` | `docs/architecture/ARCHITECTURE.md` | docs |
| ☑ | `legacy/docs/CODING_RULES.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/docs/CONTEXT.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/docs/DEPLOYMENT.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/docs/OPTIMIZATION_PROPOSAL.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/docs/PROMPT_TEMPLATES.md` | `docs/PROMPT_TEMPLATES.md` | docs |
| ☑ | `legacy/docs/TOOLS.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/evals/README.md` | `evals/EVALS.md（全專案只有根目錄一份 README）` | docs |
| ☑ | `legacy/memory/HANDOFF.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/memory/TASKS.md` | `docs/specs/ 或 docs/adr/ 或 docs/known-issues/` | docs |
| ☑ | `legacy/memory/sessions/2026-09-17-read-the-full-conversation-transcript-at-usersli-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-18-initial-textbook-pipeline-development-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-18-initial-textbook-pipeline-development-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-18-research-methods-book-conversion-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-18-research-methods-book-conversion-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-20-typography-tables-and-formula-refinement-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-20-typography-tables-and-formula-refinement-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-23-academic-journal-pipeline-and-dual-column-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-23-academic-journal-pipeline-and-dual-column-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-23-project-architecture-and-governance-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-23-project-architecture-and-governance-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-24-full-feature-enhancements-and-books-conversion-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-24-full-feature-enhancements-and-books-conversion-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-24-uv-run-python-runpy-agent-init-additional-meta-summary.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/memory/sessions/2026-09-24-uv-run-python-runpy-agent-init-additional-meta-transcript.md` | `決策 → docs/adr/、錯誤根因 → docs/known-issues/；原檔移到 .agents/conversations/（只存本機，不進 git）` | docs |
| ☑ | `legacy/.cursorrules` | `docs/standards/PROJECT_RULES.md（只留本專案特有的規則；各工具入口檔由 agentctl sync 產生）` | other |
| ☑ | `legacy/.github/workflows/ci.yml` | `比對模板產生的 .github/workflows/ci.yml，只併入本專案特有的步驟` | other |
| ☑ | `legacy//data/output/books/Research-Methods-in-Psychology-1641401901/chapters/064_The Single-Subject Versus Group \342\200\234Debate\342\200\235/064_The Single-Subject Versus Group \342\200\234Debate\342\200\235.md"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy//data/output/books/Research-Methods-in-Psychology-1641401901/chapters/081_From the \342\200\234Replicability Crisis\342\200\235 to Open Science Practices/081_From the \342\200\234Replicability Crisis\342\200\235 to Open Science Practices.md"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy//data/output/books/Research-Methods-in-Psychology-1641401901/chapters/081_From the \342\200\234Replicability Crisis\342\200\235 to Open Science Practices/images/081_081.png"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy//data/output/books/Research-Methods-in-Psychology-1641401901/chapters/081_From the \342\200\234Replicability Crisis\342\200\235 to Open Science Practices/images/081_082.jpg"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy//memory/sessions/2026-09-24-\345\237\267\350\241\214-uv-run-python-runpy-agent-init-additional-me-summary.md"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy//memory/sessions/2026-09-24-\345\237\267\350\241\214-uv-run-python-runpy-agent-init-additional-me-transcript.md"` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/LICENSE` | `LICENSE（保留原授權）` | other |
| ☑ | `legacy/Makefile` | `改用 agentctl / uv run / pnpm 指令，寫進 README；仍需要的腳本放 scripts/` | other |
| ☑ | `legacy/config/archetypes/literature.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/archetypes/textbook.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/publishers/apa.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/publishers/elsevier.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/publishers/ieee.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/publishers/springer.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/publishers/wiley.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/shared_knowledge/literature_sections.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/config/shared_knowledge/symbol_mappings.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/global_profile.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_aip.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_annual_reviews.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_apa.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_cup.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_elsevier.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_sage.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_springer.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/literature_wiley.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/publisher_cengage.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/src/doc_processor/profiles/publisher_pearson.json` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
| ☑ | `legacy/uv.lock` | `依用途判斷（資料 → DATA_DIR，靜態資源 → web/ 或 src/<pkg>/）` | other |
