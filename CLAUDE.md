# pinlint

Static linter that checks requirements files are fully version-pinned and hash-pinned.
Library plus CLI. One runtime dependency: `packaging`.

## Commands

- Create env and install: `uv venv && uv pip install -e ".[dev]"`
- Test: `uv run pytest -q`
- Lint: `uv run ruff check .` (format with `uv run ruff format .`)
- Types: `uv run mypy src`
- Build: `uv build` (then `uv run --with twine twine check dist/*` before publishing)
- Run the CLI: `uv run pinlint requirements.txt`

## Architecture

`src/pinlint/`:
- `model.py` the Finding dataclass
- `parse.py` requirements text into logical lines (comments, continuations)
- `lint.py` the rules; lint_text and lint_file (the latter follows -r and -c with cycle guard)
- `cli.py` argparse CLI; run(argv) is testable, main() is the console entry
- `__init__.py` public surface

See `docs/architecture.md` for the parsing and rules.

## Conventions

- Findings carry file, 1-based line, a stable code, a message, and the requirement text.
- Library functions take required keyword-only options; no default parameter values.
- `packaging` parses the PEP 508 specifier; `--hash` is split off separately since it is a
  pip extension, not part of PEP 508.
- Schedules of behavior past edges: includes are followed only by lint_file; unreadable
  files yield an `io-error` finding rather than raising.

## Testing rules

- Golden requirements snippets for each rule (unpinned, missing-hash, unpinnable, parse-error).
- File-level tests for includes, cycles, and missing files.
- CLI tests for exit codes and flag behavior.
- Bug fixes start with a failing test.

## Release

- Semantic versioning; update `CHANGELOG.md` and `__version__`.
- Gates: `uv run pytest && uv run ruff check . && uv run mypy src && uv build && uv run twine check dist/*`.
- Publish to PyPI, tag `vX.Y.Z`, GitHub release.

## Style

- No em dash characters in docs, comments, or commit messages.
- Comments explain non-obvious reasoning only.
