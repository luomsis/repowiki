"""Shared git subprocess helper: raw stdout on success, None on any failure.

Callers strip/split the output themselves — some call sites (e.g. ``diff
--name-only``) must distinguish "empty output" from "command failed".
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(repo: Path | str, *args: str, timeout: int = 30) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, check=True, timeout=timeout,
        ).stdout.decode("utf-8", "replace")
    except (subprocess.SubprocessError, OSError):
        return None
