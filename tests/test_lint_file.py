from pathlib import Path

from pinlint import lint_file


def test_follows_includes(tmp_path: Path) -> None:
    (tmp_path / "base.txt").write_text("flask==1.0 --hash=sha256:a\n-r child.txt\n")
    (tmp_path / "child.txt").write_text("django>=2 --hash=sha256:b\n")
    findings = lint_file(
        tmp_path / "base.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
    )
    assert [f.code for f in findings] == ["unpinned"]
    assert findings[0].file.endswith("child.txt")


def test_no_follow(tmp_path: Path) -> None:
    (tmp_path / "base.txt").write_text("flask==1.0 --hash=sha256:a\n-r child.txt\n")
    (tmp_path / "child.txt").write_text("django>=2\n")
    findings = lint_file(
        tmp_path / "base.txt", require_hashes=True, allow_unpinned=False, follow_includes=False
    )
    assert findings == []


def test_include_cycle_is_safe(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("-r b.txt\n")
    (tmp_path / "b.txt").write_text("-r a.txt\nflask>=1\n")
    findings = lint_file(
        tmp_path / "a.txt", require_hashes=False, allow_unpinned=False, follow_includes=True
    )
    assert [f.code for f in findings] == ["unpinned"]


def test_missing_file_reports_io_error(tmp_path: Path) -> None:
    findings = lint_file(
        tmp_path / "nope.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
    )
    assert findings[0].code == "io-error"
