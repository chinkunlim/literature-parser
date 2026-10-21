import sys
from pathlib import Path

# Automatically ensure src/ is in sys.path for all unit tests
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
