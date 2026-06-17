from pathlib import Path

import pytest

from pinlint.cli import run


def test_clean_file_exits_zero(tmp_path: Path) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask==1.0 --hash=sha256:a\n")
    assert run([str(path)]) == 0


def test_findings_exit_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\n")
    assert run([str(path)]) == 1
    out = capsys.readouterr().out
    assert "unpinned" in out
    assert "missing-hash" in out


def test_flags_relax_rules(tmp_path: Path) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\n")
    assert run([str(path), "--allow-unpinned", "--no-hashes"]) == 0
