#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Accuracy Verifier: Root Entrypoint
==================================
Forwards to src.book_processor.verification.verifier.main().
"""

import sys
from pathlib import Path

src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from book_processor.verification.verifier import main

if __name__ == '__main__':
    main()
