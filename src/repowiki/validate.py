"""Output validation: rule engine with deterministic auto-fix.

Anything computable (anchors, line ranges, H1, path separators) is fixed
silently and reported under ``fixed``; only semantic defects (missing
sections, dangling file references, broken fences) fail the task.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .i18n import strings
from .paths import github_anchor, nfc

MIN_SECTIONS = 6
MIN_MERMAID = 2
MAX_CITED_FILES = 15

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
_H1_RE = re.compile(r"^# (.+?)\s*$", re.M)
_H2_RE = re.compile(r"^## (.+?)\s*$", re.M)
_FILE_LINK_RE = re.compile(
    r"\[(?P<text>[^\]]*)\]\(file://(?P<path>[^)#\s]+?)(?P<range>#L(?P<start>\d+)(?:-L(?P<end>\d+))?)?\)"
)
_CITE_RE = re.compile(r"<cite>(?P<body>.*?)</cite>", re.S)
_TOC_LINE_RE = re.compile(r"^\s*\d+\.\s+\[(?P<t>.+?)\]\(#(?P<a>.+?)\)\s*$", re.M)
_WIKI_LINK_RE = re.compile(r"\]\((?!file://|#)([^)]+\.md)\)")


@dataclass
class CheckResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    text: str = ""

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


def extract_refs(text: str) -> list[tuple[str, int | None, int | None]]:
    """Extract all file:// references as (path, start, end); no range -> (None, None)."""
    refs = []
    for m in _FILE_LINK_RE.finditer(text):
        start = int(m.group("start")) if m.group("start") else None
        end = int(m.group("end")) if m.group("end") else start
        refs.append((m.group("path"), start, end))
    return refs


def _headings(text: str, level: int = 2) -> list[str]:
    if level == 1:
        return [m.group(1).strip() for m in _H1_RE.finditer(text)]
    return [m.group(1).strip() for m in _H2_RE.finditer(text)]


def _file_loc(repo_root: Path, rel: str) -> int | None:
    p = repo_root / rel
    try:
        if not p.is_file():
            return None
        data = p.read_bytes()
        if b"\0" in data[:8192]:
            return None
        return max(data.count(b"\n"), 1)
    except OSError:
        return None


def check_page(raw: str, title: str, repo_root: Path, is_update: bool = False,
               locale: str = "zh") -> CheckResult:
    res = CheckResult(text=raw)
    text = raw
    lang = strings(locale)

    # leftover template placeholders are always an error
    if _PLACEHOLDER_RE.search(text):
        res.fail("页面仍含未替换的模板占位符 {{...}}")

    # H1: exactly one, must equal the task title (auto-fix if mismatched)
    h1s = _headings(text, 1)
    if not h1s:
        res.fail("缺少一级标题（H1）")
    else:
        expected = nfc(title).strip()
        if nfc(h1s[0]).strip() != expected:
            text = _H1_RE.sub(f"# {expected}\n", text, count=1)
            res.fixed.append(f"H1 由「{h1s[0]}」改为「{expected}」")

    # required sections
    headings = _headings(text)
    required = list(lang["required_sections"])
    if is_update:
        required.insert(0, lang["update_extra"])
    for name, mode in required:
        if mode == "exact":
            hit = any(h == name for h in headings)
        else:
            hit = any(h.startswith(name) for h in headings)
        if not hit:
            res.fail(f"缺少必备小节「## {name}」")
    if len(headings) < MIN_SECTIONS:
        res.fail(f"## 小节数 {len(headings)} < {MIN_SECTIONS}，疑似内容截断")

    # <cite> block
    cite = _CITE_RE.search(text)
    if not cite:
        res.fail("缺少 <cite>…</cite> 引用块（应位于 H1 之后、「目录」之前）")
    else:
        cite_links = _FILE_LINK_RE.findall(cite.group("body"))
        if not cite_links:
            res.fail("<cite> 块内没有任何 file:// 文件引用")

    # mermaid fences
    mermaid_blocks = re.findall(r"```mermaid", text)
    fences = re.findall(r"^```.*$", text, re.M)
    if len(fences) % 2 == 1:
        res.fail("代码围栏（```）不配对，mermaid 图可能未闭合")
    if len(mermaid_blocks) < MIN_MERMAID:
        res.fail(f"mermaid 图数量 {len(mermaid_blocks)} < {MIN_MERMAID}（至少需要结构图与时序/依赖图各一）")

    # file:// links: existence (error) + line-range clamp / separator fix (auto-fix)
    cited_paths: list[str] = []
    missing: set[str] = set()

    def _fix_link(m: re.Match) -> str:
        orig_path = m.group("path")
        path = orig_path.replace("\\", "/")
        label = m.group("text").replace("\\", "/")
        start, end = m.group("start"), m.group("end")
        loc = _file_loc(repo_root, path)
        if loc is None:
            missing.add(orig_path)
            return m.group(0)
        changed = False
        if path != orig_path or label != m.group("text"):
            changed = True
            res.fixed.append(f"链接路径分隔符归一：{orig_path} → {path}")
        if start:
            s = max(1, min(int(start), loc))
            e = max(1, min(int(end or start), loc))
            if str(s) != start or str(e or s) != (end or start):
                changed = True
                res.fixed.append(
                    f"行区间钳制：{path}:{start}-{end or start} → {s}-{e}（文件共 {loc} 行）"
                )
            cited_paths.append(path)
            return f"[{path}:{s}-{e}](file://{path}#L{s}-L{e})" if changed else m.group(0)
        cited_paths.append(path)
        return f"[{label}](file://{path})" if changed else m.group(0)

    text = _FILE_LINK_RE.sub(_fix_link, text)
    if missing:
        res.fail("引用了仓库中不存在的文件: " + ", ".join(sorted(missing)))
    if len(set(cited_paths)) > MAX_CITED_FILES:
        res.warnings.append(f"单页引用文件 {len(set(cited_paths))} 个 > {MAX_CITED_FILES}")

    # wiki-to-wiki links (warn only)
    wiki_refs = [m.group(1) for m in _WIKI_LINK_RE.finditer(text)]
    if wiki_refs:
        res.warnings.append("存在指向 .md 的页间链接（应为页间零链接）: " + ", ".join(wiki_refs[:3]))

    # TOC anchors: rebuild deterministically from actual headings (auto-fix)
    toc_fixed = _fix_toc(text, lang["toc"])
    if toc_fixed:
        text, note = toc_fixed
        res.fixed.append(note)

    res.text = text
    return res


def _fix_toc(text: str, toc_name: str = "目录") -> tuple[str, str] | None:
    """Rebuild the numbered TOC from actual ## headings; return (text, note) if changed."""
    m = re.search(rf"^## {re.escape(toc_name)}\s*$", text, re.M)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"^## .+$", text[start:], re.M)
    body = text[start:start + nxt.start()] if nxt else text[start:]
    headings = [h for h in _headings(text) if h != toc_name]
    expected = [(h, github_anchor(h)) for h in headings]
    got = [(m2.group("t"), m2.group("a")) for m2 in _TOC_LINE_RE.finditer(body)]
    if got == expected:
        return None
    new_body = "\n" + "\n".join(f"{i}. [{h}](#{a})" for i, (h, a) in enumerate(expected, 1)) + "\n\n"
    new_text = text[:start] + new_body + text[start + len(body):]
    return new_text, f"「{toc_name}」锚点列表已按实际章节标题重建"


# --- catalog / knowledge plan ---

def check_catalog(data, known_paths: set[str]) -> tuple[list[str], list[str]]:
    from .catalog import validate_catalog

    return validate_catalog(data, known_paths)


KNOWLEDGE_CATEGORIES = {
    "configuration_system", "logging_system", "error_handling",
    "build_system", "dependency_management", "frontend_style",
}


def check_knowledge_plan(data, known_paths: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["knowledge.json 必须是 JSON 对象"], warnings
    modules = data.get("modules")
    cards = data.get("cards")
    if not isinstance(modules, list) or not modules:
        errors.append("缺少 modules（非空数组）")
        modules = modules if isinstance(modules, list) else []
    if not isinstance(cards, list):
        errors.append("缺少 cards（可为空数组）")
        cards = cards if isinstance(cards, list) else []
    ids = [m.get("id") for m in modules if isinstance(m, dict)]
    if len(ids) != len(set(ids)):
        errors.append("模块 id 重复")
    titles = [m.get("title") for m in modules if isinstance(m, dict)]
    if len(titles) != len(set(titles)):
        errors.append("模块 title 重复")
    for m in modules:
        if not isinstance(m, dict):
            errors.append("modules 含非对象项")
            continue
        mid = m.get("id", "?")
        if not str(m.get("title", "")).strip():
            errors.append(f"模块 {mid}: 缺少 title")
        for key in ("children", "depends_on", "related_to"):
            for ref in m.get(key) or []:
                if ref not in ids:
                    errors.append(f"模块 {mid}: {key} 引用了不存在的 id `{ref}`")
        for p in m.get("scope") or []:
            if p != "**" and p not in known_paths and not any(k.startswith(p) for k in known_paths):
                warnings.append(f"模块 {mid}: scope 路径 `{p}` 未命中任何仓库文件")
    seen_card_ids: set[str] = set()
    for c in cards:
        if not isinstance(c, dict):
            errors.append("cards 含非对象项")
            continue
        cid = c.get("id", "?")
        if cid in seen_card_ids:
            errors.append(f"卡片 id 重复 `{cid}`")
        seen_card_ids.add(cid)
        if not str(c.get("title", "")).strip():
            errors.append(f"卡片 {cid}: 缺少 title")
        if c.get("category") not in KNOWLEDGE_CATEGORIES:
            errors.append(f"卡片 {cid}: category 非法 `{c.get('category')}`（六选一）")
        for p in c.get("source_files") or []:
            if p not in known_paths:
                errors.append(f"卡片 {cid}: source_files 引用不存在的文件 `{p}`")
    return errors, warnings


# --- knowledge module / card / overview ---

def check_knowledge_module(out_dir: Path, locale: str = "zh") -> CheckResult:
    res = CheckResult()
    lang = strings(locale)
    if not out_dir.is_dir():
        res.fail(f"模块目录不存在：{out_dir}")
        return res
    for name in lang["module_required_files"]:
        f = out_dir / name
        if not f.is_file():
            res.fail(f"缺少必需文件 {name}")
        elif not f.read_text(encoding="utf-8").strip():
            res.fail(f"{name} 内容为空")
    return res


def check_knowledge_card(raw: str, title: str, category: str, repo_root: Path,
                         locale: str = "zh") -> CheckResult:
    res = CheckResult(text=raw)
    lang = strings(locale)
    if _PLACEHOLDER_RE.search(raw):
        res.fail("卡片仍含未替换的模板占位符")
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.S)
    if not fm:
        res.fail("缺少 YAML front matter")
        return res
    try:
        meta = yaml.safe_load(fm.group(1)) or {}
    except yaml.YAMLError as e:
        res.fail(f"front matter YAML 解析失败: {e}")
        return res
    for key in ("kind", "name", "category"):
        if not meta.get(key):
            res.fail(f"front matter 缺少 {key}")
    if meta.get("category") and meta.get("category") not in KNOWLEDGE_CATEGORIES:
        res.fail(f"category 非法 `{meta.get('category')}`")
    if not isinstance(meta.get("source_files"), list) or not meta.get("source_files"):
        res.fail("front matter 缺少 source_files 列表")
    for p in meta.get("source_files") or []:
        if not (repo_root / str(p)).exists():
            res.fail(f"source_files 引用不存在的文件 `{p}`")
    body = raw[fm.end():]
    for i, sec in enumerate(lang["card_sections"], start=1):
        if f"## {i}. {sec}" not in body:
            res.fail(f"缺少小节「## {i}. {sec}」")
    h1s = _headings(body, 1)
    if not h1s:
        res.fail("卡片正文缺少一级标题")
    elif nfc(h1s[0]).strip() != nfc(title).strip():
        res.fail(f"H1「{h1s[0]}」应与卡片标题「{title}」一致")
    if category and meta.get("category") != category:
        res.warnings.append(f"front matter category={meta.get('category')} 与规划的 {category} 不一致")
    return res


def check_overview(raw: str, repo_name: str, locale: str = "zh") -> CheckResult:
    res = CheckResult(text=raw)
    lang = strings(locale)
    if _PLACEHOLDER_RE.search(raw):
        res.fail("总览仍含未替换的模板占位符")
    if raw.lstrip().startswith("---"):
        res.fail("总览不应包含 YAML front matter")
    expected_h1 = f"{repo_name} {lang['overview_h1_suffix']}"
    h1s = _headings(raw, 1)
    if not h1s:
        res.fail("缺少一级标题")
    elif nfc(h1s[0]).strip() != expected_h1:
        new_text = _H1_RE.sub(f"# {expected_h1}\n", raw, count=1)
        res.text = new_text
        res.fixed.append(f"H1 由「{h1s[0]}」改为「{expected_h1}」")
    for sec in lang["overview_sections"]:
        if not any(h == sec for h in _headings(res.text)):
            res.fail(f"缺少小节「## {sec}」")
    return res
