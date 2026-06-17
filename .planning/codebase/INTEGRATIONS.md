# External Integrations

**Analysis Date:** 2026-06-17

## APIs & External Services

**GitHub:**
- Project repository: https://github.com/amaar-mc/pinlint
- Issues tracker: https://github.com/amaar-mc/pinlint/issues
- Changelog hosted: https://github.com/amaar-mc/pinlint/blob/main/CHANGELOG.md
- Homepage: https://github.com/amaar-mc/pinlint

**GitHub Code Scanning:**
- Integration: SARIF output format support
  - Implemented in: `src/pinlint/sarif.py`
  - Function: `to_sarif(findings, tool_version)` generates SARIF 2.1.0 compliant JSON
  - Schema reference: https://json.schemastore.org/sarif-2.1.0.json
  - Used for: `pinlint --format sarif` output

## Data Storage

**Databases:**
- None - this is a stateless linter

**File Storage:**
- Local filesystem only
  - Reads: requirements files (any file pattern specified on CLI)
  - Writes: baseline JSON files (optional, via `--write-baseline` flag)
  - Location: Baseline files written to user-specified path via `Path.write_text()`

**Caching:**
- None - stateless execution

## Authentication & Identity

**Auth Provider:**
- None required - completely standalone tool
- No authentication, tokens, or secrets needed at runtime

## Monitoring & Observability

**Error Tracking:**
- None - errors are reported via exit codes and stderr
  - Exit 0: No findings (or writing baseline)
  - Exit 1: Findings detected
  - Exit 2: Configuration/file I/O errors

**Logs:**
- stderr output for messages:
  - Findings summary: `"{len(findings)} issue(s) found"` (via `sys.stderr`)
  - Baseline write confirmation: `"Baseline written to {path} ({count} finding(s))"`
  - Error messages for baseline loading failures (file read or JSON parse errors)
- stdout output:
  - Findings in requested format (text, JSON, or SARIF)
  - No structured logging framework used

## CI/CD & Deployment

**Hosting:**
- GitHub (repository hosted)
- PyPI (distribution)

**CI Pipeline:**
- GitHub Actions workflow at: `.github/workflows/ci.yml`
- Triggers: on push to `main` branch and on pull requests
- Matrix testing: Python 3.10, 3.11, 3.12, 3.13
- Pipeline steps:
  1. Checkout code
  2. Setup Python (per matrix version)
  3. Install in development mode: `pip install -e ".[dev]"`
  4. Lint: `ruff check .`
  5. Type check: `mypy src`
  6. Test: `pytest -q`

**Distribution:**
- Package format: Python wheel
- Distribution platform: PyPI
- Published as: `pinlint` package
- Installation: `pip install pinlint`

## Environment Configuration

**Required env vars:**
- None - no environment variables consumed

**Secrets location:**
- No secrets managed in this codebase
- PyPI publishing handled via GitHub repository secrets (not in codebase)

## Pre-commit Integration

**Hook Registration:**
- Defined in: `.pre-commit-hooks.yaml`
- Hook ID: `pinlint`
- Entry point: `pinlint` CLI command
- File pattern: Matches `requirements.*\.txt$` files
- Usage: Users add to their `.pre-commit-config.yaml` to validate requirements files on commit

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None - no external service calls made

## Schema/Standards Compliance

**Requirements File Format:**
- PEP 508 specifiers: parsed via `packaging.requirements.Requirement`
- pip extensions: `--hash` flag (non-standard, handled separately in `_split_hashes()`)
- Include directives: `-r` (requirement) and `-c` (constraint) followed with file paths
- Continuation: Backslash line continuations supported

**SARIF Output:**
- SARIF 2.1.0 standard for code scanning integration
- Rule catalog: 5 codes (unpinned, missing-hash, unpinnable, parse-error, io-error)
- Levels: errors (pinning issues) and warnings (unpinnable entries)

---

*Integration audit: 2026-06-17*
