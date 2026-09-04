"""``repowiki update``: map git changes to incremental page_update tasks."""

from __future__ import annotations

import json

from .catalog import flatten
from .errors import UsageError
from .gitutil import run_git
from .paths import WikiPaths
from . import tasks as task_builders
from .scanner import scan
from .state import TaskStore


def _git_diff(repo, since: str) -> list[str] | None:
    out = run_git(repo, "diff", "--name-only", f"{since}..HEAD", timeout=60)
    if out is None:
        return None
    return [l.strip() for l in out.splitlines() if l.strip()]


def _last_commit_id(paths: WikiPaths) -> str | None:
    if not paths.metadata_file.exists():
        return None
    try:
        return json.loads(paths.metadata_file.read_text(encoding="utf-8")).get("wiki_repo", {}).get("last_commit_id")
    except (json.JSONDecodeError, OSError):
        return None


def map_affected(nodes, changed: set[str]) -> list:
    """Nodes whose dependent_files intersect the change set, plus ancestors."""
    by_id = {n.id: n for n in nodes}
    affected: dict[str, None] = {}  # ordered set
    for n in nodes:
        if set(n.dependent_files) & changed:
            cur = n
            while cur and cur.id not in affected:
                affected[cur.id] = None
                cur = by_id.get(cur.parent_id) if cur.parent_id else None
    return [by_id[tid] for tid in affected]


def run_update(paths: WikiPaths, since: str | None, as_json: bool) -> int:
    if not (paths.repo_root / ".git").exists():
        raise UsageError("增量更新需要 git 仓库（未发现 .git）")
    since = since or _last_commit_id(paths)
    if not since:
        raise UsageError("无法确定增量起点：metadata 中无 last_commit_id，请用 --since <commit> 指定")
    if not paths.catalog_file.exists():
        raise UsageError("state/catalog.json 不存在，请先完成首次生成")

    changed = _git_diff(paths.repo_root, since)
    if changed is None:
        raise UsageError(f"git diff {since}..HEAD 失败（起点 commit 是否存在？）")
    changed_set = set(changed)
    if not changed_set:
        print(json.dumps({"ok": True, "changed": 0, "created_tasks": []}, ensure_ascii=False) if as_json else "自上次生成以来无变更")
        return 0

    try:
        catalog = json.loads(paths.catalog_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise UsageError(
            f"state/catalog.json 损坏（{e}）：可手工修复该文件，或 `repowiki plan --replan` 重新规划"
        ) from e
    nodes = flatten(catalog, paths.locale)
    inv = scan(paths.repo_root)
    affected = map_affected(nodes, changed_set)

    store = TaskStore(paths)
    existing = store.load()["tasks"]
    stale_pending = [
        tid for tid, t in existing.items()
        if tid.endswith("-update") and t["status"] in ("pending", "failed", "in_progress")
    ]
    records = []
    for n in affected:
        tid = f"{n.id}-update"
        if tid in existing:
            continue
        records.append(task_builders.build_update_task(paths, n, sorted(changed_set & set(n.dependent_files)), inv))
    added = store.add_tasks(records)

    warnings = []
    if stale_pending:
        warnings.append(
            f"已存在 {len(stale_pending)} 个未完成的增量任务（{', '.join(sorted(stale_pending)[:5])}），"
            "其规格基于旧变更快照，可能过期；建议先完成或 release 后重跑 update"
        )
    covered_top_dirs = {d.split("/")[0] for n in nodes for d in n.dependent_files}
    new_top = {c.split("/")[0] for c in changed_set if c.split("/")[0] not in covered_top_dirs}
    if len(new_top) > 2:
        warnings.append(
            f"出现 {len(new_top)} 个 catalog 未覆盖的新顶级目录（{', '.join(sorted(new_top)[:5])}），建议 `repowiki plan --replan` 全量重规划"
        )

    result = {
        "ok": True,
        "since": since,
        "changed_files": len(changed_set),
        "affected_pages": [n.id for n in affected],
        "created_tasks": added,
        "warnings": warnings,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"自 {since[:12]} 以来变更 {len(changed_set)} 个文件，命中 {len(affected)} 个页面")
        for n in affected:
            print(f"  → {n.id} {n.title}")
        for w in warnings:
            print(f"  ⚠ {w}")
        if added:
            print(f"已创建 {len(added)} 个增量更新任务，执行 `repowiki next <repo> --claim` 领取")
    return 0
