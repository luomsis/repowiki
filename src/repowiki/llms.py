"""llms.txt / llms-full.txt export: the agent-consumption face of the wiki.

The llms.txt convention (llmstxt.org) gives coding agents a linked index of a
documentation set plus an optional full-text companion. repowiki's pages are
plain markdown already, so both files are a deterministic byproduct of the same
page collection the HTML site builds: links are relative paths into
``.repowiki/`` — no agent, network or MCP server involved.
"""

from __future__ import annotations

import os
from pathlib import Path

from .i18n import strings
from .paths import WikiPaths


def write_llms(paths: WikiPaths, repo_name: str, pages: list[dict], nav: list[dict]) -> None:
    """Write ``<locale>/llms.txt`` and ``<locale>/llms-full.txt``.

    ``pages``/``nav`` are the collections assembled for the HTML site: page
    dicts carry ``title``/``path`` (posix, relative to ``.repowiki/``)/``md``,
    nav entries are ``{"title", "page"}`` singles or ``{"title", "children"}``
    chapters whose leaves reference page indexes.
    """
    desc = strings(paths.locale)["site"]["llms_desc"].format(repo=repo_name)

    lines = [f"# {repo_name} Wiki", "", f"> {desc}"]
    for entry in nav:
        lines += ["", f"## {entry['title']}", ""]
        for leaf in entry.get("children", [entry]):
            p = pages[leaf["page"]]
            lines.append(f"- [{leaf['title']}]({_rel(paths, p['path'])})")

    full = [f"# {repo_name} Wiki", "", f"> {desc}"]
    for p in pages:
        full += ["", "---", "", p["md"].rstrip()]

    for name, text in (("llms.txt", "\n".join(lines) + "\n"),
                       ("llms-full.txt", "\n".join(full) + "\n")):
        out = paths.root / paths.locale / name
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, out)


def _rel(paths: WikiPaths, page_path: str) -> str:
    """Link target for a page, relative to the directory holding llms.txt."""
    rel = os.path.relpath(paths.root / page_path, paths.root / paths.locale)
    return Path(rel).as_posix()
