from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One problem found while linting a requirements file."""

    file: str
    line: int
    code: str
    message: str
    requirement: str
