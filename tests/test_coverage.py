"""Tests for the read-only `coverage` report: cited-vs-inventory accounting,
knowledge-card linkage, and the zero-citation page flag."""

from __future__ import annotations

import json

from conftest import valid_catalog, valid_page, write_catalog

from repowiki.cli import main
from repowiki.paths import WikiPaths


def run(*argv):
    return main(list(argv))


def setup(repo) -> WikiPaths:
    paths = WikiPaths(repo)
    write_catalog(paths)
    for rel, text in (
        ("zh/content/项目概述/核心概念.md", valid_page("核心概念")),
        ("zh/content/快速开始.md", valid_page("快速开始")),
    ):
        f = paths.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return paths


def test_coverage_counts_cited_vs_inventory(repo, capsys):
    setup(repo)
    assert run("coverage", str(repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    # valid_page cites README.md, src/demo/main.py and src/demo/api.py
    assert data["cited_files"] == 3
    assert data["repo_files"] == 13  # the conftest fixture repo has 13 files
    assert data["coverage"] > 0
    assert "src/demo/models.py" in data["uncited_files"]
    assert "src/demo/log.py" in data["uncited_files"]
    assert {p["id"] for p in data["pages"]} == {"c01", "c0101", "c02"}


def test_coverage_counts_knowledge_card_source_files(repo, capsys):
    paths = setup(repo)
    paths.knowledge_plan_file.write_text(json.dumps({
        "modules": [],
        "cards": [{"id": "k01", "title": "日志", "category": "logging_system",
                   "source_files": ["src/demo/log.py"]}],
    }, ensure_ascii=False), encoding="utf-8")
    assert run("coverage", str(repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["cited_files"] == 4
    assert data["knowledge_files"] == ["src/demo/log.py"]
    assert "src/demo/log.py" not in data["uncited_files"]


def test_coverage_flags_zero_citation_pages(repo, capsys):
    paths = setup(repo)
    f = paths.root / "zh/content/快速开始.md"
    f.write_text("# 快速开始\n\n无引用的页面正文。\n", encoding="utf-8")
    assert run("coverage", str(repo)) == 0
    out = capsys.readouterr().out
    assert "没有任何 file:// 引用" in out and "c02" in out


def test_coverage_counts_overview_citations(repo, capsys):
    paths = setup(repo)
    paths.overview_file.parent.mkdir(parents=True, exist_ok=True)
    paths.overview_file.write_text(
        "# demo Wiki 总览\n\n- [src/demo/utils.py](file://src/demo/utils.py#L1-L2)\n",
        encoding="utf-8",
    )
    assert run("coverage", str(repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert "src/demo/utils.py" not in data["uncited_files"]


def test_coverage_requires_catalog(repo, capsys):
    assert run("coverage", str(repo)) == 1
    assert "catalog" in capsys.readouterr().err


def test_coverage_ignores_citations_to_deleted_files(repo, capsys):
    paths = setup(repo)
    (repo / "src/demo/api.py").unlink()
    assert run("coverage", str(repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["cited_files"] == 2  # api.py no longer in the inventory
