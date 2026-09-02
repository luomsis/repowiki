"""Command orchestration: next / check / release / status.

``check`` is the heart of the loop: it validates agent output per task kind,
auto-fixes deterministic defects in place, flips status, and — for planning
tasks (catalog, knowledge-plan) — expands the follow-up task set.
"""

from __future__ import annotations

import json
import os
import socket

from .catalog import flatten
from .cli import ConflictError, UsageError
from .paths import WikiPaths
from . import tasks as task_builders
from .scanner import scan
from .state import TaskStore
from .validate import (
    check_knowledge_card,
    check_knowledge_module,
    check_knowledge_plan,
    check_overview,
    check_page,
    check_catalog,
)


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _task_payload(paths: WikiPaths, task: dict) -> dict:
    spec_path = paths.task_spec(task["id"])
    instructions = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
    return {
        "id": task["id"],
        "kind": task["kind"],
        "phase": task["phase"],
        "title": task["title"],
        "status": task["status"],
        "output": task["output"],
        "spec_path": str(spec_path),
        "instructions": instructions,
    }


def run_next(paths: WikiPaths, claim: bool, batch: int, worker: str | None, as_json: bool) -> int:
    store = TaskStore(paths)
    if not paths.index_file.exists():
        raise UsageError("尚未规划任务，请先运行 `repowiki plan <repo>`")
    worker = worker or _worker_id()
    ready = store.ready_tasks(limit=batch if claim else max(batch, 1))
    claimed: list[dict] = []
    if claim:
        for task in ready:
            try:
                claimed.append(store.claim(task["id"], worker))
            except ConflictError:
                continue  # lost the race; try the next one
            if len(claimed) >= batch:
                break
        result_tasks = claimed
    else:
        result_tasks = ready

    payload = [_task_payload(paths, t) for t in result_tasks]
    stats = store.stats()
    data = store.load()
    busy = sum(
        1 for t in data["tasks"].values()
        if t["status"] == "in_progress"
        and not (t["id"] in {s["id"] for s in stats["stale_claims"]})
    )
    out = {
        "ok": True,
        "claimed": claim,
        "tasks": payload,
        "busy": busy,
        "progress": {"total": stats["total"], "by_status": stats["by_status"], "current_phase": stats["current_phase"]},
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if not payload:
            hint = f"，{busy} 个任务执行中（稍后重试）" if busy else ""
            print(f"当前无可领取任务{hint}（共 {stats['total']} 个任务，状态 {stats['by_status']}）")
        for t in payload:
            print(f"[{t['kind']}] {t['id']}  {t['title']}")
            print(f"  规格: {t['spec_path']}")
            print(f"  输出: {t['output']}")
    return 0


def run_release(paths: WikiPaths, task_id: str, force: bool, as_json: bool) -> int:
    store = TaskStore(paths)
    task = store.release(task_id, force=force)
    if as_json:
        print(json.dumps({"ok": True, "released": task_id, "status": task["status"]}, ensure_ascii=False))
    else:
        print(f"已释放任务 {task_id} → pending")
    return 0


def run_status(paths: WikiPaths, as_json: bool) -> int:
    store = TaskStore(paths)
    stats = store.stats()
    if as_json:
        print(json.dumps({"ok": True, **stats}, ensure_ascii=False, indent=2))
    else:
        print(f"任务总数 {stats['total']}  当前阶段 {stats['current_phase']}")
        for status, n in sorted(stats["by_status"].items()):
            print(f"  {status}: {n}")
        for f in stats["failed"]:
            print(f"  ✗ failed: {f['id']} {f['title']}")
        for e in stats["exhausted"]:
            print(f"  ⛔ exhausted: {e['id']} {e['title']}（已试 {e['attempts']} 次，`release --task {e['id']} --force` 可重置）")
        for s in stats["stale_claims"]:
            print(f"  ⏰ stale: {s['id']}（worker {s['worker']}，心跳 {s['heartbeat_at']}）")
    return 0


def run_touch(paths: WikiPaths, task_id: str, worker: str | None, as_json: bool) -> int:
    store = TaskStore(paths)
    store.touch(task_id, worker=worker)
    if as_json:
        print(json.dumps({"ok": True, "touched": task_id}, ensure_ascii=False))
    else:
        print(f"✓ 已续期任务 {task_id} 的认领")
    return 0


# --- check ---

def run_check(paths: WikiPaths, task_id: str | None, as_json: bool,
              select_all: bool = False, worker: str | None = None,
              force: bool = False) -> int:
    store = TaskStore(paths)
    data = store.load()
    if not data["tasks"]:
        raise UsageError("没有任务，请先运行 `repowiki plan <repo>`")

    if task_id:
        if task_id not in data["tasks"]:
            raise UsageError(f"任务不存在: {task_id}")
        targets = [task_id]
    elif select_all:
        targets = [
            tid for tid, t in data["tasks"].items()
            if t["status"] in ("in_progress", "failed")
        ]
    else:
        raise UsageError("请指定 --task <id>（单任务校验）或 --all（检查全部 in_progress/failed，用于崩溃恢复）")

    if not targets:
        _emit_check(as_json, ok=True, results=[], note="没有待检查任务（无 in_progress/failed）")
        return 0

    # claim ownership guard: refuse to flip tasks held by a different live worker
    if worker and not force:
        for tid in targets:
            t = data["tasks"][tid]
            if t["status"] == "in_progress":
                try:
                    held = (store._claim_dir(tid) / "worker").read_text(encoding="utf-8").strip()
                except OSError:
                    held = ""
                if held and held != worker:
                    raise ConflictError(
                        f"任务 {tid} 由 {held} 认领；如确要代为校验请加 --force"
                    )

    inv = scan(paths.repo_root)
    results = []
    all_ok = True
    for tid in targets:
        task = data["tasks"][tid]
        if task["status"] == "done":
            # done is terminal (its spec may already be purged). Report only —
            # never flip status, otherwise the task becomes unexecutable.
            r = _check_readonly(paths, task, inv)
            results.append(r)
            all_ok = all_ok and r["ok"]
            continue
        r = _check_one(paths, store, task, inv)
        if r["status"] == "in_progress":
            store.heartbeat(tid)  # validating a task also refreshes its claim
        results.append(r)
        all_ok = all_ok and r["ok"]

    _emit_check(as_json, ok=all_ok, results=results)
    return 0 if all_ok else 1


def _check_readonly(paths: WikiPaths, task: dict, inv) -> dict:
    """Validate a done task without touching its status."""
    base = {"id": task["id"], "kind": task["kind"], "title": task["title"], "status": "done"}
    out = paths.root / task["output"]
    exists = out.is_dir() if task["kind"] == "knowledge_module" else out.is_file()
    if not exists:
        return {**base, "ok": False, "readonly": True,
                "errors": [f"产出已不存在: {task['output']}（如需重建请用 update 或 plan --replan）"]}
    if task["kind"] in ("page", "page_update"):
        from .validate import check_page

        raw = out.read_text(encoding="utf-8")
        res = check_page(raw, task["title"].replace("（增量更新）", ""), paths.repo_root,
                         is_update=(task["kind"] == "page_update"))
        return {**base, "ok": res.ok, "readonly": True, "errors": res.errors,
                "fixed": [], "warnings": res.warnings,
                "note": "done 为终态，此结果仅供参考，状态未改变"}
    return {**base, "ok": True, "readonly": True, "errors": [], "fixed": [],
            "warnings": [], "note": "done 为终态，产出存在（不做内容重校验）"}


def _emit_check(as_json: bool, ok: bool, results: list[dict], note: str = "") -> None:
    if as_json:
        print(json.dumps({"ok": ok, "results": results, "note": note}, ensure_ascii=False, indent=2))
        return
    if note:
        print(note)
    for r in results:
        mark = "✓" if r["ok"] else "✗"
        print(f"{mark} {r['id']} {r['title']} → {r['status']}")
        for e in r.get("errors", []):
            print(f"    错误: {e}")
        for f in r.get("fixed", []):
            print(f"    已修复: {f}")
        for w in r.get("warnings", []):
            print(f"    警告: {w}")


def _check_one(paths: WikiPaths, store: TaskStore, task: dict, inv) -> dict:
    kind = task["kind"]
    tid = task["id"]
    base = {"id": tid, "kind": kind, "title": task["title"]}

    if kind in ("catalog", "knowledge_plan"):
        return _check_plan_task(paths, store, task, inv, base)

    if kind in ("page", "page_update", "overview", "knowledge_card"):
        out_file = paths.root / task["output"]
        if not out_file.is_file():
            store.update(tid, status="failed")
            return {**base, "ok": False, "status": "failed",
                    "errors": [f"输出文件不存在: {task['output']}（按任务规格写入该路径）"]}
        raw = out_file.read_text(encoding="utf-8")
        if kind == "overview":
            repo_name = json.loads(paths.catalog_file.read_text(encoding="utf-8")).get("repo_name", "")
            res = check_overview(raw, repo_name)
        elif kind == "knowledge_card":
            plan = _load_json(paths.knowledge_plan_file) or {}
            card = next(
                (c for c in plan.get("cards", []) if c.get("id") == tid), {}
            )
            res = check_knowledge_card(raw, card.get("title", task["title"]), card.get("category", ""), paths.repo_root)
        else:
            res = check_page(raw, task["title"].replace("（增量更新）", ""), paths.repo_root, is_update=(kind == "page_update"))
        if res.fixed and res.text != raw:
            out_file.write_text(res.text, encoding="utf-8")
        status = "done" if res.ok else "failed"
        store.update(tid, status=status)
        return {**base, "ok": res.ok, "status": status, "errors": res.errors, "fixed": res.fixed, "warnings": res.warnings}

    if kind == "knowledge_module":
        out_dir = paths.root / task["output"]
        res = check_knowledge_module(out_dir)
        status = "done" if res.ok else "failed"
        store.update(tid, status=status)
        return {**base, "ok": res.ok, "status": status, "errors": res.errors, "fixed": res.fixed}

    store.update(tid, status="failed")
    return {**base, "ok": False, "status": "failed", "errors": [f"未知任务类型 {kind}"]}


def _load_json(path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"__parse_error__": str(e)}


def _check_plan_task(paths: WikiPaths, store: TaskStore, task: dict, inv, base: dict) -> dict:
    tid = task["id"]
    if tid == "catalog":
        plan_file, expand = paths.catalog_file, _expand_pages
    else:
        plan_file, expand = paths.knowledge_plan_file, _expand_knowledge

    data = _load_json(plan_file)
    if data is None:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": [f"规划文件不存在或 JSON 解析失败: {plan_file}"]}
    if "__parse_error__" in data:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": [f"JSON 解析失败: {data['__parse_error__']}"]}

    if tid == "catalog":
        errors, warnings = check_catalog(data, inv.known_paths())
    else:
        errors, warnings = check_knowledge_plan(data, inv.known_paths())

    if errors:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": errors, "warnings": warnings}

    added = expand(paths, store, data, inv)
    store.update(tid, status="done")
    return {**base, "ok": True, "status": "done", "warnings": warnings,
            "expanded_tasks": added}


def _expand_pages(paths: WikiPaths, store: TaskStore, catalog: dict, inv) -> list[str]:
    nodes = flatten(catalog)
    return store.add_tasks(task_builders.build_page_tasks(paths, nodes, inv))


def _expand_knowledge(paths: WikiPaths, store: TaskStore, plan: dict, inv) -> list[str]:
    return store.add_tasks(task_builders.build_knowledge_tasks(paths, plan))
