"""Repository scanner: deterministic file inventory for planning.

Uses ``git ls-files`` when available (accurate .gitignore handling), else
falls back to a manual walk. Skips binaries, VCS/build/vendor directories
and the tool's own output (``.qoder``).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

CODE_EXTS = {
    "py", "ts", "tsx", "js", "jsx", "mjs", "cjs", "go", "rs", "java", "kt",
    "rb", "c", "h", "cc", "cpp", "hpp", "cs", "swift", "scala", "sh", "bash",
    "sql", "php", "vue", "svelte", "dart", "lua", "pl",
}

LANG_BY_EXT = {
    "py": "python", "ts": "typescript", "tsx": "typescript", "js": "javascript",
    "jsx": "javascript", "mjs": "javascript", "cjs": "javascript", "go": "go",
    "rs": "rust", "java": "java", "kt": "kotlin", "rb": "ruby", "c": "c",
    "h": "c", "cc": "cpp", "cpp": "cpp", "hpp": "cpp", "cs": "csharp",
    "swift": "swift", "scala": "scala", "sh": "shell", "bash": "shell",
    "sql": "sql", "php": "php", "vue": "vue", "svelte": "svelte",
    "dart": "dart", "lua": "lua", "pl": "perl",
    "md": "markdown", "rst": "markdown", "txt": "text",
    "yaml": "yaml", "yml": "yaml", "toml": "toml", "json": "json",
    "ini": "ini", "cfg": "ini", "html": "html", "css": "css", "scss": "scss",
    "xml": "xml",
}

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "dist", "target", "build",
    "out", "__pycache__", ".qoder", ".idea", ".vscode", ".next", ".tox",
    ".eggs", "coverage", ".mypy_cache", ".pytest_cache", "site-packages",
    ".ruff_cache", ".hypothesis",
}

KEY_FILE_GLOBS = [
    "README*", "pyproject.toml", "setup.py", "setup.cfg", "package.json",
    "go.mod", "Cargo.toml", "docker-compose*.yml", "docker-compose*.yaml",
    "Makefile", "requirements*.txt", "pom.xml", "build.gradle", "*.gemspec",
]

MAX_TEXT_BYTES = 2 * 1024 * 1024  # larger files are listed but not counted by LOC
_PER_DIR_CAP = 20
_MAX_SUMMARY_LINES = 400


@dataclass
class FileEntry:
    path: str
    loc: int
    lang: str
    is_code: bool
    size: int


@dataclass
class Inventory:
    repo_root: str
    files: list[FileEntry] = field(default_factory=list)
    key_files: list[str] = field(default_factory=list)
    tree_summary: str = ""
    code_file_count: int = 0

    def to_dict(self) -> dict:
        return {
            "repo_root": self.repo_root,
            "files": [f.__dict__ for f in self.files],
            "key_files": self.key_files,
            "tree_summary": self.tree_summary,
            "code_file_count": self.code_file_count,
        }

    def known_paths(self) -> set[str]:
        return {f.path for f in self.files}


def _git_ls_files(root: Path) -> list[str] | None:
    if not (root / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(root), capture_output=True, check=True, timeout=120,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def _walk_files(root: Path) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os_walk_pruned(root):
        for name in filenames:
            rel = (Path(dirpath) / name).relative_to(root).as_posix()
            found.append(rel)
    return sorted(found)


def os_walk_pruned(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".git")]
        yield dirpath, dirnames, filenames


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\0" in fh.read(8192)
    except OSError:
        return True


def _count_loc(path: Path, size: int) -> int:
    if size > MAX_TEXT_BYTES:
        return 0
    try:
        with open(path, "rb") as fh:
            return fh.read().count(b"\n")
    except OSError:
        return 0


def scan(repo_root: str | Path) -> Inventory:
    root = Path(repo_root).resolve()
    rels = _git_ls_files(root)
    if rels is None:
        rels = _walk_files(root)
    else:
        rels = [r for r in rels if not any(part in IGNORE_DIRS for part in Path(r).parts[:-1])]

    files: list[FileEntry] = []
    for rel in sorted(rels):
        p = root / rel
        if not p.is_file() or _is_binary(p):
            continue
        size = p.stat().st_size
        ext = p.suffix.lstrip(".").lower()
        no_ext = p.name.lower()
        lang = LANG_BY_EXT.get(ext, "" )
        if not lang and no_ext in {"dockerfile", "makefile", "procfile"}:
            lang = no_ext.lower()
        is_code = ext in CODE_EXTS
        files.append(FileEntry(path=rel, loc=_count_loc(p, size), lang=lang, is_code=is_code, size=size))

    inv = Inventory(
        repo_root=str(root),
        files=files,
        code_file_count=sum(1 for f in files if f.is_code),
    )
    inv.key_files = sorted(
        {f.path for f in files for pat in KEY_FILE_GLOBS if Path(f.path).parent == Path(".") and Path(f.path).match(pat)}
    )
    inv.tree_summary = _render_tree(files)
    return inv


def _render_tree(files: list[FileEntry]) -> str:
    """Compact repo tree, capped per directory and in total size."""
    by_dir: dict[str, list[str]] = {}
    for f in files:
        by_dir.setdefault(str(Path(f.path).parent) if str(Path(f.path).parent) != "." else "", []).append(Path(f.path).name)

    lines: list[str] = ["<repo>/"]
    dirs = sorted(by_dir)
    for i, d in enumerate(dirs):
        names = by_dir[d]
        shown = names[:_PER_DIR_CAP]
        prefix = "" if d == "" else f"{d}/"
        lines.append(f"{prefix} ({len(names)} files)")
        for name in shown:
            lines.append(f"  {name}")
        if len(names) > _PER_DIR_CAP:
            lines.append(f"  … (+{len(names) - _PER_DIR_CAP} more)")
        if len(lines) > _MAX_SUMMARY_LINES:
            lines.append(f"… (tree truncated at {_MAX_SUMMARY_LINES} lines, {len(dirs) - i - 1} dirs omitted)")
            break
    return "\n".join(lines)
