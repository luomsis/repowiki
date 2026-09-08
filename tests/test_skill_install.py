"""skill install / status: bundled copy, version stamp, agent target mapping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repowiki import cli
from repowiki.skill_install import STAMP_NAME, bundled_skill

FAKE_VERSION = "9.9.9"


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


@pytest.fixture
def fake_version(monkeypatch):
    from repowiki import skill_install

    monkeypatch.setattr(skill_install, "__version__", FAKE_VERSION)
    return FAKE_VERSION


def test_bundled_skill_ships_in_package():
    skill = bundled_skill()
    assert {"SKILL.md", "SKILL.en.md"} <= {p.name for p in skill.iterdir()}
    assert "name: repowiki" in (skill / "SKILL.md").read_text(encoding="utf-8")


def test_install_default_targets_shared_agents_dir(fake_home, fake_version, capsys):
    assert cli.main(["skill", "install", "--json"]) == 0
    dest = fake_home / ".agents" / "skills" / "repowiki"
    assert (dest / "SKILL.md").exists()
    assert (dest / "SKILL.en.md").exists()
    assert (dest / STAMP_NAME).read_text(encoding="utf-8").strip() == FAKE_VERSION
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["targets"] == [{"target": str(dest), "action": "installed",
                               "previous": None, "version": FAKE_VERSION}]


def test_install_agent_and_custom_target(fake_home, fake_version, capsys, tmp_path):
    custom = tmp_path / "custom-skills"
    argv = ["skill", "install", "--agent", "claude", "--target", str(custom), "--json"]
    assert cli.main(argv) == 0
    targets = {Path(t["target"]) for t in json.loads(capsys.readouterr().out)["targets"]}
    assert fake_home / ".claude" / "skills" / "repowiki" in targets
    assert custom / "repowiki" in targets


def test_install_idempotent_then_updates_stale_copy(fake_home, fake_version, capsys):
    cli.main(["skill", "install", "--json"])
    capsys.readouterr()
    cli.main(["skill", "install", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["targets"][0]["action"] == "current"

    stamp = fake_home / ".agents" / "skills" / "repowiki" / STAMP_NAME
    stamp.write_text("0.4.0\n", encoding="utf-8")
    cli.main(["skill", "install", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["targets"][0]["action"] == "updated"
    assert out["targets"][0]["previous"] == "0.4.0"
    assert stamp.read_text(encoding="utf-8").strip() == FAKE_VERSION


def test_install_human_output_mentions_restart(fake_home, fake_version, capsys):
    assert cli.main(["skill", "install"]) == 0
    text = capsys.readouterr().out
    assert "installed:" in text and "restart" in text


def test_status_reports_all_states(fake_home, fake_version, capsys, tmp_path):
    # "absent" = no skill dir; None = dir with SKILL.md but no stamp; str = stamp value
    spec = {"none": "absent", "manual": None, "old": "0.1.0", "same": FAKE_VERSION}
    expected = {"none": "missing", "manual": "unstamped",
                "old": "outdated", "same": "current"}
    argv = ["skill", "status", "--json"]
    for name, stamp in spec.items():
        parent = tmp_path / name
        if stamp != "absent":
            skill_dir = parent / "repowiki"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("skill", encoding="utf-8")
            if stamp is not None:
                (skill_dir / STAMP_NAME).write_text(stamp, encoding="utf-8")
        argv += ["--target", str(parent)]
    assert cli.main(argv) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["package_version"] == FAKE_VERSION
    states = {Path(t["target"]).parent.name: t["state"] for t in out["targets"]}
    assert states == expected


def test_status_detects_default_dir(fake_home, fake_version, capsys):
    assert cli.main(["skill", "status", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["targets"] == [
        {"target": str(fake_home / ".agents" / "skills" / "repowiki"), "state": "missing"}]
