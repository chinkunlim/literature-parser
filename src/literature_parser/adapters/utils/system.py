"""
System Environment & Dependency Diagnostics
===========================================
"""

import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from literature_parser.config.processor_config import OLLAMA_API_BASE


def get_pdf_page_count(pdf_path: str | Path) -> int:
    """Gets total page count from a PDF, trying pdfinfo first then pure-Python fallback."""
    if check_command("pdfinfo"):
        try:
            out = subprocess.check_output(
                ["pdfinfo", str(pdf_path)],
                stderr=subprocess.DEVNULL,
                timeout=15,
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
        except Exception:
            pass

    # Pure Python fallback
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
        matches = re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", content, re.DOTALL)
        if matches:
            return max(int(m) for m in matches)
    except Exception:
        pass
    return 0


def check_command(cmd: str) -> bool:
    """Checks if a binary command is executable on the system PATH."""
    return shutil.which(cmd) is not None


def check_dependencies() -> dict:
    """Checks availability of all required local binary dependencies."""
    tools = {
        'pdfinfo': check_command('pdfinfo'),
        'pdfseparate': check_command('pdfseparate'),
        'pdfunite': check_command('pdfunite'),
        'pdftoppm': check_command('pdftoppm'),
        'pdftohtml': check_command('pdftohtml'),
        'tesseract': check_command('tesseract') or check_command('/opt/homebrew/bin/tesseract'),
        'sips': check_command('/usr/bin/sips') or check_command('sips'),
        'ollama': check_command('ollama') or check_command('/usr/local/bin/ollama')
    }
    return tools


def is_ollama_running(base_url: str = OLLAMA_API_BASE) -> bool:
    """Checks if local Ollama daemon is accessible via HTTP."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", headers={"User-Agent": "BookProcessor/2.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama_running(base_url: str = OLLAMA_API_BASE, max_wait_sec: float = 6.0) -> bool:
    """
    Checks if Ollama is running; if not, attempts to auto-launch it on macOS / Linux.
    Waits up to `max_wait_sec` seconds for the service to respond.
    """
    if is_ollama_running(base_url):
        return True

    import platform
    import time
    system = platform.system()
    try:
        if system == "Darwin":
            # Attempt to launch Ollama.app or run `ollama serve`
            subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return False

    start = time.time()
    while time.time() - start < max_wait_sec:
        time.sleep(0.5)
        if is_ollama_running(base_url):
            return True
    return False
