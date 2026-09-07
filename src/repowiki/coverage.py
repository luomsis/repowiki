"""``repowiki coverage``: which repo files has the wiki never cited?

A read-only quality report in repowiki's deterministic spirit: compare the
repository inventory against the union of ``file://`` citations across all
wiki pages and the overview, plus knowledge-card source files. No agent, no
LLM — the numbers are computable facts, useful as a writing guide ("these
modules have no page yet") and as a provable quality metric.
"""

from __future__ import annotations

import json

from .catalog import flatten
from .errors import UsageError
from .output import emit
from .paths import WikiPaths
from .scanner import scan
from .validate import extract_refs

MAX_LISTING = 50  # human output caps the uncited listing; JSON is complete


def run_coverage(paths: WikiPaths, as_json: bool) -> int:
    if not paths.catalog_file.exists():
        raise UsageError("state/catalog.json 不存在，请先完成首次生成")
    try:
        catalog = json.loads(paths.catalog_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise UsageError(
            f"state/catalog.json 损坏（{e}）：可手工修复该文件，或 `repowiki plan --replan` 重新规划"
        ) from e

    inv = scan(paths.repo_root)
    known = {f.path for f in inv.files}

    cited: set[str] = set()
    pages: list[dict] = []
    for n in flatten(catalog, paths.locale):
        f = paths.root / n.output
        refs = extract_refs(f.read_text(encoding="utf-8")) if f.is_file() else []
        page_cited = {path for path, _s, _e in refs if path in known}
        cited |= page_cited
        pages.append({"id": n.id, "title": n.title, "cited_files": len(page_cited)})

    if paths.overview_file.is_file():
        for path, _s, _e in extract_refs(paths.overview_file.read_text(encoding="utf-8")):
            if path in known:
                cited.add(path)

    knowledge_files: set[str] = set()
    if paths.knowledge_plan_file.exists():
        try:
            plan = json.loads(paths.knowledge_plan_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            plan = {}
        if isinstance(plan, dict):
            for card in plan.get("cards") or []:
                if isinstance(card, dict):
                    knowledge_files |= {p for p in card.get("source_files") or [] if p in known}
    cited |= knowledge_files

    uncited = sorted(known - cited)
    total = len(known)
    covered = total - len(uncited)
    result = {
        "ok": True,
        "repo_files": total,
        "cited_files": covered,
        "coverage": round(covered / total, 4) if total else 1.0,
        "uncited_files": uncited,
        "knowledge_files": sorted(knowledge_files),
        "pages": pages,
    }
    emit(result, _coverage_human, as_json)
    return 0


def _coverage_human(r: dict) -> str:
    lines = [
        f"覆盖率 {r['cited_files']}/{r['repo_files']}（{r['coverage'] * 100:.1f}%）"
        "——被 wiki 页面/总览/知识卡片引用过的仓库文件占比"
    ]
    uncited = r["uncited_files"]
    if uncited:
        lines.append(f"未被引用 {len(uncited)} 个（至多列出 {MAX_LISTING} 个，JSON 输出含全量）:")
        lines += [f"  → {p}" for p in uncited[:MAX_LISTING]]
    else:
        lines.append("仓库全部文件都被引用 ✓")
    zero = [p for p in r["pages"] if p["cited_files"] == 0]
    if zero:
        lines.append(
            f"⚠ {len(zero)} 个页面没有任何 file:// 引用: "
            + ", ".join(f"{p['id']}({p['title']})" for p in zero[:5])
        )
    return "\n".join(lines)
