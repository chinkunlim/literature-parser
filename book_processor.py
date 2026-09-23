#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Processor: Enterprise Root Entrypoint
===========================================
Forwards to src.book_processor.cli.main().
Exposes __path__ so imports like `from book_processor.core import ...` work seamlessly.
"""

import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent / "src"
pkg_dir = src_dir / "book_processor"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

__path__ = [str(pkg_dir)]
__version__ = "3.1.0"

from book_processor.cli import main

if __name__ == '__main__':
    main()
