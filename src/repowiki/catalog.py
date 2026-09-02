"""Catalog schema validation, flattening and output-path derivation.

The catalog is the chapter tree produced by the planning task
(``state/catalog.json``). This module is the single source of truth for
what a valid catalog looks like and where each page lands under
``zh/content/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .paths import sanitize_component, unique_name, nfc

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_DEPTH = 4  # root chapters are depth 1


@dataclass
class FlatNode:
    id: str
    title: str
    slug: str
    summary: str
    kind: str  # "chapter" | "page"
    dependent_files: list[str]
    page_brief: str
    parent_id: str | None
    depth: int
    output: str  # relative to .qoder/repowiki/, e.g. zh/content/项目概述/项目概述.md
    dir: str  # containing directory relative to wiki root ("" for standalone pages)

    def chapter_path(self, by_id: dict[str, "FlatNode"]) -> str:
        parts = [self.title]
        p = self.parent_id
        while p:
            parts.append(by_id[p].title)
            p = by_id[p].parent_id
        return " > ".join(reversed(parts))


def validate_catalog(data, known_paths: set[str]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Unknown dependent_files are dropped with a warning."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["catalog 必须是 JSON 对象"], warnings
    if not isinstance(data.get("repo_name"), str) or not data.get("repo_name", "").strip():
        errors.append("缺少 repo_name（非空字符串）")
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        errors.append("缺少 chapters（非空数组）")
        return errors, warnings

    seen_ids: dict[str, str] = {}
    seen_titles: dict[str, str] = {}
    seen_slugs: dict[str, str] = {}
    dropped_files: list[str] = []

    def walk(nodes, depth: int, path_desc: str) -> None:
        if nodes is None:
            nodes = []
        if not isinstance(nodes, list):
            errors.append(f"{path_desc}: children 必须是数组")
            return
        if depth > MAX_DEPTH:
            errors.append(f"{path_desc}: 树深度超过 {MAX_DEPTH} 层")
            return
        for i, node in enumerate(nodes):
            where = f"{path_desc}[{i}]"
            if not isinstance(node, dict):
                errors.append(f"{where}: 节点必须是对象")
                continue
            nid = node.get("id")
            title = nfc(node.get("title", "")).strip()
            slug = node.get("slug", "")
            kind = node.get("kind")
            if not isinstance(nid, str) or not nid.strip():
                errors.append(f"{where}: 缺少 id")
            elif nid in seen_ids:
                errors.append(f"{where}: id 重复 `{nid}`（首次出现于 {seen_ids[nid]}）")
            else:
                seen_ids[nid] = where
            if not title:
                errors.append(f"{where}: 缺少 title")
            elif title in seen_titles:
                errors.append(f"{where}: title 重复 `{title}`（首次出现于 {seen_titles[title]}）")
            else:
                seen_titles[title] = where
            if not isinstance(slug, str) or not SLUG_RE.match(slug or ""):
                errors.append(f"{where}: slug 非法 `{slug}`（应为小写英文与连字符，如 project-overview）")
            elif slug in seen_slugs:
                errors.append(f"{where}: slug 重复 `{slug}`（首次出现于 {seen_slugs[slug]}）")
            else:
                seen_slugs[slug] = where
            if kind not in ("chapter", "page"):
                errors.append(f"{where}: kind 必须是 chapter 或 page，得到 {kind!r}")
                kind = "page"
            brief = node.get("page_brief")
            if not isinstance(brief, str) or not brief.strip():
                errors.append(f"{where}（{title or nid}）: 缺少 page_brief（页面要点提示词）")
            deps = node.get("dependent_files")
            if deps is None:
                deps = []
            if not isinstance(deps, list):
                errors.append(f"{where}（{title or nid}）: dependent_files 必须是数组")
                deps = []
            else:
                bad = [d for d in deps if not isinstance(d, str) or d not in known_paths]
                for d in bad:
                    dropped_files.append(f"{title or nid}: {d}")
                deps = [d for d in deps if isinstance(d, str) and d in known_paths]
            node["dependent_files"] = deps
            if kind == "page" and node.get("children"):
                errors.append(f"{where}（{title or nid}）: kind=page 不能有 children")
            walk(node.get("children") if kind == "chapter" else None, depth + 1, f"{where}/children")

    walk(chapters, 1, "chapters")
    if dropped_files:
        warnings.append("以下 dependent_files 不在仓库清单中，已剔除: " + "; ".join(dropped_files))
    return errors, warnings


def flatten(data: dict) -> list[FlatNode]:
    """Flatten validated catalog into nodes with derived output paths.

    Path rules: every chapter gets a directory named after its title plus an
    index page with the same name; root-level pages are standalone files at
    ``zh/content/``. Collisions among siblings get ``__2`` suffixes.
    """
    by_id: dict[str, FlatNode] = {}
    out: list[FlatNode] = []

    def walk(nodes, parent: FlatNode | None, dir_chain: list[str], used_here: set[str]) -> None:
        for node in nodes:
            kind = node.get("kind", "page")
            comp = unique_name(sanitize_component(node["title"]), used_here)
            if kind == "chapter":
                chain = dir_chain + [comp]
                rel_dir = "/".join(chain)
                output = f"zh/content/{rel_dir}/{comp}.md"
            else:
                chain = dir_chain
                rel_dir = "/".join(chain)
                output = f"zh/content/{rel_dir}/{comp}.md" if chain else f"zh/content/{comp}.md"
            flat = FlatNode(
                id=node["id"],
                title=nfc(node["title"]).strip(),
                slug=node.get("slug", ""),
                summary=node.get("summary", ""),
                kind=kind,
                dependent_files=list(node.get("dependent_files", [])),
                page_brief=node.get("page_brief", ""),
                parent_id=parent.id if parent else None,
                depth=(parent.depth + 1) if parent else 1,
                output=output,
                dir=f"zh/content/{rel_dir}" if rel_dir else "zh/content",
            )
            by_id[flat.id] = flat
            out.append(flat)
            if kind == "chapter":
                walk(node.get("children") or [], flat, chain, set())

    walk(data.get("chapters") or [], None, [], set())
    return out


def catalog_tree_text(flat: list[FlatNode]) -> str:
    """Render the flattened catalog as an indented tree with page_briefs."""
    by_id = {n.id: n for n in flat}
    lines: list[str] = []
    for n in flat:
        indent = "  " * (n.depth - 1)
        marker = "章" if n.kind == "chapter" else "页"
        lines.append(f"{indent}- [{marker}] {n.title}  ({n.output})")
        if n.page_brief:
            brief = n.page_brief.replace("\n", " ")
            lines.append(f"{indent}    · {brief}")
    return "\n".join(lines)
