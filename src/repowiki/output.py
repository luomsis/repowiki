"""Dual-format output: the one seam every command prints through.

``--json`` mode dumps the result dict verbatim; human mode renders it with a
per-command formatter. Routing both representations through one seam keeps
them in lockstep (a new field lands in both or neither) and gives the human
branch — historically untested copy — a callable test surface.
"""

from __future__ import annotations

import json
import sys
from typing import Callable

Human = Callable[[dict], str]


def emit(result: dict, human: Human, as_json: bool, file=None) -> None:
    """Print ``result`` as JSON, or via ``human(result)`` (skipped when empty)."""
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=file)
    else:
        text = human(result)
        if text:
            print(text, file=file)


def emit_error(kind: str, detail: str, as_json: bool) -> None:
    """Report a CLI error: JSON contract on stdout, human copy on stderr."""
    prefix = {"conflict": "conflict: ", "state_corrupt": "state error: "}.get(kind, "error: ")
    emit({"ok": False, "error": kind, "detail": detail},
         lambda r: prefix + r["detail"],
         as_json,
         file=None if as_json else sys.stderr)
