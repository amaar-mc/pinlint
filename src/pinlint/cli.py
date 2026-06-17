import argparse
import json
import sys
from dataclasses import asdict

from . import __version__
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
