"""``repowiki update``: map git changes to incremental page_update tasks."""

from __future__ import annotations

import json
from typing import Callable

from .catalog import flatten
from .errors import UsageError
from .gitutil import run_git
from .knowledge import scope_covers
from .output import emit
from .paths import WikiPaths
from . import tasks as task_builders
from .scanner import scan
from .state import TaskStore


def _git_diff(repo, since: str, dirty: bool = False) -> list[str] | None:
    """Changed files since ``since`` — committed only by default; with
    ``dirty`` also uncommitted (staged + unstaged) and untracked files."""
    spec = since if dirty else f"{since}..HEAD"
    out = run_git(repo, "diff", "--name-only", spec, timeout=60)
    if out is None:
        return None
    changed = {l.strip() for l in out.splitlines() if l.strip()}
    if dirty:
        others = run_git(repo, "ls-files", "--others", "--exclude-standard", timeout=60)
        if others:
            changed |= {l.strip() for l in others.splitlines() if l.strip()}
    return sorted(changed)


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


def _load_knowledge_plan(paths: WikiPaths) -> dict | None:
    if not paths.knowledge_plan_file.exists():
        return None
    try:
        return json.loads(paths.knowledge_plan_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _map_knowledge(plan: dict, existing: dict, changed_set: set[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Cards whose source_files changed + modules whose scope was touched.

    Returns (cards, modules, skipped) where each entry is (plan_item,
    original_task, hit_files); skipped lists plan items without an original
    task record (plan written but never expanded).
    """
    cards: list = []
    modules: list = []
    skipped: list = []
    for card in plan.get("cards", []):
        if not isinstance(card, dict):
            continue
        orig = existing.get(card.get("id"))
        if not isinstance(orig, dict):
            skipped.append(card)
            continue
        hits = sorted(set(card.get("source_files") or []) & changed_set)
        if hits:
            cards.append((card, orig, hits))
    for mod in plan.get("modules", []):
        if not isinstance(mod, dict):
            continue
        orig = existing.get(mod.get("id"))
        if not isinstance(orig, dict):
            skipped.append(mod)
            continue
        scopes = [s for s in (mod.get("scope") or []) if isinstance(s, str)]
        hits = sorted(p for p in changed_set if any(scope_covers(s, p) for s in scopes))
        if hits:
            modules.append((mod, orig, hits))
    return cards, modules, skipped


def run_update(paths: WikiPaths, since: str | None, as_json: bool, dirty: bool = False) -> int:
    if not (paths.repo_root / ".git").exists():
        raise UsageError("增量更新需要 git 仓库（未发现 .git）")
    since = since or _last_commit_id(paths)
    if not since:
        raise UsageError("无法确定增量起点：metadata 中无 last_commit_id，请用 --since <commit> 指定")
    if not paths.catalog_file.exists():
        raise UsageError("state/catalog.json 不存在，请先完成首次生成")

    changed = _git_diff(paths.repo_root, since, dirty=dirty)
    if changed is None:
        raise UsageError(f"git diff {since}..HEAD 失败（起点 commit 是否存在？）")
    changed_set = set(changed)
    if not changed_set:
        emit({"ok": True, "dirty": dirty, "changed": 0, "created_tasks": []},
             lambda r: "自上次生成以来无变更", as_json)
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

    def queue_or_rearm(tid: str, build) -> None:
        """Fresh id → new task; done id from an earlier finalize epoch →
        regenerate its spec and re-arm it (otherwise the second update round
        would silently do nothing); still in flight → leave it alone."""
        prev = existing.get(tid)
        if prev is not None and prev["status"] in ("pending", "failed", "in_progress"):
            return
        spec_task = build()
        if prev is None:
            records.append(spec_task)
        else:
            store.update(tid, status="pending", attempts=0,
                         worker=None, claimed_at=None, heartbeat_at=None)
            rearmed.append(tid)

    records: list[dict] = []
    rearmed: list[str] = []
    for n in affected:
        queue_or_rearm(
            f"{n.id}-update",
            lambda n=n: task_builders.build_update_task(
                paths, n, sorted(changed_set & set(n.dependent_files)), inv),
        )

    # overview 描述仓库整体——只要命中了任何页面就一并刷新
    if affected:
        queue_or_rearm(
            "overview-update",
            lambda: task_builders.build_overview_update_task(
                paths, catalog.get("repo_name") or paths.repo_root.name, nodes,
                sorted(changed_set), inv),
        )

    # knowledge cards / modules: map changed files against the knowledge plan
    knowledge_plan = _load_knowledge_plan(paths)
    knowledge_warnings: list[str] = []
    affected_cards: list[dict] = []
    affected_modules: list[dict] = []
    if knowledge_plan is None:
        pass  # no knowledge set on this repo — nothing to refresh
    elif not isinstance(knowledge_plan, dict):
        knowledge_warnings.append("state/knowledge.json 解析失败，跳过知识卡片联动")
    else:
        cards, modules, skipped = _map_knowledge(knowledge_plan, existing, changed_set)
        for card, orig, hits in cards:
            affected_cards.append(card)
            queue_or_rearm(
                f"{card['id']}-update",
                lambda c=card, o=orig, h=hits: task_builders.build_knowledge_card_update_task(
                    paths, o, c, h, inv),
            )
        for mod, orig, hits in modules:
            affected_modules.append(mod)
            queue_or_rearm(
                f"{mod['id']}-update",
                lambda m=mod, o=orig, h=hits: task_builders.build_knowledge_module_update_task(
                    paths, o, m, h),
            )
        if skipped:
            knowledge_warnings.append(
                f"{len(skipped)} 个知识规划项尚无对应任务记录（knowledge-plan 未展开），已跳过联动"
            )
    added = store.add_tasks(records)

    warnings = knowledge_warnings
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
        "dirty": dirty,
        "changed_files": len(changed_set),
        "affected_pages": [n.id for n in affected],
        "affected_cards": [c.get("id", "") for c in affected_cards],
        "affected_modules": [m.get("id", "") for m in affected_modules],
        "created_tasks": added,
        "rearmed_tasks": rearmed,
        "overview_queued": bool(affected),
        "warnings": warnings,
    }
    emit(result, _update_human(affected, affected_cards, affected_modules), as_json)
    return 0


def _update_human(affected: list, affected_cards: list, affected_modules: list) -> Callable[[dict], str]:
    # 页面标题只活在 FlatNode 里，不进 JSON 契约——以闭包带入
    def human(r: dict) -> str:
        scope = "（含未提交/未跟踪变更）" if r.get("dirty") else ""
        lines = [f"自 {r['since'][:12]} 以来变更 {r['changed_files']} 个文件{scope}，命中 {len(affected)} 个页面"]
        lines += [f"  → {n.id} {n.title}" for n in affected]
        if affected_cards:
            lines.append(f"命中 {len(affected_cards)} 张知识卡片")
            lines += [f"  → 卡片 {c.get('id')} {c.get('title', '')}" for c in affected_cards]
        if affected_modules:
            lines.append(f"命中 {len(affected_modules)} 个知识模块")
            lines += [f"  → 模块 {m.get('id')} {m.get('title', '')}" for m in affected_modules]
        lines += [f"  ⚠ {w}" for w in r["warnings"]]
        if r.get("overview_queued"):
            lines.append("总览页已纳入本轮刷新（overview-update 任务：变更同步到定位概述与章节导航）")
        if r.get("rearmed_tasks"):
            lines.append(f"已重新武装 {len(r['rearmed_tasks'])} 个上一轮的更新任务（规格按最新变更重写）")
        if r["created_tasks"]:
            lines.append(f"已创建 {len(r['created_tasks'])} 个增量更新任务，执行 `repowiki next <repo> --claim` 领取")
        return "\n".join(lines)
    return human


def run_stale(paths: WikiPaths, since: str | None, fail_if_stale: bool, as_json: bool,
              dirty: bool = False) -> int:
    """Read-only staleness report: what would ``update`` turn into tasks?

    Same diff → affected mapping as ``update`` (catalog ``dependent_files``
    incl. ancestor chains + knowledge plan linkage), but nothing is written —
    no tasks, no state mutation. Built for CI gates: ``--fail-if-stale``
    exits 1 when any page/card/module is affected.
    """
    if not (paths.repo_root / ".git").exists():
        raise UsageError("stale 检查需要 git 仓库（未发现 .git）")
    since = since or _last_commit_id(paths)
    if not since:
        raise UsageError("无法确定对比起点：metadata 中无 last_commit_id，请用 --since <ref> 指定")
    if not paths.catalog_file.exists():
        raise UsageError("state/catalog.json 不存在，请先完成首次生成")

    changed = _git_diff(paths.repo_root, since, dirty=dirty)
    if changed is None:
        raise UsageError(f"git diff {since}..HEAD 失败（起点 ref 是否存在？）")
    changed_set = set(changed)

    affected: list = []
    affected_cards: list = []
    affected_modules: list = []
    if changed_set:
        try:
            catalog = json.loads(paths.catalog_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise UsageError(
                f"state/catalog.json 损坏（{e}）：可手工修复该文件，或 `repowiki plan --replan` 重新规划"
            ) from e
        nodes = flatten(catalog, paths.locale)
        affected = map_affected(nodes, changed_set)
        knowledge_plan = _load_knowledge_plan(paths)
        if isinstance(knowledge_plan, dict):
            existing = TaskStore(paths).load()["tasks"]
            cards, modules, _ = _map_knowledge(knowledge_plan, existing, changed_set)
            affected_cards = [card for card, _orig, _hits in cards]
            affected_modules = [mod for mod, _orig, _hits in modules]

    result = {
        "ok": True,
        "since": since,
        "dirty": dirty,
        "changed_files": len(changed_set),
        "affected_pages": [n.id for n in affected],
        "affected_cards": [c.get("id", "") for c in affected_cards],
        "affected_modules": [m.get("id", "") for m in affected_modules],
        "stale": bool(affected or affected_cards or affected_modules),
    }
    emit(result, _stale_human(affected, affected_cards, affected_modules), as_json)
    if result["stale"] and fail_if_stale:
        return 1
    return 0


def _stale_human(affected: list, affected_cards: list, affected_modules: list) -> Callable[[dict], str]:
    def human(r: dict) -> str:
        scope = "（含未提交/未跟踪变更）" if r.get("dirty") else ""
        if not r["stale"]:
            return f"自 {r['since'][:12]} 以来无受影响页面{scope}，wiki 与代码同步"
        lines = [
            f"自 {r['since'][:12]} 以来变更 {r['changed_files']} 个文件{scope}，wiki 已过期："
            f"{len(affected)} 个页面 / {len(affected_cards)} 张卡片 / {len(affected_modules)} 个模块"
        ]
        lines += [f"  → {n.id} {n.title}" for n in affected]
        lines += [f"  → 卡片 {c.get('id')} {c.get('title', '')}" for c in affected_cards]
        lines += [f"  → 模块 {m.get('id')} {m.get('title', '')}" for m in affected_modules]
        lines.append("（只读检查：未创建任何任务；执行 `repowiki update <repo>` 生成增量更新任务）")
        return "\n".join(lines)
    return human
