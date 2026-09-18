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

## Architecture & 5-Step Processing Lifecycle

```text
inbox/ <Book.pdf | Book.epub>
   │
   ▼
[Step 1: Rapid Chapter Splitting]
   │  • PDFSplitter splits book into standalone chapter PDFs in seconds (no heavy OCR)
   │  • Chapters organized under output/<Book>/chapters/<Chapter>/
   │
   ▼
[Step 2: Program & Local AI Layout Profiling]
   │  • SpecialBlockScanner & PDFAnalyzer detect geometry, columns, margins & special blocks
   │  • Ollama local AI assists on layout ambiguities and complex page blocks
   │  • Writes configuration to output/<Book>/book_profile.json (Book-level overrides global profile)
   │
   ▼
[Step 3: High-Fidelity Markdown & HTML/CSS Semantic Conversion]
   │  • Born-digital: DigitalPDFParser with auto two-column uncurling & fontspec hierarchies
   │  • Scanned/hybrid: ScannedPDFParser with full-layout text extraction & artifact cleaning
   │  • EPUB: EPUBProcessor extracts images & renders structured Markdown
   │  • Semantic HTML tables (<table class="textbook-table">) & dialogue (<div class="dialogue-block">)
   │  • Embedded typographic stylesheet (<style>): adjust presentation without re-converting from PDF
   │  • Uniform LaTeX math (\dfrac, \displaystyle) and pedagogical figures
   │  • Cross-page sentence stitching (stitch_cross_page_continuity) & hyphen repair
   │  • Active recall flashcard drawer & Anki TSV deck generation (<Chapter>_flashcards.tsv)
   │
   ▼
[Step 4: Dual Verification Engine]
   │  • Python Rules: Vocabulary accuracy (>= 90%), running header/footer noise filtering,
   │    heading distribution, LaTeX equation delimiter parity, split page continuity
   │  • Ollama AI Audit: Semantic continuity, formula integrity, and visual fidelity check
   │  ├── Passed ──► Mark CONVERTED / VERIFIED in processing_status.md & .json
   │  └── Warnings ──► Trigger Step 5
   │
   ▼
[Step 5: Self-Healing Loop & Centralized Review Desk]
   │  • Self-Healing: Re-runs continuity repair, adjusts noise regex, re-converts affected page
   │  • Human-in-the-Loop Desk: Remaining issues surfaced via `review -b <book_dir>`
   │    for fast, one-click interactive review without manual page-by-page auditing
   │
   ▼
[Automated Archival]
   • When 100% of chapters pass verification, the source book is moved to processed/
```

---

## Direct Terminal / Command-Line (Cmd) Execution Guide

All commands can be executed directly from your terminal (`Terminal.app`, `bash`, `zsh`, `cmd.exe`, or `PowerShell`) in the project root (`/Users/.../books`):

### 1. Direct Batch Conversion (High Throughput)
```bash
# Convert all chapters of a specific book directory (forces overwrite)
python3 batch_convert.py -b "output/Research Methods, Design, and Analysis 13th ed" --force
python3 batch_convert.py -b "output/Group Counseling- Strategies and Skills - Standalone Book -- Ed E. Jacobs, Christine J. Schimmel, Robert L. L. Masson, -" --force
python3 batch_convert.py -b "output/Groups- Process and Practice, Loose-Leaf Version -- Marianne Schneider Corey; Gerald Corey; Cindy Corey -- ( WeLib.org )" --force

# Convert ALL books currently under output/ in one pass
python3 batch_convert.py --all-books --force

# Target a single chapter or start from a prefix
python3 batch_convert.py -b "output/<Book>" --only "Ch01"
python3 batch_convert.py -b "output/<Book>" --from "Ch05"

# Run visual quality auditor across all chapters of a book (scores 1-10)
python3 batch_convert.py -b "output/<Book>" --audit

# Run layout feature scanner (learning objectives, tables, concept maps)
python3 batch_convert.py -b "output/<Book>" --scan
```

### 2. Unified Orchestrator CLI (`book_processor.py`)
```bash
# Environment diagnostic (verifies poppler, tesseract, ollama, sips)
python3 book_processor.py doctor

# Rapid chapter splitting (split entire book in seconds without OCR)
python3 book_processor.py split --file "inbox/<Book>.pdf"

# Full end-to-end processing (split, convert, auto-verify, and archive)
python3 book_processor.py run --file "inbox/<Book>.pdf"
python3 book_processor.py run --file "inbox/<Book>.epub"
python3 book_processor.py run --file "inbox/<Book>.pdf" --chapter "Ch01"

# Resume interrupted processing (skips already verified chapters)
python3 book_processor.py resume --file "inbox/<Book>.pdf"

# Convert a single chapter PDF with auto-verification
python3 book_processor.py convert --pdf "output/<Book>/chapters/<Chapter>/<Chapter>.pdf"

# Run multi-metric content accuracy verification suite
python3 book_processor.py verify --book-dir "output/<Book>"
python3 book_processor.py verify --chapter-dir "output/<Book>/chapters/<Chapter>"

# Centralized Human-in-the-Loop review desk
python3 book_processor.py review -b "output/<Book>"
python3 book_processor.py review -c "output/<Book>/chapters/<Chapter>"

# Background inbox watchdog & system health monitor
python3 book_processor.py watchdog --interval 5 --auto-process
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
