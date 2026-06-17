import json
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


def test_json_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\n")
    assert run([str(path), "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert {d["code"] for d in data} == {"unpinned", "missing-hash"}
    keys = {"file", "line", "code", "message", "requirement", "name"}
    assert all(keys <= set(d) for d in data)


def test_allowlist_filters_by_name(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\nrequests>=2.0\n")
    assert run([str(path), "--allow", "flask"]) == 1
    out = capsys.readouterr().out
    assert "requests" in out
    assert "flask" not in out


def test_allowlist_can_clear_all(tmp_path: Path) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\nrequests>=2.0\n")
    assert run([str(path), "--allow", "flask", "--allow", "requests"]) == 0
