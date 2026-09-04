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

from .errors import ConflictError, StateError, UsageError
from .output import emit
from .paths import WikiPaths

DEFAULT_STALE_SECONDS = 15 * 60


def max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("REPOWIKI_MAX_ATTEMPTS", "3")))
    except ValueError:
        return 3


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exclusive_lock(fh) -> None:
    """Exclusive blocking file lock: fcntl on POSIX, msvcrt on Windows (both stdlib)."""
    try:
        import fcntl
    except ImportError:
        try:
            import msvcrt
        except ImportError as e:  # broken/unusual interpreter build
            raise UsageError(
                "repowiki 需要 fcntl（POSIX）或 msvcrt（Windows）支持的文件锁；当前解释器两者均不可用"
            ) from e
        try:
            fh.seek(0)
            # LK_LOCK blocks ~10s (1 retry/s) before giving up with OSError.
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        except OSError as e:
            raise StateError(
                "state/.index.lock 被其他进程长期占用（约 10 秒未获得锁）；请稍后重试，"
                "或确认持有锁的 repowiki 进程已退出"
            ) from e
    else:
        fcntl.flock(fh, fcntl.LOCK_EX)


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
        except json.JSONDecodeError as e:
            # A corrupt manifest must never masquerade as an empty one: the
            # next read-modify-write transaction would rewrite the index with
            # only the touched task and silently wipe the whole plan.
            raise StateError(
                f"state/index.json 损坏（{e}）。文件已原样保留；"
                "可手工修复该文件恢复任务清单，或确认无需恢复后执行 `repowiki plan --replan --force` 重来"
            ) from e
        data.setdefault("tasks", {})
        return data

    def _save_atomic(self, data: dict) -> None:
        f = self.paths.index_file
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f".{f.name}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, f)

    def _lock(self):
        """Process-level exclusive lock around index read-modify-write."""
        self.paths.state_dir.mkdir(parents=True, exist_ok=True)
        fh = open(self.paths.state_dir / ".index.lock", "a+")
        try:
            _exclusive_lock(fh)
        except BaseException:
            fh.close()
            raise
        return fh

    def _transaction(self, mutate) -> None:
        """Serialize index.json read-modify-write across processes."""
        fh = self._lock()
        try:
            data = self.load()
            mutate(data)
            self._save_atomic(data)
        finally:
            fh.close()

    def _merge_task(self, task: dict) -> None:
        """Update only this task entry inside a transaction."""

        def apply(data: dict) -> None:
            data["tasks"][task["id"]] = task

        self._transaction(apply)

    def add_tasks(self, records: list[dict]) -> list[str]:
        """Insert new tasks; existing ids are skipped. Returns added ids."""
        added: list[str] = []

        def apply(data: dict) -> None:
            added.clear()
            for rec in records:
                if rec["id"] not in data["tasks"]:
                    data["tasks"][rec["id"]] = rec
                    added.append(rec["id"])

        self._transaction(apply)
        return added

    def replace_all(self, records: list[dict]) -> None:
        self._save_atomic({"tasks": {r["id"]: r for r in records}, "created_at": now_iso()})

    def get(self, task_id: str) -> dict | None:
        return self.load()["tasks"].get(task_id)

    def _require_task(self, task_id: str) -> dict:
        task = self.get(task_id)
        if task is None:
            raise UsageError(f"任务不存在: {task_id}（`repowiki status` 可查看全部任务 id）")
        return task

    def update(self, task_id: str, **fields) -> dict | None:
        result: list[dict | None] = [None]

        def apply(data: dict) -> None:
            task = data["tasks"].get(task_id)
            if task:
                task.update(fields)
                result[0] = task

        self._transaction(apply)
        return result[0]

    # --- readiness / priority ---

    def current_phase(self, data: dict | None = None) -> int | None:
        """Lowest phase that still has unfinished (not done) tasks, else None."""
        data = data or self.load()
        phases = [t["phase"] for t in data["tasks"].values() if t["status"] != "done"]
        return min(phases) if phases else None

    def ready_tasks(self, limit: int = 1) -> list[dict]:
        """Tasks claimable now: pending/failed in the current open phase,
        plus in_progress tasks whose claim has gone stale (dead worker).

        Failed tasks whose attempts reached the cap are excluded (exhausted);
        they need an explicit `release --force` reset before retrying."""
        data = self.load()
        phase = self.current_phase(data)
        if phase is None:
            return []
        cap = max_attempts()
        ready = [
            t for t in data["tasks"].values()
            if t["phase"] == phase
            and (
                (
                    t["status"] in ("pending", "failed")
                    and not (t["status"] == "failed" and t["attempts"] >= cap)
                )
                or (t["status"] == "in_progress" and self._claim_stale(self._claim_dir(t["id"])))
            )
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

    def _claim_stale(self, claim_dir: Path) -> bool:
        """Single source of truth for "this claim is abandoned": the claim dir
        is gone (orphaned in_progress entry mid-recovery), or its mtime age
        reached the stale window. Workers keep it fresh via `touch`; the
        window is the only liveness signal — repowiki runs as short-lived
        CLI processes, so recorded pids are meaningless for liveness."""
        if not claim_dir.exists():
            return True
        return self._claim_age(claim_dir) >= self.stale_seconds

    def _try_mkdir_claim(self, task_id: str, worker: str) -> bool:
        """Create claims/<id>/ atomically, stealing it first if stale."""
        self.paths.claims_dir.mkdir(parents=True, exist_ok=True)
        cd = self._claim_dir(task_id)
        for _attempt in range(3):
            try:
                os.mkdir(cd)
            except FileExistsError:
                if not self._claim_stale(cd):
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
        task = self._require_task(task_id)
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
        task = self._require_task(task_id)
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
        task = self._require_task(task_id)
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
            and self._claim_stale(self._claim_dir(t["id"]))
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
        stale_ids = {s["id"] for s in stale}
        return {
            "total": len(tasks),
            "by_status": by_status,
            "current_phase": self.current_phase(data),
            # in-flight claims that are actually alive (stale ones will be
            # handed back out, so they don't count as busy)
            "busy": sum(1 for t in tasks if t["status"] == "in_progress" and t["id"] not in stale_ids),
            "failed": failed,
            "exhausted": exhausted,
            "stale_claims": stale,
        }


def run_clean(paths: WikiPaths, as_json: bool = False) -> int:
    """Remove state/ entirely (opt-in). The wiki output under .repowiki/ is kept."""
    import shutil

    if not paths.state_dir.exists():
        emit({"ok": True, "removed": False, "detail": "state/ 不存在，无需清理"},
             lambda r: r["detail"], as_json)
        return 0
    shutil.rmtree(paths.state_dir)
    msg = (
        f"已删除 {paths.state_dir}。"
        "失去的能力：增量更新（update）、断点续跑、plan 幂等（重跑 plan 将全新规划）。"
        "wiki 产出（zh/ 与 knowledge/）未受影响。"
    )
    emit({"ok": True, "removed": True, "detail": msg},
         lambda r: f"✓ {r['detail']}", as_json)
    return 0
