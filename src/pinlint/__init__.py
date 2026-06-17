"""Static linter for full version pinning and hash pinning in requirements files."""

from .baseline import build_baseline, filter_by_baseline, load_baseline, serialize_baseline
from .lint import lint_file, lint_text
from .model import Finding
from .sarif import to_sarif

__all__ = [
    "Finding",
    "build_baseline",
    "filter_by_baseline",
    "lint_file",
    "lint_text",
    "load_baseline",
    "serialize_baseline",
    "to_sarif",
]
__version__ = "0.4.0"
