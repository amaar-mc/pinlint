# Testing Patterns

**Analysis Date:** 2026-06-17

## Test Framework

**Runner:**
- pytest 8+ (`pyproject.toml`: `pytest>=8`)
- Config: `pyproject.toml` (no separate pytest.ini)

**Assertion Library:**
- pytest assertions with `assert` statement
- No explicit library; plain Python comparisons

**Run Commands:**

```bash
uv run pytest -q              # Run all tests
uv run pytest -q tests/       # Run test directory
uv run pytest tests/test_lint.py  # Run single file
```

Run options commonly used:
- `-q`: Quiet mode (summary only)
- No explicit pytest markers or xfail used
- No test filtering by pattern observed

## Test File Organization

**Location:**
- Tests in `tests/` directory at repository root
- One test file per source module: `test_lint.py` (for `src/pinlint/lint.py`), `test_cli.py` (for `src/pinlint/cli.py`), etc.
- No fixtures in separate `conftest.py`; helper functions defined in test files

**Naming:**
- Test files: `test_*.py`
- Test functions: `test_*` (descriptive names)
- Helper functions: `_f()` (private, lowercase with underscore)

**Structure:**

```
tests/
├── test_lint.py         # Tests for lint_text() and related functions
├── test_lint_file.py    # Tests for lint_file() with file system
├── test_cli.py          # Tests for CLI run() function
├── test_baseline.py     # Tests for baseline functions and CLI flags
└── test_sarif.py        # Tests for SARIF output
```

## Test Structure

**Test function anatomy:**

```python
def test_clean_file_exits_zero(tmp_path: Path) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask==1.0 --hash=sha256:a\n")
    assert run([str(path)]) == 0
```

Pattern: Arrange → Act → Assert (AAA)

**Common structure across test files:**

1. **Arrange:** Create test data (temp files, test strings, fixtures)
2. **Act:** Call the function under test
3. **Assert:** Check result (return code, output, findings list)

## Test Patterns by Module

### test_lint.py (lint_text() unit tests)

**Helper function for conciseness:**

```python
def lint(text: str, *, require_hashes: bool = True, allow_unpinned: bool = False) -> list[str]:
    return [
        f.code
        for f in lint_text(
            text, source="req.txt", require_hashes=require_hashes, allow_unpinned=allow_unpinned
        )
    ]
```

Rationale: Tests focus on error codes, not full Finding objects. Helper extracts codes for brevity.

**Test organization:**
- Golden requirements snippets for each rule: `test_fully_pinned_and_hashed_passes()`, `test_unpinned_range()`, `test_missing_hash()`
- Behavior tests: `test_wildcard_is_not_exact()`, `test_editable_is_unpinnable()`, `test_comments_and_blank_lines_ignored()`
- Edge cases: `test_line_continuation_joins_hashes()`, `test_marker_with_pin_and_hash_passes()`
- Option tests: `test_relaxed_flags()`

**Assertion patterns:**
```python
assert lint("flask==2.0.1 --hash=abc123\n") == []  # No findings
assert [f.code for f in findings] == ["unpinned"]  # Check codes
assert findings[0].line == 1  # Check specific field
assert set(lint(...)) == {"unpinned", "missing-hash"}  # Check set of codes
```

### test_lint_file.py (lint_file() with file system)

**Pattern: Use pytest tmp_path for isolated file system tests:**

```python
def test_follows_includes(tmp_path: Path) -> None:
    (tmp_path / "base.txt").write_text("flask==1.0 --hash=sha256:a\n-r child.txt\n")
    (tmp_path / "child.txt").write_text("django>=2 --hash=sha256:b\n")
    findings = lint_file(
        tmp_path / "base.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
    )
    assert [f.code for f in findings] == ["unpinned"]
    assert findings[0].file.endswith("child.txt")
```

**Test coverage:**
- Include following: `test_follows_includes()`, `test_no_follow()`
- Cycle detection: `test_include_cycle_is_safe()`
- Error handling: `test_missing_file_reports_io_error()`

### test_cli.py (CLI run() function)

**Pattern: Test exit codes and output capture with capsys:**

```python
def test_findings_exit_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\n")
    assert run([str(path)]) == 1
    out = capsys.readouterr().out
    assert "unpinned" in out
    assert "missing-hash" in out
```

**capsys fixture usage:**
- `capsys.readouterr()` after `run()` call
- Check `.out` for stdout, `.err` for stderr
- Call once to consume output (subsequent calls see empty)

**Test patterns:**
- Exit codes: `0` (success), `1` (findings), `2` (error)
- Flag combinations: `--allow-unpinned --no-hashes`
- Output formats: text, json (parse with `json.loads`), sarif
- Allowlist: `--allow` flag (case-insensitive matching)

**Text output testing:**
```python
out = capsys.readouterr().out
assert "unpinned" in out
assert "missing-hash" in out
```

**JSON output testing:**
```python
data = json.loads(capsys.readouterr().out)
assert isinstance(data, list)
assert {d["code"] for d in data} == {"unpinned", "missing-hash"}
keys = {"file", "line", "code", "message", "requirement", "name"}
assert all(keys <= set(d) for d in data)
```

### test_baseline.py (baseline functions and CLI integration)

**Structure: Organized into two sections with comments:**

```python
# ---------------------------------------------------------------------------
# Unit tests for pure functions
# ---------------------------------------------------------------------------

def _f(code: str, file: str = "r.txt", req: str = "flask>=1", name: str = "flask") -> Finding:
    return Finding(file=file, line=1, code=code, message="test", requirement=req, name=name)

def test_build_baseline_deduplicates() -> None:
    f = _f("unpinned")
    result = build_baseline(findings=[f, f])
    assert len(result) == 1

# ---------------------------------------------------------------------------
# CLI golden tests
# ---------------------------------------------------------------------------

def test_write_baseline_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ...
```

**Unit test helper:**
- `_f()` function creates test Finding with sensible defaults
- Tests invoke pure functions directly: `build_baseline()`, `serialize_baseline()`, `load_baseline()`, `filter_by_baseline()`

**Golden test pattern (integration):**
- Write baseline from dirty file
- Verify baseline content
- Re-run with `--baseline` to suppress existing findings
- Verify new findings still surface
- Example: `test_baseline_suppresses_all_existing_findings()`, `test_baseline_surfaces_new_finding()`, `test_baseline_surfaces_only_new_finding()`

**Edge case tests:**
- Line number drift ignored: `test_filter_ignores_line_number_drift()`, `test_baseline_line_drift_suppressed()`
- JSON validation: `test_load_baseline_rejects_*` tests
- Determinism: `test_serialize_is_deterministic()`, `test_write_baseline_deterministic()`
- Composition: `test_baseline_compose_with_format_json()`

### test_sarif.py (SARIF output)

**Pattern: Test document structure, field mapping, and CLI integration**

```python
def test_document_shape() -> None:
    doc = to_sarif([], tool_version="9.9.9")
    assert doc["version"] == "2.1.0"
    assert doc["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    ...

def test_result_maps_finding_fields() -> None:
    finding = Finding(
        "requirements.txt", 3, "unpinned", "flask is not pinned", "flask>=1.0", "flask"
    )
    [result] = to_sarif([finding], tool_version="0.3.0")["runs"][0]["results"]
    assert result["ruleId"] == "unpinned"
    ...
```

**JSON structure testing:**
- Assert dict keys and values
- Unpack single-element lists with `[result] = list`
- Check nested paths with direct dict access

## Mocking

**Framework:** None; tests use real objects and file systems

**Approach:**
- Use `tmp_path` fixture for file I/O tests instead of mocking Path
- Pass test strings directly to `lint_text()`
- Create temporary files with `path.write_text()`
- No mock.patch, unittest.mock, or pytest-mock used

Rationale: The codebase has no complex external dependencies (only `packaging`). Real objects are simpler and more robust.

## Fixtures and Test Data

**Built-in pytest fixtures used:**
- `tmp_path: Path` — Temporary directory for file tests (auto-cleanup)
- `capsys: pytest.CaptureFixture[str]` — Capture stdout/stderr

**Test data patterns:**

1. **Inline strings for lint_text() tests:**
   ```python
   def test_unpinned_range() -> None:
       findings = lint_text(
           "flask>=2.0 --hash=sha256:abc\n", source="r", require_hashes=True, allow_unpinned=False
       )
   ```

2. **Temp file writes for lint_file() tests:**
   ```python
   (tmp_path / "base.txt").write_text("flask==1.0 --hash=sha256:a\n-r child.txt\n")
   ```

3. **Test Finding factory in baseline tests:**
   ```python
   def _f(code: str, file: str = "r.txt", req: str = "flask>=1", name: str = "flask") -> Finding:
       return Finding(...)
   ```

No fixture files, no yaml data files. Data is embedded in test code.

## Coverage

**Requirements:** Not explicitly enforced (no pytest-cov config in pyproject.toml)

**Target:** Implicit goal of comprehensive test coverage for all public functions

**Measured by:** Full test suite run; high coverage expected for core logic

## Test Types

### Unit Tests

**Scope:** Single function in isolation

Examples:
- `test_lint.py`: `lint_text()` with various requirement strings
- `test_baseline.py`: `build_baseline()`, `filter_by_baseline()`, `serialize_baseline()`, `load_baseline()`
- `test_sarif.py`: `to_sarif()`

Approach: Call function directly, assert return value.

### Integration Tests

**Scope:** Multiple modules working together, or CLI with file system

Examples:
- `test_lint_file.py`: `lint_file()` with actual file system (tmp_path) and include following
- `test_cli.py`: `run()` with temp files and output capture
- `test_baseline.py` CLI tests: Full workflow with `--write-baseline` and `--baseline` flags

Approach: Set up temporary files, call public function or CLI, verify outputs and side effects.

### CLI Tests

**Focus:** Exit codes, argument parsing, output formats

Examples:
- `test_cli.py`: Exit codes (0/1/2), flag combinations
- `test_baseline.py`: `--write-baseline`, `--baseline` flags and file writes

Approach: Call `run(argv)` with list of args, check return code and output with `capsys`.

## Common Assertions

**Exit codes:**
```python
assert run([str(path)]) == 0  # Success
assert run([str(path)]) == 1  # Findings found
assert code == 2              # Error (missing file, bad baseline)
```

**Finding codes:**
```python
assert [f.code for f in findings] == ["unpinned"]
assert {f.code for f in findings} == {"unpinned", "missing-hash"}
assert "unpinned" in lint(text)
```

**Finding fields:**
```python
assert findings[0].line == 1
assert findings[0].file.endswith("child.txt")
assert all(f.name == "flask" for f in findings)
```

**Output format:**
```python
assert "Baseline written" in out
assert "issue(s) found" in capsys.readouterr().err
```

**JSON structure:**
```python
data = json.loads(capsys.readouterr().out)
assert isinstance(data, list)
assert {d["code"] for d in data} == {"unpinned", "missing-hash"}
```

**File I/O:**
```python
assert baseline.exists()
doc = json.loads(baseline.read_text())
```

## Bug Fix Pattern

**Test-driven approach:**

1. Write failing test that reproduces the bug
2. Fix implementation
3. Verify test passes

Example from codebase (implicit): All tests written before or concurrently with feature implementation.

## No Test Skips

No `@pytest.mark.skip`, `@pytest.mark.xfail`, or `skipif` used in test suite. All tests run and pass.

---

*Testing analysis: 2026-06-17*
