"""Task state store: status machine, atomic claiming, stale reclaim.

Concurrency safety comes from one primitive: ``os.mkdir`` of a per-task
claim directory (atomic, fails if exists). Index updates merge only the
touched task entry to shrink read-modify-write windows.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .cli import ConflictError
from .paths import WikiPaths

DEFAULT_STALE_SECONDS = 45 * 60


def max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("REPOWIKI_MAX_ATTEMPTS", "3")))
    except ValueError:
        return 3


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(iso: str) -> float:
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return 0.0


def new_task(task_id: str, kind: str, phase: int, title: str, output: str) -> dict:
    return {
        "id": task_id,
        "kind": kind,
        "phase": phase,
        "title": title,
        "status": "pending",
        "output": output,
        "spec": f"state/tasks/{task_id}.md",
        "attempts": 0,
        "claimed_at": None,
        "heartbeat_at": None,
        "worker": None,
        "created_at": now_iso(),
    }


class TaskStore:
    def __init__(self, paths: WikiPaths, stale_seconds: int | None = None):
        self.paths = paths
        self.stale_seconds = stale_seconds or int(os.environ.get("REPOWIKI_STALE_SECONDS", DEFAULT_STALE_SECONDS))

    # --- persistence ---

    def load(self) -> dict:
        f = self.paths.index_file
        if not f.exists():
            return {"tasks": {}, "created_at": now_iso()}
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"tasks": {}, "created_at": now_iso()}
        data.setdefault("tasks", {})
        return data

    def _save_atomic(self, data: dict) -> None:
        f = self.paths.index_file
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f".{f.name}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, f)

    def _merge_task(self, task: dict) -> None:
        """Re-read index, update only this task entry, write atomically."""
        data = self.load()
        data["tasks"][task["id"]] = task
        self._save_atomic(data)

    def add_tasks(self, records: list[dict]) -> list[str]:
        """Insert new tasks; existing ids are skipped. Returns added ids."""
        added: list[str] = []
        data = self.load()
        for rec in records:
            if rec["id"] not in data["tasks"]:
                data["tasks"][rec["id"]] = rec
                added.append(rec["id"])
        self._save_atomic(data)
        return added

    def replace_all(self, records: list[dict]) -> None:
        self._save_atomic({"tasks": {r["id"]: r for r in records}, "created_at": now_iso()})

    def get(self, task_id: str) -> dict | None:
        return self.load()["tasks"].get(task_id)

    def update(self, task_id: str, **fields) -> dict | None:
        data = self.load()
        task = data["tasks"].get(task_id)
        if not task:
            return None
        task.update(fields)
        self._save_atomic(data)
        return task

    # --- readiness / priority ---

    def current_phase(self, data: dict | None = None) -> int | None:
        """Lowest phase that still has unfinished (not done) tasks, else None."""
        data = data or self.load()
        phases = [t["phase"] for t in data["tasks"].values() if t["status"] != "done"]
        return min(phases) if phases else None

    def ready_tasks(self, limit: int = 1) -> list[dict]:
        """Tasks claimable now: pending/failed in the current open phase.

        Failed tasks whose attempts reached the cap are excluded (exhausted);
        they need an explicit `release --force` reset before retrying."""
        data = self.load()
        phase = self.current_phase(data)
        if phase is None:
            return []
        cap = max_attempts()
        ready = [
            t for t in data["tasks"].values()
            if t["phase"] == phase and t["status"] in ("pending", "failed")
            and not (t["status"] == "failed" and t["attempts"] >= cap)
        ]
        order = {tid: i for i, tid in enumerate(data["tasks"])}
        ready.sort(key=lambda t: (t["attempts"], t["phase"], order[t["id"]]))
        return ready[:limit]

    # --- claiming ---

    def _claim_dir(self, task_id: str) -> Path:
        return self.paths.claims_dir / task_id

    def _claim_age(self, claim_dir: Path) -> float:
        """Age of the claim directory itself (mtime), NOT the ts file inside:
        the ts file is written after mkdir, so a just-created claim would
        otherwise look infinitely old and get stolen while still fresh."""
        try:
            return time.time() - claim_dir.stat().st_mtime
        except OSError:
            return float("inf")

    def _try_mkdir_claim(self, task_id: str, worker: str) -> bool:
        """Create claims/<id>/ atomically, stealing it first if stale."""
        self.paths.claims_dir.mkdir(parents=True, exist_ok=True)
        cd = self._claim_dir(task_id)
        for _attempt in range(3):
            try:
                os.mkdir(cd)
            except FileExistsError:
                if self._claim_age(cd) < self.stale_seconds:
                    return False  # live claim held by someone else
                # stale: rename it away (only one racer succeeds) and retry
                zombie = cd.with_name(f".stale-{task_id}-{uuid.uuid4().hex[:6]}")
                try:
                    os.rename(cd, zombie)
                except OSError:
                    continue  # another racer already stole it; loop retries mkdir
            else:
                try:
                    (cd / "worker").write_text(worker, encoding="utf-8")
                    (cd / "ts").write_text(now_iso(), encoding="utf-8")
                except OSError:
                    pass
                return True
        return False

    def claim(self, task_id: str, worker: str) -> dict:
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        if task["status"] == "done":
            raise ConflictError(f"任务 {task_id} 已完成，无需认领")
        if not self._try_mkdir_claim(task_id, worker):
            raise ConflictError(f"任务 {task_id} 正被其他 worker 执行中（认领未过期）")
        task.update(
            status="in_progress",
            worker=worker,
            claimed_at=now_iso(),
            heartbeat_at=now_iso(),
            attempts=task["attempts"] + 1,
        )
        self._merge_task(task)
        return task

    def release(self, task_id: str, force: bool = False) -> dict:
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        cap = max_attempts()
        if task["status"] == "failed" and task["attempts"] >= cap:
            # exhausted poison task: --force is the explicit human reset
            if not force:
                raise ConflictError(
                    f"任务 {task_id} 已重试 {task['attempts']} 次仍未通过（上限 {cap}）。"
                    "确要重置请加 --force"
                )
            task.update(status="pending", attempts=0, worker=None,
                        claimed_at=None, heartbeat_at=None)
            self._merge_task(task)
            return task
        if task["status"] != "in_progress":
            raise ConflictError(f"任务 {task_id} 状态为 {task['status']}，无需释放")
        cd = self._claim_dir(task_id)
        try:
            held_by = (cd / "worker").read_text(encoding="utf-8").strip()
        except OSError:
            held_by = ""
        if held_by and held_by != (task.get("worker") or "") and not force:
            raise ConflictError(f"任务 {task_id} 由 {held_by} 认领，需 --force 才能释放")
        if cd.exists():
            zombie = cd.with_name(f".released-{task_id}-{uuid.uuid4().hex[:6]}")
            try:
                os.rename(cd, zombie)
            except OSError:
                pass
        task.update(status="pending", worker=None, claimed_at=None, heartbeat_at=None)
        self._merge_task(task)
        return task

    def heartbeat(self, task_id: str) -> None:
        cd = self._claim_dir(task_id)
        now = now_iso()
        try:
            (cd / "ts").write_text(now, encoding="utf-8")
            os.utime(cd)  # keep the dir mtime (staleness signal) fresh too
        except OSError:
            pass
        self.update(task_id, heartbeat_at=now)

    def touch(self, task_id: str, worker: str | None = None) -> dict:
        """Worker-side heartbeat: call periodically while executing a long task
        so the claim is not stolen as stale. Fails on tasks not in flight."""
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        if task["status"] != "in_progress":
            raise ConflictError(f"任务 {task_id} 状态为 {task['status']}，无需续期")
        if worker:
            try:
                held = (self._claim_dir(task_id) / "worker").read_text(encoding="utf-8").strip()
            except OSError:
                held = ""
            if held and held != worker:
                raise ConflictError(f"任务 {task_id} 由 {held} 认领，不是 {worker}")
        self.heartbeat(task_id)
        return self.get(task_id)

    def cleanup_runtime(self) -> list[str]:
        """Drop runtime artifacts after successful finalize: claim dirs and
        task specs. Planning artifacts (index/catalog/knowledge) are kept —
        `update` and idempotent `plan` depend on them."""
        import shutil

        removed = []
        for d in (self.paths.claims_dir, self.paths.tasks_dir):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                removed.append(d.name)
        return removed


    # --- reporting ---

    def stats(self) -> dict:
        data = self.load()
        tasks = list(data["tasks"].values())
        by_status: dict[str, int] = {}
        for t in tasks:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        stale = [
            {"id": t["id"], "worker": t["worker"], "heartbeat_at": t["heartbeat_at"]}
            for t in tasks
            if t["status"] == "in_progress"
            and t.get("heartbeat_at")
            and (time.time() - _ts(t["heartbeat_at"])) > self.stale_seconds
        ]
        failed = [
            {"id": t["id"], "title": t["title"]}
            for t in tasks if t["status"] == "failed"
        ]
        cap = max_attempts()
        exhausted = [
            {"id": t["id"], "title": t["title"], "attempts": t["attempts"]}
            for t in tasks
            if t["status"] == "failed" and t["attempts"] >= cap
        ]
        return {
            "total": len(tasks),
            "by_status": by_status,
            "current_phase": self.current_phase(data),
            "failed": failed,
            "exhausted": exhausted,
            "stale_claims": stale,
        }


def run_clean(paths: WikiPaths, as_json: bool = False) -> int:
    """Remove state/ entirely (opt-in). The wiki output under .repowiki/ is kept."""
    import json as _json
    import shutil

    if not paths.state_dir.exists():
        msg = "state/ 不存在，无需清理"
        if as_json:
            print(_json.dumps({"ok": True, "removed": False, "detail": msg}, ensure_ascii=False))
        else:
            print(msg)
        return 0
    shutil.rmtree(paths.state_dir)
    msg = (
        f"已删除 {paths.state_dir}。"
        "失去的能力：增量更新（update）、断点续跑、plan 幂等（重跑 plan 将全新规划）。"
        "wiki 产出（zh/ 与 knowledge/）未受影响。"
    )
    if as_json:
        print(_json.dumps({"ok": True, "removed": True, "detail": msg}, ensure_ascii=False))
    else:
        print(f"✓ {msg}")
    return 0
