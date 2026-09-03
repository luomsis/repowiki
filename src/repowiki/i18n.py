"""Locale support: per-language UI strings for generated output + detection.

The wiki output language follows the target repository: ``plan`` detects it
deterministically (CJK ratio over README + source samples, zero network),
persists it in ``state/locale``, and every later command honors it. Adding a
language = one entry in ``STRINGS`` plus a template directory.
"""

from __future__ import annotations

import re
from pathlib import Path

SUPPORTED = ("zh", "en")
DEFAULT_LOCALE = "zh"

# Section/file names the validator enforces, per locale. "prefix" sections
# accept variants (e.g. 性能与一致性考量 / 性能考量).
STRINGS: dict[str, dict] = {
    "zh": {
        "name": "简体中文",
        "toc": "目录",
        "required_sections": [
            ("简介", "exact"),
            ("项目结构", "exact"),
            ("核心组件", "exact"),
            ("架构总览", "exact"),
            ("详细组件分析", "exact"),
            ("依赖关系分析", "exact"),
            ("性能", "prefix"),
            ("故障", "prefix"),
            ("结论", "exact"),
        ],
        "update_extra": ("更新摘要", "exact"),
        "overview_h1_suffix": "Wiki 总览",
        "overview_sections": ("章节导航", "如何使用本 Wiki"),
        "module_required_files": ["概述.md", "技术栈.md", "架构设计.md"],
        "card_sections": ["体系概览", "关键文件与包", "架构与设计约定", "开发者应遵循的规则"],
    },
    "en": {
        "name": "English",
        "toc": "Contents",
        "required_sections": [
            ("Introduction", "exact"),
            ("Project Structure", "exact"),
            ("Core Components", "exact"),
            ("Architecture Overview", "exact"),
            ("Detailed Component Analysis", "exact"),
            ("Dependency Analysis", "exact"),
            ("Performance", "prefix"),
            ("Troubleshooting", "prefix"),
            ("Conclusion", "exact"),
        ],
        "update_extra": ("Update Summary", "exact"),
        "overview_h1_suffix": "Wiki Overview",
        "overview_sections": ("Section Navigation", "How to Use This Wiki"),
        "module_required_files": ["overview.md", "tech-stack.md", "architecture.md"],
        "card_sections": [
            "System Overview", "Key Files and Packages",
            "Architecture and Design Conventions", "Rules for Developers",
        ],
    },
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_SAMPLE_SUFFIXES = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".c", ".h", ".cpp", ".cs", ".swift", ".sh",
}
_SAMPLE_BYTES = 8192
_CODE_SAMPLES = 24
_MIN_README_SIGNAL = 20   # letters (CJK included) before the README is decisive
_MIN_CODE_CJK = 30        # CJK chars in one source file => non-English comments


def strings(locale: str) -> dict:
    return STRINGS.get(locale) or STRINGS[DEFAULT_LOCALE]


def _read_head(path: Path) -> str:
    try:
        data = path.read_bytes()[:_SAMPLE_BYTES]
    except OSError:
        return ""
    if b"\0" in data:
        return ""
    return data.decode("utf-8", "ignore")


def detect_locale(repo_root: Path, code_files: list[str] | None = None) -> str:
    """Decide zh vs en from repository text. The README decides when it
    carries enough natural text (identifiers in code are always latin, so
    they must not dilute the docs-language signal); without a decisive README,
    any source file with substantial CJK text (comments/docstrings) picks zh.
    Deterministic, no network."""
    root = Path(repo_root)
    readme = next((p for p in sorted(root.glob("README*")) if p.is_file()), None)
    if readme is not None:
        text = _read_head(readme)
        cjk = len(_CJK_RE.findall(text))
        latin = len(_LATIN_RE.findall(text))
        if cjk + latin >= _MIN_README_SIGNAL:
            return "zh" if cjk / (cjk + latin) >= 0.15 else "en"

    candidates = [root / rel for rel in sorted(code_files or [])[:_CODE_SAMPLES]]
    candidates = [p for p in candidates if p.suffix in _SAMPLE_SUFFIXES and p.is_file()]
    if readme is not None:
        candidates.append(readme)
    for p in candidates:
        if len(_CJK_RE.findall(_read_head(p))) >= _MIN_CODE_CJK:
            return "zh"
    return "en"
