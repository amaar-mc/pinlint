import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .baseline import filter_by_baseline, load_baseline, serialize_baseline
from .lint import lint_file
from .model import Finding
from .sarif import to_sarif_annotated
from .severity import (
    AnnotatedFinding,
    SeverityMap,
    apply_severities,
    default_severity_map,
    known_codes,
)


def _print_text(annotated: list[AnnotatedFinding]) -> None:
    for af in annotated:
        print(f"{af.file}:{af.line}: [{af.effective_severity}] {af.code}: {af.message}")


def _print_json(annotated: list[AnnotatedFinding]) -> None:
    records = []
    for af in annotated:
        d = asdict(af.finding)
        d["effective_severity"] = af.effective_severity
        records.append(d)
    print(json.dumps(records, indent=2))


def _print_sarif(annotated: list[AnnotatedFinding]) -> None:
    print(json.dumps(to_sarif_annotated(annotated, tool_version=__version__), indent=2))


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pinlint",
        description="Check that requirements files are fully version-pinned and hash-pinned.",
    )
    parser.add_argument("files", nargs="+", help="requirements files to check")
    parser.add_argument(
        "--allow-unpinned", action="store_true", help="do not require exact == version pins"
    )
    parser.add_argument("--no-hashes", action="store_true", help="do not require --hash entries")
    parser.add_argument("--no-follow", action="store_true", help="do not follow -r and -c includes")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="PACKAGE",
        help="ignore findings for this package name (repeatable)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "sarif"),
        default="text",
        help="output format",
    )
    parser.add_argument(
        "--write-baseline",
        metavar="PATH",
        help=(
            "compute findings and write a baseline JSON file to PATH, then exit 0;"
            " use --baseline PATH on subsequent runs to suppress these findings"
        ),
    )
    parser.add_argument(
        "--baseline",
        metavar="PATH",
        help=(
            "load a baseline file and suppress findings whose fingerprint is in it;"
            " exit nonzero only when new findings remain"
        ),
    )
    parser.add_argument(
        "--error",
        action="append",
        default=[],
        metavar="CODE",
        dest="severity_error",
        help="treat CODE as an error (repeatable); CODE must be a known rule code",
    )
    parser.add_argument(
        "--warning",
        action="append",
        default=[],
        metavar="CODE",
        dest="severity_warning",
        help="treat CODE as a warning (repeatable); warnings are printed but exit 0",
    )
    parser.add_argument(
        "--off",
        action="append",
        default=[],
        metavar="CODE",
        dest="severity_off",
        help="silence CODE entirely (repeatable); matching findings are dropped",
    )
    args = parser.parse_args(argv)

    # Validate and build the severity map from the three flag groups.
    sev_map: SeverityMap = default_severity_map()
    for code in args.severity_error:
        if code not in known_codes():
            print(
                f"pinlint: unknown rule code {code!r}; known codes are: "
                + ", ".join(sorted(known_codes())),
                file=sys.stderr,
            )
            return 2
        sev_map[code] = "error"
    for code in args.severity_warning:
        if code not in known_codes():
            print(
                f"pinlint: unknown rule code {code!r}; known codes are: "
                + ", ".join(sorted(known_codes())),
                file=sys.stderr,
            )
            return 2
        sev_map[code] = "warning"
    for code in args.severity_off:
        if code not in known_codes():
            print(
                f"pinlint: unknown rule code {code!r}; known codes are: "
                + ", ".join(sorted(known_codes())),
                file=sys.stderr,
            )
            return 2
        sev_map[code] = "off"

    allowed = {name.lower() for name in args.allow}
    findings: list[Finding] = []
    for file in args.files:
        findings.extend(
            lint_file(
                file,
                require_hashes=not args.no_hashes,
                allow_unpinned=args.allow_unpinned,
                follow_includes=not args.no_follow,
            )
        )
    findings = [f for f in findings if f.name == "" or f.name.lower() not in allowed]

    # --write-baseline wins when both flags are given. Baseline is written before
    # severity filtering so it captures the full set of raw findings.
    if args.write_baseline:
        text = serialize_baseline(findings=findings, tool_version=__version__)
        Path(args.write_baseline).write_text(text, encoding="utf-8")
        print(f"Baseline written to {args.write_baseline} ({len(findings)} finding(s))")
        return 0

    if args.baseline:
        try:
            baseline_text = Path(args.baseline).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"pinlint: cannot read baseline file: {exc}", file=sys.stderr)
            return 2
        try:
            baseline = load_baseline(text=baseline_text)
        except ValueError as exc:
            print(f"pinlint: invalid baseline file: {exc}", file=sys.stderr)
            return 2
        findings = filter_by_baseline(findings=findings, baseline=baseline)

    # Apply severity map: drops "off" findings, annotates the rest.
    annotated = apply_severities(findings=findings, severity_map=sev_map)

    if args.format == "json":
        _print_json(annotated)
    elif args.format == "sarif":
        _print_sarif(annotated)
    else:
        _print_text(annotated)
        if annotated:
            print(f"{len(annotated)} issue(s) found", file=sys.stderr)

    # Exit 1 only when at least one ERROR-level finding remains. Warnings alone exit 0.
    has_errors = any(af.effective_severity == "error" for af in annotated)
    return 1 if has_errors else 0


def main() -> int:
    return run(sys.argv[1:])
