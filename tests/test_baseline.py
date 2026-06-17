"""Tests for baseline.py and the --write-baseline / --baseline CLI flags."""

import json
from pathlib import Path

import pytest

from pinlint import (
    Finding,
    build_baseline,
    filter_by_baseline,
    lint_file,
    load_baseline,
    serialize_baseline,
)
from pinlint.cli import run

# ---------------------------------------------------------------------------
# Unit tests for pure functions
# ---------------------------------------------------------------------------


def _f(code: str, file: str = "r.txt", req: str = "flask>=1", name: str = "flask") -> Finding:
    return Finding(file=file, line=1, code=code, message="test", requirement=req, name=name)


def test_build_baseline_deduplicates() -> None:
    f = _f("unpinned")
    result = build_baseline(findings=[f, f])
    assert len(result) == 1


def test_build_baseline_sorted() -> None:
    findings = [
        _f("unpinned", req="requests>=1", name="requests"),
        _f("missing-hash", req="flask>=1", name="flask"),
        _f("unpinned", req="flask>=1", name="flask"),
    ]
    result = build_baseline(findings=findings)
    keys = [(e["code"], e["name"]) for e in result]
    assert keys == sorted(keys)


def test_build_baseline_contains_expected_fields() -> None:
    f = _f("unpinned")
    [entry] = build_baseline(findings=[f])
    assert set(entry.keys()) == {"code", "file", "requirement", "name"}
    assert entry["code"] == "unpinned"
    assert entry["file"] == "r.txt"
    assert entry["requirement"] == "flask>=1"
    assert entry["name"] == "flask"


def test_serialize_round_trip() -> None:
    findings = [_f("unpinned"), _f("missing-hash")]
    text = serialize_baseline(findings=findings, tool_version="0.4.0")
    doc = json.loads(text)
    assert doc["tool"] == "pinlint"
    assert doc["version"] == "0.4.0"
    assert isinstance(doc["findings"], list)
    loaded = load_baseline(text=text)
    assert len(loaded) == 2


def test_serialize_is_deterministic() -> None:
    findings = [
        _f("unpinned", req="requests>=1", name="requests"),
        _f("missing-hash", req="flask>=1", name="flask"),
    ]
    t1 = serialize_baseline(findings=findings, tool_version="0.4.0")
    t2 = serialize_baseline(findings=list(reversed(findings)), tool_version="0.4.0")
    assert t1 == t2


def test_serialize_ends_with_newline() -> None:
    text = serialize_baseline(findings=[], tool_version="0.4.0")
    assert text.endswith("\n")


def test_load_baseline_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        load_baseline(text="not json")


def test_load_baseline_rejects_missing_findings_key() -> None:
    with pytest.raises(ValueError, match="missing the 'findings' key"):
        load_baseline(text=json.dumps({"tool": "pinlint"}))


def test_load_baseline_rejects_non_array_findings() -> None:
    with pytest.raises(ValueError, match="must be a JSON array"):
        load_baseline(text=json.dumps({"findings": "bad"}))


def test_load_baseline_rejects_non_object_entry() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_baseline(text=json.dumps({"findings": ["not-a-dict"]}))


def test_load_baseline_rejects_missing_field() -> None:
    entry = {"code": "unpinned", "file": "r.txt", "requirement": "flask>=1"}
    with pytest.raises(ValueError, match="missing field 'name'"):
        load_baseline(text=json.dumps({"findings": [entry]}))


def test_filter_by_baseline_suppresses_matching() -> None:
    f = _f("unpinned")
    baseline = build_baseline(findings=[f])
    remaining = filter_by_baseline(findings=[f], baseline=baseline)
    assert remaining == []


def test_filter_by_baseline_returns_new_findings() -> None:
    old = _f("unpinned", req="flask>=1", name="flask")
    new = _f("unpinned", req="requests>=1", name="requests")
    baseline = build_baseline(findings=[old])
    remaining = filter_by_baseline(findings=[old, new], baseline=baseline)
    assert remaining == [new]


def test_filter_ignores_line_number_drift() -> None:
    """A finding on a different line but same code/file/req/name is suppressed."""
    original = Finding(
        file="r.txt", line=3, code="unpinned", message="msg", requirement="flask>=1", name="flask"
    )
    drifted = Finding(
        file="r.txt", line=99, code="unpinned", message="msg", requirement="flask>=1", name="flask"
    )
    baseline = build_baseline(findings=[original])
    remaining = filter_by_baseline(findings=[drifted], baseline=baseline)
    assert remaining == []


# ---------------------------------------------------------------------------
# CLI golden tests
# ---------------------------------------------------------------------------


def test_write_baseline_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\nrequests>=2\n")
    baseline = tmp_path / "baseline.json"
    code = run([str(req), "--write-baseline", str(baseline)])
    assert code == 0
    assert baseline.exists()
    out = capsys.readouterr().out
    assert "Baseline written" in out


def test_write_baseline_content_valid(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    run([str(req), "--write-baseline", str(baseline)])
    doc = json.loads(baseline.read_text())
    assert doc["tool"] == "pinlint"
    assert isinstance(doc["findings"], list)
    assert len(doc["findings"]) > 0


def test_baseline_suppresses_all_existing_findings(tmp_path: Path) -> None:
    """Golden: write baseline from dirty file, then --baseline suppresses all, exits 0."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\nrequests>=2\n")
    baseline = tmp_path / "baseline.json"

    # Write baseline from dirty file.
    assert run([str(req), "--write-baseline", str(baseline)]) == 0

    # Re-run with --baseline: same file, all findings suppressed.
    assert run([str(req), "--baseline", str(baseline)]) == 0


def test_baseline_surfaces_new_finding(tmp_path: Path) -> None:
    """Golden: after baselining, adding a new unpinned dep exits 1 for only that dep."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"

    # Baseline contains only flask findings.
    assert run([str(req), "--write-baseline", str(baseline)]) == 0

    # Add a new dependency.
    req.write_text("flask>=1\ndjango>=3\n")

    assert run([str(req), "--baseline", str(baseline)]) == 1


def test_baseline_surfaces_only_new_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The old baselined finding is suppressed; only the new one is printed."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    run([str(req), "--write-baseline", str(baseline)])

    req.write_text("flask>=1\ndjango>=3\n")
    run([str(req), "--baseline", str(baseline)])
    out = capsys.readouterr().out
    assert "django" in out
    assert "flask" not in out


def test_baseline_line_drift_suppressed(tmp_path: Path) -> None:
    """A baselined finding is suppressed even when its line number changes."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    run([str(req), "--write-baseline", str(baseline)])

    # Insert a pinned+hashed line above flask so flask's line number drifts.
    req.write_text("ok==1.0 --hash=sha256:abc\nflask>=1\n")

    # flask is now on line 2 instead of line 1 but fingerprint matches; still suppressed.
    assert run([str(req), "--baseline", str(baseline)]) == 0


def test_write_baseline_wins_when_both_given(tmp_path: Path) -> None:
    """When --write-baseline and --baseline are both given, --write-baseline wins."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    # Baseline does not exist yet but --write-baseline should succeed anyway.
    code = run([str(req), "--write-baseline", str(baseline), "--baseline", str(baseline)])
    assert code == 0
    assert baseline.exists()


def test_missing_baseline_file_exits_two(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    code = run([str(req), "--baseline", str(tmp_path / "nope.json")])
    assert code == 2


def test_invalid_baseline_json_exits_two(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    code = run([str(req), "--baseline", str(bad)])
    assert code == 2


def test_baseline_compose_with_format_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--baseline composes with --format json: suppressed findings absent from output."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    run([str(req), "--write-baseline", str(baseline)])
    capsys.readouterr()  # discard the "Baseline written" message

    req.write_text("flask>=1\ndjango>=3\n")
    run([str(req), "--baseline", str(baseline), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    names = {entry["name"] for entry in data}
    assert "django" in names
    assert "flask" not in names


def test_baseline_uses_lint_file_findings(tmp_path: Path) -> None:
    """--write-baseline respects the same lint options as normal runs."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    baseline = tmp_path / "baseline.json"
    # With --no-hashes and --allow-unpinned the file is clean; baseline has no findings.
    run([str(req), "--write-baseline", str(baseline), "--no-hashes", "--allow-unpinned"])
    doc = json.loads(baseline.read_text())
    assert doc["findings"] == []


def test_write_baseline_deterministic(tmp_path: Path) -> None:
    """Writing the same baseline twice produces identical files (no spurious diff)."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\nrequests>=2\n")
    b1 = tmp_path / "b1.json"
    b2 = tmp_path / "b2.json"
    run([str(req), "--write-baseline", str(b1)])
    run([str(req), "--write-baseline", str(b2)])
    assert b1.read_text() == b2.read_text()


def test_lint_file_used_for_baseline_fingerprints(tmp_path: Path) -> None:
    """Fingerprints from lint_file match what --baseline loads, so suppression works."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1\n")
    findings = lint_file(
        str(req), require_hashes=True, allow_unpinned=False, follow_includes=False
    )
    baseline = build_baseline(findings=findings)
    remaining = filter_by_baseline(findings=findings, baseline=baseline)
    assert remaining == []
