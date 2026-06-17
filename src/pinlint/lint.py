from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet

from .model import Finding
from .parse import logical_lines

_INCLUDE = ("-r", "--requirement", "-c", "--constraint")
_EDITABLE = ("-e", "--editable")
_VCS_PREFIXES = ("git+", "hg+", "svn+", "bzr+")


def _split_hashes(text: str) -> tuple[str, list[str]]:
    """Separate the requirement specifier from any --hash options on the line."""
    tokens = text.split()
    spec_tokens: list[str] = []
    hashes: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--hash="):
            hashes.append(token[len("--hash=") :])
        elif token == "--hash" and i + 1 < len(tokens):
            hashes.append(tokens[i + 1])
            i += 1
        else:
            spec_tokens.append(token)
        i += 1
    return " ".join(spec_tokens), hashes


def _is_exactly_pinned(specifier: SpecifierSet) -> bool:
    specs = list(specifier)
    if len(specs) != 1:
        return False
    only = specs[0]
    return only.operator in ("==", "===") and "*" not in only.version


def lint_text(
    text: str, *, source: str, require_hashes: bool, allow_unpinned: bool
) -> list[Finding]:
    """Lint the contents of a requirements file. Includes (-r, -c) are not followed here;
    use lint_file for that."""
    findings: list[Finding] = []
    for entry in logical_lines(text):
        line = entry.text
        first = line.split(maxsplit=1)[0]
        if first in _INCLUDE:
            continue
        if first in _EDITABLE:
            findings.append(
                Finding(
                    source, entry.number, "unpinnable", "editable install cannot be pinned", line
                )
            )
            continue
        if first.startswith("-"):
            continue  # global option such as --index-url or --find-links
        spec, hashes = _split_hashes(line)
        if "://" in spec or spec.startswith(_VCS_PREFIXES):
            findings.append(
                Finding(
                    source, entry.number, "unpinnable", "URL or VCS install cannot be pinned", spec
                )
            )
            continue
        try:
            requirement = Requirement(spec)
        except InvalidRequirement as exc:
            findings.append(
                Finding(
                    source, entry.number, "parse-error", f"cannot parse requirement: {exc}", spec
                )
            )
            continue
        if requirement.url is not None:
            findings.append(
                Finding(source, entry.number, "unpinnable", "URL install cannot be pinned", spec)
            )
            continue
        if not allow_unpinned and not _is_exactly_pinned(requirement.specifier):
            findings.append(
                Finding(
                    source,
                    entry.number,
                    "unpinned",
                    f"{requirement.name} is not pinned to an exact version (use ==)",
                    spec,
                    name=requirement.name,
                )
            )
        if require_hashes and not hashes:
            findings.append(
                Finding(
                    source,
                    entry.number,
                    "missing-hash",
                    f"{requirement.name} has no --hash",
                    spec,
                    name=requirement.name,
                )
            )
    return findings


def _include_targets(text: str) -> list[str]:
    targets: list[str] = []
    for entry in logical_lines(text):
        parts = entry.text.split(maxsplit=1)
        if len(parts) == 2 and parts[0] in _INCLUDE:
            targets.append(parts[1].strip())
    return targets


def _lint_file(
    path: Path, require_hashes: bool, allow_unpinned: bool, follow_includes: bool, seen: set[Path]
) -> list[Finding]:
    resolved = path.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Finding(str(path), 0, "io-error", f"cannot read file: {exc}", "")]
    findings = lint_text(
        text, source=str(path), require_hashes=require_hashes, allow_unpinned=allow_unpinned
    )
    if follow_includes:
        for target in _include_targets(text):
            findings.extend(
                _lint_file(
                    path.parent / target, require_hashes, allow_unpinned, follow_includes, seen
                )
            )
    return findings


def lint_file(
    path: str | Path, *, require_hashes: bool, allow_unpinned: bool, follow_includes: bool
) -> list[Finding]:
    """Lint a requirements file on disk, optionally following -r and -c includes with
    cycle protection."""
    return _lint_file(Path(path), require_hashes, allow_unpinned, follow_includes, set())
