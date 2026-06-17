from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One problem found while linting a requirements file."""

    file: str
    line: int
    code: str
    message: str
    requirement: str
    # Distribution name when the requirement parsed, else "" (for example a URL install).
    name: str = ""
