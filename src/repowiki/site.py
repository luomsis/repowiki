"""``repowiki site``: render the finished wiki into one self-contained HTML file.

Reads every generated page plus the overview, embeds the source lines behind
each ``file://`` reference, and inlines the vendored markdown/mermaid JS.
The result (``<locale>/wiki.html``) opens in any browser with zero network
and zero server — double-click, or share the single file.
"""

from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path

from . import templates
from .catalog import FlatNode, flatten
from .errors import UsageError
from .i18n import strings
from .paths import WikiPaths
from .state import now_iso
from .validate import extract_refs

MAX_SNIPPET_LINES = 20_000  # larger spans are skipped rather than bloating the file


def run_site(paths: WikiPaths, open_browser: bool, as_json: bool) -> int:
    if not paths.metadata_file.is_file():
        raise UsageError(
            f"未找到 {paths.metadata_file}：请先完成全部任务并运行 `repowiki finalize <repo>`"
        )
    try:
        metadata = json.loads(paths.metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise UsageError(f"repowiki-metadata.json 损坏（{e}）：请重新运行 `repowiki finalize <repo>`") from e

    nodes = _ordered_nodes(paths)
    pages = _collect_pages(paths, metadata, nodes)
    if not pages:
        raise UsageError(f"未找到任何已生成的 wiki 页面（{paths.content_dir} 为空）")
    nav = _build_nav(paths, pages, nodes)
    snippets = _collect_snippets(paths.repo_root, pages)

    payload = {
        "repo": _repo_name(paths, metadata),
        "locale": paths.locale,
        "generatedAt": now_iso(),
        "ui": strings(paths.locale)["site"],
        "nav": nav,
        "pages": pages,
        "snippets": snippets,
    }
    html = _render_html(payload, paths.locale)

    out = paths.site_file
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, out)
    if open_browser:
        webbrowser.open(out.as_uri())

    summary = {
        "ok": True,
        "site": str(out),
        "pages": len(pages),
        "snippets": len(snippets),
        "size_mb": round(out.stat().st_size / 1024 / 1024, 2),
    }
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"✓ 站点已生成: {out}\n"
            f"  页面 {summary['pages']} · 源码片段 {summary['snippets']} · 体积 {summary['size_mb']} MB\n"
            f"  单文件离线可用：浏览器直接打开即可（--open 自动打开）"
        )
    return 0


# --- content assembly ---

def _repo_name(paths: WikiPaths, metadata: dict) -> str:
    return (metadata.get("wiki_repo") or {}).get("name") or paths.repo_root.name


def _collect_pages(paths: WikiPaths, metadata: dict, nodes: list[FlatNode]) -> list[dict]:
    site = strings(paths.locale)["site"]
    pages: list[dict] = []

    overview = metadata.get("wiki_overview") or ""
    if not overview and paths.overview_file.is_file():
        overview = paths.overview_file.read_text(encoding="utf-8")
    if overview and overview != "No overview yet.":
        pages.append({
            "id": "overview",
            "title": site["overview_label"],
            "path": paths.overview_file.relative_to(paths.root).as_posix(),
            "md": overview,
        })

    for node in nodes:
        f = paths.root / node.output
        if not f.is_file():
            continue
        pages.append({
            "id": node.id,
            "title": node.title,
            "path": node.output,
            "md": f.read_text(encoding="utf-8"),
        })
    return pages


def _ordered_nodes(paths: WikiPaths) -> list[FlatNode]:
    """Plan order from state/catalog.json; after `repowiki clean`, degrade to
    the on-disk directory layout so the site stays buildable."""
    if paths.catalog_file.is_file():
        try:
            catalog = json.loads(paths.catalog_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            catalog = None
        if catalog is not None:
            return flatten(catalog, paths.locale)
    return _nodes_from_disk(paths)


def _nodes_from_disk(paths: WikiPaths) -> list[FlatNode]:
    """Chapter per sub-directory, page per .md file — plan order is lost,
    but the site stays buildable after `repowiki clean`."""
    nodes: list[FlatNode] = []
    content = paths.content_dir
    if not content.is_dir():
        return nodes

    def page_node(f: Path, parent_id: str | None) -> FlatNode:
        return FlatNode(
            id=f.stem, title=f.stem, slug=f.stem, summary="", kind="page",
            dependent_files=[], page_brief="", parent_id=parent_id, depth=2,
            output=f.relative_to(paths.root).as_posix(),
        )

    for entry in sorted(content.iterdir(), key=lambda p: p.name):
        if entry.is_dir() and any(entry.glob("*.md")):
            nodes.append(FlatNode(
                id=entry.name, title=entry.name, slug=entry.name, summary="", kind="chapter",
                dependent_files=[], page_brief="", parent_id=None, depth=1,
                output=f"{entry.relative_to(paths.root).as_posix()}/__chapter__.md",
            ))
            for f in sorted(entry.glob("*.md")):
                nodes.append(page_node(f, entry.name))
        elif entry.is_file() and entry.suffix == ".md":
            nodes.append(page_node(entry, None))
    return nodes


def _build_nav(paths: WikiPaths, pages: list[dict], nodes: list[FlatNode]) -> list[dict]:
    site = strings(paths.locale)["site"]
    by_output = {p["path"]: i for i, p in enumerate(pages)}
    children_of: dict[str | None, list[FlatNode]] = {}
    for n in nodes:
        children_of.setdefault(n.parent_id, []).append(n)

    def descendants(node_id: str) -> list[FlatNode]:
        out: list[FlatNode] = []
        for k in children_of.get(node_id, []):
            out.append(k)
            out.extend(descendants(k.id))
        return out

    entries: list[dict] = []
    for i, p in enumerate(pages):
        if p["id"] == "overview":
            entries.append({"title": site["overview_label"], "page": i})
            break

    for top in children_of.get(None, []):
        own = [{"title": top.title, "page": by_output[top.output]}] if top.output in by_output else []
        kids = [
            {"title": k.title, "page": by_output[k.output]}
            for k in descendants(top.id) if k.output in by_output
        ]
        if not kids:
            if own:  # standalone top-level page (with or without a chapter wrapper)
                entries.append({"title": top.title, "page": own[0]["page"]})
            continue
        entries.append({"title": top.title, "children": own + kids})
    return entries


# --- source snippet extraction ---

def _collect_snippets(repo_root: Path, pages: list[dict]) -> dict:
    snippets: dict = {}
    for p in pages:
        for path, start, end in extract_refs(p["md"]):
            if start is None:
                key, s, e = path, 1, None
            else:
                key, s, e = f"{path}#L{start}-L{end}", start, end
            if key in snippets:
                continue
            lines = _read_lines(repo_root / path)
            if lines is None:
                snippets[key] = {"path": path, "missing": True}
                continue
            e = min(e or len(lines), len(lines))
            s = max(1, min(s, e))
            if e - s + 1 > MAX_SNIPPET_LINES:
                snippets[key] = {"path": path, "missing": True}
                continue
            snippets[key] = {"path": path, "start": s, "end": e, "lines": lines[s - 1:e]}
    return snippets


def _read_lines(p: Path) -> list[str] | None:
    try:
        if not p.is_file():
            return None
        data = p.read_bytes()
        if b"\0" in data[:8192]:  # binary file
            return None
        return data.decode("utf-8", "replace").splitlines()
    except OSError:
        return None


# --- HTML assembly ---

def _render_html(payload: dict, locale: str) -> str:
    payload_js = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    shell = (templates.TEMPLATE_DIR / "site.html").read_text(encoding="utf-8")
    app_js = _script_safe((templates.TEMPLATE_DIR / "site" / "app.js").read_text(encoding="utf-8"))
    return templates.render(
        shell,
        SITE_PAYLOAD=payload_js,
        MARKED_JS=_vendor("marked.min.js"),
        MERMAID_JS=_vendor("mermaid.min.js"),
        APP_JS=app_js,
    )


def _vendor(name: str) -> str:
    js = (Path(__file__).parent / "vendor" / name).read_text(encoding="utf-8")
    return _script_safe(js)


def _script_safe(js: str) -> str:
    # Inside an inline <script> the literal `</script` would close the tag;
    # `<\/script` is an equivalent escape inside JS strings and regexes.
    return js.replace("</script", "<\\/script")
