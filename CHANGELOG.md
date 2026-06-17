# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0]

### Added
- `--format sarif` output: a SARIF 2.1.0 log for GitHub code scanning and other analysis
  tools, with a rule catalog (unpinned and missing-hash and parse-error and io-error as
  errors, unpinnable as a warning) and 1-based source regions.
- `to_sarif(findings, *, tool_version)` in the public API for building the SARIF document
  programmatically.

## [0.2.0]

### Added
- `--format json` output for editor and CI integration.
- A `.pre-commit-hooks.yaml` so pinlint can be used directly as a pre-commit hook.
- `--allow PACKAGE` (repeatable) to ignore findings for named packages.
- A `name` field on `Finding` holding the distribution name when the requirement parsed.

## [0.1.0]

### Added
- `lint_text` and `lint_file` returning structured findings.
- Rules: unpinned, missing-hash, unpinnable (editable, URL, VCS), and parse-error.
- Requirements parsing: comments, blank lines, backslash continuations, `--hash` options,
  markers and extras, and `-r` and `-c` includes (followed with cycle protection).
- A `pinlint` CLI that prints `file:line: code: message` and exits nonzero on findings.
- Test suite with golden requirements files for each rule, includes, cycles, and the CLI.
