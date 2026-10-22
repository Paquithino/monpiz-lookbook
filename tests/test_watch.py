from __future__ import annotations

import os
from pathlib import Path

from monpiz_lookbook.builder import BuildOptions
from monpiz_lookbook.watch import build_command, changed_files, snapshot


def _touch(path: Path, mtime_ns: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    os.utime(path, ns=(mtime_ns, mtime_ns))  # explicit times: no flaky timing


def test_changed_files_reports_modified_added_and_removed(tmp_path: Path) -> None:
    kept, edited, removed = tmp_path / "kept.yaml", tmp_path / "edited.yaml", tmp_path / "removed.jpg"
    for path in (kept, edited, removed):
        _touch(path, 1_000)
    before = snapshot([tmp_path])

    _touch(edited, 2_000)
    removed.unlink()
    added = tmp_path / "sub" / "added.png"
    _touch(added, 1_000)

    assert changed_files(before, snapshot([tmp_path])) == {edited, removed, added}


def test_snapshot_ignores_python_caches(tmp_path: Path) -> None:
    _touch(tmp_path / "__pycache__" / "theme.cpython-313.pyc", 1_000)
    _touch(tmp_path / "theme.py", 1_000)
    assert set(snapshot([tmp_path])) == {tmp_path / "theme.py"}


def test_rebuild_command_forwards_every_option() -> None:
    options = BuildOptions(Path("c/l.yaml"), Path("a"), Path("out.pdf"), dpi=150)
    command = build_command(options)
    assert command[1:4] == ["-m", "monpiz_lookbook", "build"]
    assert command[4:] == ["--content", "c/l.yaml", "--assets", "a", "--output", "out.pdf", "--dpi", "150"]
