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
    breakdown = _classify_uncited(uncited, cited, paths.locale)
    eff_total = total - len(breakdown["vendor"]) - len(breakdown["locale_mirror"])
    result = {
        "ok": True,
        "repo_files": total,
        "cited_files": covered,
        "coverage": round(covered / total, 4) if total else 1.0,
        "effective_coverage": round(covered / eff_total, 4) if eff_total else 1.0,
        "uncited_files": uncited,
        "uncited_breakdown": breakdown,
        "knowledge_files": sorted(knowledge_files),
        "pages": pages,
    }
    emit(result, _coverage_human, as_json)
    return 0


def _locale_mirrors(p: str, locale: str) -> set[str]:
    """Candidate paths of the other-locale twin of ``p`` (deterministic)."""
    out: set[str] = set()
    for old, new in (
        (f"/{locale}/", "/en/"), ("/en/", f"/{locale}/"),
        (f".{locale}.", ".en."), (".en.", f".{locale}."), (".en.", "."),
    ):
        if old in p:
            out.add(p.replace(old, new, 1))
    return out


def _classify_uncited(uncited: list[str], cited: set[str], locale: str) -> dict[str, list[str]]:
    """Bucket uncited files: vendored third-party code, other-locale mirrors
    of already-cited files, and the rest (the actionable residue)."""
    vendor: list[str] = []
    mirror: list[str] = []
    other: list[str] = []
    for p in uncited:
        if "/vendor/" in f"/{p}":
            vendor.append(p)
        elif _locale_mirrors(p, locale) & cited:
            mirror.append(p)
        else:
            other.append(p)
    return {"vendor": sorted(vendor), "locale_mirror": sorted(mirror), "other": sorted(other)}


def _coverage_human(r: dict) -> str:
    lines = [
        f"覆盖率 {r['cited_files']}/{r['repo_files']}（{r['coverage'] * 100:.1f}%）"
        "——被 wiki 页面/总览/知识卡片引用过的仓库文件占比"
    ]
    if r.get("effective_coverage") != r["coverage"]:
        lines.append(
            f"有效覆盖率 {r['effective_coverage'] * 100:.1f}%"
            "（剔除 vendor 与其他语言镜像后的口径）"
        )
    uncited = r["uncited_files"]
    if uncited:
        bd = r.get("uncited_breakdown") or {}
        mirror = bd.get("locale_mirror", [])
        vendored = bd.get("vendor", [])
        actionable = bd.get("other", uncited)
        lines.append(f"未被引用 {len(uncited)} 个（JSON 输出含全量分组）:")
        if mirror:
            lines.append(f"  其他语言镜像（无需引用）: {', '.join(mirror[:5])}"
                         + (f" 等 {len(mirror)} 个" if len(mirror) > 5 else ""))
        if vendored:
            lines.append(f"  vendor 第三方（无需引用）: {', '.join(vendored[:5])}"
                         + (f" 等 {len(vendored)} 个" if len(vendored) > 5 else ""))
        show = actionable[:MAX_LISTING]
        lines.append(f"  值得补引用 {len(actionable)} 个（至多列出 {MAX_LISTING} 个）:")
        lines += [f"  → {p}" for p in show]
    else:
        lines.append("仓库全部文件都被引用 ✓")
    zero = [p for p in r["pages"] if p["cited_files"] == 0]
    if zero:
        lines.append(
            f"⚠ {len(zero)} 个页面没有任何 file:// 引用: "
            + ", ".join(f"{p['id']}({p['title']})" for p in zero[:5])
        )
    return "\n".join(lines)
