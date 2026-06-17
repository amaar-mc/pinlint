"""Tests for per-rule severity configuration (v0.5.0).

Golden tests for severity.py and the --error / --warning / --off CLI flags.
"""

import json
from pathlib import Path

import pytest

from pinlint import (
    AnnotatedFinding,
    Finding,
    apply_severities,
    default_severity_map,
    known_codes,
    to_sarif_annotated,
)
from pinlint.cli import run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _f(
    code: str,
    file: str = "r.txt",
    req: str = "flask>=1",
    name: str = "flask",
    line: int = 1,
) -> Finding:
    return Finding(file=file, line=line, code=code, message="test", requirement=req, name=name)


# ---------------------------------------------------------------------------
# Unit tests: default_severity_map
# ---------------------------------------------------------------------------


def test_default_severity_map_returns_all_codes() -> None:
    sev = default_severity_map()
    assert set(sev.keys()) == known_codes()


def test_default_severity_map_matches_sarif_catalog() -> None:
    """Default severities must match the SARIF _RULES catalog in sarif.py."""
    sev = default_severity_map()
    assert sev["unpinned"] == "error"
    assert sev["missing-hash"] == "error"
    assert sev["unpinnable"] == "warning"
    assert sev["parse-error"] == "error"
    assert sev["io-error"] == "error"


def test_default_severity_map_is_independent_copy() -> None:
    a = default_severity_map()
    b = default_severity_map()
    a["unpinned"] = "warning"
    assert b["unpinned"] == "error"


# ---------------------------------------------------------------------------
# Unit tests: known_codes
# ---------------------------------------------------------------------------


def test_known_codes_contains_all_rule_codes() -> None:
    assert known_codes() == frozenset(
        ["unpinned", "missing-hash", "unpinnable", "parse-error", "io-error"]
    )


# ---------------------------------------------------------------------------
# Unit tests: apply_severities
# ---------------------------------------------------------------------------


def test_apply_severities_default_annotates_correctly() -> None:
    sev = default_severity_map()
    findings = [_f("unpinned"), _f("unpinnable")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    assert len(annotated) == 2
    assert annotated[0].effective_severity == "error"
    assert annotated[1].effective_severity == "warning"


def test_apply_severities_off_drops_finding() -> None:
    sev = default_severity_map()
    sev["missing-hash"] = "off"
    findings = [_f("unpinned"), _f("missing-hash")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    assert len(annotated) == 1
    assert annotated[0].code == "unpinned"


def test_apply_severities_warning_downgrade() -> None:
    sev = default_severity_map()
    sev["unpinned"] = "warning"
    findings = [_f("unpinned")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    assert annotated[0].effective_severity == "warning"


def test_apply_severities_error_upgrade() -> None:
    sev = default_severity_map()
    sev["unpinnable"] = "error"
    findings = [_f("unpinnable")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    assert annotated[0].effective_severity == "error"


def test_apply_severities_unknown_code_raises() -> None:
    sev: dict[str, str] = {"not-a-real-code": "error"}  # type: ignore[assignment]
    with pytest.raises(ValueError, match="unknown rule code 'not-a-real-code'"):
        apply_severities(findings=[], severity_map=sev)  # type: ignore[arg-type]


def test_apply_severities_preserves_order() -> None:
    sev = default_severity_map()
    findings = [_f("unpinned", line=1), _f("missing-hash", line=2), _f("unpinnable", line=3)]
    annotated = apply_severities(findings=findings, severity_map=sev)
    assert [af.line for af in annotated] == [1, 2, 3]


def test_annotated_finding_delegates_attributes() -> None:
    f = _f("unpinned")
    af = AnnotatedFinding(finding=f, effective_severity="error")
    assert af.file == f.file
    assert af.line == f.line
    assert af.code == f.code
    assert af.message == f.message
    assert af.requirement == f.requirement
    assert af.name == f.name
    assert af.effective_severity == "error"
    assert af.finding is f


# ---------------------------------------------------------------------------
# SARIF tests: to_sarif_annotated
# ---------------------------------------------------------------------------


def test_sarif_annotated_reflects_warning_override() -> None:
    sev = default_severity_map()
    sev["unpinned"] = "warning"
    findings = [_f("unpinned")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    doc = to_sarif_annotated(annotated, tool_version="0.5.0")
    result = doc["runs"][0]["results"][0]  # type: ignore[index]
    assert result["level"] == "warning"
    assert result["ruleId"] == "unpinned"


def test_sarif_annotated_reflects_error_upgrade() -> None:
    sev = default_severity_map()
    sev["unpinnable"] = "error"
    findings = [_f("unpinnable")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    doc = to_sarif_annotated(annotated, tool_version="0.5.0")
    result = doc["runs"][0]["results"][0]  # type: ignore[index]
    assert result["level"] == "error"


def test_sarif_annotated_empty_when_all_off() -> None:
    sev = default_severity_map()
    for k in sev:
        sev[k] = "off"  # type: ignore[literal-required]
    findings = [_f("unpinned"), _f("missing-hash")]
    annotated = apply_severities(findings=findings, severity_map=sev)
    doc = to_sarif_annotated(annotated, tool_version="0.5.0")
    assert doc["runs"][0]["results"] == []  # type: ignore[index]


# ---------------------------------------------------------------------------
# CLI golden tests
# ---------------------------------------------------------------------------


def test_warning_unpinned_exits_zero_when_only_unpinned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--warning unpinned: only unpinned findings -> warnings -> exit 0."""
    req = tmp_path / "r.txt"
    # unpinned and missing-hash; downgrade both to warnings
    req.write_text("flask>=1.0\n")
    code = run(
        [str(req), "--warning", "unpinned", "--warning", "missing-hash"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "warning" in out
    assert "unpinned" in out


def test_warning_unpinned_exits_one_when_other_errors_remain(
    tmp_path: Path,
) -> None:
    """--warning unpinned still exits 1 if a non-downgraded error remains."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1.0\n")
    # Downgrade unpinned to warning; missing-hash remains error.
    code = run([str(req), "--warning", "unpinned"])
    assert code == 1


def test_off_missing_hash_removes_those_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--off missing-hash: missing-hash findings vanish from output."""
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0\n")  # pinned but no hash -> only missing-hash
    code = run([str(req), "--off", "missing-hash"])
    assert code == 0
    out = capsys.readouterr().out
    assert "missing-hash" not in out


def test_error_unpinnable_escalates_and_exits_one(
    tmp_path: Path,
) -> None:
    """--error unpinnable: unpinnable upgraded from warning to error -> exit 1."""
    req = tmp_path / "r.txt"
    req.write_text("-e .\n")  # editable -> unpinnable (normally warning)
    # Without override the default is warning -> exit 0 (no errors).
    default_code = run([str(req), "--no-hashes"])
    assert default_code == 0
    # With --error unpinnable -> error -> exit 1.
    escalated_code = run([str(req), "--no-hashes", "--error", "unpinnable"])
    assert escalated_code == 1


def test_unknown_code_raises_in_apply_severities() -> None:
    """apply_severities raises ValueError for an unknown rule code."""
    sev: dict[str, str] = {"bad-code": "error"}  # type: ignore[assignment]
    with pytest.raises(ValueError, match="unknown rule code 'bad-code'"):
        apply_severities(findings=[], severity_map=sev)  # type: ignore[arg-type]


def test_unknown_code_in_cli_flag_exits_two(tmp_path: Path) -> None:
    """--error with unknown CODE exits 2 with a clear error message."""
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    code = run([str(req), "--error", "not-a-rule"])
    assert code == 2


def test_unknown_code_warning_flag_exits_two(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    code = run([str(req), "--warning", "bad-code"])
    assert code == 2


def test_unknown_code_off_flag_exits_two(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    code = run([str(req), "--off", "bad-code"])
    assert code == 2


def test_sarif_level_reflects_warning_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--format sarif + --warning unpinned: SARIF level for unpinned finding is 'warning'."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1.0 --hash=sha256:a\n")  # unpinned only (hash present)
    run([str(req), "--format", "sarif", "--warning", "unpinned"])
    doc = json.loads(capsys.readouterr().out)
    results = doc["runs"][0]["results"]
    unpinned_results = [r for r in results if r["ruleId"] == "unpinned"]
    assert len(unpinned_results) == 1
    assert unpinned_results[0]["level"] == "warning"


def test_default_no_flags_matches_040_behavior(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no severity flags the behavior is identical to 0.4.0: findings -> exit 1."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1.0\n")
    code = run([str(req)])
    assert code == 1
    out = capsys.readouterr().out
    assert "unpinned" in out
    assert "missing-hash" in out


def test_default_clean_file_exits_zero(tmp_path: Path) -> None:
    """With no severity flags a clean file still exits 0."""
    req = tmp_path / "r.txt"
    req.write_text("flask==1.0 --hash=sha256:a\n")
    assert run([str(req)]) == 0


def test_json_format_includes_effective_severity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--format json output includes an effective_severity field on each finding."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1.0\n")
    run([str(req), "--format", "json", "--warning", "unpinned"])
    data = json.loads(capsys.readouterr().out)
    for entry in data:
        assert "effective_severity" in entry
    unpinned = [e for e in data if e["code"] == "unpinned"]
    assert all(e["effective_severity"] == "warning" for e in unpinned)


def test_all_off_exits_zero_and_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Silencing all active rules yields no output and exit 0."""
    req = tmp_path / "r.txt"
    req.write_text("flask>=1.0\n")
    code = run([str(req), "--off", "unpinned", "--off", "missing-hash"])
    assert code == 0
    out = capsys.readouterr().out
    assert out.strip() == ""
