# Contributing to pinlint

Thanks for your interest. This project values correctness, clear diagnostics, and a small
dependency footprint.

## Development

```sh
uv venv
uv pip install -e ".[dev]"
uv run pytest -q
uv run ruff check .
uv run mypy src
```

A standard virtual environment with `pip install -e ".[dev]"` works the same way.

## Guidelines

- Keep the dependency footprint minimal. `packaging` is the canonical PEP 508 parser and
  is the only runtime dependency; new runtime dependencies need a strong reason.
- Every rule and parsing behavior needs a golden test with a sample requirements snippet.
- A bug fix starts with a failing test.
- Findings carry a file, a 1-based line number, a stable code, and a clear message.
- Run `uv run ruff format .` before committing.
- Commit messages follow `type(scope): description`.

## Adding a rule

Give it a short stable code, a clear message, and golden tests for both the passing and
failing cases. Document the code in the README.

## Reporting issues

Open an issue with the requirements snippet, the finding you expected, and what pinlint
reported.
