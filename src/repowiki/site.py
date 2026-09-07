"""``repowiki site``: render the finished wiki into one self-contained HTML file.

Reads every generated page plus the overview, embeds the source lines behind
each ``file://`` reference, and inlines the vendored markdown/mermaid JS.
Knowledge module docs and cards (``knowledge/<locale>/``) are included as
regular pages under a dedicated nav chapter.
The result (``<locale>/wiki.html``) opens in any browser with zero network
and zero server — double-click, or share the single file.
"""

from __future__ import annotations

import json
import os
import re
import webbrowser
from pathlib import Path

import yaml

from . import templates
from .catalog import FlatNode, flatten
from .errors import UsageError
from .i18n import strings
from .output import emit
from .paths import WikiPaths, sanitize_component
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
    knowledge_pages, knowledge_nav = _collect_knowledge(paths, base=len(pages))
    pages.extend(knowledge_pages)
    nav = _build_nav(paths, pages, nodes)
    if knowledge_nav:
        nav.append(knowledge_nav)
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
        "knowledge_pages": len(knowledge_pages),
        "snippets": len(snippets),
        "size_mb": round(out.stat().st_size / 1024 / 1024, 2),
    }
    emit(summary, _site_human, as_json)
    return 0


def _site_human(r: dict) -> str:
    return (
        f"✓ 站点已生成: {r['site']}\n"
        f"  页面 {r['pages']}（含知识页 {r['knowledge_pages']}）· 源码片段 {r['snippets']} · 体积 {r['size_mb']} MB\n"
        f"  单文件离线可用：浏览器直接打开即可（--open 自动打开）"
    )


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


# --- knowledge pages ---

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_H1_RE = re.compile(r"^#\s+(.+)$", re.M)


def _collect_knowledge(paths: WikiPaths, base: int) -> tuple[list[dict], dict | None]:
    """Module docs + cards under knowledge/<locale>/ as site pages.

    Returns (pages, nav_entry); nav children reference absolute page indexes
    starting at ``base``. Order follows state/knowledge.json (modules then
    cards, by sanitized title) and degrades to on-disk sorting.
    """
    site = strings(paths.locale)["site"]
    kdir = paths.knowledge_dir
    if not kdir.is_dir():
        return [], None
    dirs = sorted(d for d in kdir.iterdir() if d.is_dir())
    if not dirs:
        return [], None

    module_files = set(strings(paths.locale)["module_required_files"])
    rank = _knowledge_plan_order(paths)

    def sort_key(d: Path) -> tuple:
        return (rank.get(d.name, len(rank)), d.name)
    dirs.sort(key=sort_key)

    module_title_of: dict[str, str] = {}
    pages: list[dict] = []
    children: list[dict] = []
    for d in dirs:
        docs = sorted(f for f in d.glob("*.md") if f.name in module_files)
        if docs:
            title = _module_title(paths, d)
            module_title_of[d.name] = title
            for f in docs:
                pages.append({
                    "id": f"kb:{d.name}/{f.name}",
                    "title": f"{title} · {f.stem}",
                    "path": f.relative_to(paths.root).as_posix(),
                    "md": f.read_text(encoding="utf-8"),
                })
                children.append({"title": f"{title} · {f.stem}", "page": base + len(pages) - 1})
            continue
        card = d / f"{d.name}.md"
        if card.is_file():
            md, title = _card_body(card.read_text(encoding="utf-8"), d.name)
            pages.append({
                "id": f"kb:{d.name}/{d.name}.md",
                "title": title,
                "path": card.relative_to(paths.root).as_posix(),
                "md": md,
            })
            children.append({"title": title, "page": base + len(pages) - 1})
    if not pages:
        return [], None
    return pages, {"title": site["knowledge_label"], "children": children}


def _knowledge_plan_order(paths: WikiPaths) -> dict[str, int]:
    """Directory-name -> plan rank, from state/knowledge.json item titles."""
    f = paths.knowledge_plan_file
    if not f.is_file():
        return {}
    try:
        plan = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    rank: dict[str, int] = {}
    if not isinstance(plan, dict):
        return rank
    i = 0
    for kind in ("modules", "cards"):
        for item in plan.get(kind) or []:
            if isinstance(item, dict) and item.get("title"):
                rank.setdefault(sanitize_component(item["title"]), i)
                i += 1
    return rank


def _module_title(paths: WikiPaths, d: Path) -> str:
    f = d / "_module.yaml"
    if f.is_file():
        try:
            meta = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(meta, dict) and meta.get("title"):
                return str(meta["title"])
        except yaml.YAMLError:
            pass
    return d.name


def _card_body(raw: str, dirname: str) -> tuple[str, str]:
    """Strip YAML front matter for display; title = fm name / first H1 / dir."""
    title = dirname
    body = raw
    fm = _FM_RE.match(raw)
    meta = {}
    if fm:
        body = raw[fm.end():]
        try:
            meta = yaml.safe_load(fm.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        if isinstance(meta, dict) and meta.get("name"):
            title = str(meta["name"])
    if title == dirname:
        h1 = _H1_RE.search(body)
        if h1:
            title = h1.group(1).strip()
    return body, title


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
