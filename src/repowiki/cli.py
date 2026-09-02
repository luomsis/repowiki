"""Command-line interface.

Exit codes: 0 = ok, 1 = validation failure / usage error, 2 = state conflict
(e.g. task already claimed by a live worker).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .paths import WikiPaths


def _print_json(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repowiki",
        description="Deterministic repo-wiki build system driven by coding agents (zero LLM, zero network).",
    )
    parser.add_argument("--version", action="version", version=f"repowiki {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="scan repo and create the task manifest (phase 1: catalog task)")
    p.add_argument("repo", help="path to the repository")
    p.add_argument("--replan", action="store_true", help="discard existing catalog and plan again")
    p.add_argument("--max-pages", type=int, default=None, help="cap number of page tasks (for cheap trial runs)")
    p.add_argument("--knowledge", action="store_true", help="also append the knowledge-card task set")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("next", help="list (and optionally claim) ready tasks")
    p.add_argument("repo")
    p.add_argument("--claim", action="store_true", help="atomically claim the returned tasks")
    p.add_argument("--batch", type=int, default=1, help="number of tasks to return/claim")
    p.add_argument("--worker", default=None, help="worker identifier recorded on claim")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("check", help="validate task output, auto-fix deterministic defects, update status")
    p.add_argument("repo")
    p.add_argument("--task", default=None, help="check a single task id (default: all claimed-by-me / failed tasks)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("release", help="return an in_progress task to pending")
    p.add_argument("repo")
    p.add_argument("--task", required=True)
    p.add_argument("--force", action="store_true", help="release even if claimed by another worker")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("finalize", help="assemble zh/meta/repowiki-metadata.json (requires all tasks done)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("update", help="map git changes to page_update tasks (incremental regeneration)")
    p.add_argument("repo")
    p.add_argument("--since", default=None, help="commit sha to diff from (default: last_commit_id in metadata)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("knowledge", help="append the knowledge-card task set (planning + cards)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("status", help="show task statistics, failures and stale claims")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("clean", help="remove .repowiki/state entirely (wiki output is kept)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = WikiPaths(args.repo)
    handlers = {
        "plan": cmd_plan,
        "next": cmd_next,
        "check": cmd_check,
        "release": cmd_release,
        "finalize": cmd_finalize,
        "update": cmd_update,
        "knowledge": cmd_knowledge,
        "status": cmd_status,
        "clean": cmd_clean,
    }
    try:
        return handlers[args.command](args, paths)
    except ConflictError as e:
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": "conflict", "detail": str(e)})
        else:
            print(f"conflict: {e}", file=sys.stderr)
        return 2
    except UsageError as e:
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": "usage", "detail": str(e)})
        else:
            print(f"error: {e}", file=sys.stderr)
        return 1


class ConflictError(Exception):
    """State conflict, e.g. task already claimed by a live worker."""


class UsageError(Exception):
    """User/input error reported with exit code 1."""


# --- command implementations are filled in by their owning modules ---

def cmd_plan(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in tasks.py
    from .plan import run_plan

    return run_plan(paths, replan=args.replan, max_pages=args.max_pages, knowledge=args.knowledge, as_json=args.json)


def cmd_next(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in state.py
    from .dispatch import run_next

    return run_next(paths, claim=args.claim, batch=args.batch, worker=args.worker, as_json=args.json)


def cmd_check(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in validate.py
    from .dispatch import run_check

    return run_check(paths, task_id=args.task, as_json=args.json)


def cmd_release(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in state.py
    from .dispatch import run_release

    return run_release(paths, task_id=args.task, force=args.force, as_json=args.json)


def cmd_finalize(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in metadata.py
    from .metadata import run_finalize

    return run_finalize(paths, as_json=args.json)


def cmd_update(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in updater.py
    from .updater import run_update

    return run_update(paths, since=args.since, as_json=args.json)


def cmd_knowledge(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in knowledge.py
    from .knowledge import run_knowledge

    return run_knowledge(paths, as_json=args.json)


def cmd_status(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in dispatch.py
    from .dispatch import run_status

    return run_status(paths, as_json=args.json)


def cmd_clean(args, paths: WikiPaths) -> int:  # pragma: no cover - wired in state.py
    from .state import run_clean

    return run_clean(paths, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
