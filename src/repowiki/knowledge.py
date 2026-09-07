"""``repowiki knowledge``: append the knowledge-card task set, and aggregate
knowledge outputs (_index.yaml / _module.yaml) at finalize time.

Card categories default to the built-in six; ``--categories <file>`` replaces
them wholesale with a repo-specific list (YAML/JSON), persisted in
``state/knowledge_categories.json`` so later ``check``/``update`` rounds
validate against the same set.
"""

from __future__ import annotations

import json
import re

import yaml

from .errors import UsageError
from .gitutil import run_git
from .output import emit
from .paths import WikiPaths, sanitize_component
from . import tasks as task_builders
from .scanner import scan
from .state import TaskStore, now_iso

_CATEGORY_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_CATEGORIES = 12


def run_knowledge(paths: WikiPaths, as_json: bool, categories: str | None = None) -> int:
    if categories:
        custom = _load_category_file(paths.repo_root / categories)
        paths.knowledge_categories_file.write_text(
            json.dumps({"categories": custom}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    store = TaskStore(paths)
    data = store.load()
    if not data["tasks"]:
        raise UsageError("请先运行 `repowiki plan <repo>`")
    effective = effective_categories(paths)
    added = store.add_tasks([
        task_builders.build_knowledge_plan_task(paths, scan(paths.repo_root), effective)
    ])
    result = {
        "ok": True,
        "added": added,
        "categories": [c["id"] for c in effective],
        "note": "knowledge-plan 任务已就绪，领取执行后 check 会自动展开模块/卡片任务",
    }
    emit(result, _knowledge_human, as_json)
    return 0


def _knowledge_human(r: dict) -> str:
    head = "已添加 knowledge-plan 任务" if r["added"] else "knowledge 任务集已存在"
    cats = "、".join(r["categories"])
    return f"{head}（类别清单：{cats}）\n{r['note']}"


def _load_category_file(path) -> list[dict]:
    """Parse + validate a user-supplied category list (YAML or JSON).

    Entries are ``id`` strings or objects with ``id`` and optional
    ``name``/``guidance``. The list replaces the built-in categories.
    """
    if not path.is_file():
        raise UsageError(f"类别文件不存在: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = (yaml.safe_load(raw) if path.suffix in (".yaml", ".yml")
                else json.loads(raw))
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise UsageError(f"类别文件解析失败（{path.name}）: {e}") from e
    if not isinstance(data, list) or not data:
        raise UsageError("类别文件必须是非空数组（字符串 id，或含 id/name/guidance 的对象）")
    seen: set[str] = set()
    cats: list[dict] = []
    for i, item in enumerate(data):
        where = f"categories[{i}]"
        if isinstance(item, str):
            item = {"id": item}
        if not isinstance(item, dict):
            raise UsageError(f"{where}: 必须是字符串或对象")
        cid = str(item.get("id", "")).strip()
        if not _CATEGORY_ID_RE.match(cid):
            raise UsageError(
                f"{where}: id 非法 `{cid}`（小写字母开头，仅小写字母/数字/下划线）"
            )
        if cid in seen:
            raise UsageError(f"{where}: id 重复 `{cid}`")
        seen.add(cid)
        cats.append({
            "id": cid,
            "name": str(item.get("name", "")).strip() or cid,
            "guidance": str(item.get("guidance", "")).strip(),
        })
    if len(cats) > MAX_CATEGORIES:
        raise UsageError(f"类别过多（{len(cats)} > {MAX_CATEGORIES}）：机制卡片贵精不贵多")
    return cats


def effective_categories(paths: WikiPaths) -> list[dict]:
    """The category list in force: user-supplied (persisted) or built-in."""
    f = paths.knowledge_categories_file
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("categories"), list) and data["categories"]:
            return data["categories"]
    return [
        {"id": cid, "name": guide}
        for cid, guide in task_builders.DEFAULT_KNOWLEDGE_CATEGORIES
    ]


def scope_covers(scope_entry: str, path: str) -> bool:
    """True when ``path`` falls under a plan scope entry like ``src/core/``,
    ``src/core/**`` or ``**``."""
    if scope_entry in ("**", "", "*"):
        return True
    prefix = scope_entry
    for suffix in ("/**", "/*", "/"):
        if prefix.endswith(suffix):
            prefix = prefix[: -len(suffix)]
            break
    if not prefix:
        return True
    return path == prefix or path.startswith(prefix + "/")


def _module_source_files(plan: dict, mod: dict) -> list[str]:
    """Card-declared source files that fall under this module's scope — the
    module docs describe structure, so their key files come from the cards."""
    scopes = [s for s in (mod.get("scope") or []) if isinstance(s, str)]
    files: set[str] = set()
    for c in plan.get("cards", []):
        if not isinstance(c, dict):
            continue
        for p in c.get("source_files") or []:
            if any(scope_covers(s, p) for s in scopes):
                files.add(p)
    return sorted(files)


def aggregate_knowledge(paths: WikiPaths, plan: dict, task_records: dict) -> str:
    """Write knowledge/<locale>/_index.yaml and per-module _module.yaml.

    Returns a human summary. Module -> directory mapping comes from the
    knowledge_module task outputs (recorded when the task set was expanded).
    """
    mod_dirs: dict[str, str] = {}
    used: set[str] = set()
    for tid, t in task_records.items():
        if t["kind"] == "knowledge_module":
            dir_name = t["output"].rstrip("/").split("/")[-1]
            mod_dirs[tid] = dir_name
            used.add(dir_name)

    if not mod_dirs:
        return ""

    def dir_of(mid: str) -> str | None:
        return mod_dirs.get(mid)

    modules_by_id = {m["id"]: m for m in plan.get("modules", []) if isinstance(m, dict)}
    branch = ((run_git(paths.repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()) or "main"

    # per-module _module.yaml
    for mid, mod in modules_by_id.items():
        d = dir_of(mid)
        if not d:
            continue
        mod_path = (mod.get("scope") or [""])[0]
        content = {
            "schema_version": 1,
            "module_path": mod_path if mod_path != "**" else "",
            "title": mod.get("title", ""),
            "scope": mod.get("scope") or [],
            "source_files": _module_source_files(plan, mod),
            "depends_on": [dir_of(x) for x in (mod.get("depends_on") or []) if dir_of(x)],
            "related_to": [dir_of(x) for x in (mod.get("related_to") or []) if dir_of(x)],
        }
        f = paths.knowledge_dir / d / "_module.yaml"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(
            "# 知识卡导出模块文件\n" + yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    # _index.yaml with a module tree keyed by module_path
    index_modules: dict[str, dict] = {}
    for mid, mod in modules_by_id.items():
        d = dir_of(mid)
        if not d:
            continue
        key = (mod.get("scope") or [""])[0]
        key = "" if key in ("**", "") else key
        index_modules[key] = {
            "dir_name": d,
            "title": mod.get("title", ""),
            "scope": mod.get("scope") or [],
            "source_files": _module_source_files(plan, mod),
            "children": [
                (modules_by_id[c].get("scope") or [""])[0] or ""
                for c in (mod.get("children") or []) if c in modules_by_id
            ],
            "depends_on": [dir_of(x) for x in (mod.get("depends_on") or []) if dir_of(x)],
            "related_to": [dir_of(x) for x in (mod.get("related_to") or []) if dir_of(x)],
        }
    index = {
        "schema_version": 1,
        "locale": "zh-CN" if paths.locale == "zh" else "en",
        "branch": branch,
        "nodes_managed": True,
        "exported_at": now_iso(),
        "modules": index_modules,
    }
    paths.knowledge_dir.mkdir(parents=True, exist_ok=True)
    (paths.knowledge_dir / "_index.yaml").write_text(
        "# 知识卡导出索引文件\n" + yaml.safe_dump(index, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    cards = len(plan.get("cards", []))
    return f"_index.yaml + {len(index_modules)} 个 _module.yaml（卡片 {cards} 张）"
