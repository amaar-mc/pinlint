# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0]

### Added
- Per-rule severity configuration: `--error CODE`, `--warning CODE`, and `--off CODE` CLI
  flags (all repeatable) let teams treat some rules as errors, others as warnings, and
  silence others entirely. CODE must be a known rule code; an unknown code exits 2 with a
  clear message.
- Exit-code semantics: exit 1 only when at least one ERROR-level finding remains after
  applying severities and `--allow` filtering. Warnings are printed but exit 0.
- Default severities (no flags) are backward compatible with 0.4.0: unpinned, missing-hash,
  parse-error, and io-error are errors; unpinnable is a warning.  These match the SARIF
  rule catalog in `sarif.py` exactly.
- `severity.py` module with pure, testable functions: `default_severity_map()`,
  `apply_severities(*, findings, severity_map)`, and `known_codes()`.
- `AnnotatedFinding` class pairing a `Finding` with its `effective_severity` field.
- `to_sarif_annotated(annotated, *, tool_version)` in `sarif.py` builds a SARIF 2.1.0
  document using the effective severity from each annotated finding rather than the
  rule default.
- JSON output (`--format json`) now includes an `effective_severity` field on each entry.
- All new public symbols exported from `__init__.__all__`:
  `AnnotatedFinding`, `SeverityMap`, `apply_severities`, `default_severity_map`,
  `known_codes`, `to_sarif_annotated`.

## [0.4.0]

### Added
- Baseline support for incremental adoption: `--write-baseline PATH` computes all
  current findings and writes them to a JSON file; `--baseline PATH` on subsequent
  runs suppresses those known findings and exits nonzero only when new findings appear.
- `baseline.py` module with four pure, testable functions exported from the public API:
  `build_baseline`, `serialize_baseline`, `load_baseline`, and `filter_by_baseline`.
- Fingerprint design: each finding is identified by (code, file, requirement, name),
  omitting the line number so that adding lines above an existing requirement does not
  break suppression.
- Both baseline flags compose with all existing flags (`--format`, `--allow`,
  `--no-hashes`, `--allow-unpinned`, `--no-follow`). When both `--write-baseline`
  and `--baseline` are given, `--write-baseline` wins.

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
