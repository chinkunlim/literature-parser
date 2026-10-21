"""CLI entrypoint for literature-parser.

Unified CLI command line interface delegating to `literature_parser.entrypoints.run:main`.
"""

from __future__ import annotations

import sys
from literature_parser.entrypoints.run import main as run_main


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint for literature-parser.

    Args:
        argv: Optional list of CLI argument strings; defaults to sys.argv[1:].

    Returns:
        Exit code integer.
    """
    if argv is None:
        argv = sys.argv[1:]
    return run_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
