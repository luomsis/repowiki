"""Task record + spec-file builders.

Every task is (a) a record in ``state/index.json`` and (b) an immutable
markdown spec under ``state/tasks/<id>.md`` that tells the executing agent
exactly what to do. Specs embed the full page template and style rules so
tasks are self-contained and parallel-safe.
"""

from __future__ import annotations

from pathlib import Path

from .catalog import FlatNode, catalog_tree_text
from .paths import WikiPaths, sanitize_component, unique_name
from .scanner import Inventory
from .state import new_task
from . import templates

FILE_LIST_CAP = 800


def _hint_list(paths: list[str], inv: Inventory) -> str:
    by_path = {f.path: f for f in inv.files}
    lines = []
    for p in paths:
        f = by_path.get(p)
        if f:
            meta = f"（{f.lang or 'file'}，{f.loc} 行）" if f.loc else ""
            lines.append(f"- {p} {meta}".rstrip())
        else:
            lines.append(f"- {p}")
    return "\n".join(lines) or "- <无提示文件——请自行浏览仓库相关目录>"


def _yaml_list(items: list[str], indent: str = "  ") -> str:
    lines = []
    for it in items:
        # quote YAML-unsafe scalars: `**` reads as an alias node, etc.
        safe = f'"{it}"' if it.startswith(("*", "&", "!", "{", "[", "#")) else it
        lines.append(f"{indent}- {safe}")
    return "\n".join(lines) or f"{indent}- []"


def _brief_bullets(brief: str) -> str:
    brief = (brief or "").strip()
    if not brief:
        return "- <catalog 未提供要点，请通读提示文件后自行提炼>"
    if "\n" in brief or brief.startswith(("-", "•", "·")):
        return brief
    return f"- {brief}"


def write_spec(paths: WikiPaths, task_id: str, text: str) -> None:
    spec = paths.task_spec(task_id)
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(text, encoding="utf-8")


# --- phase 1: catalog planning ---

def build_catalog_task(paths: WikiPaths, inv: Inventory) -> dict:
    code_paths = [f.path for f in inv.files if f.is_code]
    shown = code_paths[:FILE_LIST_CAP]
    file_list = "\n".join(shown)
    if len(code_paths) > len(shown):
        file_list += f"\n… (+{len(code_paths) - len(shown)} more)"
    spec = templates.render_file(
        "catalog_task.md",
        REPO_NAME=inv.repo_root.rstrip("/").split("/")[-1],
        CODE_FILE_COUNT=inv.code_file_count,
        KEY_FILES=", ".join(inv.key_files) or "<未发现>",
        TREE_SUMMARY=inv.tree_summary or "<空仓库>",
        FILE_LIST=file_list,
        FILE_LIST_COUNT=len(shown),
    )
    write_spec(paths, "catalog", spec)
    return new_task("catalog", "catalog", 1, "目录规划（catalog）", "state/catalog.json")


# --- phase 2: pages ---

def build_page_tasks(paths: WikiPaths, nodes: list[FlatNode], inv: Inventory, max_pages: int | None = None) -> list[dict]:
    by_id = {n.id: n for n in nodes}
    records: list[dict] = []
    selected = nodes if max_pages is None else nodes[:max_pages]
    for node in selected:
        siblings = [
            n.title for n in nodes
            if n.parent_id == node.parent_id and n.id != node.id
        ]
        output_abs = str(Path(".repowiki") / node.output)
        spec = templates.render_file(
            "page_task.md",
            TASK_ID=node.id,
            TITLE=node.title,
            OUTPUT=node.output,
            OUTPUT_ABS=output_abs,
            HINT_FILES=_hint_list(node.dependent_files, inv),
            HINT_FILES_YAML=_yaml_list(node.dependent_files),
            CHAPTER_PATH=node.chapter_path(by_id),
            SUMMARY=node.summary or "<catalog 未提供>",
            PAGE_BRIEF=_brief_bullets(node.page_brief),
            SIBLINGS="\n".join(f"- {s}" for s in siblings) or "<无姊妹页面>",
            PAGE_TEMPLATE=templates.render(templates.load("page_template.md"), TITLE=node.title),
            STYLE=templates.load("STYLE.md"),
        )
        write_spec(paths, node.id, spec)
        records.append(new_task(node.id, "page", 2, node.title, node.output))
    return records


# --- phase 3: overview ---

def build_overview_task(paths: WikiPaths, repo_name: str, nodes: list[FlatNode]) -> dict:
    spec = templates.render_file(
        "overview_task.md",
        OUTPUT_ABS=".repowiki/zh/meta/wiki-overview.md",
        REPO_NAME=repo_name,
        CATALOG_TREE=catalog_tree_text(nodes),
        STYLE=templates.load("STYLE.md"),
    )
    write_spec(paths, "overview", spec)
    return new_task("overview", "overview", 3, "Wiki 总览（wiki_overview）", "zh/meta/wiki-overview.md")


# --- incremental updates (phase 2 tasks appended post-finalize) ---

def build_update_task(paths: WikiPaths, node: FlatNode, changed_files: list[str], inv: Inventory) -> dict:
    old = (paths.root / node.output)
    old_text = old.read_text(encoding="utf-8") if old.exists() else "<页面文件不存在——按 page 模板全量撰写>"
    task_id = f"{node.id}-update"
    output_abs = str(Path(".repowiki") / node.output)
    spec = templates.render_file(
        "update_task.md",
        TASK_ID=task_id,
        TITLE=node.title,
        OUTPUT=node.output,
        OUTPUT_ABS=output_abs,
        CHANGED_FILES=_hint_list(changed_files, inv),
        PAGE_BRIEF=_brief_bullets(node.page_brief),
        OLD_PAGE=old_text,
        STYLE=templates.load("STYLE.md"),
        HINT_FILES_YAML=_yaml_list(node.dependent_files),
    )
    write_spec(paths, task_id, spec)
    return new_task(task_id, "page_update", 2, f"{node.title}（增量更新）", node.output)


# --- knowledge (phase 2) ---

KNOWLEDGE_CATEGORIES = [
    "configuration_system", "logging_system", "error_handling",
    "build_system", "dependency_management", "frontend_style",
]


def build_knowledge_plan_task(paths: WikiPaths, inv: Inventory) -> dict:
    spec = templates.render_file(
        "knowledge_task.md",
        REPO_NAME=inv.repo_root.rstrip("/").split("/")[-1],
        KEY_FILES=", ".join(inv.key_files) or "<未发现>",
        TREE_SUMMARY=inv.tree_summary or "<空仓库>",
    )
    write_spec(paths, "knowledge-plan", spec)
    return new_task("knowledge-plan", "knowledge_plan", 2, "知识库规划（modules + cards）", "state/knowledge.json")


def build_knowledge_tasks(paths: WikiPaths, plan: dict) -> list[dict]:
    """Expand a validated knowledge plan into module + card tasks."""
    used_dirs: set[str] = set()
    records: list[dict] = []
    for mod in plan.get("modules", []):
        task_id = mod["id"]
        dir_name = unique_name(sanitize_component(mod["title"]), used_dirs)
        out_dir = f"knowledge/zh/{dir_name}"
        (paths.root / out_dir).mkdir(parents=True, exist_ok=True)
        spec = templates.render_file(
            "knowledge_module_task.md",
            TASK_ID=task_id,
            TITLE=mod["title"],
            OUTPUT_DIR=out_dir,
            OUTPUT_DIR_ABS=f".repowiki/{out_dir}",
            SCOPE=", ".join(mod.get("scope") or []) or "<整个仓库>",
            CHILDREN=", ".join(
                m["title"] for m in plan.get("modules", []) if m["id"] in (mod.get("children") or [])
            ) or "<无>",
        )
        write_spec(paths, task_id, spec)
        records.append(new_task(task_id, "knowledge_module", 2, f"知识模块：{mod['title']}", out_dir))
    for card in plan.get("cards", []):
        task_id = card["id"]
        dir_name = unique_name(sanitize_component(card["title"]), used_dirs)
        out = f"knowledge/zh/{dir_name}/{dir_name}.md"
        (paths.root / out).parent.mkdir(parents=True, exist_ok=True)
        spec = templates.render_file(
            "knowledge_card_task.md",
            TASK_ID=task_id,
            TITLE=card["title"],
            CATEGORY=card.get("category", ""),
            OUTPUT=out,
            OUTPUT_ABS=f".repowiki/{out}",
            SCOPE_YAML=_yaml_list(card.get("scope") or ["**"]),
            SOURCE_FILES_YAML=_yaml_list(card.get("source_files") or []),
            SOURCE_FILES=_hint_list(card.get("source_files") or [], Inventory(repo_root="")),
        )
        write_spec(paths, task_id, spec)
        records.append(new_task(task_id, "knowledge_card", 2, f"知识卡片：{card['title']}", out))
    return records
