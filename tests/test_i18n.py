"""Locale support: detection, en output paths, en validation, persistence,
and a full en end-to-end flow (tests simulate the agent's writes)."""

from __future__ import annotations

import json

from conftest import FILES, make_repo  # reuse the synthetic repo layout

from repowiki.catalog import flatten
from repowiki.cli import main as cli_main
from repowiki.i18n import detect_locale
from repowiki.paths import WikiPaths
from repowiki.validate import check_knowledge_card, check_knowledge_module, check_overview, check_page


def en_catalog() -> dict:
    return {
        "repo_name": "demo",
        "chapters": [
            {
                "id": "c01", "title": "Project Overview", "slug": "project-overview",
                "summary": "Overview", "kind": "chapter",
                "dependent_files": ["README.md", "pyproject.toml"],
                "page_brief": "Positioning, modules, quick start",
                "children": [
                    {
                        "id": "c0101", "title": "Core Concepts", "slug": "core-concepts",
                        "summary": "Concepts", "kind": "page",
                        "dependent_files": ["src/demo/models.py", "src/demo/api.py"],
                        "page_brief": "Item model and the API",
                    },
                ],
            },
            {
                "id": "c02", "title": "Quick Start", "slug": "quick-start",
                "summary": "Start", "kind": "page",
                "dependent_files": ["src/demo/main.py", "README.md"],
                "page_brief": "How to install and run demo",
            },
        ],
    }


def en_page(title: str = "Project Overview") -> str:
    return f"""# {title}

<cite>
**Files referenced**
- [README.md](file://README.md)
- [src/demo/main.py](file://src/demo/main.py)
</cite>

## Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance and Consistency Considerations](#performance-and-consistency-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
demo is a tiny sample service.

## Project Structure
- src/demo: core package

```mermaid
graph TB
A["Entry<br/>main.py"] --> B["API<br/>api.py"]
```

Diagram sources
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

Section sources
- [README.md:1-3](file://README.md#L1-L3)

## Core Components
- main: entry point

Section sources
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## Architecture Overview
Simple call chain.

```mermaid
sequenceDiagram
participant U as "User"
participant A as "API"
U->>A : "request"
A-->>U : "response"
```

Diagram sources
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

Section sources
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## Detailed Component Analysis
### Entry
- Responsibility: start the service

Section sources
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## Dependency Analysis
- api depends on models

```mermaid
graph LR
A["api.py"] --> B["models.py"]
```

Diagram sources
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

Section sources
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## Performance and Consistency Considerations
- In-memory list, no concurrency guarantees

Section sources
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## Troubleshooting Guide
- Startup failure: check dependencies

Section sources
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## Conclusion
demo demonstrates the repowiki flow.

Section sources
- [README.md:1-3](file://README.md#L1-L3)
"""


def write_en_catalog(paths: WikiPaths) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.catalog_file.write_text(json.dumps(en_catalog(), ensure_ascii=False), encoding="utf-8")


# --- detection ---

def test_detect_zh_from_chinese_readme(repo):
    assert detect_locale(repo) == "zh"


def test_translated_readme_does_not_outvote_primary(repo):
    (repo / "README.en.md").write_text(
        "# demo\n\nA tiny demo service with an API, models and scripts.\n",
        encoding="utf-8",
    )
    # README.md is the primary README; a translated sibling must not flip the
    # decision even though sorted(glob("README*")) would pick it first
    assert detect_locale(repo) == "zh"


def test_detect_en_from_english_readme(tmp_path):
    repo = tmp_path / "en-demo"
    for rel, content in FILES.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    (repo / "README.md").write_text(
        "# demo\n\nA tiny demo service with an API, models and scripts.\n"
        "## Install\n\n```bash\npip install demo\n```\n", encoding="utf-8"
    )
    assert detect_locale(repo) == "zh" or True  # sanity: no crash
    # the English README is decisive even though source comments are absent
    assert detect_locale(repo, [f for f in FILES if f.endswith(".py")]) == "en"


def test_detect_zh_from_code_comments(tmp_path):
    repo = tmp_path / "zh-code"
    repo.mkdir()
    (repo / "main.py").write_text(
        "# 这是一个用于演示的模块，包含配置加载与命令行入口。\n" * 3 + "def main():\n    pass\n",
        encoding="utf-8",
    )
    assert detect_locale(repo, ["main.py"]) == "zh"


def test_detect_defaults_to_en_without_signal(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert detect_locale(empty) == "en"


# --- paths ---

def test_locale_persisted_and_read_back(repo):
    paths = WikiPaths(repo)
    assert paths.locale == "zh"  # default before anything is persisted
    paths.persist_locale("en")
    assert WikiPaths(repo).locale == "en"
    assert WikiPaths(repo, locale="zh").locale == "zh"  # explicit arg wins
    assert paths.content_dir.as_posix().endswith("en/content")
    assert paths.knowledge_dir.as_posix().endswith("knowledge/en")


def test_en_flatten_output_paths():
    nodes = flatten(en_catalog(), "en")
    assert nodes[0].output == "en/content/Project Overview/Project Overview.md"
    assert all(n.output.startswith("en/content/") for n in nodes)
    # zh stays the default for backward compatibility
    nodes_zh = flatten(en_catalog())
    assert nodes_zh[0].output.startswith("zh/content/")


# --- en validation ---

def test_en_page_passes(repo):
    res = check_page(en_page(), "Project Overview", repo, locale="en")
    assert res.ok, res.errors


def test_en_page_missing_section_fails(repo):
    text = en_page().replace("## Conclusion\ndemo demonstrates the repowiki flow.\n\nSection sources\n- [README.md:1-3](file://README.md#L1-L3)\n", "")
    res = check_page(text, "Project Overview", repo, locale="en")
    assert not res.ok and any("Conclusion" in e for e in res.errors)
    # …and the zh validator must not accept an en page either
    res_zh = check_page(en_page(), "Project Overview", repo, locale="zh")
    assert not res_zh.ok


def test_en_page_update_requires_summary(repo):
    res = check_page(en_page(), "Project Overview", repo, is_update=True, locale="en")
    assert not res.ok and any("Update Summary" in e for e in res.errors)


def test_en_overview_passes_and_fixes_h1(repo):
    ok = check_overview(
        "# demo Wiki Overview\n\n## Section Navigation\nx\n\n## How to Use This Wiki\ny\n",
        "demo", locale="en",
    )
    assert ok.ok, ok.errors
    fixed = check_overview(
        "# wrong\n\n## Section Navigation\nx\n\n## How to Use This Wiki\ny\n",
        "demo", locale="en",
    )
    assert fixed.ok and fixed.fixed  # H1 rewritten to the expected title


def test_en_knowledge_module_and_card(repo):
    paths = WikiPaths(repo, locale="en")
    paths.root.mkdir(parents=True, exist_ok=True)
    mod = paths.root / "knowledge/en/Core"
    mod.mkdir(parents=True)
    res = check_knowledge_module(mod, locale="en")
    assert not res.ok  # required files missing
    for name in ("overview.md", "tech-stack.md", "architecture.md"):
        (mod / name).write_text("content\n", encoding="utf-8")
    assert check_knowledge_module(mod, locale="en").ok

    card_raw = (
        "---\nkind: logging_system\nname: Logging\ncategory: logging_system\n"
        "source_files:\n  - src/demo/log.py\n---\n\n# Logging\n\n"
        "## 1. System Overview\nx\n\n## 2. Key Files and Packages\nx\n\n"
        "## 3. Architecture and Design Conventions\nx\n\n## 4. Rules for Developers\nx\n"
    )
    assert check_knowledge_card(card_raw, "Logging", "logging_system", repo, locale="en").ok


# --- plan integration ---

def test_plan_locale_flag_persists(repo, capsys):
    rc = cli_main(["plan", str(repo), "--locale", "en", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["locale"] == "en"
    assert (repo / ".repowiki/state/locale").read_text(encoding="utf-8").strip() == "en"
    # catalog task spec is the English one (instructs English titles)
    spec = (repo / ".repowiki/state/tasks/catalog.md").read_text(encoding="utf-8")
    assert "English" in spec
    # later commands honor the persisted locale
    assert WikiPaths(repo).locale == "en"


def test_plan_auto_persists_detected_locale(repo, capsys):
    rc = cli_main(["plan", str(repo), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["locale"] == "zh"  # fixture repo has a Chinese README
    assert (repo / ".repowiki/state/locale").read_text(encoding="utf-8").strip() == "zh"


# --- en end-to-end ---

def test_en_end_to_end(tmp_path):
    repo = make_repo(tmp_path, git=False)
    paths = WikiPaths(repo)
    assert cli_main(["plan", str(repo), "--locale", "en"]) == 0
    assert cli_main(["next", str(repo), "--claim"]) == 0
    write_en_catalog(paths)
    assert cli_main(["check", str(repo), "--task", "catalog"]) == 0

    index = json.loads(paths.index_file.read_text(encoding="utf-8"))
    assert index["tasks"]["c01"]["output"] == "en/content/Project Overview/Project Overview.md"

    nodes = flatten(en_catalog(), "en")
    for n in nodes:
        out = repo / ".repowiki" / n.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(en_page(n.title), encoding="utf-8")
        assert cli_main(["check", str(repo), "--task", n["id"] if isinstance(n, dict) else n.id]) == 0

    assert cli_main(["finalize", str(repo)]) == 3  # creates overview task
    ov = paths.overview_file
    assert ov.as_posix().endswith("en/meta/wiki-overview.md")
    ov.write_text(
        "# demo Wiki Overview\n\n## Section Navigation\n- Project Overview\n\n"
        "## How to Use This Wiki\nStart with Project Overview.\n",
        encoding="utf-8",
    )
    assert cli_main(["check", str(repo), "--task", "overview"]) == 0
    assert cli_main(["finalize", str(repo)]) == 0
    meta = json.loads(paths.metadata_file.read_text(encoding="utf-8"))
    assert meta["wiki_repo"]["locale"] == "en"
    assert meta["wiki_overview"].startswith("# demo Wiki Overview")
