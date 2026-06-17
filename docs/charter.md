# Charter

## Purpose

Provide a fast static check that a requirements file is fully version-pinned and
hash-pinned, so unpinned or unhashed dependencies are caught in review and CI before
anything is installed.

## Scope

- Parse requirements files the way pip reads them: comments, blank lines, backslash
  continuations, `--hash` options, markers and extras, and `-r` and `-c` includes.
- Report unpinned requirements, missing hashes, unpinnable installs (editable, URL, VCS),
  and unparseable lines, with file and line numbers.
- A library API and a CLI suitable for CI and pre-commit.

## Non-goals

- Resolving, downloading, or installing anything. pinlint is static and offline.
- Vulnerability scanning. `pip-audit` and `safety` cover that.
- Generating pinned files. `pip-compile` covers that; pinlint checks the result.
- Lockfile formats beyond requirements files (a possible later addition).

## Principles

- Correctness and clear diagnostics first. Every rule has golden tests.
- Minimal dependencies. Only `packaging`, the canonical PEP 508 parser.
- Stable, small API. Required, explicit options.
- Predictable behavior at edges. Unreadable files report a finding rather than crashing.

## Audience

Teams hardening their Python supply chain, and maintainers who want a requirements gate in
CI or pre-commit.
