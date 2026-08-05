"""Traceability stamp for exports: project name, date, git revision."""

import subprocess
from datetime import date
from pathlib import Path


def git_revision(cwd: Path | str | None = None) -> str | None:
    """Short git revision of the working directory, with -dirty suffix.

    Returns None when not in a git repository (or git is unavailable).
    """
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if rev.returncode != 0:
            return None
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty = "-dirty" if status.returncode == 0 and status.stdout.strip() else ""
        return rev.stdout.strip() + dirty
    except (OSError, subprocess.TimeoutExpired):
        return None


def export_stamp(project_name: str, cwd: Path | str | None = None) -> str:
    """Human-readable one-line stamp for export footers/headers."""
    revision = git_revision(cwd)
    git_part = f"git {revision}" if revision else "no git revision"
    return f"{project_name} | exported {date.today().isoformat()} | {git_part}"
