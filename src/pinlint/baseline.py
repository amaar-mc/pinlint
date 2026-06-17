"""Baseline support: suppress known findings to allow incremental adoption.

A baseline records a set of fingerprints for existing findings. On subsequent
runs, findings whose fingerprint is in the baseline are suppressed so only NEW
findings cause a non-zero exit.

Fingerprint design
------------------
The fingerprint is (code, file, requirement, name) -- deliberately excluding the
line number. Line numbers drift whenever lines are added or removed above an
existing finding. The requirement text and package name identify the entry more
stably: they change only when the requirement itself changes, which is exactly
when the suppression should be re-evaluated.
"""

import json
from typing import Any

from .model import Finding


def fingerprint(*, finding: Finding) -> dict[str, str]:
    """Return a stable, line-number-free fingerprint dict for a finding."""
    return {
        "code": finding.code,
        "file": finding.file,
        "requirement": finding.requirement,
        "name": finding.name,
    }


def build_baseline(*, findings: list[Finding]) -> list[dict[str, str]]:
    """Build a sorted, deduplicated list of fingerprints from findings.

    The output is sorted so that writing an unchanged set of findings produces
    an identical JSON document (no spurious diff).
    """
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, str]] = []
    for f in findings:
        fp = fingerprint(finding=f)
        key = (fp["code"], fp["file"], fp["requirement"], fp["name"])
        if key not in seen:
            seen.add(key)
            result.append(fp)
    result.sort(key=lambda fp: (fp["code"], fp["file"], fp["requirement"], fp["name"]))
    return result


def serialize_baseline(*, findings: list[Finding], tool_version: str) -> str:
    """Serialize a baseline to a deterministic JSON string.

    The JSON includes a small header (tool name, version) and a sorted list of
    fingerprint objects so the file is human-readable and diffable.
    """
    doc: dict[str, Any] = {
        "tool": "pinlint",
        "version": tool_version,
        "findings": build_baseline(findings=findings),
    }
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


def load_baseline(*, text: str) -> list[dict[str, str]]:
    """Load a baseline from JSON text produced by serialize_baseline.

    Raises ValueError if the text is not valid JSON or lacks the expected
    structure.
    """
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"baseline is not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("baseline must be a JSON object")
    if "findings" not in doc:
        raise ValueError("baseline is missing the 'findings' key")
    entries = doc["findings"]
    if not isinstance(entries, list):
        raise ValueError("baseline 'findings' must be a JSON array")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"baseline finding at index {i} must be a JSON object")
        for field in ("code", "file", "requirement", "name"):
            if field not in entry:
                raise ValueError(
                    f"baseline finding at index {i} is missing field '{field}'"
                )
    return entries


def filter_by_baseline(
    *, findings: list[Finding], baseline: list[dict[str, str]]
) -> list[Finding]:
    """Return findings whose fingerprint is NOT in the baseline.

    Findings present in the baseline are suppressed; findings absent from the
    baseline are returned unchanged. This is the set of NEW findings.
    """
    baseline_keys: set[tuple[str, ...]] = {
        (entry["code"], entry["file"], entry["requirement"], entry["name"])
        for entry in baseline
    }
    return [
        f
        for f in findings
        if (f.code, f.file, f.requirement, f.name) not in baseline_keys
    ]
