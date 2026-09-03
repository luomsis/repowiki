"""End-to-end flow tests (no LLM: tests simulate the agent's writes)."""

from __future__ import annotations

import json
import multiprocessing as mp
import subprocess
import time

import pytest
from conftest import valid_catalog, valid_page, write_catalog

from repowiki.catalog import flatten
from repowiki.cli import main
from repowiki.paths import WikiPaths
from repowiki.state import TaskStore, new_task


def run(*argv):
    code = main(list(argv))
    return code


class TestPlan:
    def test_plan_creates_catalog_task(self, repo):
        assert run("plan", str(repo)) == 0
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert "catalog" in index["tasks"]
        spec = (repo / ".repowiki/state/tasks/catalog.md").read_text()
        assert "state/catalog.json" in spec and "src/demo/main.py" in spec

    def test_plan_rejects_tiny_repo(self, tmp_path):
        tiny = tmp_path / "tiny"
        tiny.mkdir()
        (tiny / "a.py").write_text("x = 1\n")
        assert run("plan", str(tiny)) == 1

    def test_plan_with_existing_catalog_expands_pages(self, repo):
        write_catalog(WikiPaths(repo))
        assert run("plan", str(repo)) == 0
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert {"c01", "c0101", "c02"} <= set(index["tasks"])
        spec = (repo / ".repowiki/state/tasks/c0101.md").read_text()
        assert "核心概念" in spec and "src/demo/models.py" in spec
        assert "## 架构总览" in spec  # full template embedded

    def test_plan_max_pages(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo), "--max-pages", "1")
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert set(index["tasks"]) == {"c01"}


class TestNext:
    def test_next_and_claim(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        code = run("next", str(repo), "--claim", "--json")
        assert code == 0


class TestCheckLoop:
    def _prepare(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        run("next", str(repo), "--claim", "--batch", "5")

    def test_check_catalog_expands_pages(self, repo):
        # no catalog.json yet: plan creates the catalog task, agent writes
        # the catalog, check validates and expands phase-2 page tasks
        run("plan", str(repo))
        run("next", str(repo), "--claim")
        write_catalog(WikiPaths(repo))
        code = run("check", str(repo), "--task", "catalog", "--json")
        assert code == 0
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["catalog"]["status"] == "done"
        assert {"c01", "c0101", "c02"} <= set(index["tasks"])
        spec = (repo / ".repowiki/state/tasks/c02.md").read_text()
        assert "快速开始" in spec

    def test_check_bad_catalog_fails_with_errors(self, repo):
        write_catalog(WikiPaths(repo), {"repo_name": "demo", "chapters": [{"id": "c01"}]})
        run("plan", str(repo))  # invalid existing catalog → new catalog task
        run("next", str(repo), "--claim")
        code = run("check", str(repo), "--task", "catalog")
        assert code == 1
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["catalog"]["status"] == "failed"

    def test_page_passes_check_and_done(self, repo):
        self._prepare(repo)
        p = repo / ".repowiki/zh/content/项目概述/项目概述.md"
        p.parent.mkdir(parents=True)
        p.write_text(valid_page("项目概述"), encoding="utf-8")
        code = run("check", str(repo), "--task", "c01")
        assert code == 0
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["c01"]["status"] == "done"

    def test_missing_output_fails(self, repo):
        self._prepare(repo)
        code = run("check", str(repo), "--task", "c01")
        assert code == 1
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["c01"]["status"] == "failed"


class TestFinalize:
    def _full_gen(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        catalog = valid_catalog()
        for n in flatten(catalog):
            p = repo / ".repowiki" / n.output
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(valid_page(n.title), encoding="utf-8")
            TaskStore(WikiPaths(repo)).update(n.id, status="done")
        TaskStore(WikiPaths(repo)).update("catalog", status="done")

    def test_finalize_two_step_overview(self, repo):
        self._full_gen(repo)
        # first finalize creates the overview task
        code = run("finalize", str(repo))
        assert code == 3
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert "overview" in index["tasks"]
        # simulate agent writing overview
        ov = repo / ".repowiki/zh/meta/wiki-overview.md"
        ov.write_text("# demo Wiki 总览\n\n## 章节导航\n- 项目概述\n\n## 如何使用本 Wiki\nx\n", encoding="utf-8")
        TaskStore(WikiPaths(repo)).update("overview", status="done")
        # done tasks must pass check first
        run("check", str(repo), "--task", "overview")
        assert run("finalize", str(repo)) == 0
        meta = json.loads((repo / ".repowiki/zh/meta/repowiki-metadata.json").read_text())
        assert meta["wiki_repo"]["progress_status"] == "completed"
        assert len(meta["wiki_catalogs"]) == 3
        assert meta["wiki_overview"].startswith("# demo Wiki 总览")
        src = {s["path"] for s in meta["source_files"]}
        assert "README.md" in src and "src/demo/main.py" in src
        assert any(r["type"] == "CONTAINS" for r in meta["knowledge_relations"])
        assert any(s["line_range"] for s in meta["code_snippets"])

    def test_finalize_blocked_by_unfinished(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        TaskStore(WikiPaths(repo)).update("catalog", status="done")
        for nid in ("c01", "c0101", "c02"):
            pth = repo / ".repowiki" / dict(
                (n.id, n.output) for n in flatten(valid_catalog())
            )[nid]
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_text(valid_page(TaskStore(WikiPaths(repo)).get(nid)["title"].replace("（增量更新）", "")), encoding="utf-8")
            TaskStore(WikiPaths(repo)).update(nid, status="done")
        run("finalize", str(repo))  # creates overview (exit 3)
        TaskStore(WikiPaths(repo)).update("overview", status="in_progress")  # unfinished
        assert run("finalize", str(repo)) == 1


class TestUpdate:
    def test_update_maps_changed_files(self, git_repo):
        paths = WikiPaths(git_repo)
        write_catalog(paths)
        run("plan", str(paths.repo_root))
        TaskStore(paths).update("catalog", status="done")
        # simulate a full first run being finalized
        meta = {"wiki_repo": {"last_commit_id": _head(git_repo)}}
        paths.meta_dir.mkdir(parents=True, exist_ok=True)
        paths.metadata_file.write_text(json.dumps(meta), encoding="utf-8")
        # old page must exist for the update spec to embed
        p = paths.root / "zh/content/项目概述/项目概述.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(valid_page("项目概述"), encoding="utf-8")
        # make a change touching models.py (c0101 depends on it) → c0101 + ancestor c01
        (git_repo / "src/demo/models.py").write_text(
            "from dataclasses import dataclass\n\n\n@dataclass\nclass Item:\n    id: int\n    name: str\n    tag: str = ''\n"
        )
        subprocess.run(["git", "add", "-A"], cwd=str(git_repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "change"], cwd=str(git_repo), check=True, capture_output=True)

        code = run("update", str(git_repo))
        assert code == 0
        index = json.loads(paths.index_file.read_text())
        assert "c0101-update" in index["tasks"]
        assert "c01-update" in index["tasks"]
        assert "c02-update" not in index["tasks"]
        # c01 has an old page on disk -> real page_update spec with 更新摘要
        spec = (paths.tasks_dir / "c01-update.md").read_text()
        assert "更新摘要" in spec
        # c0101 never generated a page -> falls back to a fresh page task
        assert index["tasks"]["c0101-update"]["kind"] == "page"
        spec2 = (paths.tasks_dir / "c0101-update.md").read_text()
        assert "更新摘要" not in spec2 and "models.py" in spec2

    def test_update_requires_git(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        assert run("update", str(repo)) == 1


class TestKnowledge:
    def test_knowledge_command_and_expansion(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        assert run("knowledge", str(repo)) == 0
        # write a knowledge plan as the agent would
        plan = {
            "modules": [
                {"id": "m01", "title": "核心模块", "scope": ["src/demo/"], "children": [], "depends_on": [], "related_to": []}
            ],
            "cards": [
                {"id": "k01", "title": "配置系统", "category": "configuration_system",
                 "scope": ["**"], "source_files": ["src/demo/config.py"]}
            ],
        }
        kp = repo / ".repowiki/state/knowledge.json"
        kp.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        run("check", str(repo), "--task", "knowledge-plan")
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["knowledge-plan"]["status"] == "done"
        assert "m01" in index["tasks"] and "k01" in index["tasks"]

        # simulate agent outputs
        mdir = repo / ".repowiki/knowledge/zh/核心模块"
        mdir.mkdir(parents=True, exist_ok=True)
        for n in ("概述.md", "技术栈.md", "架构设计.md"):
            (mdir / n).write_text("内容\n", encoding="utf-8")
        cdir = repo / ".repowiki/knowledge/zh/配置系统"
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "配置系统.md").write_text(
            "---\nkind: configuration_system\nname: 配置系统\ncategory: configuration_system\n"
            "scope:\n  - '**'\nsource_files:\n  - src/demo/config.py\n---\n\n"
            "# 配置系统\n\n## 1. 体系概览\nx\n\n## 2. 关键文件与包\nx\n\n"
            "## 3. 架构与设计约定\nx\n\n## 4. 开发者应遵循的规则\nx\n",
            encoding="utf-8",
        )
        assert run("check", str(repo), "--task", "m01") == 0
        assert run("check", str(repo), "--task", "k01") == 0

        # aggregation via knowledge module
        from repowiki.knowledge import aggregate_knowledge

        summary = aggregate_knowledge(WikiPaths(repo), plan, TaskStore(WikiPaths(repo)).load()["tasks"])
        assert "_index.yaml" in summary
        idx = (repo / ".repowiki/knowledge/zh/_index.yaml").read_text()
        assert "核心模块" in idx and "schema_version: 1" in idx
        assert (repo / ".repowiki/knowledge/zh/核心模块/_module.yaml").exists()


def _head(repo) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, check=True
    ).stdout.decode().strip()


class TestCleanup:
    def test_finalize_purges_runtime_keeps_planning(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        catalog = valid_catalog()
        for n in flatten(catalog):
            p = repo / ".repowiki" / n.output
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(valid_page(n.title), encoding="utf-8")
            TaskStore(WikiPaths(repo)).update(n.id, status="done")
        TaskStore(WikiPaths(repo)).update("catalog", status="done")
        run("finalize", str(repo))
        ov = repo / ".repowiki/zh/meta/wiki-overview.md"
        ov.write_text("# demo Wiki 总览\n\n## 章节导航\nx\n\n## 如何使用本 Wiki\ny\n", encoding="utf-8")
        TaskStore(WikiPaths(repo)).update("overview", status="done")
        run("check", str(repo), "--task", "overview")
        assert run("finalize", str(repo)) == 0
        # runtime artifacts purged
        assert not (repo / ".repowiki/state/claims").exists()
        assert not (repo / ".repowiki/state/tasks").exists()
        # planning artifacts kept
        assert (repo / ".repowiki/state/index.json").exists()
        assert (repo / ".repowiki/state/catalog.json").exists()

    def test_update_still_works_after_cleanup(self, git_repo):
        paths = WikiPaths(git_repo)
        write_catalog(paths)
        run("plan", str(paths.repo_root))
        TaskStore(paths).update("catalog", status="done")
        meta = {"wiki_repo": {"last_commit_id": _head(git_repo)}}
        paths.meta_dir.mkdir(parents=True, exist_ok=True)
        paths.metadata_file.write_text(json.dumps(meta), encoding="utf-8")
        p = paths.root / "zh/content/项目概述/项目概述.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(valid_page("项目概述"), encoding="utf-8")
        (git_repo / "src/demo/models.py").write_text("# changed\n")
        subprocess.run(["git", "add", "-A"], cwd=str(git_repo), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "c2"], cwd=str(git_repo), check=True, capture_output=True)
        run("update", str(git_repo))
        # update wrote the new spec even though tasks/ was purged
        assert (paths.tasks_dir / "c0101-update.md").exists()

    def test_clean_removes_state_and_is_idempotent(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        assert (repo / ".repowiki/state").exists()
        assert run("clean", str(repo)) == 0
        assert not (repo / ".repowiki/state").exists()
        # wiki output untouched
        assert (repo / ".repowiki/zh/content").exists()
        # idempotent
        assert run("clean", str(repo)) == 0

    def test_first_finalize_does_not_purge(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        catalog = valid_catalog()
        for n in flatten(catalog):
            p = repo / ".repowiki" / n.output
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(valid_page(n.title), encoding="utf-8")
            TaskStore(WikiPaths(repo)).update(n.id, status="done")
        TaskStore(WikiPaths(repo)).update("catalog", status="done")
        run("finalize", str(repo))  # creates overview task, exit 3
        assert (repo / ".repowiki/state/tasks/overview.md").exists()


class TestLifecycleGuards:
    def test_check_requires_selector(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        run("next", str(repo), "--claim")
        assert run("check", str(repo)) == 1  # no --task / --all

    def test_check_done_is_readonly(self, repo):
        self._make_done_page(repo)
        # source file gone → validation would fail, but status must stay done
        (repo / "README.md").unlink()
        code = run("check", str(repo), "--task", "c01", "--json")
        index = json.loads((repo / ".repowiki/state/index.json").read_text())
        assert index["tasks"]["c01"]["status"] == "done"  # unchanged
        assert code in (0, 1)

    def _make_done_page(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        p = repo / ".repowiki/zh/content/项目概述/项目概述.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(valid_page("项目概述"), encoding="utf-8")
        TaskStore(WikiPaths(repo)).update("c01", status="done")

    def test_touch_refreshes_claim(self, repo):
        run("plan", str(repo))  # no catalog.json yet -> catalog task
        run("next", str(repo), "--claim", "--worker", "wz")
        store = TaskStore(WikiPaths(repo))
        before = store._claim_dir("catalog").stat().st_mtime_ns
        time.sleep(0.01)
        assert run("touch", str(repo), "--task", "catalog", "--worker", "wz") == 0
        after = store._claim_dir("catalog").stat().st_mtime_ns
        assert after > before
        # other worker's identity is refused
        assert run("touch", str(repo), "--task", "catalog", "--worker", "other") == 2

    def test_poison_task_exhausts_and_reset(self, repo):
        run("plan", str(repo))  # -> catalog task
        run("next", str(repo), "--claim", "--worker", "w0")
        store = TaskStore(WikiPaths(repo), stale_seconds=1)
        store.update("catalog", status="failed", attempts=3)  # reached the cap
        stats = store.stats()
        assert any(e["id"] == "catalog" for e in stats["exhausted"])
        assert [t["id"] for t in store.ready_tasks()] == []  # no longer claimable
        # explicit human reset
        assert run("release", str(repo), "--task", "catalog", "--force") == 0
        t = store.get("catalog")
        assert t["status"] == "pending" and t["attempts"] == 0
        # without --force the reset is refused
        store.update("catalog", status="failed", attempts=3)
        assert run("release", str(repo), "--task", "catalog") == 2

    def test_check_refuses_foreign_claim(self, repo):
        run("plan", str(repo))
        write_catalog(WikiPaths(repo))
        run("next", str(repo), "--claim", "--worker", "holder")
        assert run("check", str(repo), "--task", "catalog", "--worker", "intruder") == 2
        assert run("check", str(repo), "--task", "catalog", "--worker", "intruder", "--force") == 0

    def test_check_all_still_works(self, repo):
        run("plan", str(repo))
        write_catalog(WikiPaths(repo))
        run("next", str(repo), "--claim")
        run("check", str(repo), "--task", "catalog")  # done
        assert run("check", str(repo), "--all") == 0  # nothing in flight


def _flip_done(args):
    root, tid = args
    s = TaskStore(WikiPaths(root))
    return s.update(tid, status="done") is not None


class TestP1Guards:
    def test_finalize_first_step_exit_3(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        catalog = valid_catalog()
        for n in flatten(catalog):
            p = repo / ".repowiki" / n.output
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(valid_page(n.title), encoding="utf-8")
            TaskStore(WikiPaths(repo)).update(n.id, status="done")
        TaskStore(WikiPaths(repo)).update("catalog", status="done")
        assert run("finalize", str(repo)) == 3  # progress, not error

    def test_finalize_refuses_missing_pages(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        TaskStore(WikiPaths(repo)).update("catalog", status="done")
        # only c01 exists; c0101/c02 missing (--max-pages style trial run)
        p = repo / ".repowiki/zh/content/项目概述/项目概述.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(valid_page("项目概述"), encoding="utf-8")
        TaskStore(WikiPaths(repo)).update("c01", status="done")
        run("finalize", str(repo))  # creates overview task
        TaskStore(WikiPaths(repo)).update("overview", status="done")
        assert run("finalize", str(repo)) == 1  # missing pages gate
        assert not (repo / ".repowiki/zh/meta/repowiki-metadata.json").exists()

    def test_replan_guard(self, repo):
        write_catalog(WikiPaths(repo))
        run("plan", str(repo))
        run("next", str(repo), "--claim")  # catalog in_progress
        assert run("plan", str(repo), "--replan") == 1
        assert (repo / ".repowiki/state/index.json").exists()  # untouched
        assert run("plan", str(repo), "--replan", "--force") == 0

    def test_index_transaction_no_lost_updates(self, repo):
        """Multi-process status flips on distinct tasks: no flip may be lost."""
        paths = WikiPaths(repo)
        paths.ensure()
        store = TaskStore(paths)
        store.replace_all([new_task(f"t{i:02d}", "page", 2, f"页{i}", f"p{i}.md") for i in range(12)])

        with mp.Pool(processes=6) as pool:
            oks = pool.map(_flip_done, [(str(repo), f"t{i:02d}") for i in range(12)])
        assert all(oks)
        data = store.load()["tasks"]
        assert sum(1 for t in data.values() if t["status"] == "done") == 12


class TestWatch:
    def _setup_tasks(self, repo, n=2):
        paths = WikiPaths(repo)
        paths.ensure()
        store = TaskStore(paths)
        store.replace_all([new_task(f"t{i}", "page", 2, f"页{i}", f"p{i}.md") for i in range(n)])
        return store

    def test_watch_exits_zero_when_all_done(self, repo):
        store = self._setup_tasks(repo)

        def finish():
            time.sleep(0.15)
            for tid in ("t0", "t1"):
                store.update(tid, status="done")

        import threading
        threading.Thread(target=finish, daemon=True).start()
        assert run("watch", str(repo), "--interval", "0.05", "--timeout", "10") == 0

    def test_watch_stall_exits_one(self, repo):
        store = self._setup_tasks(repo)
        store.update("t0", status="failed", attempts=3)  # exhausted
        store.update("t1", status="done")
        assert run("watch", str(repo), "--interval", "0.05", "--timeout", "10") == 1

    def test_watch_timeout_exits_one(self, repo):
        self._setup_tasks(repo)  # tasks stay pending forever
        assert run("watch", str(repo), "--interval", "0.05", "--timeout", "0.2") == 1

    def test_watch_empty_manifest(self, repo):
        WikiPaths(repo).ensure()
        assert run("watch", str(repo), "--interval", "0.05", "--timeout", "1") == 1
