"""
Unified Command-Line Interface (CLI)
====================================
Subcommands:
  split    - Rapidly splits a book into chapter PDFs (takes seconds).
  convert  - Converts a single chapter PDF to Markdown, images & LaTeX math, and auto-verifies.
  run      - Splits and converts a book (or a target chapter) with automatic verification.
  resume   - Resumes interrupted processing, automatically skipping already verified chapters.
  verify   - Runs standalone multi-metric content accuracy verification.
"""

import sys
import argparse
from pathlib import Path
from book_processor import __version__
from book_processor.core.orchestrator import BookProcessorOrchestrator
from book_processor.verification.verifier import AccuracyVerifier
from book_processor.utils.system import check_dependencies
from book_processor.config import DEFAULT_OLLAMA_MODEL


def main():
    parser = argparse.ArgumentParser(
        prog="book-processor",
        description="Enterprise PDF & EPUB Structured Markdown Extractor with Neural Layout OCR, LaTeX Math & Local AI Verification."
    )
    parser.add_argument('--version', '-v', action='version', version=f"book-processor {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")

    # 1. SPLIT Subcommand
    p_split = subparsers.add_parser("split", help="Split entire book into chapter PDFs in seconds (no OCR)")
    p_split.add_argument("--file", "-f", required=True, help="Path to input PDF file")
    p_split.add_argument("--output-dir", "-o", default="./output", help="Output directory")

    # 2. CONVERT Subcommand (with auto-verify)
    p_convert = subparsers.add_parser("convert", help="Convert a single chapter PDF to Markdown + LaTeX, then auto-verify")
    p_convert.add_argument("--pdf", "-p", required=True, help="Path to chapter PDF file")
    p_convert.add_argument("--ollama", action="store_true", help="Enable local Ollama AI audit")
    p_convert.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Local Ollama model name (default: {DEFAULT_OLLAMA_MODEL})")

    # 3. RUN Subcommand
    p_run = subparsers.add_parser("run", help="Split, convert & auto-verify full book or target chapter")
    p_run.add_argument("--file", "-f", default=None, help="Process a specific PDF or EPUB file")
    p_run.add_argument("--chapter", "-c", default=None, help="Target a specific chapter name or number")
    p_run.add_argument("--input-dir", "-i", default=".", help="Input directory (default: current directory)")
    p_run.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    p_run.add_argument("--ollama", action="store_true", help="Enable local Ollama AI audit")
    p_run.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Local Ollama model name (default: {DEFAULT_OLLAMA_MODEL})")
    p_run.add_argument("--parallel", action="store_true", help="Process chapters concurrently utilizing Apple M5 P-Cores")

    # 4. RESUME Subcommand
    p_resume = subparsers.add_parser("resume", help="Resume interrupted processing, skipping verified chapters")
    p_resume.add_argument("--file", "-f", required=True, help="Path to book PDF file to resume")
    p_resume.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    p_resume.add_argument("--ollama", action="store_true", help="Enable local Ollama AI audit")
    p_resume.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Local Ollama model name (default: {DEFAULT_OLLAMA_MODEL})")
    p_resume.add_argument("--parallel", action="store_true", help="Process chapters concurrently utilizing Apple M5 P-Cores")

    # 5. VERIFY Subcommand
    p_verify = subparsers.add_parser("verify", help="Run content accuracy verification suite")
    p_verify.add_argument("--chapter-dir", "-c", help="Path to specific chapter folder")
    p_verify.add_argument("--book-dir", "-b", help="Path to book output folder (containing chapters/)")
    p_verify.add_argument("--expected-pages", "-p", type=int, default=None, help="Expected page count for split PDF")
    p_verify.add_argument("--ollama", action="store_true", help="Enable local Ollama AI audit")
    p_verify.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Local Ollama model name (default: {DEFAULT_OLLAMA_MODEL})")


    # 6. DOCTOR Subcommand
    subparsers.add_parser("doctor", help="Check system dependencies (tesseract, poppler, sips, ollama)")

    # 7. WATCHDOG Subcommand
    p_watch = subparsers.add_parser("watchdog", help="Monitor inbox for new books and inspect system health")
    p_watch.add_argument("--inbox-dir", default="./inbox", help="Directory to monitor for incoming books")
    p_watch.add_argument("--processed-dir", default="./processed", help="Directory to archive completed books")
    p_watch.add_argument("--output-dir", default="./output", help="Output directory")
    p_watch.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    p_watch.add_argument("--auto-process", action="store_true", help="Automatically process newly detected books without asking")

    # 8. REVIEW Subcommand
    p_rev = subparsers.add_parser("review", help="Interactively review and accept/reject AI-proposed corrections")
    p_rev.add_argument("--book-dir", "-b", default=None, help="Path to book directory to review all chapters")
    p_rev.add_argument("--chapter-dir", "-c", default=None, help="Path to chapter folder containing review manifest")

    # Parse arguments
    args = parser.parse_args()

    if not args.subcommand:
        # Default behavior when called without subcommand: check if legacy arguments passed
        # If no arguments at all, print help
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(0)
        # Fallback to 'run' subcommand
        args.subcommand = "run"

    if args.subcommand == "doctor":
        tools = check_dependencies()
        print("\n=== Book Processor System Environment Check ===")
        all_ok = True
        for name, ok in tools.items():
            status = "[✓] Installed" if ok else "[✗] Missing"
            print(f"  • {name:<15}: {status}")
            if not ok and name not in ('ollama',):
                all_ok = False
        print(f"\nStatus: {'All core dependencies ready!' if all_ok else 'Some dependencies are missing. Please check brew/path.'}\n")
        sys.exit(0 if all_ok else 1)

    elif args.subcommand == "split":
        orchestrator = BookProcessorOrchestrator(output_dir=args.output_dir)
        orchestrator.split_book_only(args.file)

    elif args.subcommand == "convert":
        orchestrator = BookProcessorOrchestrator(use_ollama=args.ollama, ollama_model=args.ollama_model)
        res = orchestrator.convert_single_chapter(args.pdf)
        sys.exit(0 if res.get('passed') else 1)

    elif args.subcommand == "resume":
        orchestrator = BookProcessorOrchestrator(output_dir=args.output_dir, use_ollama=args.ollama, ollama_model=args.ollama_model)
        orchestrator.process_pdf_book(args.file, resume=True, parallel=getattr(args, 'parallel', False))

    elif args.subcommand == "run":
        orchestrator = BookProcessorOrchestrator(
            input_dir=getattr(args, 'input_dir', '.'),
            output_dir=getattr(args, 'output_dir', './output'),
            use_ollama=getattr(args, 'ollama', False),
            ollama_model=getattr(args, 'ollama_model', 'qwen2.5:7b')
        )

        books = orchestrator.discover_books(getattr(args, 'file', None))
        if not books:
            print("[!] No PDF or EPUB files found.")
            sys.exit(1)
        for bpath, ext in books:
            if ext == '.pdf':
                orchestrator.process_pdf_book(
                    bpath,
                    target_chapter=getattr(args, 'chapter', None),
                    resume=False,
                    parallel=getattr(args, 'parallel', False)
                )
            elif ext == '.epub':
                orchestrator.process_epub_book(bpath)

    elif args.subcommand == "verify":
        verifier = AccuracyVerifier(use_ollama=args.ollama, ollama_model=args.ollama_model)
        if args.chapter_dir:
            res = verifier.verify_chapter(args.chapter_dir, expected_pages=args.expected_pages)
            sys.exit(0 if res['passed'] else 1)
        elif args.book_dir:
            ch_dir = Path(args.book_dir) / "chapters"
            if not ch_dir.exists():
                print(f"[!] Chapters directory not found: {ch_dir}")
                sys.exit(1)
            all_ok = True
            for c in sorted(ch_dir.iterdir()):
                if c.is_dir():
                    res = verifier.verify_chapter(str(c))
                    if not res['passed']:
                        all_ok = False
            sys.exit(0 if all_ok else 1)

    elif args.subcommand == "watchdog":
        from book_processor.core.watchdog import WatchdogService
        watchdog = WatchdogService(
            inbox_dir=args.inbox_dir,
            processed_dir=args.processed_dir,
            output_dir=args.output_dir
        )
        orchestrator = BookProcessorOrchestrator(
            inbox_dir=args.inbox_dir,
            processed_dir=args.processed_dir,
            output_dir=args.output_dir
        )

        def on_new_book(bpath):
            if bpath.lower().endswith('.pdf'):
                orchestrator.process_pdf_book(bpath)
            elif bpath.lower().endswith('.epub'):
                orchestrator.process_epub_book(bpath)

        watchdog.start_monitoring(
            interactive=not args.auto_process,
            auto_process=args.auto_process,
            interval=args.interval,
            on_new_book_callback=on_new_book
        )

    elif args.subcommand == "review":
        from book_processor.verification.review_manager import ReviewManager
        if args.book_dir:
            ReviewManager.interactive_review_book(args.book_dir)
        elif args.chapter_dir:
            ReviewManager.interactive_review(args.chapter_dir)
        else:
            print("[!] Please specify either --book-dir (-b) or --chapter-dir (-c).")


if __name__ == '__main__':
    main()
