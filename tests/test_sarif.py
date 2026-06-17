import json
from pathlib import Path

import pytest

from pinlint import Finding, __version__, to_sarif
from pinlint.cli import run


def test_document_shape() -> None:
    doc = to_sarif([], tool_version="9.9.9")
    assert doc["version"] == "2.1.0"
    assert doc["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    runs = doc["runs"]
    assert isinstance(runs, list) and len(runs) == 1
    driver = runs[0]["tool"]["driver"]
    assert driver["name"] == "pinlint"
    assert driver["version"] == "9.9.9"
    assert driver["informationUri"] == "https://github.com/amaar-mc/pinlint"
    assert [rule["id"] for rule in driver["rules"]] == [
        "unpinned",
        "missing-hash",
        "unpinnable",
        "parse-error",
        "io-error",
    ]
    assert runs[0]["results"] == []


def test_result_maps_finding_fields() -> None:
    finding = Finding(
        "requirements.txt", 3, "unpinned", "flask is not pinned", "flask>=1.0", "flask"
    )
    [result] = to_sarif([finding], tool_version="0.3.0")["runs"][0]["results"]
    assert result["ruleId"] == "unpinned"
    assert result["ruleIndex"] == 0
    assert result["level"] == "error"
    assert result["message"]["text"] == "flask is not pinned"
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "requirements.txt"
    assert location["region"] == {"startLine": 3}
    assert result["properties"] == {"requirement": "flask>=1.0"}


def test_unpinnable_is_warning() -> None:
    finding = Finding("r.txt", 2, "unpinnable", "URL install cannot be pinned", "x @ http://e")
    [result] = to_sarif([finding], tool_version="0.3.0")["runs"][0]["results"]
    assert result["level"] == "warning"
    assert result["ruleIndex"] == 2


def test_io_error_omits_region() -> None:
    # The io-error finding carries line 0, which is not a valid 1-based SARIF region.
    finding = Finding("missing.txt", 0, "io-error", "cannot read file", "")
    [result] = to_sarif([finding], tool_version="0.3.0")["runs"][0]["results"]
    location = result["locations"][0]["physicalLocation"]
    assert "region" not in location
    assert "properties" not in result


def test_cli_sarif_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "r.txt"
    path.write_text("flask>=1.0\n")
    assert run([str(path), "--format", "sarif"]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["version"] == __version__
    codes = {result["ruleId"] for result in doc["runs"][0]["results"]}
    assert codes == {"unpinned", "missing-hash"}
