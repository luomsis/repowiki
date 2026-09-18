"""Tests for the configurable output directory (-o/--output, REPOWIKI_OUTPUT).

Default behaviour (``.repowiki``) must be unchanged; a custom output dir must
move the WHOLE tree — state, content, meta, site, llms — together so the
relative paths in state/catalog.json stay valid and incremental update/stale
keep working.
"""

from __future__ import annotations

from repowiki.cli import build_parser, main
from repowiki.paths import WikiPaths


def test_default_root_is_repowiki(repo):
    p = WikiPaths(repo)
    assert p.root_name == ".repowiki"
    assert p.root == repo / ".repowiki"
    assert p.state_dir == repo / ".repowiki" / "state"


def test_explicit_output_dir_moves_whole_tree(repo):
    p = WikiPaths(repo, output_dir="docs", locale="en")
    assert p.root == repo / "docs"
    # every derived location hangs off the new root
    assert p.state_dir == repo / "docs" / "state"
    assert p.content_dir == repo / "docs" / "en" / "content"
    assert p.meta_dir == repo / "docs" / "en" / "meta"
    assert p.site_file == repo / "docs" / "en" / "wiki.html"
    assert p.llms_file == repo / "docs" / "en" / "llms.txt"
    assert p.catalog_file == repo / "docs" / "state" / "catalog.json"


def test_env_var_sets_output_dir(repo, monkeypatch):
    monkeypatch.setenv("REPOWIKI_OUTPUT", "wiki-out")
    assert WikiPaths(repo).root_name == "wiki-out"


def test_explicit_arg_beats_env(repo, monkeypatch):
    monkeypatch.setenv("REPOWIKI_OUTPUT", "fromenv")
    assert WikiPaths(repo, output_dir="fromarg").root_name == "fromarg"


def test_output_option_accepted_in_trailing_position():
    # argparse: -o must be usable AFTER the subcommand (natural form)
    args = build_parser().parse_args(["plan", "somerepo", "-o", "docs"])
    assert args.output == "docs"
    args2 = build_parser().parse_args(["stale", "somerepo", "--output", "docs"])
    assert args2.output == "docs"


def test_plan_writes_under_custom_dir_without_repowiki_leak(git_repo):
    rc = main(["plan", str(git_repo), "-o", "docs", "--locale", "en"])
    assert rc == 0
    # state landed under docs/, not .repowiki/
    assert (git_repo / "docs" / "state" / "tasks" / "catalog.md").is_file()
    assert not (git_repo / ".repowiki").exists()
    # the agent-facing task spec must reference docs/, never .repowiki/
    spec = (git_repo / "docs" / "state" / "tasks" / "catalog.md").read_text(encoding="utf-8")
    assert "docs/state/catalog.json" in spec
    assert ".repowiki" not in spec


def test_default_run_unchanged(git_repo):
    rc = main(["plan", str(git_repo), "--locale", "en"])
    assert rc == 0
    spec = (git_repo / ".repowiki" / "state" / "tasks" / "catalog.md").read_text(encoding="utf-8")
    assert ".repowiki/state/catalog.json" in spec
    assert not (git_repo / "docs").exists()
