import argparse
import sys

from .lint import lint_file


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
    args = parser.parse_args(argv)

    findings = []
    for file in args.files:
        findings.extend(
            lint_file(
                file,
                require_hashes=not args.no_hashes,
                allow_unpinned=args.allow_unpinned,
                follow_includes=not args.no_follow,
            )
        )

    for finding in findings:
        print(f"{finding.file}:{finding.line}: {finding.code}: {finding.message}")
    if findings:
        print(f"{len(findings)} issue(s) found", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])
