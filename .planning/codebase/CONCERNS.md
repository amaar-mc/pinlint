# Codebase Concerns

**Analysis Date:** 2026-06-17

## Tech Debt

### Empty Hash Values Not Validated

**Issue:** The `_split_hashes` function accepts `--hash=` with empty values, which passes the "has hashes" check even though the hash itself is invalid.

**Files:** `src/pinlint/lint.py` (lines 14-30, 94-104)

**Impact:** A requirements line like `flask==1.0 --hash=` will pass the `require_hashes=True` check because `hashes` list is non-empty (`['']`), but the hash value is actually empty and thus useless for verification. This defeats the supply-chain security goal of the linter.

**Fix approach:** Validate that hash values are non-empty after extraction. Either:
1. Filter out empty hashes in `_split_hashes` before returning, or
2. Add validation in `lint_text` to check `any(h.strip() for h in hashes)` instead of just checking if the list is truthy

**Priority:** HIGH - Affects core security guarantee

---

### Malformed Hash Flag Syntax Creates Spec Pollution

**Issue:** The `_split_hashes` tokenizer does not handle `--hash` with space before `=` correctly. Input like `flask==1.0 --hash = sha256:abc` produces `spec = "flask==1.0 sha256:abc"` and `hashes = ['=']`, creating an invalid specifier.

**Files:** `src/pinlint/lint.py` (lines 14-30)

**Impact:** The spec becomes unparseable. The code gracefully handles this with a `parse-error` finding, but it leaks the invalid syntax into the error message rather than flagging it as a malformed hash option. Edge case, but the error reporting is suboptimal.

**Fix approach:** Preprocess tokens to handle `--hash` followed by `=` as a unit, or document that `--hash = value` (with spaces) is unsupported and will be treated as a parse error.

**Priority:** LOW - Works but could be clearer in error reporting

---

## Known Bugs

### Missing Test for Constraint (-c) Include Handling

**Issue:** Tests cover `-r` includes thoroughly but do not explicitly test `-c` (constraint) include handling, even though both use the same code path.

**Files:** `tests/test_lint_file.py`

**Trigger:** Run any test that verifies includes work; `lint_file` processes both `-r` and `-c` the same way (line 9 in `parse.py`), but only `-r` is explicitly tested.

**Current coverage:** `test_follows_includes` tests `-r` behavior, `_INCLUDE` constants at line 9 in `lint.py` show both are supported, but no dedicated test for `-c`.

**Workaround:** Current code treats `-c` identically to `-r`, so if `-r` works, `-c` works. But a failing edge case would go unnoticed.

**Fix approach:** Add test like:
```python
def test_follows_constraint_includes(tmp_path: Path) -> None:
    (tmp_path / "base.txt").write_text("flask==1.0 --hash=sha256:a\n-c constraints.txt\n")
    (tmp_path / "constraints.txt").write_text("django>=2 --hash=sha256:b\n")
    findings = lint_file(
        tmp_path / "base.txt", require_hashes=True, allow_unpinned=False, follow_includes=True
    )
    assert [f.code for f in findings] == ["unpinned"]
```

---

## Security Considerations

### Path Traversal via Include Targets Unvalidated

**Issue:** The `_include_targets` function extracts paths from `-r` and `-c` lines without any validation. A requirements file can include `..` sequences to reach files outside the requirements directory tree.

**Files:** `src/pinlint/lint.py` (lines 108-114, 132-137)

**Current mitigation:** Resolved paths are stored in `seen` set to prevent cycles. Unreadable files yield `io-error` findings rather than raising. The behavior matches pip's own path resolution.

**Risk assessment:** NOT a security issue in pinlint's context. The tool is static analysis; it cannot execute code. A malicious requirements file could include `../../../etc/passwd`, but:
1. pinlint would try to read it as a requirements file (and likely fail or treat it as parse-error),
2. pinlint is run by the user, so reading accessible files is expected,
3. pinlint does not modify files or execute code.

**Recommendations:** Document this behavior in SECURITY.md (already exists). No code change needed.

---

### No Validation of Hash Algorithm or Format

**Issue:** Hash values are extracted and stored but never validated for algorithm (sha256 vs md5, etc.) or format.

**Files:** `src/pinlint/lint.py` (lines 14-30, 94-104)

**Current mitigation:** `packaging` and pip's own hash validation at install time would catch malformed hashes. pinlint only checks presence.

**Risk:** An unpinned package with a well-formed but invalid hash (e.g., `--hash=sha256:invalid`) would pass pinlint but fail at install. This is acceptable since pinlint's goal is to enforce the *discipline of pinning*, not validate the pins themselves.

**Recommendations:** Document in README that pinlint checks presence and basic syntax, not hash validity. (Already documented: "fully pinned and hash-pinned" focus is on presence, not validation.)

---

## Performance Bottlenecks

### Recursive Include Resolution Has No Depth Limit

**Issue:** The `_lint_file` function recursively follows includes via a `seen` set to prevent cycles, but there is no hard limit on recursion depth.

**Files:** `src/pinlint/lint.py` (lines 117-138)

**Current capacity:** Python's default recursion limit is ~1000. A deeply nested chain of includes (1000+ files) would hit a `RecursionError`.

**Scenario:** While unlikely in practice, a malformed or adversarial requirements file with a chain like:
```
-r level1.txt
# level1.txt:
-r level2.txt
# level2.txt:
-r level3.txt
... (1000+ times)
```

Would exhaust the stack.

**Scaling path:** Convert to iterative processing with a deque, or set a configurable depth limit (e.g., max 50 nested includes). Low priority given the unlikely scenario.

**Priority:** LOW - Requires pathological input

---

### No Caching of Read Files or Parse Results

**Issue:** Each `lint_file` call re-reads and re-parses the same files if they are included multiple times (though cycle protection prevents infinite loops).

**Files:** `src/pinlint/lint.py` (lines 117-138)

**Impact:** Negligible for typical use (requirements files are small, reads are fast). Only noticeable with dozens of large included files.

**Scaling path:** Cache results by resolved path: `{Path: (findings, parsed_text)}`. Would require careful lifetime management to avoid stale caches.

**Priority:** LOW - Not a practical bottleneck at current scale

---

## Fragile Areas

### Logical Line Number Tracking Relies on Implicit Behavior

**Issue:** The `LogicalLine.number` field (1-based line number) is set to the starting physical line when a logical line spans multiple lines via backslash continuation.

**Files:** `src/pinlint/parse.py` (lines 6-10, 28-40)

**Why fragile:** The correctness of the line number depends on the order of operations: `start = i + 1` must happen *before* the continuation loop. If someone refactors the loop structure, this could silently break.

**Safe modification:** Document the invariant with a comment: "start is set before the continuation loop to capture the first physical line of the logical line."

**Test coverage:** `test_line_number_is_logical_start` covers this (line 55 in test_lint.py), so regressions would be caught. SAFE.

---

### Include Cycle Protection Depends on Path Resolution

**Issue:** The `_lint_file` function guards against cycles using a set of resolved paths. If `Path.resolve()` behaves unexpectedly (e.g., with symlinks, relative paths, or case-insensitive filesystems), the cycle guard could fail.

**Files:** `src/pinlint/lint.py` (lines 117-123)

**Current behavior:** `path.resolve()` is called at the start of `_lint_file`. On case-insensitive filesystems (macOS, Windows), `Path.resolve()` preserves the case given, not the canonical case, so two paths referring to the same file with different cases would not be detected as equal.

**Safe modification:** Test on case-insensitive systems or use `path.resolve().as_posix()` with `.lower()` on Windows/macOS for the key. However, breaking change.

**Priority:** LOW - Test coverage (`test_include_cycle_is_safe`) would catch most issues. Real-world impact depends on filesystem semantics.

---

### Baseline Fingerprint Design Assumes Stable Requirement Text

**Issue:** The baseline fingerprint includes the requirement text (`finding.requirement`) as part of the key. If a requirement is reformatted (e.g., `flask>=1.0` vs `flask >= 1.0`), the fingerprint changes and the suppression breaks.

**Files:** `src/pinlint/baseline.py` (lines 22-29, 42)

**Impact:** If a user fixes a requirement by reformatting it (not changing the version), the baseline suppression is lost. Example:
```
# Old requirement: flask>=1.0 --hash=sha256:abc (unpinned)
# Baseline suppresses this
# Fix: add ==1.0, but with extra spaces: flask == 1.0 --hash=sha256:abc
# Requirement text changed -> fingerprint misses -> finding reappears
```

**Why this matters:** Users doing incremental adoption with baselines may encounter unexpected noise when reformatting.

**Workaround:** Users can re-run `--write-baseline` after formatting changes.

**Fix approach:** Normalize requirement text in fingerprint (strip whitespace, etc.) before hashing. Would require careful consideration of what counts as "the same requirement."

**Priority:** MEDIUM - Affects usability of the baseline feature, but has a workaround

---

## Test Coverage Gaps

### No Test for Empty Requirement Lines

**Issue:** The `logical_lines` function filters empty lines, but there is no explicit test for edge cases like all-whitespace lines or continuation that results in empty text.

**Files:** `tests/test_lint.py`

**What's not tested:** A line like `flask==1.0 \` (ends with backslash but has no continuation) - does it become empty?

**Current behavior:** `parse.py` line 32-36 continues reading until a non-backslash line is found. If the file ends with a backslash, `i >= n` breaks the loop and the accumulated `buf` is used. If `buf` is all whitespace, line 38 filters it out.

**Risk:** Low - the filtering is correct. But a test would document the expected behavior.

**Priority:** LOW - No known issue, just documentation gap

---

### Missing Test for Multiple File Arguments

**Issue:** The CLI accepts multiple files, but tests only pass a single file at a time.

**Files:** `tests/test_cli.py`, `src/pinlint/cli.py` (line 32: `nargs="+"`)

**Scenario:** `pinlint req1.txt req2.txt` - are findings from both files combined correctly?

**Current implementation:** Line 71-79 in `cli.py` loops through all files and extends the findings list, so it should work. But there is no explicit test.

**Recommendation:** Add test:
```python
def test_multiple_files(tmp_path: Path) -> None:
    r1 = tmp_path / "r1.txt"
    r2 = tmp_path / "r2.txt"
    r1.write_text("flask>=1.0\n")
    r2.write_text("django>=2.0\n")
    assert run([str(r1), str(r2)]) == 1
    # Both findings should be present
```

**Priority:** MEDIUM - Multi-file is a documented feature but under-tested

---

### No Test for Baseline with Absolute File Paths

**Issue:** Baselines use file paths as part of the fingerprint. If a file is referenced by absolute path in one run and relative path in another, the fingerprints might differ.

**Files:** `tests/test_baseline.py`, `src/pinlint/baseline.py` (line 27: `"file": finding.file`)

**Scenario:**
```
pinlint requirements.txt --write-baseline baseline.json  # file="requirements.txt"
pinlint /absolute/path/requirements.txt --baseline baseline.json  # file="/abs/.../requirements.txt"
```

The file paths differ, so the fingerprint changes.

**Current behavior:** CLI accepts both, and each use case is valid. But the baseline behavior is not documented.

**Recommendation:** Normalize file paths in the CLI before linting (resolve to absolute, or use relative consistently).

**Priority:** MEDIUM - Could surprise users moving repos or changing how they invoke the CLI

---

## Scaling Limits

### No Limit on Number of Findings

**Issue:** The CLI prints all findings to stdout. A requirements file with 100,000 unpinned packages would produce 100,000 lines of output (or larger JSON).

**Files:** `src/pinlint/cli.py` (lines 14-24, 102-107)

**Current capacity:** Tested to work with hundreds of findings. No known performance issue.

**Scaling path:** For very large files, consider:
1. Pagination or summary output (e.g., "5000 findings found" without listing all),
2. Streaming output (one finding per line, JSON lines format),
3. Exit early if a threshold is reached.

**Priority:** VERY LOW - Not a practical issue, and current output is useful for CI/CD

---

## Dependencies at Risk

### Packaging>=21 Constraint Is Broad

**Issue:** The dependency allows `packaging>=21`, which spans multiple major version releases (21, 22, 23, 24 as of 2024).

**Files:** `pyproject.toml` (line 39)

**Risk:** LOW. The APIs used (Requirement, SpecifierSet, operator, version) have been stable since at least version 21. No breaking changes detected in the 24.x line.

**Impact:** New versions of `packaging` could introduce breaking changes to the public API. More likely: better performance, new features. Pinlint would inherit those improvements.

**Recommendation:** Consider upper bound if/when `packaging>=25` is released and contains breaking changes. Current policy (broad constraint) is reasonable for a mature, dependency-light tool.

**Priority:** VERY LOW

---

### Hatchling Build Backend Has No Upper Bound

**Issue:** `pyproject.toml` specifies `requires = ["hatchling"]` with no version constraint.

**Files:** `pyproject.toml` (line 2)

**Risk:** LOW. Hatchling is actively maintained and unlikely to break the simple wheel-only build.

**Impact:** Future versions of Hatchling could change wheel format, causing build failures. But Hatchling aims for backward compatibility.

**Recommendation:** If build issues arise, add version constraint (e.g., `hatchling>=1.20,<2`).

**Priority:** VERY LOW

---

## Missing Critical Features

### No Validation of Hash Algorithm

**Issue:** Pinlint checks for the presence of hashes but not their algorithm or strength.

**Files:** `src/pinlint/lint.py` (entire file)

**What's missing:** A check like "warn if hashes use weak algorithms (md5)" or "require sha256 or stronger".

**Why it's not critical:** The linter's goal is discipline (pinning and hashing), not security policy enforcement. Hash algorithm choice should be enforced by the package manager or CI policy, not the linter.

**Recommendation:** Document this limitation in README. If users want to enforce algorithm strength, they can post-process the JSON output or use a separate tool.

**Priority:** LOW - Out of scope for this linter

---

### No Support for URL Hashes (PEP 720)

**Issue:** Pinlint treats URL installs as unpinnable. But PEP 720 introduces a way to pin them.

**Files:** `src/pinlint/lint.py` (lines 62-67, 78-82)

**Current behavior:** Lines like `flask @ https://example.com/flask-1.0.tar.gz` are flagged as unpinnable.

**Impact:** Modern Python projects using PEP 720 "direct references" would get a false positive from pinlint.

**Fix approach:** Parse URL hashes (if present) and allow them similar to other hashes. Requires updating the spec/hash splitting logic.

**Priority:** MEDIUM - Emerging standard, may become more common

---

## PyPI Publishing Risks

### Version Bump Must Update Three Locations

**Issue:** The version number `0.4.0` appears in:
1. `pyproject.toml` (line 7: `version = "0.4.0"`)
2. `src/pinlint/__init__.py` (line 18: `__version__ = "0.4.0"`)

**Files:** `pyproject.toml`, `src/pinlint/__init__.py`

**Risk:** Publishing with mismatched versions would confuse users. The `__version__` reported by the CLI would not match the PyPI version.

**Current mitigation:** CLAUDE.md release checklist includes manual verification.

**Fix approach:** Use single source of truth:
```python
# pyproject.toml: dynamic = ["version"]
# pyproject.toml [tool.hatch.version]: path = "src/pinlint/__init__.py"
# src/pinlint/__init__.py: __version__ = "0.4.0"
```

This requires hatchling to read the version from the module. Minor refactor.

**Priority:** MEDIUM - Affects release process reliability

---

### CHANGELOG Not Enforced

**Issue:** The CHANGELOG.md file is manually maintained. A release without a CHANGELOG entry would go unnoticed.

**Files:** `CHANGELOG.md`, `src/pinlint/__init__.py`

**Risk:** Users cannot track what changed between versions.

**Current mitigation:** CLAUDE.md includes manual reminder ("update CHANGELOG.md").

**Fix approach:** Add a pre-commit or CI check that verifies an "Unreleased" section exists before pushing, or that version in `__init__.py` matches an entry in CHANGELOG.

**Priority:** LOW - Process issue, not code issue

---

### Build Artifacts Not Tested Before Publish

**Issue:** The release workflow builds with `uv build` and checks with `uv run twine check`, but does not install and test the built wheel.

**Files:** `CLAUDE.md` (release section)

**Risk:** A wheel could be built successfully but fail to install or import due to packaging metadata issues.

**Fix approach:** Add step:
```bash
# After uv build, before publish:
pip install dist/pinlint-*.whl
python -c "import pinlint; print(pinlint.__version__)"
```

**Priority:** MEDIUM - Catches issues before PyPI

---

*Concerns audit: 2026-06-17*
