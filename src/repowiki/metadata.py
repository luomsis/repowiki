"""``repowiki finalize``: assemble zh/meta/repowiki-metadata.json.

Parses every finished page for file:// references and builds the metadata
document (source_files / code_snippets / knowledge_relations), mirroring the
shape of Qoder's repowiki-metadata.json minus its encrypted internals.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .catalog import flatten
from .cli import UsageError
from .paths import WikiPaths
from .state import TaskStore, now_iso
from .tasks import build_overview_task
from .validate import extract_refs


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, check=True, timeout=30
        ).stdout.decode().strip()
        return out or None
    except (subprocess.SubprocessError, OSError):
        return None


def run_finalize(paths: WikiPaths, as_json: bool) -> int:
    store = TaskStore(paths)
    data = store.load()
    if not data["tasks"]:
        raise UsageError("没有任务，请先运行 `repowiki plan <repo>`")

    if "overview" not in data["tasks"]:
        catalog = _require_catalog(paths)
        nodes = flatten(catalog)
        store.add_tasks([build_overview_task(paths, catalog.get("repo_name", ""), nodes)])
        msg = "已创建阶段3 overview 任务，请领取执行后再次运行 finalize"
        _emit_progress(as_json, msg)
        return 3  # progress, not error: waiting for the overview task

    missing_pages = _missing_pages(paths, _require_catalog(paths))
    if missing_pages:
        raise UsageError(
            f"catalog 中有 {len(missing_pages)} 个页面尚未生成: "
            + ", ".join(missing_pages[:8])
            + ("…" if len(missing_pages) > 8 else "")
            + "（--max-pages 试跑后请补齐页面再 finalize，或 plan --replan 重来）"
        )

    unfinished = {tid: t["status"] for tid, t in data["tasks"].items() if t["status"] != "done"}
    if unfinished:
        raise UsageError(
            f"仍有 {len(unfinished)} 个任务未完成: "
            + ", ".join(f"{k}({v})" for k, v in list(unfinished.items())[:8])
        )

    catalog = _require_catalog(paths)
    nodes = flatten(catalog)
    by_id = {n.id: n for n in nodes}

    source_files: dict[str, dict] = {}
    snippets: dict[str, dict] = {}
    relations: list[dict] = []
    for n in nodes:
        page_file = paths.root / n.output
        refs = extract_refs(page_file.read_text(encoding="utf-8")) if page_file.is_file() else []
        for path, start, end in refs:
            sf_id = _md5(path)
            if sf_id not in source_files:
                source_files[sf_id] = {"id": sf_id, "path": path, "filename": path.rsplit("/", 1)[-1]}
            relations.append({"type": "CONTAINS", "from": n.id, "to": sf_id})
            if start is not None:
                rng = f"{start}-{end}" if end and end != start else f"{start}-{start}"
                sn_id = _md5(f"{path}:{rng}")
                if sn_id not in snippets:
                    snippets[sn_id] = {"id": sn_id, "path": path, "line_range": rng}
                relations.append({"type": "REFERENCED_BY", "from": sn_id, "to": n.id})

    repo_name = catalog.get("repo_name") or paths.repo_root.name
    metadata = {
        "wiki_repo": {
            "id": _md5(str(paths.repo_root)),
            "name": repo_name,
            "progress_status": "completed",
            "wiki_present_status": "COMPLETED",
            "last_commit_id": _git(paths.repo_root, "rev-parse", "HEAD"),
            "generated_at": now_iso(),
        },
        "wiki_catalogs": [
            {
                "id": n.id,
                "repo_id": _md5(str(paths.repo_root)),
                "name": n.title,
                "description": n.slug,
                "prompt": n.page_brief,
                "parent_id": n.parent_id,
                "dependent_files": ", ".join(n.dependent_files),
                "progress_status": "completed",
            }
            for n in nodes
        ],
        "wiki_items": [{"catalog_id": n.id, "title": n.title} for n in nodes],
        "source_files": sorted(source_files.values(), key=lambda x: x["path"]),
        "code_snippets": sorted(snippets.values(), key=lambda x: (x["path"], x["line_range"])),
        "knowledge_relations": relations,
    }

    overview = paths.overview_file
    if overview.is_file():
        metadata["wiki_overview"] = overview.read_text(encoding="utf-8")
    else:
        metadata["wiki_overview"] = "No overview yet."

    knowledge_summary = _aggregate_knowledge_if_present(paths, store)

    paths.meta_dir.mkdir(parents=True, exist_ok=True)
    tmp = paths.metadata_file.with_name(".metadata.tmp")
    tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, paths.metadata_file)

    summary = {
        "ok": True,
        "metadata": str(paths.metadata_file),
        "pages": len(nodes),
        "source_files": len(source_files),
        "code_snippets": len(snippets),
        "knowledge_relations": len(relations),
        "knowledge": knowledge_summary,
    }
    removed = store.cleanup_runtime()
    summary["cleaned_runtime"] = removed
    _emit(as_json, True, json.dumps(summary, ensure_ascii=False, indent=2) if as_json else _fmt_summary(summary))
    return 0


def _fmt_summary(s: dict) -> str:
    lines = [
        f"✓ metadata 已生成: {s['metadata']}",
        f"  页面 {s['pages']} · 引用文件 {s['source_files']} · 代码片段 {s['code_snippets']} · 知识关系 {s['knowledge_relations']}",
    ]
    if s["knowledge"]:
        lines.append(f"  知识库: {s['knowledge']}")
    if s.get("cleaned_runtime"):
        lines.append(f"  已清理运行时产物: state/{', state/'.join(s['cleaned_runtime'])}（保留 index/catalog/knowledge 供增量更新）")
    return "\n".join(lines)


def _emit(as_json: bool, ok: bool, payload: str) -> None:
    if as_json:
        try:
            print(json.dumps(json.loads(payload), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(json.dumps({"ok": ok, "detail": payload}, ensure_ascii=False))
    else:
        print(payload)


def _emit_progress(as_json: bool, msg: str) -> None:
    if as_json:
        print(json.dumps({"ok": True, "waiting": True, "detail": msg,
                          "next_action": "执行 overview 任务后再次运行 finalize"}, ensure_ascii=False))
    else:
        print(msg)


def _missing_pages(paths: WikiPaths, catalog: dict) -> list[str]:
    """Catalog nodes whose output page does not exist on disk (e.g. created
    via `plan --max-pages` trial runs). finalize refuses to claim completion."""
    missing = []
    for n in flatten(catalog):
        if not (paths.root / n.output).is_file():
            missing.append(f"{n.id}({n.title})")
    return missing


def _require_catalog(paths: WikiPaths) -> dict:
    if not paths.catalog_file.exists():
        raise UsageError("state/catalog.json 不存在：请先完成 catalog 任务")
    return json.loads(paths.catalog_file.read_text(encoding="utf-8"))


def _aggregate_knowledge_if_present(paths: WikiPaths, store: TaskStore) -> str:
    if not paths.knowledge_plan_file.exists():
        return ""
    try:
        plan = json.loads(paths.knowledge_plan_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "knowledge.json 解析失败，已跳过聚合"
    from .knowledge import aggregate_knowledge

    return aggregate_knowledge(paths, plan, store.load()["tasks"])
