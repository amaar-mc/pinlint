# Codebase Structure

**Analysis Date:** 2026-06-17

## Directory Layout

```
pinlint/
├── src/pinlint/          # Main package source code
│   ├── __init__.py       # Public API surface
│   ├── model.py          # Finding dataclass
│   ├── parse.py          # Text normalization (logical lines)
│   ├── lint.py           # Linting rules and file handling
│   ├── cli.py            # CLI entry points and formatters
│   ├── baseline.py       # Baseline fingerprinting and filtering
│   └── sarif.py          # SARIF 2.1.0 output format
├── tests/                # Test suite
│   ├── test_lint.py      # Core linting rules
│   ├── test_lint_file.py # File I/O, includes, cycles
│   ├── test_baseline.py  # Baseline fingerprinting and filtering
│   ├── test_cli.py       # CLI flags, exit codes, output formats
│   └── test_sarif.py     # SARIF document rendering
├── docs/                 # Documentation
│   ├── architecture.md   # Parsing and rule flow explanation
│   └── charter.md        # Project charter and scope
├── examples/             # Example usage
│   └── check.py          # Programmatic API usage example
├── .github/              # GitHub templates and workflows
├── pyproject.toml        # Project metadata and dependencies
├── README.md             # User guide and comparison
├── CHANGELOG.md          # Release history
├── CONTRIBUTING.md       # Contribution guidelines
├── SECURITY.md           # Security policy
└── LICENSE               # MIT license
```

## Directory Purposes

**`src/pinlint/`:**
- Purpose: Main package implementation
- Contains: Python modules for parsing, linting, CLI, output formats
- Key files: `__init__.py` (public API), `lint.py` (rules), `cli.py` (entry points)

**`tests/`:**
- Purpose: Test suite with golden examples for each rule
- Contains: pytest test files, fixtures via tmp_path, golden requirement snippets inline
- Key files: `test_lint.py` (rule unit tests), `test_cli.py` (integration tests)

**`docs/`:**
- Purpose: Architecture documentation and project charter
- Contains: Markdown documents explaining parsing, rules, and project scope
- Key files: `architecture.md` (implementation notes), `charter.md` (scope)

**`examples/`:**
- Purpose: Reference implementations for library consumers
- Contains: Python script showing programmatic lint_file usage
- Key files: `check.py`

**`.github/`:**
- Purpose: GitHub templates and CI workflows
- Contains: PR template, issue templates, workflow YAML
- Key files: GitHub Actions workflows, issue templates

## Key File Locations

**Entry Points:**
- `src/pinlint/cli.py:main()` - Console script entry point (defined in pyproject.toml)
- `src/pinlint/cli.py:run()` - Testable argv handler for CLI tests
- `src/pinlint/__init__.py` - Library public API exports

**Configuration:**
- `pyproject.toml` - Project metadata, dependencies, tool config (ruff, mypy)
- `.pre-commit-hooks.yaml` - Pre-commit hook definition (if present)

**Core Logic:**
- `src/pinlint/lint.py` - Core rule engine: unpinned, missing-hash, unpinnable, parse-error
- `src/pinlint/parse.py` - Text normalization: comment stripping, line continuation joining
- `src/pinlint/baseline.py` - Fingerprinting mechanism for incremental adoption
- `src/pinlint/sarif.py` - SARIF 2.1.0 output format with rule catalog

**Data Models:**
- `src/pinlint/model.py` - Finding frozen dataclass
- `src/pinlint/parse.py` - LogicalLine frozen dataclass

**Testing:**
- `tests/test_lint.py` - Rule behavior with golden snippets (unpinned, missing-hash, etc.)
- `tests/test_lint_file.py` - File I/O, include following, cycle detection
- `tests/test_cli.py` - Exit codes, flag behavior, output formats
- `tests/test_baseline.py` - Fingerprinting, deduplication, filtering
- `tests/test_sarif.py` - SARIF document structure and rule catalog

## Naming Conventions

**Files:**
- Core modules: `parse.py`, `lint.py`, `cli.py`, `baseline.py`, `sarif.py` (lowercase, underscore separators)
- Test files: `test_<module>.py` pattern (pytest discovery)
- Entry point: `__init__.py` and `__main__.py` (Python package convention)

**Functions:**
- Public API: `lint_text()`, `lint_file()`, `load_baseline()`, `serialize_baseline()`, `to_sarif()` (lowercase snake_case)
- Private helpers: Prefixed with `_` (e.g., `_split_hashes()`, `_is_exactly_pinned()`, `_lint_file()`)
- Internal iterator: `logical_lines()` (yields LogicalLine objects)

**Classes/Dataclasses:**
- `Finding` - Single linting problem record
- `LogicalLine` - Normalized requirements file line
- Both frozen (immutable) dataclasses

**Variables:**
- Requirement codes: UPPERCASE strings (`"unpinned"`, `"missing-hash"`, `"unpinnable"`, `"parse-error"`, `"io-error"`)
- Line numbers: Integer, 1-based (editors convention)
- Set collections for identity checks: `seen` (resolved paths), `baseline_keys` (fingerprint tuples)
- Lookup tables in SARIF: `_INDEX_BY_CODE`, `_LEVEL_BY_CODE` (prefix with underscore)

## Where to Add New Code

**New Rule/Finding Type:**
1. Define stable code in `_RULES` catalog in `src/pinlint/sarif.py` with level and description
2. Add classification logic in `src/pinlint/lint.py:lint_text()` where appropriate
3. Create golden requirement snippets in `tests/test_lint.py`
4. Document rule in README.md under "Checks" section
5. Update CHANGELOG.md with new rule

**New Output Format:**
1. Create function in `src/pinlint/cli.py` (e.g., `_print_xml()`) that takes list[Finding]
2. Return formatted string for printing or write directly with print()
3. Add `elif args.format == "xml":` branch in `run()` function
4. Add format choice to argparse `--format` argument
5. Write integration tests in `tests/test_cli.py` to verify output structure

**New CLI Flag:**
1. Add argument to argparse parser in `src/pinlint/cli.py:run()`
2. Store in args object; prefix flag with `--` (e.g., `--no-follow`, `--allow-unpinned`)
3. Pass as keyword-only parameter to linting functions (no defaults)
4. Test exit code and behavior in `tests/test_cli.py`

**Baseline Function Extension:**
1. Keep fingerprint logic in `src/pinlint/baseline.py` (code, file, requirement, name)
2. Maintain deterministic serialization (sorted, deduplicated JSON)
3. Add unit tests in `tests/test_baseline.py` for pure functions
4. Add CLI integration tests in `tests/test_cli.py` for --write-baseline and --baseline

**Utilities:**
- Shared parsing helpers → `src/pinlint/parse.py` (e.g., line continuation, comment stripping)
- Shared validation helpers → `src/pinlint/lint.py` (e.g., pinning checks)
- Do NOT create a separate utils module; keep functions co-located with their domain

## Special Directories

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (created by `uv venv`)
- Committed: No

**`.github/`:**
- Purpose: GitHub CI workflows and templates
- Generated: No (hand-written)
- Committed: Yes

**`.pytest_cache/`:**
- Purpose: pytest cache for test discovery and state
- Generated: Yes (created by pytest)
- Committed: No

## Import Organization

**Pattern in `src/pinlint/` modules:**
1. Standard library imports (`from pathlib import Path`, `import json`)
2. Third-party imports (`from packaging.requirements import Requirement`)
3. Local imports (`from .model import Finding`, `from .parse import logical_lines`)

**Public Surface (`src/pinlint/__init__.py`):**
- Imports key functions and classes
- Uses `__all__` to define public API
- Example:
  ```python
  from .baseline import build_baseline, filter_by_baseline, load_baseline, serialize_baseline
  from .lint import lint_file, lint_text
  from .model import Finding
  from .sarif import to_sarif
  
  __all__ = [
      "Finding",
      "build_baseline",
      "filter_by_baseline",
      "lint_file",
      "lint_text",
      "load_baseline",
      "serialize_baseline",
      "to_sarif",
  ]
  ```

**No Path Aliases:**
- Project is small; relative imports (`.module`) sufficient
- No `src/` path alias needed (modern editable installs handle it)

## Dependency Graph

```
cli.py
  → lint.py (lint_file, lint_text)
  → baseline.py (load_baseline, filter_by_baseline, serialize_baseline)
  → sarif.py (to_sarif)
  → model.py (Finding)

lint.py
  → parse.py (logical_lines)
  → model.py (Finding)
  → packaging (Requirement, SpecifierSet)

baseline.py
  → model.py (Finding)

sarif.py
  → model.py (Finding)

parse.py
  → None (dataclass only)

model.py
  → None (dataclass only)

__init__.py
  → All of the above (public re-exports)
```

---

*Structure analysis: 2026-06-17*
