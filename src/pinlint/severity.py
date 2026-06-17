"""Per-rule severity configuration.

Allows teams to treat some rules as errors, others as warnings, and silence
others entirely. The defaults match the SARIF rule catalog in sarif.py so the
two are always in agreement.
"""

from typing import Literal

from .model import Finding

SeverityLevel = Literal["error", "warning", "off"]
SeverityMap = dict[str, SeverityLevel]

# All valid rule codes.
_KNOWN_CODES: frozenset[str] = frozenset(
    ["unpinned", "missing-hash", "unpinnable", "parse-error", "io-error"]
)

# Default severity per code. Matches sarif.py _RULES level column exactly.
_DEFAULTS: SeverityMap = {
    "unpinned": "error",
    "missing-hash": "error",
    "unpinnable": "warning",
    "parse-error": "error",
    "io-error": "error",
}


def known_codes() -> frozenset[str]:
    """Return the set of known rule codes."""
    return _KNOWN_CODES


def default_severity_map() -> SeverityMap:
    """Return the default severity map (matches the SARIF rule catalog defaults).

    Intended as a named constructor so callers do not pass a defaulted argument.
    unpinned=error, missing-hash=error, unpinnable=warning, parse-error=error, io-error=error.
    """
    return dict(_DEFAULTS)


def apply_severities(
    *,
    findings: list[Finding],
    severity_map: SeverityMap,
) -> list["AnnotatedFinding"]:
    """Apply a severity map to a list of findings.

    Each finding is annotated with its effective severity as determined by
    severity_map. Findings whose effective severity is "off" are dropped.
    Returns a list of AnnotatedFinding in the same order as the input
    (minus "off" findings).

    Raises ValueError if severity_map references an unknown rule code.
    """
    for code in severity_map:
        if code not in _KNOWN_CODES:
            raise ValueError(
                f"unknown rule code {code!r}; known codes are: "
                + ", ".join(sorted(_KNOWN_CODES))
            )

    result: list[AnnotatedFinding] = []
    for finding in findings:
        level = severity_map.get(finding.code, _DEFAULTS.get(finding.code, "error"))
        if level == "off":
            continue
        result.append(AnnotatedFinding(finding=finding, effective_severity=level))
    return result


class AnnotatedFinding:
    """A finding paired with its effective severity after applying a severity map.

    Attributes mirror Finding fields for convenience, plus effective_severity.
    """

    __slots__ = ("effective_severity", "finding")

    def __init__(
        self,
        *,
        finding: Finding,
        effective_severity: SeverityLevel,
    ) -> None:
        self.finding = finding
        self.effective_severity: SeverityLevel = effective_severity

    # Delegate attribute access to the wrapped finding for convenience.
    @property
    def file(self) -> str:
        return self.finding.file

    @property
    def line(self) -> int:
        return self.finding.line

    @property
    def code(self) -> str:
        return self.finding.code

    @property
    def message(self) -> str:
        return self.finding.message

    @property
    def requirement(self) -> str:
        return self.finding.requirement

    @property
    def name(self) -> str:
        return self.finding.name

    def __repr__(self) -> str:
        return (
            f"AnnotatedFinding(finding={self.finding!r}, "
            f"effective_severity={self.effective_severity!r})"
        )
