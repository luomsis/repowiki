"""Path derivation and normalization rules (all deterministic).

- Chapter titles become directory/file names: NFC normalize, replace
  filesystem-illegal characters with full-width counterparts, strip
  control characters and leading/trailing dots or spaces.
- Name collisions get a ``__2`` style suffix.
- GitHub-style heading anchors keep CJK characters, drop punctuation
  (including ``：`` and ``:``) and turn spaces into ``-``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .i18n import DEFAULT_LOCALE, SUPPORTED

_ILLEGAL_MAP = {
    "/": "／",
    "\\": "＼",
    ":": "：",
    "*": "＊",
    "?": "？",
    '"': "＂",
    "<": "＜",
    ">": "＞",
    "|": "｜",
}
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

_GITHUB_PUNCT_RE = re.compile(
    r"[" + re.escape("`~!#$%^&*()+=[]{}\\|:;'\",.<>/?_-—─·•„“”«»…！￥（）【】《》「」：；‘’\"，。、？") + r"]"
)
_GITHUB_SPACE_RE = re.compile(r"\s+")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sanitize_component(title: str) -> str:
    """Title -> single path component (directory or file stem)."""
    s = nfc(title).strip()
    s = _CONTROL_RE.sub("", s)
    for bad, full in _ILLEGAL_MAP.items():
        s = s.replace(bad, full)
    s = s.strip(" .")
    return s or "untitled"


def unique_name(name: str, used: set[str]) -> str:
    """Return ``name`` or ``name__2``, ``name__3``... so it is unique in ``used``."""
    if name not in used:
        used.add(name)
        return name
    n = 2
    while f"{name}__{n}" in used:
        n += 1
    candidate = f"{name}__{n}"
    used.add(candidate)
    return candidate


def github_anchor(heading: str) -> str:
    """GitHub-style anchor: lowercase, delete punctuation (CJK included),
    whitespace -> '-'.  ``附录：一键运行清单`` -> ``附录一键运行清单``;
    ``BM25 关键词`` -> ``bm25-关键词``.
    """
    s = nfc(heading).strip().lower()
    s = _GITHUB_PUNCT_RE.sub("", s)
    s = _GITHUB_SPACE_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


class WikiPaths:
    """Resolves every location the tool reads/writes under a repository.

    The output locale follows the target repository: explicit argument wins,
    else the persisted ``state/locale`` file, else the default (zh).
    """

    def __init__(self, repo_root: str | Path, locale: str | None = None):
        self.repo_root = Path(repo_root).resolve()
        self._locale = locale

    @property
    def locale(self) -> str:
        if self._locale is None:
            f = self.state_dir / "locale"
            try:
                value = f.read_text(encoding="utf-8").strip()
            except OSError:
                value = ""
            self._locale = value if value in SUPPORTED else DEFAULT_LOCALE
        return self._locale

    def persist_locale(self, locale: str) -> None:
        """Pin the output locale for this and all later commands."""
        if locale not in SUPPORTED:
            raise ValueError(f"unsupported locale: {locale}")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "locale").write_text(locale, encoding="utf-8")
        self._locale = locale

    @property
    def root(self) -> Path:
        return self.repo_root / ".repowiki"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def tasks_dir(self) -> Path:
        return self.state_dir / "tasks"

    @property
    def claims_dir(self) -> Path:
        return self.state_dir / "claims"

    @property
    def catalog_file(self) -> Path:
        return self.state_dir / "catalog.json"

    @property
    def knowledge_plan_file(self) -> Path:
        return self.state_dir / "knowledge.json"

    @property
    def index_file(self) -> Path:
        return self.state_dir / "index.json"

    @property
    def content_dir(self) -> Path:
        return self.root / self.locale / "content"

    @property
    def meta_dir(self) -> Path:
        return self.root / self.locale / "meta"

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge" / self.locale

    @property
    def metadata_file(self) -> Path:
        return self.meta_dir / "repowiki-metadata.json"

    @property
    def overview_file(self) -> Path:
        return self.meta_dir / "wiki-overview.md"

    def ensure(self) -> None:
        for d in (self.state_dir, self.tasks_dir, self.claims_dir, self.content_dir, self.meta_dir):
            d.mkdir(parents=True, exist_ok=True)

    def task_spec(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.md"
