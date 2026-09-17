"""Archetype coverage tests: template wiring, per-archetype validation
tables, and end-to-end page generation for every page archetype (no LLM:
tests simulate the agent's writes)."""

from __future__ import annotations

import json

import pytest
from conftest import valid_catalog, write_catalog

from repowiki import templates as templates_mod
from repowiki.catalog import ARCHETYPES, flatten, validate_catalog
from repowiki.cli import main
from repowiki.dispatch import _node_archetype
from repowiki.i18n import STRINGS, strings
from repowiki.paths import WikiPaths, github_anchor
from repowiki.tasks import _PAGE_TEMPLATE_BY_ARCHETYPE
from repowiki.validate import _SECTION_TABLE_BY_ARCHETYPE, check_page


def run(*argv):
    return main(list(argv))


_GRAPH_BLOCK = """```mermaid
graph TB
A["组件 A<br/>main.py"] --> B["组件 B"]
```
"""

_SEQ_BLOCK = """```mermaid
sequenceDiagram
participant U as "调用方"
participant S as "服务"
U->>S : "请求"
S-->>U : "响应"
```
"""

_CITE = {
    "zh": "**本文引用的文件**",
    "en": "**Files referenced**",
}


def archetype_page(title: str, archetype: str, locale: str = "zh",
                   drop: str | None = None) -> str:
    """A minimal valid page for the given archetype: one `## <section>` per
    entry of the archetype's required-sections table, each with a source
    list, two mermaid diagrams, and a cite block. `drop` omits one section
    (used to prove the validator enforces the archetype's own table)."""
    lang = strings(locale)
    src = lang["section_sources"]
    toc_name = lang["toc"]
    diagram_src = "图表来源" if locale == "zh" else "Diagram sources"
    sections = [name for name, _ in lang[_SECTION_TABLE_BY_ARCHETYPE[archetype]]]
    if drop is not None:
        sections = [s for s in sections if not s.startswith(drop)]

    toc = "\n".join(
        f"{i}. [{name}](#{github_anchor(name)})"
        for i, name in enumerate(sections, 1)
    )
    parts = [f"# {title}\n", f"<cite>\n{_CITE[locale]}\n"
             "- [README.md](file://README.md)\n"
             "- [src/demo/main.py](file://src/demo/main.py)\n</cite>\n",
             f"## {toc_name}\n{toc}\n"]
    for i, name in enumerate(sections):
        parts.append(f"## {name}\n<正文要点>。\n")
        if i == 1:
            parts.append(f"{_GRAPH_BLOCK}\n{diagram_src}\n"
                         "- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)\n")
        if i == 2:
            parts.append(f"{_SEQ_BLOCK}\n{diagram_src}\n"
                         "- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)\n")
        parts.append(f"{src}\n- [README.md:1-2](file://README.md#L1-L2)\n")
    return "\n".join(parts)


class TestWiring:
    def test_archetypes_tables_and_templates_consistent(self):
        """Every archetype maps to an existing template file (zh+en) and an
        existing i18n section table; template headings cover the table."""
        assert set(_PAGE_TEMPLATE_BY_ARCHETYPE) == set(ARCHETYPES)
        assert set(_SECTION_TABLE_BY_ARCHETYPE) == set(ARCHETYPES)
        for archetype in ARCHETYPES:
            fname = _PAGE_TEMPLATE_BY_ARCHETYPE[archetype]
            key = _SECTION_TABLE_BY_ARCHETYPE[archetype]
            for locale in ("zh", "en"):
                f = templates_mod.TEMPLATE_DIR / locale / fname
                assert f.is_file(), f"missing template {f}"
                assert key in STRINGS[locale], f"missing {key} in {locale}"
                text = f.read_text(encoding="utf-8")
                headings = [
                    line[3:].strip() for line in text.splitlines()
                    if line.startswith("## ")
                ]
                for name, mode in STRINGS[locale][key]:
                    if mode == "exact":
                        assert name in headings, f"{fname}/{locale}: {name}"
                    else:
                        assert any(h.startswith(name) for h in headings), \
                            f"{fname}/{locale}: prefix {name}"

    def test_template_name_mapping(self):
        from repowiki.tasks import _page_template_name
        from repowiki.catalog import FlatNode

        def node(archetype):
            return FlatNode(id="x", title="t", slug="t", summary="", kind="page",
                            dependent_files=[], page_brief="", parent_id=None,
                            depth=1, output="x.md", archetype=archetype)

        assert _page_template_name(node("flow")) == "flow_template.md"
        assert _page_template_name(node("layer")) == "layer_template.md"
        assert _page_template_name(node("data")) == "data_template.md"
        assert _page_template_name(node("api")) == "api_template.md"
        assert _page_template_name(node("event")) == "event_template.md"
        assert _page_template_name(node("nonsense")) == "page_template.md"

    def test_unknown_archetype_falls_back_to_module(self):
        catalog = valid_catalog()
        catalog["chapters"][0]["children"][0]["archetype"] = "diagram"
        errors, _ = validate_catalog(catalog, known_paths=set())
        assert any("archetype" in e for e in errors)
        nodes = {n.id: n for n in flatten(catalog)}
        assert nodes["c0101"].archetype == "module"

    def test_dispatch_archetype_lookup(self, repo):
        paths = WikiPaths(repo)
        catalog = valid_catalog()
        catalog["chapters"][0]["children"][0]["archetype"] = "diagram"
        write_catalog(paths, catalog)
        assert _node_archetype(paths, "c0101") == "module"
        catalog["chapters"][0]["children"][0]["archetype"] = "event"
        write_catalog(paths, catalog)
        assert _node_archetype(paths, "c0101") == "event"


class TestCheckPage:
    """Unit-level: a generated page per archetype passes its own table and
    fails when one of its required sections is removed."""

    @pytest.mark.parametrize("locale", ["zh", "en"])
    @pytest.mark.parametrize("archetype", ARCHETYPES)
    def test_page_passes_check(self, repo, archetype, locale):
        res = check_page(archetype_page("T", archetype, locale), "T", repo,
                         locale=locale, archetype=archetype,
                         known_paths={"README.md", "src/demo/main.py"})
        assert res.errors == [], res.errors
        assert res.ok

    @pytest.mark.parametrize("locale", ["zh", "en"])
    @pytest.mark.parametrize("archetype", ["flow", "layer", "data", "api", "event"])
    def test_missing_section_fails_check(self, repo, archetype, locale):
        lang = strings(locale)
        table = lang[_SECTION_TABLE_BY_ARCHETYPE[archetype]]
        victim = table[1][0]  # drop the 2nd required section (non-简介, non-prefix fallback)
        raw = archetype_page("T", archetype, locale, drop=victim)
        res = check_page(raw, "T", repo, locale=locale, archetype=archetype,
                         known_paths={"README.md", "src/demo/main.py"})
        assert not res.ok
        assert any(victim[:4] in e for e in res.errors), res.errors


class TestEndToEnd:
    NEW = ["layer", "data", "api", "event"]

    def test_plan_embeds_new_archetype_templates(self, repo):
        paths = WikiPaths(repo)
        catalog = valid_catalog()
        children = []
        for i, arch in enumerate(self.NEW, 1):
            children.append({
                "id": f"c010{i}", "title": f"页面{arch}", "slug": f"page-{arch}",
                "summary": "s", "kind": "page",
                "dependent_files": ["src/demo/models.py"],
                "page_brief": "b", "archetype": arch,
            })
        catalog["chapters"][0]["children"] = children
        write_catalog(paths, catalog)
        assert run("plan", str(repo)) == 0
        for i, arch in enumerate(self.NEW, 1):
            spec = (paths.tasks_dir / f"c010{i}.md").read_text(encoding="utf-8")
            marker = STRINGS["zh"][_SECTION_TABLE_BY_ARCHETYPE[arch]][1][0]
            assert f"## {marker}" in spec, (arch, marker)
            assert "## 项目结构" not in spec  # module skeleton not embedded

    def test_event_page_end_to_end(self, repo):
        paths = WikiPaths(repo)
        catalog = valid_catalog()
        catalog["chapters"][0]["children"][0]["archetype"] = "event"
        write_catalog(paths, catalog)
        run("plan", str(repo))
        out = paths.root / "zh/content/项目概述/核心概念.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(archetype_page("核心概念", "event"), encoding="utf-8")
        assert run("check", str(repo), "--task", "c0101") == 0
        index = json.loads(paths.index_file.read_text(encoding="utf-8"))
        assert index["tasks"]["c0101"]["status"] == "done"

    def test_en_locale_layer_page_end_to_end(self, repo):
        paths = WikiPaths(repo)
        catalog = valid_catalog()
        catalog["chapters"][0]["children"][0]["archetype"] = "layer"
        write_catalog(paths, catalog)
        assert run("plan", str(repo), "--locale", "en") == 0
        spec = (paths.tasks_dir / "c0101.md").read_text(encoding="utf-8")
        assert "## Layer Overview" in spec and "## 项目结构" not in spec
        out = paths.root / "en/content/项目概述/核心概念.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(archetype_page("核心概念", "layer", locale="en"), encoding="utf-8")
        assert run("check", str(repo), "--task", "c0101") == 0
        index = json.loads(paths.index_file.read_text(encoding="utf-8"))
        assert index["tasks"]["c0101"]["status"] == "done"
