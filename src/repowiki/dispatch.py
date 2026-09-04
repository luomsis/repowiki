"""Command orchestration: next / check / release / status.

``check`` is the heart of the loop: it validates agent output per task kind,
auto-fixes deterministic defects in place, flips status, and — for planning
tasks (catalog, knowledge-plan) — expands the follow-up task set.
"""

from __future__ import annotations

import json
import os
import socket

from .catalog import flatten, validate_catalog
from .errors import ConflictError, UsageError
from .output import emit
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


def run_next(paths: WikiPaths, claim: bool, worker: str | None, as_json: bool) -> int:
    store = TaskStore(paths)
    if not paths.index_file.exists():
        raise UsageError("尚未规划任务，请先运行 `repowiki plan <repo>`")
    worker = worker or _worker_id()
    result_tasks: list[dict] = []
    if claim:
        # 队列是纯 FIFO 拉取，一次只发放一个任务（worker 契约：一次只持有一个认领）
        for task in store.ready_tasks(limit=1):
            try:
                result_tasks.append(store.claim(task["id"], worker))
            except ConflictError:
                pass  # lost the race; the next `next` will re-pick
    else:
        result_tasks = store.ready_tasks(limit=1)

    payload = [_task_payload(paths, t) for t in result_tasks]
    stats = store.stats()
    out = {
        "ok": True,
        "claimed": claim,
        "tasks": payload,
        "busy": stats["busy"],
        "progress": {"total": stats["total"], "by_status": stats["by_status"], "current_phase": stats["current_phase"]},
    }
    emit(out, _next_human, as_json)
    return 0


def _next_human(out: dict) -> str:
    lines = []
    if not out["tasks"]:
        hint = f"，{out['busy']} 个任务执行中（稍后重试）" if out["busy"] else ""
        lines.append(f"当前无可领取任务{hint}（共 {out['progress']['total']} 个任务，状态 {out['progress']['by_status']}）")
    for t in out["tasks"]:
        lines += [f"[{t['kind']}] {t['id']}  {t['title']}",
                  f"  规格: {t['spec_path']}",
                  f"  输出: {t['output']}"]
    return "\n".join(lines)


def run_release(paths: WikiPaths, task_id: str, force: bool, as_json: bool) -> int:
    store = TaskStore(paths)
    task = store.release(task_id, force=force)
    emit({"ok": True, "released": task_id, "status": task["status"]},
         lambda r: f"已释放任务 {r['released']} → pending", as_json)
    return 0


def run_status(paths: WikiPaths, as_json: bool) -> int:
    store = TaskStore(paths)
    stats = store.stats()
    emit({"ok": True, **stats}, _status_human, as_json)
    return 0


def _status_human(out: dict) -> str:
    lines = [f"任务总数 {out['total']}  当前阶段 {out['current_phase']}"]
    for status, n in sorted(out["by_status"].items()):
        lines.append(f"  {status}: {n}")
    for f in out["failed"]:
        lines.append(f"  ✗ failed: {f['id']} {f['title']}")
    for e in out["exhausted"]:
        lines.append(f"  ⛔ exhausted: {e['id']} {e['title']}（已试 {e['attempts']} 次，`release --task {e['id']} --force` 可重置）")
    for s in out["stale_claims"]:
        lines.append(f"  ⏰ stale: {s['id']}（worker {s['worker']}，心跳 {s['heartbeat_at']}）")
    return "\n".join(lines)


def run_touch(paths: WikiPaths, task_id: str, worker: str | None, as_json: bool) -> int:
    store = TaskStore(paths)
    store.touch(task_id, worker=worker)
    emit({"ok": True, "touched": task_id},
         lambda r: f"✓ 已续期任务 {r['touched']} 的认领", as_json)
    return 0


def run_watch(paths: WikiPaths, interval: float, timeout: float, as_json: bool) -> int:
    """Block until all tasks are done, the pipeline stalls, or timeout.

    Designed for the driving session: spawn background workers, then run
    watch (foreground or background) — its exit code tells the session what
    to do next without any polling logic of its own.
    """
    import time as _time

    store = TaskStore(paths)
    data = store.load()
    if not data["tasks"]:
        raise UsageError("没有任务，请先运行 `repowiki plan <repo>`")

    started = _time.monotonic()
    last_line = ""
    stats = store.stats()

    while True:
        stats = store.stats()
        done = stats["by_status"].get("done", 0)
        total = stats["total"]
        stale_ids = {s["id"] for s in stats["stale_claims"]}
        # stale claims are not "in flight": their worker is gone, the queue
        # will hand those tasks back out — counting them hides real stalls
        in_flight = [
            t for t in store.load()["tasks"].values()
            if t["status"] == "in_progress" and t["id"] not in stale_ids
        ]
        ready = store.ready_tasks(limit=1)

        line = (
            f"[{_time.strftime('%H:%M:%S')}] {done}/{total} done"
            f" · 阶段{stats['current_phase']}"
            f" · 进行中: {', '.join(t['id'] + '(' + (t['worker'] or '?') + ')' for t in in_flight) or '无'}"
            f" · failed {len(stats['failed'])} · exhausted {len(stats['exhausted'])} · stale {len(stale_ids)}"
        )
        if line != last_line:
            if not as_json:
                print(line, flush=True)
            last_line = line

        # terminal: everything done
        if total > 0 and done == total:
            emit({"reason": "completed", "stats": stats},
                 lambda r: f"✓ 全部 {r['stats']['total']} 个任务完成", as_json)
            return 0

        # terminal: stalled — work remains but nothing is running or claimable
        if not in_flight and not ready:
            reason = (
                f"停滞：剩余 {total - done} 个任务未完成，但无执行中且无可领取任务"
                "（通常是 exhausted 毒任务；`repowiki status` 查看详情，`release --force` 可重置）"
            )
            emit({"reason": "stalled", "detail": reason, "stats": stats},
                 lambda r: f"⏹ {r['detail']}", as_json)
            return 1

        if _time.monotonic() - started >= timeout:
            reason = f"超时（{int(timeout)}s）：剩余 {total - done} 个任务未完成"
            emit({"reason": "timeout", "detail": reason, "stats": stats},
                 lambda r: f"⏰ {r['detail']}", as_json)
            return 1

        _time.sleep(interval)


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
        raw = out.read_text(encoding="utf-8")
        res = check_page(raw, task["title"].replace("（增量更新）", ""), paths.repo_root,
                         is_update=(task["kind"] == "page_update"), locale=paths.locale)
        return {**base, "ok": res.ok, "readonly": True, "errors": res.errors,
                "fixed": [], "warnings": res.warnings,
                "note": "done 为终态，此结果仅供参考，状态未改变"}
    return {**base, "ok": True, "readonly": True, "errors": [], "fixed": [],
            "warnings": [], "note": "done 为终态，产出存在（不做内容重校验）"}


def _emit_check(as_json: bool, ok: bool, results: list[dict], note: str = "") -> None:
    emit({"ok": ok, "results": results, "note": note}, _check_human, as_json)


def _check_human(r: dict) -> str:
    lines = [r["note"]] if r["note"] else []
    for res in r["results"]:
        mark = "✓" if res["ok"] else "✗"
        lines.append(f"{mark} {res['id']} {res['title']} → {res['status']}")
        lines += [f"    错误: {e}" for e in res.get("errors", [])]
        lines += [f"    已修复: {f}" for f in res.get("fixed", [])]
        lines += [f"    警告: {w}" for w in res.get("warnings", [])]
    return "\n".join(lines)


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
            try:
                repo_name = json.loads(paths.catalog_file.read_text(encoding="utf-8")).get("repo_name", "")
            except (json.JSONDecodeError, OSError) as e:
                store.update(tid, status="failed")
                return {**base, "ok": False, "status": "failed",
                        "errors": [f"state/catalog.json 无法读取（{e}），无法校验 overview"]}
            res = check_overview(raw, repo_name, locale=paths.locale)
        elif kind == "knowledge_card":
            plan = _load_json(paths.knowledge_plan_file) or {}
            card = next(
                (c for c in plan.get("cards", []) if c.get("id") == tid), {}
            )
            res = check_knowledge_card(raw, card.get("title", task["title"]), card.get("category", ""), paths.repo_root, locale=paths.locale)
        else:
            res = check_page(raw, task["title"].replace("（增量更新）", ""), paths.repo_root,
                             is_update=(kind == "page_update"), locale=paths.locale)
        if res.fixed and res.text != raw:
            out_file.write_text(res.text, encoding="utf-8")
        status = "done" if res.ok else "failed"
        store.update(tid, status=status)
        return {**base, "ok": res.ok, "status": status, "errors": res.errors, "fixed": res.fixed, "warnings": res.warnings}

    if kind == "knowledge_module":
        out_dir = paths.root / task["output"]
        res = check_knowledge_module(out_dir, locale=paths.locale)
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
    plan_file = paths.catalog_file if tid == "catalog" else paths.knowledge_plan_file

    data = _load_json(plan_file)
    if data is None:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": [f"规划文件不存在或 JSON 解析失败: {plan_file}"]}
    if "__parse_error__" in data:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": [f"JSON 解析失败: {data['__parse_error__']}"]}

    if tid == "catalog":
        errors, warnings = validate_catalog(data, inv.known_paths())
    else:
        errors, warnings = check_knowledge_plan(data, inv.known_paths())

    if errors:
        store.update(tid, status="failed")
        return {**base, "ok": False, "status": "failed", "errors": errors, "warnings": warnings}

    if tid == "catalog":
        added = _expand_pages(paths, store, data, inv)
    else:
        added = _expand_knowledge(paths, store, data)
    store.update(tid, status="done")
    return {**base, "ok": True, "status": "done", "warnings": warnings,
            "expanded_tasks": added}


def _expand_pages(paths: WikiPaths, store: TaskStore, catalog: dict, inv) -> list[str]:
    nodes = flatten(catalog, paths.locale)
    return store.add_tasks(task_builders.build_page_tasks(paths, nodes, inv))


def _expand_knowledge(paths: WikiPaths, store: TaskStore, plan: dict) -> list[str]:
    return store.add_tasks(task_builders.build_knowledge_tasks(paths, plan))
