"""State store tests: claim/release, stale reclaim, and a multi-process race."""

from __future__ import annotations

import multiprocessing as mp
import time

import pytest

from repowiki.cli import ConflictError
from repowiki.paths import WikiPaths
from repowiki.state import TaskStore, new_task


@pytest.fixture
def store(paths):
    paths.ensure()
    s = TaskStore(paths, stale_seconds=2)
    s.replace_all([new_task(f"t{i:02d}", "page", 2, f"页{i}", f"zh/content/p{i}.md") for i in range(20)])
    return s


def test_add_and_ready(store):
    ready = store.ready_tasks(limit=3)
    assert [t["id"] for t in ready] == ["t00", "t01", "t02"]


def test_claim_and_conflict(store):
    store.claim("t00", "w1")
    with pytest.raises(ConflictError):
        store.claim("t00", "w2")
    assert store.get("t00")["status"] == "in_progress"
    assert store.get("t00")["attempts"] == 1


def test_release(store):
    store.claim("t00", "w1")
    store.release("t00")
    assert store.get("t00")["status"] == "pending"
    # releasable again by someone else
    store.claim("t00", "w2")
    assert store.get("t00")["attempts"] == 2


def test_stale_claim_reclaimed(store, paths):
    import os

    store.claim("t00", "w1")
    # simulate a dead worker: backdate the claim dir beyond the threshold
    cd = store._claim_dir("t00")
    old = time.time() - 999
    os.utime(cd, (old, old))
    store.update("t00", heartbeat_at="2020-01-01T00:00:00Z")

    store2 = TaskStore(paths, stale_seconds=2)
    task = store2.claim("t00", "w2")  # should steal the stale claim
    assert task["worker"] == "w2"
    assert task["attempts"] == 2


def test_phase_gating(paths):
    paths.ensure()
    s = TaskStore(paths)
    s.replace_all([
        new_task("catalog", "catalog", 1, "规划", "state/catalog.json"),
        new_task("p1", "page", 2, "页1", "zh/content/1.md"),
        new_task("overview", "overview", 3, "总览", "zh/meta/wiki-overview.md"),
    ])
    assert [t["id"] for t in s.ready_tasks()] == ["catalog"]
    s.update("catalog", status="done")
    assert [t["id"] for t in s.ready_tasks()] == ["p1"]
    s.update("p1", status="done")
    assert [t["id"] for t in s.ready_tasks()] == ["overview"]
    s.update("overview", status="done")
    assert s.ready_tasks() == []
    assert s.current_phase() is None


def test_failed_task_is_reclaimable(paths):
    paths.ensure()
    s = TaskStore(paths)
    s.replace_all([new_task("p1", "page", 2, "页1", "zh/content/1.md")])
    s.update("p1", status="failed")
    ready = s.ready_tasks()
    assert [t["id"] for t in ready] == ["p1"]


# --- multi-process race: N workers claim M tasks, zero duplicates ---

def _worker_claim(args):
    """Mimic the documented worker loop. Exit when nothing is left to claim:
    no pending/failed tasks (claimed-by-others work is theirs to finish)."""
    root, worker = args
    store = TaskStore(WikiPaths(root), stale_seconds=60)
    claimed = []
    empty_polls = 0
    while len(claimed) < 10 and empty_polls < 200:
        data = store.load()["tasks"]
        if not any(t["status"] in ("pending", "failed") for t in data.values()):
            break
        ready = store.ready_tasks(limit=1)
        if not ready:
            empty_polls += 1
            time.sleep(0.02)
            continue
        empty_polls = 0
        try:
            store.claim(ready[0]["id"], worker)
            claimed.append(ready[0]["id"])
        except (ConflictError, KeyError):
            continue
    return claimed


def test_concurrent_claims_no_duplicates(paths):
    paths.ensure()
    s = TaskStore(paths)
    s.replace_all([new_task(f"t{i:02d}", "page", 2, f"页{i}", f"p{i}.md") for i in range(30)])
    with mp.Pool(processes=6) as pool:
        results = pool.map(_worker_claim, [(str(paths.repo_root), f"w{i}") for i in range(6)])
    all_claimed = [tid for r in results for tid in r]
    assert len(all_claimed) == len(set(all_claimed)), "出现重复认领"
    assert len(all_claimed) == 30, f"有任务未被认领: {30 - len(all_claimed)}"
