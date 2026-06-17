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
- `parse-error`: the line could not be parsed as a requirement.

It understands comments, blank lines, backslash line continuations, `--hash` options,
environment markers and extras, and `-r` and `-c` includes (followed with cycle
protection). The only dependency is `packaging`, the canonical PEP 508 parser.

## Options

- `--allow-unpinned` do not require exact version pins.
- `--no-hashes` do not require `--hash` entries.
- `--no-follow` do not follow `-r` and `-c` includes.
- `--allow PACKAGE` ignore findings for a package name (repeatable).
- `--format text|json` choose the output format; `json` suits CI and editors.

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
