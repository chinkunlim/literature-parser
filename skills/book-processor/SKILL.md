---
name: book-processor
description: Enterprise-grade PDF and EPUB textbook conversion tool. Performs high-fidelity Markdown extraction with uniform LaTeX math, neural layout OCR, automated multi-metric verification, content continuity stitching, cross-book noise learning, Anki flashcard generation, and local AI review.
---

# Book Processor Skill

This skill provides comprehensive instructions for autonomous AI agents to convert academic textbooks (born-digital PDFs, scanned PDFs, and EPUBs) into high-fidelity, student-ready structured Markdown with uniform LaTeX formulas, pedagogical figure extraction, active recall flashcards, and self-healing quality verification.

---

## When to Use

Activate this skill whenever the user or system needs to:
- Convert textbooks or academic PDFs/EPUBs into structured Markdown.
- Extract high-resolution illustrations and pedagogical vector figures without junk backgrounds or full-page scans.
- Normalize mathematical and statistical formulas to standardized LaTeX (`\dfrac` and `\displaystyle`).
- Generate Mermaid concept mindmaps, formatted learning objectives, and callouts.
- Export active-recall flashcard decks for Anki (`<Chapter>_flashcards.tsv`) and collapsible details (`<details id="flashcard-...">`).
- Verify extraction quality (vocabulary ratio, noise filter, heading balance, LaTeX delimiter parity, cross-page continuity).
- Safely resume interrupted book conversion runs without re-converting already `VERIFIED` chapters.
- Diagnose and auto-heal layout anomalies or audit quality via `VisualAuditor`.

---

## Architecture & Pipeline Lifecycle

```text
inbox/ <Book.pdf>
   │
   ▼
python3 book_processor.py run --file "inbox/<Book.pdf>"
   │
   ├── 1. Outline Analysis & Fast Splitting:
   │      Extract chapter bookmark hierarchy via PDFAnalyzer and split into chapters/<Chapter>/
   │
   ├── 2. Profile Calibration & Feature Discovery:
   │      • CoordinateCalibrator: Determine odd/even page margins and geometry
   │      • SpecialBlockScanner: Detect learning objectives, concept maps, margin glossaries, tables
   │      • StyleLoader: Merge global_profile.json, publisher profile, and book_style_override.py
   │
   ├── 3. Pedagogical Figure & Media Extraction:
   │      • Extract genuine raster figures and render vector diagrams (figure_X_Y.png)
   │      • Discard full-page background scans (coverage >= 80%, dimensions >= 1100x1400)
   │
   ├── 4. Vector / Neural Layout Extraction:
   │      • Born-digital: Parse XML font trees, preserve bold/italic/weight hierarchies
   │      • Scanned: Multi-column neural OCR (Tesseract at 300/400 DPI)
   │      • Extract learning objectives (🎯 **X.X**), tables with colspan, exhibits, footnotes
   │
   ├── 5. LaTeX Math Normalization:
   │      • Uniform fraction sizing: force \dfrac and \displaystyle
   │      • Math symbol mapping (p-value, ANOVA, Chi-square, Greek letters, \rightarrow)
   │
   ├── 6. Layout Auto-Healing & Continuity Stitching:
   │      • LayoutAutoHealer: Fix quad-asterisks (****), repair broken table headers & delimiters
   │      • stitch_cross_page_continuity: Join hyphenated line-end words and page-break splits
   │
   ├── 7. Active Recall Flashcards & Anki Export:
   │      • Collapsible details at chapter end (<details id="flashcard-...">)
   │      • Auto-export to Anki-compatible TSV (<Chapter>_flashcards.tsv)
   │
   ├── 8. Multi-Metric Content Accuracy Verification:
   │      • Vocabulary dictionary ratio (>= 90% pass threshold)
   │      • Header/footer noise filtering (strip copyright/running headers, ignore citations)
   │      • Heading structure sanity (headings < 40% of total lines)
   │      • LaTeX delimiter balance check ($ and $$ parity)
   │      • Genuine image presence & split page continuity
   │      ├── Passed ──► Mark VERIFIED in checkpoint (processing_status.md & .json)
   │      └── Failed ──► AdaptiveLearner self-healing auto-retry (up to 2 attempts)
   │                         • Update learned_rules.json & ~/.book_processor/global_rules.json
   │                         • Escalate OCR resolution to 400 DPI if vocabulary is low
   │                         • Circuit breaker trips if 3 consecutive chapters fail
   │
   └── 9. Automated Archival:
          When 100% of chapters reach VERIFIED status, orchestrator automatically
          moves the completed book from inbox/ to processed/
```

---

## CLI Command Reference

All commands should be executed from the project root (`/Users/.../books`):

```bash
# 1. Environment & Dependency Diagnostic
python3 book_processor.py doctor

# 2. End-to-End Processing (Full Pipeline)
python3 book_processor.py run --file "inbox/<Book>.pdf"
python3 book_processor.py run --file "inbox/<Book>.epub"
python3 book_processor.py run --file "inbox/<Book>.pdf" --chapter "Ch01"

# 3. Safe Resume (skips already VERIFIED chapters, archives when 100% complete)
python3 book_processor.py resume --file "inbox/<Book>.pdf"

# 4. Rapid Split-Only (seconds, creates chapter PDFs without OCR)
python3 book_processor.py split --file "inbox/<Book>.pdf"

# 5. Convert Single Chapter (with auto-verification)
python3 book_processor.py convert --pdf "output/<Book>/chapters/<Chapter>/<Chapter>.pdf"

# 6. Content Accuracy Verification Suite
python3 book_processor.py verify --chapter-dir "output/<Book>/chapters/<Chapter>"
python3 book_processor.py verify --book-dir "output/<Book>"

# 7. Interactive Local AI Review Desk (Ollama)
python3 book_processor.py review -c "output/<Book>/chapters/<Chapter>"

# 8. Background Watchdog & Health Monitor
python3 book_processor.py watchdog --interval 5
python3 book_processor.py watchdog --interval 10 --auto-process

# 9. Batch Re-Conversion & Quality Profiling (Utility)
python3 batch_convert.py                           # Batch convert all split chapters
python3 batch_convert.py --only "Ch02"             # Target specific chapter
python3 batch_convert.py --from "Ch10"             # Start from chapter prefix
python3 batch_convert.py --force                   # Force re-conversion
python3 batch_convert.py --status                  # View current conversion status
python3 batch_convert.py --audit                   # Run visual quality auditor
python3 batch_convert.py --scan                    # Run special block feature scanner
```

---

## Standard Operating Procedures (SOP) for AI Agents

### Scenario A: User asks to convert a book in `inbox/`
1. Check environment dependencies: `python3 book_processor.py doctor`
2. Check if the book was already partially processed:
   - Inspect `output/<Book>/processing_status.json` or `processing_status.md` if present.
   - If chapters are already verified, prefer `python3 book_processor.py resume --file "inbox/<Book>.pdf"`.
   - If starting fresh, run `python3 book_processor.py run --file "inbox/<Book>.pdf"`.
3. Check status upon completion:
   - Open `output/<Book>/processing_status.md` and verify progress is 100.0%.
   - Ensure the source PDF was archived to `processed/<Book>.pdf`.

### Scenario B: Chapter fails verification
1. Inspect the exact verification failure:
   `python3 book_processor.py verify --chapter-dir "output/<Book>/chapters/<Chapter>"`
2. Check common causes:
   - **Noise False Positive**: If a bibliographic citation or abstract contains "all rights reserved" or similar, check `rules.py` exclusion patterns.
   - **Vector Figure Filter**: If large vector diagrams (e.g. `figure_X_Y.png`) trigger full-page scan warnings, ensure `img_filename.startswith("figure_")` is respected.
   - **LaTeX Delimiter Mismatch**: Check for unmatched `$` in formulas and fix using `LayoutAutoHealer`.
3. Re-run verification for that chapter:
   `python3 book_processor.py verify --chapter-dir "output/<Book>/chapters/<Chapter>"`
4. Resume book processing to update checkpoint and archive:
   `python3 book_processor.py resume --file "inbox/<Book>.pdf"`

### Scenario C: Book styling & feature customization
To customize formatting without altering core library code, configure:
- `output/<Book>/book_style_override.py` with a `STYLE_OVERRIDE` dict.
- Available style toggles:
  - `gloss_placement`: `"chapter_end"` (generates flashcards & Anki TSV) or `"inline"`.
  - `generate_toc`: `True`/`False` (generates clickable Markdown TOC).
  - `table_heading_style`: `"bold-label"` or `"markdown"`.
  - `css_justify_body`: `True`/`False`.

### Scenario D: Validating Codebase Integrity
Before and after making changes to the book processor engine, run the full automated test suite:
```bash
python3 -m unittest discover -s tests
```
Ensure all 111 unit tests pass (`OK`).
