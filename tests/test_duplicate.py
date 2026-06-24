"""Tests for the duplicate-requirement rule (v0.6.0).

A project listed on more than one requirement line in a single file is flagged.
Comparison is by PEP 503 normalized name; lines guarded by different environment
markers are mutually exclusive and are not duplicates.
"""

import json
from pathlib import Path

import pytest

from pinlint import lint_text
from pinlint.cli import run


def _dups(text: str) -> list[tuple[int, str]]:
    """Return (line, name) for every duplicate finding, in order."""
    findings = lint_text(
        text, source="req.txt", require_hashes=False, allow_unpinned=True
    )
    return [(f.line, f.name) for f in findings if f.code == "duplicate"]


def test_same_pin_twice_flags_one_duplicate() -> None:
    text = "requests==2.0\nrequests==2.0\n"
    dups = _dups(text)
    assert dups == [(2, "requests")]


def test_three_occurrences_flag_two_duplicates() -> None:
    text = "requests==2.0\nrequests==2.1\nrequests==2.2\n"
    dups = _dups(text)
    assert dups == [(2, "requests"), (3, "requests")]


def test_message_cites_first_line() -> None:
    findings = lint_text(
        "requests==2.0\nrequests==2.0\n",
        source="req.txt",
        require_hashes=False,
        allow_unpinned=True,
    )
    [dup] = [f for f in findings if f.code == "duplicate"]
    assert "requests" in dup.message
    assert "line 1" in dup.message


def test_case_insensitive_normalization() -> None:
    assert _dups("Flask==2.0\nflask==2.0\n") == [(2, "flask")]


def test_separator_normalization() -> None:
    # typing-extensions and typing_extensions normalize to the same project.
    assert _dups("typing-extensions==4.0\ntyping_extensions==4.0\n") == [
        (2, "typing-extensions")
    ]


def test_dot_separator_normalization() -> None:
    assert _dups("zope.interface==5.0\nzope-interface==5.0\n") == [
        (2, "zope-interface")
    ]


def test_differing_markers_not_flagged() -> None:
    text = 'foo==1 ; python_version < "3.9"\nfoo==2 ; python_version >= "3.9"\n'
    assert _dups(text) == []


def test_same_marker_is_flagged() -> None:
    text = 'foo==1 ; python_version < "3.9"\nfoo==2 ; python_version < "3.9"\n'
    assert _dups(text) == [(2, "foo")]


def test_marker_versus_no_marker_not_flagged() -> None:
    # A marked line and an unconditional line carry different marker keys, so the rule
    # stays conservative and does not flag them. The "markers differ -> do not flag"
    # policy favors avoiding false positives over catching partial-overlap cases.
    text = 'foo==1\nfoo==2 ; python_version < "3.9"\n'
    assert _dups(text) == []


def test_differing_extras_are_duplicates_of_base() -> None:
    # pip resolves a single version per project regardless of extras requested.
    assert _dups("foo[a]==1\nfoo[b]==1\n") == [(2, "foo")]


def test_distinct_packages_not_flagged() -> None:
    text = "flask==2.0\nrequests==2.0\ndjango==4.0\n"
    assert _dups(text) == []


def test_clean_file_has_no_duplicate_findings() -> None:
    text = "flask==1.0 --hash=sha256:a\nrequests==2.0 --hash=sha256:b\n"
    findings = lint_text(
        text, source="req.txt", require_hashes=True, allow_unpinned=False
    )
    assert [f for f in findings if f.code == "duplicate"] == []


def test_duplicate_off_silences_it(tmp_path: Path) -> None:
    req = tmp_path / "r.txt"
    req.write_text("requests==2.0\nrequests==2.0\n")
    code = run([str(req), "--no-hashes", "--off", "duplicate"])
    assert code == 0


def test_duplicate_error_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    req = tmp_path / "r.txt"
    req.write_text("requests==2.0\nrequests==2.0\n")
    # Default severity for duplicate is warning, so a clean-but-duplicated, pinned,
    # no-hash run exits 0 on the duplicate alone.
    assert run([str(req), "--no-hashes"]) == 0
    capsys.readouterr()
    # Escalated to error -> exit 1.
    assert run([str(req), "--no-hashes", "--error", "duplicate"]) == 1


def test_duplicate_appears_in_sarif(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    req = tmp_path / "r.txt"
    req.write_text("requests==2.0\nrequests==2.0\n")
    run([str(req), "--no-hashes", "--format", "sarif"])
    doc = json.loads(capsys.readouterr().out)
    results = doc["runs"][0]["results"]
    dup_results = [r for r in results if r["ruleId"] == "duplicate"]
    assert len(dup_results) == 1
    assert dup_results[0]["level"] == "warning"
    rule_ids = [rule["id"] for rule in doc["runs"][0]["tool"]["driver"]["rules"]]
    assert "duplicate" in rule_ids
