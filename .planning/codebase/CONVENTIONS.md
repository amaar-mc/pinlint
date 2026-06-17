# Coding Conventions

**Analysis Date:** 2026-06-17

## Naming Patterns

**Files:**
- Lowercase with underscores: `model.py`, `parse.py`, `lint.py`, `baseline.py`, `sarif.py`
- Test files use `test_` prefix: `test_lint.py`, `test_cli.py`, `test_baseline.py`

**Functions:**
- Lowercase with underscores: `logical_lines()`, `_strip_comment()`, `_split_hashes()`, `lint_text()`, `lint_file()`
- Private functions prefixed with single underscore: `_is_exactly_pinned()`, `_include_targets()`, `_lint_file()`
- CLI command named plainly: `run()`, `main()`

**Classes/Dataclasses:**
- PascalCase: `Finding`, `LogicalLine`
- Use `@dataclass(frozen=True)` for immutable value objects

**Variables:**
- Lowercase with underscores: `source`, `require_hashes`, `allow_unpinned`
- Single letter acceptable for loop variables: `i`, `ch`, `f`, `n`
- Dict keys use lowercase: `"code"`, `"file"`, `"requirement"`, `"name"`

**Type Aliases/Constants:**
- Uppercase with underscores: `_INCLUDE`, `_EDITABLE`, `_VCS_PREFIXES`, `_SCHEMA`, `_INFORMATION_URI`, `_RULES`, `_INDEX_BY_CODE`, `_LEVEL_BY_CODE`

## Code Style

**Formatting:**
- Tool: Ruff with line length 100 (`src/pinlint`)
- Linting: Ruff rules `E`, `F`, `I`, `UP`, `B`, `SIM`, `RUF` selected
- Type checking: MyPy in strict mode (`files = ["src"]`)

**Imports:**
- Standard library first, then third-party (`packaging`), then local relative imports
- Ordered: `from collections.abc import`, `from dataclasses import`, `from pathlib import`, `from packaging.*`, then locals
- Unused imports removed

**Line length:** 100 characters (Ruff configured)

## Keyword-Only Arguments

**Pattern: All library functions use keyword-only arguments** (required parameter style per CLAUDE.md)

Examples from codebase:
- `lint_text(text: str, *, source: str, require_hashes: bool, allow_unpinned: bool) -> list[Finding]`
- `lint_file(path: str | Path, *, require_hashes: bool, allow_unpinned: bool, follow_includes: bool) -> list[Finding]`
- `fingerprint(*, finding: Finding) -> dict[str, str]`
- `build_baseline(*, findings: list[Finding]) -> list[dict[str, str]]`
- `serialize_baseline(*, findings: list[Finding], tool_version: str) -> str`
- `load_baseline(*, text: str) -> list[dict[str, str]]`
- `filter_by_baseline(*, findings: list[Finding], baseline: list[dict[str, str]]) -> list[Finding]`
- `to_sarif(findings: list[Finding], *, tool_version: str) -> dict[str, object]`

Rationale: Prevents silent bugs from positional argument reordering; makes call sites explicit.

## Type Annotations

**Strict mode required** (MyPy strict = true)

All functions and methods require:
- Explicit parameter types
- Explicit return types
- No `Any` unless unavoidable

Examples:
```python
def logical_lines(text: str) -> Iterator[LogicalLine]:
def _strip_comment(physical: str) -> str:
def _is_exactly_pinned(specifier: SpecifierSet) -> bool:
def lint_text(text: str, *, source: str, require_hashes: bool, allow_unpinned: bool) -> list[Finding]:
```

Use modern union syntax:
- `str | Path` not `Union[str, Path]`
- `list[Finding]` not `List[Finding]`
- `dict[str, str]` not `Dict[str, str]`

## Error Handling

**Strategy:** Exceptions caught narrowly and converted to findings or `ValueError`

Patterns observed:

1. **Parse errors caught and reported as Finding:**
   ```python
   try:
       requirement = Requirement(spec)
   except InvalidRequirement as exc:
       findings.append(
           Finding(
               source, entry.number, "parse-error", f"cannot parse requirement: {exc}", spec
           )
       )
   ```

2. **File I/O errors caught and reported as Finding (not raised):**
   ```python
   try:
       text = path.read_text(encoding="utf-8")
   except OSError as exc:
       return [Finding(str(path), 0, "io-error", f"cannot read file: {exc}", "")]
   ```

3. **JSON validation errors as ValueError (library function):**
   ```python
   try:
       doc = json.loads(text)
   except json.JSONDecodeError as exc:
       raise ValueError(f"baseline is not valid JSON: {exc}") from exc
   ```

   Followed by structural validation with descriptive ValueError messages.

## Comments

**When to comment:**
- Non-obvious algorithm or parsing logic (e.g., `_strip_comment`)
- Edge cases and special behavior (e.g., io-error line 0, cycle detection)
- File-level docstrings for module purpose

Example docstrings:
```python
def logical_lines(text: str) -> Iterator[LogicalLine]:
    """Yield the non-empty logical lines of a requirements file, joining lines that end
    with a backslash and dropping comments and blank lines."""
```

**No comments for obvious code:**
- Variable assignments that are clear
- Simple loops
- Type annotations that explain intent

## Function Design

**Size:** Functions typically 10-40 lines; longer functions (60-70 lines) for CLI argument parsing

**Parameters:**
- Positional arguments for primary input (the thing being transformed): `text`, `path`, `findings`
- Keyword-only arguments for options/flags: `source=`, `require_hashes=`, `allow_unpinned=`
- No default parameter values (per CLAUDE.md)

**Return values:**
- Return findings in a list: `list[Finding]`
- Return computed data as plain dicts/lists when appropriate: `list[dict[str, str]]`, `dict[str, object]`
- Return single values when simple: `bool`, `str`, `int`

**Pure functions preferred:**
- `_split_hashes()` takes a string, returns a tuple
- `_is_exactly_pinned()` takes a specifier, returns a bool
- `fingerprint()` takes a Finding, returns a dict
- `build_baseline()` takes findings, returns a sorted, deduplicated list

## Module Design

**Exports:**
- Public API in `__init__.py` with `__all__`: `Finding`, `lint_text`, `lint_file`, `build_baseline`, `filter_by_baseline`, `load_baseline`, `serialize_baseline`, `to_sarif`
- Private functions use `_` prefix: `_strip_comment()`, `_include_targets()`, `_lint_file()`, `_rule_name()`, `_driver_rules()`, `_result()`

**Barrel files:** None used; single function imports work fine

**Layering:**
- `model.py`: Core dataclass, no dependencies
- `parse.py`: Logical line parsing, no dependencies
- `lint.py`: Linting rules, depends on `model` and `parse`
- `baseline.py`: Baseline management, depends on `model`
- `sarif.py`: SARIF output formatting, depends on `model`
- `cli.py`: Argument parsing and orchestration, depends on all above
- `__init__.py`: Public surface only

## Docstrings & Type Hints

**Module docstrings:**
- One-line summary starting with verb: `"""Static linter that checks requirements files are fully version-pinned and hash-pinned."""`
- Multi-line docstrings for complex modules explain design: baseline.py includes design rationale for fingerprint structure

**Function docstrings:**
- Single-line docstring describing what the function does
- No parameter documentation; type hints are sufficient
- Mention important edge cases or non-obvious behavior

---

*Convention analysis: 2026-06-17*
