"""Lint a requirements snippet with the library API.

Run with: python examples/check.py
"""

from pinlint import lint_text

requirements = """\
flask==2.0.1 --hash=sha256:aaaa
requests>=2.0 --hash=sha256:bbbb
click==8.1.3
-e .
"""

findings = lint_text(requirements, source="example.txt", require_hashes=True, allow_unpinned=False)
for finding in findings:
    print(f"line {finding.line}: {finding.code}: {finding.message}")
print(f"\n{len(findings)} issue(s)")
