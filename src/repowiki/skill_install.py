"""Install the bundled agent skill into coding-agent skill directories.

The skill files ship inside the wheel (``repowiki/skills/repowiki/``), so a
pip install carries them; these commands copy that bundled copy into the
user-scope skills directories of the supported agents and stamp the installed
version, so ``skill status`` can flag manual or stale copies.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from . import __version__
from .output import emit

SKILL_NAME = "repowiki"
STAMP_NAME = ".repowiki-skill-version"

AGENTS = ("agents", "claude", "codex", "zcode", "cursor", "opencode")


def agent_skills_dirs() -> dict[str, Path]:
    """User-scope skills directory per agent; rebuilt per call (tests patch Path.home)."""
    home = Path.home()
    return {
        "agents": home / ".agents" / "skills",
        "claude": home / ".claude" / "skills",
        "codex": home / ".codex" / "skills",
        "zcode": home / ".zcode" / "skills",
        "cursor": home / ".cursor" / "skills",
        "opencode": home / ".config" / "opencode" / "skills",
    }


def bundled_skill() -> resources.abc.Traversable:
    return resources.files("repowiki") / "skills" / SKILL_NAME


def _resolve_targets(agent: list[str] | None, target: list[str] | None) -> list[Path]:
    dirs = agent_skills_dirs()
    targets: list[Path] = [dirs[name] for name in (agent or [])]
    targets += [Path(t).expanduser() for t in (target or [])]
    if not targets:  # no agent/target given: the shared cross-tool directory
        targets = [dirs["agents"]]
    unique: list[Path] = []
    for t in targets:
        if t not in unique:
            unique.append(t)
    return unique


def _copy_tree(src: resources.abc.Traversable, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name == STAMP_NAME:
            continue
        if item.is_dir():
            _copy_tree(item, dest / item.name)
        else:
            (dest / item.name).write_bytes(item.read_bytes())


def _read_stamp(skill_dir: Path) -> str | None:
    try:
        return (skill_dir / STAMP_NAME).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def run_skill_install(args, paths=None) -> int:
    src = bundled_skill()
    results = []
    for parent in _resolve_targets(args.agent, args.target):
        skill_dir = parent / SKILL_NAME
        previous = _read_stamp(skill_dir)
        if previous == __version__ and (skill_dir / "SKILL.md").exists():
            results.append({"target": str(skill_dir), "action": "current",
                            "version": __version__})
            continue
        _copy_tree(src, skill_dir)
        (skill_dir / STAMP_NAME).write_text(__version__ + "\n", encoding="utf-8")
        results.append({"target": str(skill_dir),
                        "action": "installed" if previous is None else "updated",
                        "previous": previous, "version": __version__})
    emit({"ok": True, "targets": results,
          "hint": "restart the agent client session to pick up the new skill; "
                  "rerun after upgrading repowiki"},
         _install_human, args.json)
    return 0


def run_skill_status(args, paths=None) -> int:
    results = []
    for parent in _resolve_targets(args.agent, args.target):
        skill_dir = parent / SKILL_NAME
        if not (skill_dir / "SKILL.md").exists():
            results.append({"target": str(skill_dir), "state": "missing"})
            continue
        stamp = _read_stamp(skill_dir)
        if stamp is None:
            results.append({"target": str(skill_dir), "state": "unstamped"})
        elif _version_tuple(stamp) < _version_tuple(__version__):
            results.append({"target": str(skill_dir), "state": "outdated",
                            "version": stamp})
        elif _version_tuple(stamp) > _version_tuple(__version__):
            results.append({"target": str(skill_dir), "state": "newer",
                            "version": stamp})
        else:
            results.append({"target": str(skill_dir), "state": "current",
                            "version": stamp})
    emit({"ok": True, "package_version": __version__, "targets": results},
         _status_human, args.json)
    return 0


def _install_human(result: dict) -> str:
    lines = []
    for t in result["targets"]:
        if t["action"] == "current":
            lines.append(f"already current: {t['target']} ({t['version']})")
        elif t["action"] == "installed":
            lines.append(f"installed: {t['target']} ({t['version']})")
        else:
            lines.append(f"updated: {t['target']} ({t['previous']} -> {t['version']})")
    lines.append(result["hint"])
    return "\n".join(lines)


_STATUS_COPY = {
    "missing": "not installed",
    "unstamped": "unknown version (manual copy? rerun skill install to manage)",
    "current": "up to date",
}


def _status_human(result: dict) -> str:
    lines = []
    for t in result["targets"]:
        if t["state"] in ("outdated", "newer"):
            lines.append(f"{'outdated' if t['state'] == 'outdated' else 'newer than package'}: "
                         f"{t['target']} ({t['version']} vs package {result['package_version']})")
        else:
            lines.append(f"{_STATUS_COPY[t['state']]}: {t['target']}")
    return "\n".join(lines)
