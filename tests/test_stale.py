"""Tests for the read-only `stale` command: affected-page mapping without
task creation, the --fail-if-stale CI exit gate, and usage errors mirroring
`update`."""

from __future__ import annotations

import json
import subprocess

from conftest import make_repo, valid_catalog

from repowiki.cli import main
from repowiki.gitutil import run_git
from repowiki.paths import WikiPaths


def run(*argv):
    return main(list(argv))


def commit_all(repo: object, message: str) -> None:
    run = lambda *a: subprocess.run(a, cwd=str(repo), check=True, capture_output=True)
    run("git", "add", "-A")
    run("git", "commit", "-qm", message)


def setup_wiki(repo) -> WikiPaths:
    """Catalog + metadata pinned to the initial commit (post-finalize shape)."""
    (repo / ".gitignore").write_text(".repowiki/\n", encoding="utf-8")
    commit_all(repo, "ignore .repowiki")  # keep later diffs to source files only
    paths = WikiPaths(repo)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.catalog_file.write_text(json.dumps(valid_catalog()), encoding="utf-8")
    base = run_git(repo, "rev-parse", "HEAD").strip()
    paths.meta_dir.mkdir(parents=True, exist_ok=True)
    paths.metadata_file.write_text(json.dumps(
        {"wiki_repo": {"name": "demo", "last_commit_id": base}, "wiki_overview": ""},
        ensure_ascii=False,
    ), encoding="utf-8")
    return paths


# --- happy path ---

def test_stale_reports_affected_pages_with_ancestors(git_repo, capsys):
    setup_wiki(git_repo)
    (git_repo / "src/demo/api.py").write_text("CHANGED = True\n", encoding="utf-8")
    commit_all(git_repo, "touch api")
    assert run("stale", str(git_repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True and data["stale"] is True
    assert data["changed_files"] == 1
    assert data["affected_pages"] == ["c0101", "c01"]  # page hit first, then its ancestor
    assert data["affected_cards"] == [] and data["affected_modules"] == []


def test_stale_clean_when_changes_miss_dependent_files(git_repo, capsys):
    setup_wiki(git_repo)
    (git_repo / "scripts/build.sh").write_text("#!/bin/sh\necho new\n", encoding="utf-8")
    commit_all(git_repo, "touch build script")
    assert run("stale", str(git_repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["stale"] is False and data["affected_pages"] == []


def test_stale_clean_when_no_changes_at_all(git_repo, capsys):
    setup_wiki(git_repo)
    assert run("stale", str(git_repo)) == 0
    assert "wiki 与代码同步" in capsys.readouterr().out


# --- CI gate ---

def test_stale_fail_if_stale_exit_codes(git_repo, capsys):
    setup_wiki(git_repo)
    (git_repo / "src/demo/main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    commit_all(git_repo, "touch main")
    assert run("stale", str(git_repo), "--fail-if-stale") == 1
    assert "wiki 已过期" in capsys.readouterr().out
    # nothing was created by the gate — it is read-only
    assert not (git_repo / ".repowiki/state/tasks").exists()
    assert not (git_repo / ".repowiki/state/claims").exists()
    # without the flag the same stale report still exits 0 (gate is opt-in)
    assert run("stale", str(git_repo), "--since", "HEAD") == 0


# --- knowledge linkage ---

def test_stale_maps_knowledge_cards_with_source_files(git_repo, capsys):
    paths = setup_wiki(git_repo)
    paths.knowledge_plan_file.write_text(json.dumps({
        "modules": [],
        "cards": [{
            "id": "k01", "title": "日志", "category": "logging_system",
            "source_files": ["src/demo/log.py"],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    paths.index_file.write_text(json.dumps({"tasks": {"k01": {"status": "done"}}}), encoding="utf-8")
    (git_repo / "src/demo/log.py").write_text("log = None\n", encoding="utf-8")
    commit_all(git_repo, "touch log")
    assert run("stale", str(git_repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["affected_cards"] == ["k01"] and data["stale"] is True


# --- usage errors (mirror `update`) ---

def test_stale_requires_git(tmp_path, capsys):
    repo = make_repo(tmp_path, git=False)
    assert run("stale", str(repo)) == 1
    assert "git" in capsys.readouterr().err


def test_stale_requires_catalog(git_repo, capsys):
    assert run("stale", str(git_repo), "--since", "HEAD") == 1
    assert "catalog" in capsys.readouterr().err


def test_stale_requires_since_when_metadata_missing(git_repo, capsys):
    WikiPaths(git_repo).state_dir.mkdir(parents=True, exist_ok=True)
    (git_repo / ".repowiki/state/catalog.json").write_text("{}", encoding="utf-8")
    assert run("stale", str(git_repo)) == 1
    assert "--since" in capsys.readouterr().err


def test_stale_unknown_since_ref_fails_cleanly(git_repo, capsys):
    setup_wiki(git_repo)
    assert run("stale", str(git_repo), "--since", "deadbeef") == 1
    assert "起点 ref" in capsys.readouterr().err
