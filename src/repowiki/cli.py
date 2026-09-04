"""Command-line interface.

Exit codes: 0 = ok, 1 = validation failure / usage error / corrupted state,
2 = state conflict (e.g. task already claimed by a live worker).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .dispatch import run_check, run_next, run_release, run_status, run_touch, run_watch
from .errors import ConflictError, StateError, UsageError  # noqa: F401 (re-exported)
from .knowledge import run_knowledge
from .metadata import run_finalize
from .output import emit_error
from .paths import WikiPaths
from .plan import run_plan
from .site import run_site
from .state import run_clean
from .updater import run_update


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
    p.add_argument("--force", action="store_true", help="with --replan: proceed even if tasks are in flight")
    p.add_argument("--max-pages", type=int, default=None, help="cap number of page tasks (for cheap trial runs)")
    p.add_argument("--knowledge", action="store_true", help="also append the knowledge-card task set")
    p.add_argument("--locale", default="auto", choices=["auto", "zh", "en"],
                   help="output language: auto-detect from the repo (README-weighted) or force zh/en")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_plan(
        paths, replan=a.replan, max_pages=a.max_pages, knowledge=a.knowledge,
        force=a.force, as_json=a.json, locale=a.locale))

    p = sub.add_parser("next", help="list (and optionally claim) ready tasks")
    p.add_argument("repo")
    p.add_argument("--claim", action="store_true", help="atomically claim the returned tasks")
    p.add_argument("--worker", default=None, help="worker identifier recorded on claim")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_next(paths, claim=a.claim, worker=a.worker, as_json=a.json))

    p = sub.add_parser("check", help="validate task output, auto-fix deterministic defects, update status")
    p.add_argument("repo")
    p.add_argument("--task", default=None, help="check a single task id")
    p.add_argument("--all", dest="select_all", action="store_true",
                   help="check all in_progress/failed tasks (crash recovery / main agent)")
    p.add_argument("--worker", default=None, help="caller identity; in_progress tasks held by others are refused")
    p.add_argument("--force", action="store_true", help="check even if claimed by another worker")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_check(
        paths, task_id=a.task, as_json=a.json, select_all=a.select_all,
        worker=a.worker, force=a.force))

    p = sub.add_parser("touch", help="refresh a task's claim while executing (heartbeat)")
    p.add_argument("repo")
    p.add_argument("--task", required=True)
    p.add_argument("--worker", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_touch(paths, task_id=a.task, worker=a.worker, as_json=a.json))

    p = sub.add_parser("watch", help="block until all tasks are done (or stalled/timeout); exit 0=completed, 1=stalled/timeout")
    p.add_argument("repo")
    p.add_argument("--interval", type=float, default=10.0, help="poll interval seconds (default 10)")
    p.add_argument("--timeout", type=float, default=3600.0, help="give up after this many seconds (default 3600)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_watch(
        paths, interval=a.interval, timeout=a.timeout, as_json=a.json))

    p = sub.add_parser("release", help="return an in_progress task to pending")
    p.add_argument("repo")
    p.add_argument("--task", required=True)
    p.add_argument("--force", action="store_true", help="release even if claimed by another worker")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_release(
        paths, task_id=a.task, force=a.force, as_json=a.json))

    p = sub.add_parser("finalize", help="assemble zh/meta/repowiki-metadata.json (requires all tasks done)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_finalize(paths, as_json=a.json))

    p = sub.add_parser("site", help="render the finished wiki into one offline HTML file (.repowiki/<locale>/wiki.html)")
    p.add_argument("repo")
    p.add_argument("--open", dest="open_browser", action="store_true",
                   help="open the generated file in the default browser")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_site(
        paths, open_browser=a.open_browser, as_json=a.json))

    p = sub.add_parser("update", help="map git changes to page_update tasks (incremental regeneration)")
    p.add_argument("repo")
    p.add_argument("--since", default=None, help="commit sha to diff from (default: last_commit_id in metadata)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_update(paths, since=a.since, as_json=a.json))

    p = sub.add_parser("knowledge", help="append the knowledge-card task set (planning + cards)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_knowledge(paths, as_json=a.json))

    p = sub.add_parser("status", help="show task statistics, failures and stale claims")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_status(paths, as_json=a.json))

    p = sub.add_parser("clean", help="remove .repowiki/state entirely (wiki output is kept)")
    p.add_argument("repo")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, paths: run_clean(paths, as_json=a.json))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = WikiPaths(args.repo)
    try:
        return args.func(args, paths)
    except ConflictError as e:
        emit_error("conflict", str(e), args.json)
        return 2
    except StateError as e:
        emit_error("state_corrupt", str(e), args.json)
        return 1
    except UsageError as e:
        emit_error("usage", str(e), args.json)
        return 1


if __name__ == "__main__":
    sys.exit(main())
