# Architecture

**Analysis Date:** 2026-06-17

## Pattern Overview

**Overall:** Functional pipeline with layered separation between parsing, classification, and output.

**Key Characteristics:**
- Linear transformation pipeline: raw text → logical lines → findings → formatted output
- Pure functions throughout; no mutable state or side effects except I/O
- Keyword-only required parameters; no default argument values
- Data-driven rule definitions (SARIF rules as stable catalog)
- Incremental adoption through baseline fingerprinting mechanism

## Layers

**Parsing Layer:**
- Purpose: Normalize requirements file text into logical, executable lines
- Location: `src/pinlint/parse.py`
- Contains: `LogicalLine` dataclass, comment stripping, line continuation joining
- Depends on: None (standard library only)
- Used by: `lint.lint_text()` via `logical_lines()` iterator

**Linting/Classification Layer:**
- Purpose: Examine each logical line and emit findings based on rules
- Location: `src/pinlint/lint.py`
- Contains: Requirement classification rules, hash detection, pinning validation
- Depends on: `packaging.requirements.Requirement`, `packaging.specifiers.SpecifierSet`
- Used by: CLI, library API, SARIF rendering

**Model Layer:**
- Purpose: Define the atomic unit of output (a single linting problem)
- Location: `src/pinlint/model.py`
- Contains: `Finding` frozen dataclass with file, line, code, message, requirement, name
- Depends on: None
- Used by: All downstream consumers (baseline, SARIF, CLI printers)

**Output Formats:**
- `src/pinlint/sarif.py`: Render findings as SARIF 2.1.0 log with rule catalog
- `src/pinlint/baseline.py`: Fingerprint findings for incremental adoption
- `src/pinlint/cli.py`: Text, JSON, SARIF printers; baseline I/O

**Entry Points:**
- `src/pinlint/cli.py:run()`: Testable CLI entry point (takes argv list)
- `src/pinlint/cli.py:main()`: Console script entry point (reads sys.argv)
- Library API in `src/pinlint/__init__.py`: Public functions for programmatic use

## Data Flow

**CLI Invocation:**

1. `main()` → `run(sys.argv[1:])`
2. `run()` parses arguments with argparse
3. For each file in args.files:
   - `lint_file(path, require_hashes, allow_unpinned, follow_includes)` → list[Finding]
4. Optional: Filter findings by `--allow` package names
5. Optional: Write findings to baseline file (`--write-baseline`) or exit early
6. Optional: Load baseline and suppress known findings (`--baseline`)
7. Format findings (text, json, or sarif)
8. Exit with code: 0 = clean, 1 = findings, 2 = error

**File Linting with Includes:**

1. `lint_file(path)` wraps `_lint_file()` with empty seen set
2. `_lint_file()` resolves path, reads text (catches OSError → io-error finding)
3. Call `lint_text()` on file contents
4. If `follow_includes=True`, extract `-r` and `-c` targets from logical lines
5. Recursively `_lint_file()` each target (seen set prevents cycles)
6. Accumulate all findings across tree

**Requirement Classification:**

1. `lint_text()` iterates over `logical_lines()` (comments stripped, continuations joined)
2. Split first token to decide line type:
   - `-r`, `--requirement`, `-c`, `--constraint` → skip (handled by lint_file)
   - `-e`, `--editable` → unpinnable finding
   - Starts with `-` → global option, skip
3. Otherwise, process as requirement:
   - `_split_hashes()` separates `--hash` options from specifier (pip extension, not PEP 508)
   - Check for `://` or VCS prefix (`git+`, `hg+`, `svn+`, `bzr+`) → unpinnable
   - Parse with `packaging.requirements.Requirement`
   - Check for URL in requirement → unpinnable
   - Check if pinning is exact (single `==` or `===` without `*` wildcard)
   - If not exactly pinned and `allow_unpinned=False` → unpinned finding
   - If no `--hash` and `require_hashes=True` → missing-hash finding
4. Return list of findings with stable codes

**Baseline Fingerprinting:**

1. `fingerprint(finding)` → dict with (code, file, requirement, name)
2. Deliberately excludes line number to survive line additions above requirement
3. `build_baseline()` deduplicates and sorts for deterministic JSON
4. `serialize_baseline()` outputs with tool name and version header
5. `filter_by_baseline()` suppresses findings present in baseline set

**SARIF Rendering:**

1. `_RULES` tuple catalog defines all rule codes, severity levels, descriptions in stable order
2. `_INDEX_BY_CODE` and `_LEVEL_BY_CODE` lookup tables map code → rule metadata
3. `_result()` converts each Finding to SARIF result object
4. `to_sarif()` builds document with driver rules and results array

## Key Abstractions

**Finding:**
- Purpose: Immutable record of a single linting problem
- Examples: `src/pinlint/model.py`
- Pattern: Frozen dataclass with required fields; no methods
- Fields: file (str), line (int, 1-based), code (str, rule identifier), message (str), requirement (str, the parsed line), name (str, package name or "")

**LogicalLine:**
- Purpose: Normalized view of one executable line (comments removed, continuations joined)
- Examples: `src/pinlint/parse.py`
- Pattern: Frozen dataclass tracking 1-based start line number and text
- Used by: Entire linting pipeline to preserve correct line references

**Requirement Classification States:**
- `unpinned`: Version not locked to exact == or === (without wildcards)
- `missing-hash`: No --hash option when hashes required
- `unpinnable`: Editable, URL, or VCS install that cannot be pinned
- `parse-error`: Line failed PEP 508 parsing
- `io-error`: File could not be read (OSError, not exception)

## Entry Points

**Library:**
- `src/pinlint/__init__.py`: Exports Finding, lint_file, lint_text, baseline functions, to_sarif
- `src/pinlint/lint.py:lint_text()`: Core rule engine; takes text + flags → findings
- `src/pinlint/lint.py:lint_file()`: File I/O + recursive includes; takes path + flags → findings

**CLI:**
- `src/pinlint/cli.py:main()`: Console script (defined in pyproject.toml as entry point)
- `src/pinlint/cli.py:run(argv)`: Testable function (used by tests)

## Error Handling

**Strategy:** No exceptions cross the public API; errors are findings

**Patterns:**
- OSError during file read → io-error finding (not exception)
- Invalid requirement syntax → parse-error finding (not exception)
- Invalid baseline JSON → ValueError raised to CLI (user misconfiguration)
- Include cycle → Prevented by seen set (resolved paths)

## Cross-Cutting Concerns

**Logging:** None (no logging framework; findings are the output)

**Validation:** All validation is implicit in classification rules; no separate validation layer

**Authentication:** Not applicable (no external services)

**Path Resolution:** `Path.resolve()` normalizes before storing in seen set to catch cycles; relative includes resolved via `path.parent / target`

## Conventions

**Line Numbers:** 1-based throughout (matches editor convention). io-error findings use 0 for line (no specific problem line).

**Requirement Name:** Extracted from parsed Requirement object; empty string ("") for unpinnable entries (URLs, editable, VCS) that don't parse to a package name.

**Code Stability:** Five stable rule codes (unpinned, missing-hash, unpinnable, parse-error, io-error) maintained in SARIF rule catalog; used for fingerprinting.

---

*Architecture analysis: 2026-06-17*
