"""Tests for `repowiki site`: single-file HTML assembly, snippet embedding,
payload safety, nav structure and degraded (post-clean) modes."""

from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import valid_page, write_catalog

from repowiki.cli import main
from repowiki.paths import WikiPaths


def run(*argv):
    return main(list(argv))


SITE_DATA_RE = re.compile(r"window\.SITE_DATA = (.*?);</script>", re.S)


def write_page(paths: WikiPaths, rel: str, text: str | None = None) -> None:
    f = paths.root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text or valid_page("核心概念"), encoding="utf-8")


def write_metadata(paths: WikiPaths, overview: str = "# demo Wiki 总览\n\n概览内容。\n") -> None:
    paths.meta_dir.mkdir(parents=True, exist_ok=True)
    paths.metadata_file.write_text(
        json.dumps({"wiki_repo": {"name": "demo"}, "wiki_overview": overview}, ensure_ascii=False),
        encoding="utf-8",
    )


def build_finished_wiki(paths: WikiPaths) -> None:
    """Simulate a completed run: catalog + two pages + metadata."""
    write_catalog(paths)
    write_page(paths, "zh/content/项目概述/核心概念.md")
    write_page(paths, "zh/content/快速开始.md", valid_page("快速开始"))
    write_metadata(paths)


def extract_payload(html: str) -> dict:
    m = SITE_DATA_RE.search(html)
    assert m, "SITE_DATA payload missing"
    return json.loads(m.group(1))


# --- gating ---

def test_site_requires_finalize(repo, capsys):
    assert run("site", str(repo)) == 1
    assert "finalize" in capsys.readouterr().err


def test_site_with_no_content_at_all_fails_cleanly(repo, paths, capsys):
    paths.ensure()
    write_metadata(paths, overview="")
    assert run("site", str(repo)) == 1
    assert "未找到任何已生成的 wiki 页面" in capsys.readouterr().err


# --- happy path ---

def test_site_generates_single_file(repo, paths, capsys):
    build_finished_wiki(paths)
    assert run("site", str(repo)) == 0
    out = capsys.readouterr().out
    assert paths.site_file.is_file()
    assert "站点已生成" in out
    html = paths.site_file.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "marked.min.js" not in html  # vendored code is inlined, not referenced
    assert "src=" not in html.split("<body")[1].split("SITE_DATA")[0]  # no external assets


def test_site_payload_pages_and_nav(repo, paths):
    build_finished_wiki(paths)
    assert run("site", str(repo)) == 0
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    assert payload["repo"] == "demo"
    assert [p["title"] for p in payload["pages"]] == ["总览", "核心概念", "快速开始"]
    nav = payload["nav"]
    assert nav[0] == {"title": "总览", "page": 0}
    chapter = nav[1]
    assert chapter["title"] == "项目概述"
    assert chapter["children"] == [{"title": "核心概念", "page": 1}]
    assert nav[2] == {"title": "快速开始", "page": 2}
    assert payload["ui"]["search_placeholder"]


def test_site_ui_strings_follow_locale(repo, paths):
    build_finished_wiki(paths)
    write_page(paths, "en/content/quick-start.md", valid_page("Quick Start"))
    paths.persist_locale("en")
    paths.meta_dir.mkdir(parents=True, exist_ok=True)
    paths.metadata_file.write_text(
        json.dumps({"wiki_repo": {"name": "demo"},
                    "wiki_overview": "# demo Wiki Overview\n\nOverview text.\n"}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert run("site", str(repo)) == 0
    assert paths.site_file == paths.root / "en" / "wiki.html"
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    assert payload["locale"] == "en"
    assert payload["ui"]["search_placeholder"] == "Search wiki…"
    # zh output untouched
    assert not (paths.root / "zh" / "wiki.html").exists()


def test_site_rebuild_is_idempotent(repo, paths):
    build_finished_wiki(paths)
    assert run("site", str(repo), "--json") == 0
    first = paths.site_file.read_text(encoding="utf-8")
    assert run("site", str(repo), "--json") == 0
    second = paths.site_file.read_text(encoding="utf-8")
    p1, p2 = extract_payload(first), extract_payload(second)
    p1.pop("generatedAt"), p2.pop("generatedAt")
    assert p1 == p2


# --- snippet embedding ---

def test_site_snippets_embed_line_ranges(repo, paths):
    build_finished_wiki(paths)
    run("site", str(repo))
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    sn = payload["snippets"]["src/demo/main.py#L1-L7"]
    assert sn["start"] == 1 and sn["end"] == 7
    assert len(sn["lines"]) == 7
    assert sn["lines"][0] == "def main():"
    whole = payload["snippets"]["README.md"]  # file:// ref without a range
    assert whole["start"] == 1
    assert whole["lines"][0] == "# demo"


def test_site_snippet_for_missing_source_marks_missing(repo, paths):
    write_catalog(paths)
    write_page(paths, "zh/content/项目概述/核心概念.md",
               valid_page("核心概念").replace("src/demo/main.py", "src/demo/ghost.py"))
    write_metadata(paths)
    assert run("site", str(repo)) == 0
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    assert payload["snippets"]["src/demo/ghost.py#L1-L7"]["missing"] is True
    assert "def main():" not in json.dumps(payload["snippets"])


# --- payload safety ---

def test_site_payload_cannot_break_out_of_script_tag(repo, paths):
    write_catalog(paths)
    evil = valid_page("核心概念").replace(
        "demo 是一个微型示例服务。",
        "demo 演示。</script><script>alert(1)</script>注入结束。",
    )
    write_page(paths, "zh/content/项目概述/核心概念.md", evil)
    write_metadata(paths)
    assert run("site", str(repo)) == 0
    html = paths.site_file.read_text(encoding="utf-8")
    # exactly the 4 script tags the shell itself emits survive
    assert html.count("</script>") == 4
    assert "\\u003c/script>" in html


# --- degraded modes ---

def test_site_builds_nav_from_disk_after_clean(repo, paths):
    build_finished_wiki(paths)
    for f in paths.state_dir.glob("*.json"):
        f.unlink()
    assert not paths.catalog_file.exists()
    assert run("site", str(repo)) == 0
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    assert sorted(p["title"] for p in payload["pages"]) == ["快速开始", "总览", "核心概念"]
    chapter = next(e for e in payload["nav"] if e["title"] == "项目概述")
    assert [c["title"] for c in chapter["children"]] == ["核心概念"]


def test_site_skips_missing_page_files(repo, paths):
    write_catalog(paths)
    write_page(paths, "zh/content/项目概述/核心概念.md")  # 快速开始.md never written
    write_metadata(paths)
    assert run("site", str(repo)) == 0
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    assert [p["title"] for p in payload["pages"]] == ["总览", "核心概念"]
    assert all(e["title"] != "快速开始" for e in payload["nav"])


def test_site_chapter_own_page_leads_children(repo, paths):
    write_catalog(paths)
    write_page(paths, "zh/content/项目概述/项目概述.md", valid_page("项目概述"))
    write_page(paths, "zh/content/项目概述/核心概念.md")
    write_metadata(paths)
    assert run("site", str(repo)) == 0
    payload = extract_payload(paths.site_file.read_text(encoding="utf-8"))
    chapter = next(e for e in payload["nav"] if e["title"] == "项目概述")
    assert [c["title"] for c in chapter["children"]] == ["项目概述", "核心概念"]
    assert chapter["children"][0]["page"] == 1  # right after the overview


# --- cli surface ---

def test_site_json_output(repo, paths, capsys):
    build_finished_wiki(paths)
    assert run("site", str(repo), "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert data["pages"] == 3
    assert data["size_mb"] > 1  # vendored mermaid dominates the size
    assert data["site"].endswith("wiki.html")


def test_site_open_flag_launches_browser(repo, paths, monkeypatch):
    build_finished_wiki(paths)
    opened = []
    import repowiki.site as site_mod
    monkeypatch.setattr(site_mod.webbrowser, "open", lambda uri: opened.append(uri) or True)
    assert run("site", str(repo), "--open") == 0
    assert len(opened) == 1
    assert opened[0].startswith("file://")
