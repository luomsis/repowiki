"""Scanner tests: git vs walk parity, ignores, truncation, key files."""

from __future__ import annotations

from pathlib import Path

from conftest import make_repo

from repowiki.scanner import scan, _render_tree


def test_scan_walk_finds_code_files(repo):
    inv = scan(repo)
    paths = {f.path for f in inv.files}
    assert "src/demo/main.py" in paths
    assert "README.md" in paths
    assert "scripts/build.sh" in paths
    assert inv.code_file_count >= 10
    assert "README.md" in inv.key_files
    assert "pyproject.toml" in inv.key_files


def test_scan_git_matches_walk(repo, tmp_path):
    git_repo = make_repo(tmp_path, git=True)
    walk_paths = {f.path for f in scan(repo).files}
    git_paths = {f.path for f in scan(git_repo).files}
    assert walk_paths == git_paths


def test_scan_ignores_build_dirs(repo):
    (repo / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "node_modules" / "pkg" / "index.js").write_text("x\n")
    (repo / ".qoder" / "repowiki").mkdir(parents=True)
    (repo / ".qoder" / "repowiki" / "x.md").write_text("x\n")
    inv = scan(repo)
    assert not any("node_modules" in f.path for f in inv.files)
    assert not any(".qoder" in f.path for f in inv.files)


def test_scan_skips_binary(repo):
    (repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    inv = scan(repo)
    assert not any(f.path == "logo.png" for f in inv.files)


def test_scan_empty_repo(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    inv = scan(empty)
    assert inv.files == []
    assert inv.code_file_count == 0


def test_tree_summary_truncates_per_dir(repo):
    big = repo / "many"
    big.mkdir()
    for i in range(30):
        (big / f"f{i}.py").write_text("x = 1\n")
    tree = scan(repo).tree_summary
    assert "… (+10 more)" in tree


def test_tree_summary_total_cap():
    files = []
    for d in range(500):
        for i in range(3):
            files.append(type("F", (), {"path": f"d{d}/f{i}.py"})())
    tree = _render_tree(files)
    assert tree.count("\n") <= 410
