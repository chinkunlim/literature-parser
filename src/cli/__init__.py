"""
Unified CLI Package
===================
Modular command center split into dedicated domain modules:
- cli_audit: Format auditing and compliance verification
- cli_fix: Playbook and recipe inspection, application, and synthesis
- cli_git: Date synchronization, checkpoints, handoff, and session archiving
- cli_process: Pipeline conversion and directory batch processing
- cli_project: Health checks, watchdog, scaffolding, and dashboard
"""

from src.cli.cli_audit import cmd_audit
from src.cli.cli_fix import cmd_fix
from src.cli.cli_git import (
    cmd_agent_init,
    cmd_archive_sessions,
    cmd_end_session,
    cmd_handoff,
    cmd_publish,
    cmd_save,
)
from src.cli.cli_process import cmd_batch, cmd_epub, cmd_process
from src.cli.cli_project import (
    cmd_dashboard,
    cmd_doctor,
    cmd_init_project,
    cmd_obsidian_link,
    cmd_status,
    cmd_test_ollama_auto_trigger,
    cmd_watchdog,
)
from src.cli.common import (
    ROOT,
    clean_dangling_tmp_files,
    get_current_date,
    get_current_timestamp,
    sync_markdown_dates,
)

__all__ = [
    "ROOT",
    "clean_dangling_tmp_files",
    "cmd_agent_init",
    "cmd_archive_sessions",
    "cmd_audit",
    "cmd_batch",
    "cmd_dashboard",
    "cmd_doctor",
    "cmd_end_session",
    "cmd_epub",
    "cmd_fix",
    "cmd_handoff",
    "cmd_init_project",
    "cmd_obsidian_link",
    "cmd_process",
    "cmd_publish",
    "cmd_save",
    "cmd_status",
    "cmd_test_ollama_auto_trigger",
    "cmd_watchdog",
    "get_current_date",
    "get_current_timestamp",
    "sync_markdown_dates",
]
