import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .baseline import filter_by_baseline, load_baseline, serialize_baseline
from .lint import lint_file
from .model import Finding
from .sarif import to_sarif


def _print_text(findings: list[Finding]) -> None:
    for finding in findings:
        print(f"{finding.file}:{finding.line}: {finding.code}: {finding.message}")


def _print_json(findings: list[Finding]) -> None:
    print(json.dumps([asdict(finding) for finding in findings], indent=2))


def _print_sarif(findings: list[Finding]) -> None:
    print(json.dumps(to_sarif(findings, tool_version=__version__), indent=2))


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
    args = parser.parse_args(argv)

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

    # --write-baseline wins when both flags are given.
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

    if args.format == "json":
        _print_json(findings)
    elif args.format == "sarif":
        _print_sarif(findings)
    else:
        _print_text(findings)
        if findings:
            print(f"{len(findings)} issue(s) found", file=sys.stderr)
    return 1 if findings else 0


def main() -> int:
    return run(sys.argv[1:])
