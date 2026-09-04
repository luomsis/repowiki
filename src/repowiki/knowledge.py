"""``repowiki knowledge``: append the knowledge-card task set, and aggregate
knowledge outputs (_index.yaml / _module.yaml) at finalize time.
"""

from __future__ import annotations


import yaml

from .errors import UsageError
from .gitutil import run_git
from .output import emit
from .paths import WikiPaths, sanitize_component
from . import tasks as task_builders
from .scanner import scan
from .state import TaskStore, now_iso


def run_knowledge(paths: WikiPaths, as_json: bool) -> int:
    store = TaskStore(paths)
    data = store.load()
    if not data["tasks"]:
        raise UsageError("请先运行 `repowiki plan <repo>`")
    added = store.add_tasks([task_builders.build_knowledge_plan_task(paths, scan(paths.repo_root))])
    result = {
        "ok": True,
        "added": added,
        "note": "knowledge-plan 任务已就绪，领取执行后 check 会自动展开模块/卡片任务",
    }
    emit(result, _knowledge_human, as_json)
    return 0


def _knowledge_human(r: dict) -> str:
    head = "已添加 knowledge-plan 任务" if r["added"] else "knowledge 任务集已存在"
    return f"{head}\n{r['note']}"
    return 0


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
            "source_files": [],
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
            "source_files": [],
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
