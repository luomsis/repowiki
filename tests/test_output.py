"""Output seam tests: dual-format emit, human formatters, and the regression
for `next` (human mode with nothing claimable used to raise NameError)."""

from __future__ import annotations

import json

from repowiki.cli import main
from repowiki.dispatch import _next_human, _status_human
from repowiki.output import emit, emit_error
from repowiki.paths import WikiPaths
from repowiki.state import TaskStore, new_task


def run(*argv):
    return main(list(argv))


# --- emit seam ---

def test_emit_dual_format(capsys):
    emit({"a": 1, "中文": "值"}, lambda r: f"值 {r['a']}", as_json=True)
    assert json.loads(capsys.readouterr().out) == {"a": 1, "中文": "值"}
    emit({"a": 1, "中文": "值"}, lambda r: f"值 {r['a']}", as_json=False)
    assert capsys.readouterr().out.strip() == "值 1"


def test_emit_skips_empty_human_text(capsys):
    emit({}, lambda r: "", as_json=False)
    assert capsys.readouterr().out == ""


def test_emit_error_json_stdout_human_stderr(capsys):
    emit_error("usage", "参数不对", as_json=True)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"ok": False, "error": "usage", "detail": "参数不对"}
    assert captured.err == ""
    emit_error("usage", "参数不对", as_json=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error: 参数不对" in captured.err


# --- human formatters ---

def test_status_human_lists_failures_and_stale():
    out = {"ok": True, "total": 3, "current_phase": 2,
           "by_status": {"done": 1, "failed": 1, "pending": 1},
           "failed": [{"id": "f1", "title": "坏页"}],
           "exhausted": [{"id": "x1", "title": "毒任务", "attempts": 3}],
           "stale_claims": [{"id": "s1", "worker": "w", "heartbeat_at": "T"}]}
    text = _status_human(out)
    assert "任务总数 3" in text
    assert "  done: 1" in text
    assert "✗ failed: f1 坏页" in text
    assert "⛔ exhausted: x1" in text and "--force" in text
    assert "⏰ stale: s1（worker w" in text


def test_next_human_empty_with_busy_hint():
    out = {"ok": True, "claimed": True, "tasks": [], "busy": 2,
           "progress": {"total": 5, "by_status": {"done": 1, "in_progress": 2, "pending": 2},
                        "current_phase": 2}}
    text = _next_human(out)
    assert "当前无可领取任务，2 个任务执行中（稍后重试）" in text
    assert "共 5 个任务" in text


# --- regression: human `next` with nothing claimable used to NameError ---

def _seed_task(paths: WikiPaths, task: dict) -> None:
    store = TaskStore(paths)
    store.replace_all([task])


def test_next_human_busy_but_nothing_ready(repo, paths, capsys):
    paths.ensure()
    done = new_task("t1", "page", 2, "已完成", "zh/content/done.md")
    done["status"] = "done"
    _seed_task(paths, done)
    store = TaskStore(paths)
    store.add_tasks([new_task("t2", "page", 2, "进行中", "zh/content/wip.md")])
    store.claim("t2", "w1")  # 新鲜认领：busy=1 且不可领取
    assert run("next", str(repo)) == 0
    out = capsys.readouterr().out
    assert "当前无可领取任务，1 个任务执行中（稍后重试）" in out
    assert "共 2 个任务" in out


def test_next_human_idle_queue(repo, paths, capsys):
    paths.ensure()
    done = new_task("t1", "page", 2, "已完成", "zh/content/done.md")
    done["status"] = "done"
    _seed_task(paths, done)
    assert run("next", str(repo)) == 0
    out = capsys.readouterr().out
    assert "当前无可领取任务（共 1 个任务" in out
    assert "个任务执行中" not in out
