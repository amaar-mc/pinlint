from pinlint import lint_text


def lint(text: str, *, require_hashes: bool = True, allow_unpinned: bool = False) -> list[str]:
    return [
        f.code
        for f in lint_text(
            text, source="req.txt", require_hashes=require_hashes, allow_unpinned=allow_unpinned
        )
    ]


def test_fully_pinned_and_hashed_passes() -> None:
    assert lint("flask==2.0.1 --hash=sha256:abc123\n") == []


def test_unpinned_range() -> None:
    findings = lint_text(
        "flask>=2.0 --hash=sha256:abc\n", source="r", require_hashes=True, allow_unpinned=False
    )
    assert [f.code for f in findings] == ["unpinned"]
    assert findings[0].line == 1


def test_missing_hash() -> None:
    assert lint("flask==2.0.1\n") == ["missing-hash"]


def test_no_version_is_unpinned_and_unhashed() -> None:
    assert set(lint("flask\n")) == {"unpinned", "missing-hash"}


def test_wildcard_is_not_exact() -> None:
    assert "unpinned" in lint("flask==2.* --hash=sha256:abc\n")


def test_editable_is_unpinnable() -> None:
    assert lint("-e .\n") == ["unpinnable"]


def test_url_and_vcs_are_unpinnable() -> None:
    assert lint("git+https://github.com/x/y.git\n") == ["unpinnable"]
    assert lint("https://example.com/pkg-1.0-py3-none-any.whl\n") == ["unpinnable"]


def test_comments_and_blank_lines_ignored() -> None:
    assert lint("# header\n\nflask==1.0 --hash=sha256:a  # inline note\n") == []


def test_line_continuation_joins_hashes() -> None:
    text = "flask==2.0.1 \\\n    --hash=sha256:aaa \\\n    --hash=sha256:bbb\n"
    assert lint(text) == []


def test_line_number_is_logical_start() -> None:
    findings = lint_text(
        "ok==1 --hash=sha256:a\nbad>=2 --hash=sha256:b\n",
        source="r",
        require_hashes=True,
        allow_unpinned=False,
    )
    assert findings[0].line == 2


def test_marker_with_pin_and_hash_passes() -> None:
    assert lint('flask==2.0.1 ; python_version >= "3.8" --hash=sha256:abc\n') == []


def test_global_option_lines_ignored() -> None:
    assert (
        lint("--index-url https://pypi.org/simple\n-i https://x\nflask==1.0 --hash=sha256:a\n")
        == []
    )


def test_relaxed_flags() -> None:
    assert lint("flask>=2.0\n", require_hashes=False, allow_unpinned=True) == []


def test_parse_error() -> None:
    assert lint("==1.0 --hash=sha256:a\n") == ["parse-error"]


def test_findings_carry_package_name() -> None:
    findings = lint_text("flask>=2.0\n", source="r", require_hashes=True, allow_unpinned=False)
    assert findings
    assert all(f.name == "flask" for f in findings)
