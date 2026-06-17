from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LogicalLine:
    """A requirements line after comment stripping and backslash continuation joining."""

    number: int  # 1-based line number where the logical line starts
    text: str


def _strip_comment(physical: str) -> str:
    """Remove a trailing comment. A comment begins at a '#' that is at the start of the
    line or preceded by whitespace, matching how pip reads requirements files."""
    for i, ch in enumerate(physical):
        if ch == "#" and (i == 0 or physical[i - 1].isspace()):
            return physical[:i]
    return physical


def logical_lines(text: str) -> Iterator[LogicalLine]:
    """Yield the non-empty logical lines of a requirements file, joining lines that end
    with a backslash and dropping comments and blank lines."""
    physical = text.splitlines()
    n = len(physical)
    i = 0
    while i < n:
        start = i + 1
        buf = _strip_comment(physical[i]).rstrip()
        while buf.endswith("\\"):
            buf = buf[:-1].rstrip()
            i += 1
            if i >= n:
                break
            buf = (buf + " " + _strip_comment(physical[i]).strip()).rstrip()
        i += 1
        line = buf.strip()
        if line:
            yield LogicalLine(number=start, text=line)
