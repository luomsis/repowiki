"""Regression tests for the failure paths a new user hits on day one:
corrupt state files and invalid task ids must fail with friendly errors,
never with a raw traceback, and never by silently destroying data."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from repowiki.cli import StateError, UsageError
from repowiki.cli import main as cli_main
from repowiki.metadata import _require_catalog
from repowiki.paths import WikiPaths
from repowiki.state import TaskStore, new_task


def _seed(store: TaskStore) -> None:
    store.replace_all([new_task("t00", "page", 2, "页0", "zh/content/p0.md")])


def _corrupt_index(paths: WikiPaths, raw: str = "{ not json") -> None:
    paths.ensure()
    paths.index_file.write_text(raw, encoding="utf-8")


# --- corrupt state/index.json: loud failure, data preserved ---

def test_corrupt_index_raises_state_error(paths):
    _corrupt_index(paths)
    store = TaskStore(paths)
    with pytest.raises(StateError):
        store.load()
    with pytest.raises(StateError):
        store.stats()
    # the corrupt file stays untouched for manual recovery
    assert paths.index_file.read_text(encoding="utf-8") == "{ not json"


def test_corrupt_index_next_fails_cleanly(repo, paths, capsys):
    _corrupt_index(paths)
    rc = cli_main(["next", str(repo), "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "state_corrupt"


def test_corrupt_index_status_fails_cleanly(repo, paths, capsys):
    _corrupt_index(paths)
    rc = cli_main(["status", str(repo)])
    assert rc == 1
    assert "state/index.json 损坏" in capsys.readouterr().err


def test_replan_with_corrupt_index_requires_force(repo, paths, capsys):
    _corrupt_index(paths)
    rc = cli_main(["plan", str(repo), "--replan"])
    assert rc == 1
    assert "--force" in capsys.readouterr().err


def test_replan_force_recovers_from_corrupt_index(git_repo):
    paths = WikiPaths(git_repo)
    _corrupt_index(paths)
    rc = cli_main(["plan", str(git_repo), "--replan", "--force"])
    assert rc == 0


# --- unknown task id: usage error, not KeyError traceback ---

def test_unknown_task_id_touch_and_release_fail_cleanly(repo, paths, capsys):
    paths.ensure()
    _seed(TaskStore(paths))
    for cmd in (
        ["touch", str(repo), "--task", "nope"],
        ["release", str(repo), "--task", "nope"],
    ):
        rc = cli_main(cmd)
        assert rc == 1
        assert "任务不存在: nope" in capsys.readouterr().err


# --- lock backend: with both backends blocked (on POSIX msvcrt does not exist,
# --- on Windows fcntl does not), a missing lock layer must surface as a
# --- friendly usage error, never a traceback

def test_missing_lock_backends_reports_usage_error(paths, monkeypatch):
    paths.ensure()
    monkeypatch.setitem(sys.modules, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", None)
    store = TaskStore(paths)
    with pytest.raises(UsageError, match="文件锁"):
        store._lock()


# --- corrupt state/catalog.json ---

def test_require_catalog_corrupt_raises_usage(paths):
    paths.ensure()
    paths.catalog_file.write_text("[[[", encoding="utf-8")
    with pytest.raises(UsageError, match="损坏"):
        _require_catalog(paths)


def test_finalize_with_corrupt_catalog_fails_cleanly(repo, paths, capsys):
    paths.ensure()
    _seed(TaskStore(paths))
    paths.catalog_file.write_text("{bad", encoding="utf-8")
    rc = cli_main(["finalize", str(repo)])
    assert rc == 1
    assert "catalog.json 损坏" in capsys.readouterr().err


def test_update_with_corrupt_catalog_fails_cleanly(git_repo, capsys):
    paths = WikiPaths(git_repo)
    paths.ensure()
    paths.catalog_file.write_text("{bad", encoding="utf-8")
    # make the diff non-empty so update reaches the catalog parse
    (git_repo / "src/demo/api.py").write_text("# changed\n", encoding="utf-8")
    run = lambda *a: subprocess.run(a, cwd=str(git_repo), check=True, capture_output=True)
    run("git", "add", "-A")
    run("git", "commit", "-qm", "change")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD~1"], cwd=str(git_repo), check=True, capture_output=True
    ).stdout.decode().strip()
    rc = cli_main(["update", str(git_repo), "--since", base])
    assert rc == 1
    assert "catalog.json 损坏" in capsys.readouterr().err


def test_check_overview_with_corrupt_catalog_marks_failed(repo, paths):
    paths.ensure()
    store = TaskStore(paths)
    task = new_task("overview", "overview", 3, "总览", "zh/meta/wiki-overview.md")
    store.replace_all([task])
    paths.catalog_file.write_text("{bad", encoding="utf-8")
    out_file = paths.root / task["output"]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("# 总览\n", encoding="utf-8")
    from repowiki.dispatch import _check_one
    from repowiki.scanner import scan

    result = _check_one(paths, store, store.get("overview"), scan(paths.repo_root))
    assert result["ok"] is False
    assert result["status"] == "failed"
    assert any("catalog.json" in e for e in result["errors"])
