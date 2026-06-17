# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- A pre-commit hook entry.
- JSON and SARIF output for CI annotations.
- Per-package allowlists.

## [0.1.0]

### Added
- `lint_text` and `lint_file` returning structured findings.
- Rules: unpinned, missing-hash, unpinnable (editable, URL, VCS), and parse-error.
- Requirements parsing: comments, blank lines, backslash continuations, `--hash` options,
  markers and extras, and `-r` and `-c` includes (followed with cycle protection).
- A `pinlint` CLI that prints `file:line: code: message` and exits nonzero on findings.
- Test suite with golden requirements files for each rule, includes, cycles, and the CLI.
