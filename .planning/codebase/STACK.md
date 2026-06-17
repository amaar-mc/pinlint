# Technology Stack

**Analysis Date:** 2026-06-17

## Languages

**Primary:**
- Python 3.10+ - Entire codebase (CLI tool, library, tests)
- Supported versions: 3.10, 3.11, 3.12, 3.13

## Runtime

**Environment:**
- Python interpreter (3.10+ required via `requires-python = ">=3.10"` in `pyproject.toml`)

**Package Manager:**
- pip (implied via requirements file validation)
- Build system: hatchling (for packaging and distribution)

## Frameworks

**Core:**
- None - Pure Python library with minimal dependencies

**Testing:**
- pytest 8+ - Test runner, configured via `pyproject.toml`
- Used in: `tests/` directory for unit and integration tests

**Build/Dev:**
- hatchling - Build backend for packaging (`pyproject.toml` line 2)
- ruff 0.6+ - Linter and formatter (project-wide code quality)
- mypy 1.11+ - Static type checker (strict mode enabled)
- pytest 8+ - Test execution

## Key Dependencies

**Critical:**
- packaging 21+ - Parses PEP 508 requirements and version specifiers
  - Used in: `src/pinlint/lint.py` (imports `packaging.requirements.Requirement`, `packaging.specifiers.SpecifierSet`)
  - Why it matters: Core to requirement parsing; any change breaks the linter

**Development Only:**
- pytest 8+ - Test framework
- ruff 0.6+ - Code linting with rules: E, F, I, UP, B, SIM, RUF
- mypy 1.11+ - Type checking in strict mode

## Configuration

**Environment:**
- No external service configuration required
- No environment variables consumed by the runtime code

**Build:**
- `pyproject.toml` - Single source of truth for project metadata, dependencies, and tool config
  - Tool configs: `[tool.ruff]` (linting), `[tool.mypy]` (type checking)
  - Build config: `[tool.hatch.build.targets.wheel]` packages `src/pinlint`
- `.pre-commit-hooks.yaml` - Defines pinlint as a pre-commit hook
  - Entry point: `pinlint`
  - Files pattern: `requirements.*\.txt$`

**Entry Points:**
- CLI: `pinlint.cli:main` - Console script for command-line usage
  - Exposed as: `[project.scripts] pinlint = "pinlint.cli:main"`

## Build Artifacts

**Wheel:**
- Built to `dist/` directory via `uv build`
- Requires validation before publishing: `uv run twine check dist/*`

## Platform Requirements

**Development:**
- Python 3.10+ with pip or compatible package manager (uv recommended per CLAUDE.md)
- Git (for pre-commit hook integration)

**Production:**
- Python 3.10+ only (no external services, no databases, no web server)
- Installable via: `pip install pinlint`

## Publishing

**Target:**
- PyPI (Python Package Index)
- Uses: twine for publishing (noted in CLAUDE.md)
- Version: semantic versioning (currently 0.4.0)

---

*Stack analysis: 2026-06-17*
