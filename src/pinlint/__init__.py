"""Static linter for full version pinning and hash pinning in requirements files."""

from .baseline import build_baseline, filter_by_baseline, load_baseline, serialize_baseline
from .lint import lint_file, lint_text
from .model import Finding
from .sarif import to_sarif, to_sarif_annotated
from .severity import (
    AnnotatedFinding,
    SeverityMap,
    apply_severities,
    default_severity_map,
    known_codes,
)

__all__ = [
    "AnnotatedFinding",
    "Finding",
    "SeverityMap",
    "apply_severities",
    "build_baseline",
    "default_severity_map",
    "filter_by_baseline",
    "known_codes",
    "lint_file",
    "lint_text",
    "load_baseline",
    "serialize_baseline",
    "to_sarif",
    "to_sarif_annotated",
]
__version__ = "0.5.0"
