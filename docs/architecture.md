# Architecture

`pinlint` is a small pipeline: parse a requirements file into logical lines, classify each
line, and emit findings.

## Parsing

`parse.logical_lines` turns the raw text into logical lines. It strips comments (a `#` at
the start of a line or preceded by whitespace, matching pip), joins physical lines that end
with a backslash, and drops blank lines. Each logical line keeps the 1-based number of the
physical line where it started, so findings point at the right place.

## Classification and rules

`lint.lint_text` walks the logical lines. The first token decides the kind of line:

- `-r`, `--requirement`, `-c`, `--constraint`: an include. Not flagged; followed by
  `lint_file`.
- `-e`, `--editable`: an editable install, reported as `unpinnable`.
- any other token starting with `-`: a global option (such as `--index-url`), ignored.
- otherwise: a requirement.

For a requirement, `_split_hashes` separates the `--hash` options from the specifier, since
hashes are a pip extension and not part of PEP 508. A specifier containing `://` or a VCS
prefix is reported as `unpinnable`. Otherwise the specifier is parsed with
`packaging.requirements.Requirement`. A requirement with a URL is `unpinnable`. A specifier
that is not exactly one `==` or `===` clause (and not a `*` wildcard) is `unpinned`. A
requirement with no `--hash`, when hashes are required, is `missing-hash`. A specifier that
fails to parse is a `parse-error`.

## Files and includes

`lint_file` reads a file and lints it, then, when following includes is enabled, resolves
each `-r` and `-c` target relative to the including file and lints it too. A set of resolved
paths guards against include cycles. An unreadable file yields an `io-error` finding rather
than raising.

## Why packaging

Version specifiers, extras, and environment markers are defined by PEP 508, which is
intricate. `packaging` is the canonical parser (pip vendors it), so pinlint uses it rather
than re-implementing the grammar. The pip-specific `--hash` option, which PEP 508 does not
cover, is the one piece parsed by hand.
