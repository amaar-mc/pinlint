"""Render findings as a SARIF 2.1.0 log.

SARIF (Static Analysis Results Interchange Format) is the format GitHub code scanning and
other tools ingest. The document is built as plain dictionaries so it can be serialized with
the standard library json module and asserted against in tests.
"""

from .model import Finding

_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_INFORMATION_URI = "https://github.com/amaar-mc/pinlint"

# Catalog of rules in a stable order. The index into this list is the SARIF ruleIndex.
# level is the SARIF level reported for the rule: pinning problems are errors, while an entry
# that simply cannot be pinned or hashed is a warning.
_RULES: list[tuple[str, str, str]] = [
    ("unpinned", "error", "Requirement is not pinned to an exact version"),
    ("missing-hash", "error", "Requirement has no --hash entry"),
    ("unpinnable", "warning", "Requirement cannot be pinned or hashed"),
    ("parse-error", "error", "Requirement could not be parsed"),
    ("io-error", "error", "Requirements file could not be read"),
]

_INDEX_BY_CODE = {code: index for index, (code, _level, _desc) in enumerate(_RULES)}
_LEVEL_BY_CODE = {code: level for code, level, _desc in _RULES}


def _rule_name(code: str) -> str:
    """A PascalCase identifier for the rule, for example missing-hash to MissingHash."""
    return "".join(part.capitalize() for part in code.split("-"))


def _driver_rules() -> list[dict[str, object]]:
    rules: list[dict[str, object]] = []
    for code, level, description in _RULES:
        rules.append(
            {
                "id": code,
                "name": _rule_name(code),
                "shortDescription": {"text": description},
                "defaultConfiguration": {"level": level},
            }
        )
    return rules


def _result(finding: Finding) -> dict[str, object]:
    location: dict[str, object] = {"artifactLocation": {"uri": finding.file}}
    # SARIF regions are 1-based; the io-error finding carries line 0, so omit the region there.
    if finding.line >= 1:
        location["region"] = {"startLine": finding.line}
    result: dict[str, object] = {
        "ruleId": finding.code,
        "ruleIndex": _INDEX_BY_CODE[finding.code],
        "level": _LEVEL_BY_CODE[finding.code],
        "message": {"text": finding.message},
        "locations": [{"physicalLocation": location}],
    }
    if finding.requirement:
        result["properties"] = {"requirement": finding.requirement}
    return result


def to_sarif(findings: list[Finding], *, tool_version: str) -> dict[str, object]:
    """Build a SARIF 2.1.0 document for the given findings."""
    return {
        "version": "2.1.0",
        "$schema": _SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pinlint",
                        "informationUri": _INFORMATION_URI,
                        "version": tool_version,
                        "rules": _driver_rules(),
                    }
                },
                "results": [_result(finding) for finding in findings],
            }
        ],
    }
