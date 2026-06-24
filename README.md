# pinlint

<p align="center">
  <img src="assets/logo.png" alt="pinlint logo" width="160">
</p>

[![PyPI](https://img.shields.io/pypi/v/pinlint)](https://pypi.org/project/pinlint/)
[![CI](https://github.com/amaar-mc/pinlint/actions/workflows/ci.yml/badge.svg)](https://github.com/amaar-mc/pinlint/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

A static linter that checks a requirements file is fully version-pinned and hash-pinned. Built for CI and pre-commit, so unpinned or unhashed dependencies fail review before anything is installed.

## Install

```sh
pip install pinlint
```

## 30-second example

```sh
pinlint requirements.txt
```

```
requirements.txt:3: unpinned: requests is not pinned to an exact version (use ==)
requirements.txt:7: missing-hash: flask has no --hash
2 issue(s) found
```

Exit code is 1 when there are findings, 0 when the file is clean, so it drops straight
into CI or a pre-commit hook.

As a library:

```python
from pinlint import lint_file

findings = lint_file(
    "requirements.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
)
for f in findings:
    print(f.file, f.line, f.code, f.message)
```

## Why this exists

Reproducible, tamper-evident installs need every requirement pinned to an exact version
and carrying a hash. The existing tools each do something adjacent: `pip-compile
--generate-hashes` generates such a file, `pip install --require-hashes` enforces hashes
at install time, and `requirements-txt-fixer` tidies formatting. None of them is a fast,
static check you can run in review to assert that an arbitrary requirements file is fully
pinned and hashed. `pinlint` is that check.

## Comparison

| | pinlint | pip-compile | pip --require-hashes | requirements-txt-fixer |
|---|:---:|:---:|:---:|:---:|
| Static check, no install | yes | n/a | no (install time) | yes |
| Flags unpinned versions | yes | generates | at install | no |
| Flags missing hashes | yes | generates | at install | no |
| CI / pre-commit gate | yes | partial | no | yes (formatting only) |

## Checks

- `unpinned`: the requirement is not pinned with `==` or `===` to an exact version.
- `missing-hash`: the requirement has no `--hash` (unless `--no-hashes`).
- `unpinnable`: an editable, URL, or VCS install that cannot be version-pinned.
- `duplicate`: the same project is listed on more than one requirement line. Comparison is
  by PEP 503 normalized name (so `Flask` and `flask`, or `typing-extensions` and
  `typing_extensions`, are the same project). Lines guarded by different environment markers
  are mutually exclusive and are not flagged; differing extras of the same project
  (`foo[a]` and `foo[b]`) are still duplicates of the base project, since pip resolves one
  version.
- `parse-error`: the line could not be parsed as a requirement.

It understands comments, blank lines, backslash line continuations, `--hash` options,
environment markers and extras, and `-r` and `-c` includes (followed with cycle
protection). The only dependency is `packaging`, the canonical PEP 508 parser.

## Options

- `--allow-unpinned` do not require exact version pins.
- `--no-hashes` do not require `--hash` entries.
- `--no-follow` do not follow `-r` and `-c` includes.
- `--allow PACKAGE` ignore findings for a package name (repeatable).
- `--format text|json|sarif` choose the output format. `json` suits CI and editors; `sarif`
  emits SARIF 2.1.0 for GitHub code scanning and other analysis tools.
- `--write-baseline PATH` write all current findings to a baseline JSON file, then exit 0.
- `--baseline PATH` suppress findings present in the baseline; exit nonzero only when new
  findings remain.
- `--error CODE` treat CODE as an error (repeatable).
- `--warning CODE` treat CODE as a warning; warnings are printed but do not cause a nonzero
  exit (repeatable).
- `--off CODE` silence CODE entirely; matching findings are dropped from output (repeatable).

## Per-rule severity

Different teams have different tolerances. Severity flags let you decide which rules block
CI and which are advisory.

```sh
# Treat unpinned as a warning (printed, exit 0) and silence missing-hash entirely.
pinlint requirements.txt --warning unpinned --off missing-hash

# Escalate unpinnable from its default warning to a hard error.
pinlint requirements.txt --error unpinnable
```

**Exit-code semantics**: exit 1 only when at least one ERROR-level finding remains after
applying severity overrides and any `--allow` filtering. Warnings alone exit 0. This lets
you run pinlint in advisory mode (all warnings) during migration without breaking CI.

Default severities (no flags) match the SARIF rule catalog and are backward compatible with
0.4.0:

| Rule | Default severity |
|---|:---:|
| `unpinned` | error |
| `missing-hash` | error |
| `unpinnable` | warning |
| `duplicate` | warning |
| `parse-error` | error |
| `io-error` | error |

Valid rule codes: `unpinned`, `missing-hash`, `unpinnable`, `duplicate`, `parse-error`,
`io-error`.
Passing an unknown code exits 2 with a clear error message listing the valid codes.

### Programmatic API

```python
from pinlint import (
    apply_severities,
    default_severity_map,
    lint_file,
    to_sarif_annotated,
)

findings = lint_file(
    "requirements.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
)
sev = default_severity_map()
sev["unpinned"] = "warning"   # downgrade
sev["missing-hash"] = "off"   # silence

annotated = apply_severities(findings=findings, severity_map=sev)
for af in annotated:
    print(af.effective_severity, af.code, af.message)

# SARIF output with effective severities:
doc = to_sarif_annotated(annotated, tool_version="0.5.0")
```

## Baseline: adopt pinlint incrementally

If an existing project has many unpinned requirements you cannot fix all at once, use a
baseline to suppress the known findings and fail only on new ones.

```sh
# Record the current state.
pinlint requirements.txt --write-baseline .pinlint-baseline.json

# In CI, suppress known findings and fail only on new ones.
pinlint requirements.txt --baseline .pinlint-baseline.json
```

The baseline file is deterministic and human-readable, so it diffs cleanly in code review.
Findings are fingerprinted by rule code, file path, requirement text, and package name --
not by line number -- so adding or removing unrelated lines above a requirement does not
invalidate its suppression.

Commit `.pinlint-baseline.json` to version control. When you fix a requirement, re-run
`--write-baseline` and commit the smaller file; the diff shows the fix.

## Pre-commit

pinlint ships a hook, so you can add it to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/amaar-mc/pinlint
    rev: v0.2.0
    hooks:
      - id: pinlint
```

The hook runs on files matching `requirements.*\.txt`.

## Testing

```sh
pip install -e ".[dev]"
pytest
```

Tests use golden requirements files for each rule, including includes, cycles, line
continuations, and the CLI exit codes.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT. See [LICENSE](./LICENSE).
