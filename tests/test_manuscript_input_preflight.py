import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/check_manuscript_inputs.py")


def test_manuscript_input_preflight_reports_missing_required(tmp_path: Path) -> None:
    missing_required = tmp_path / "missing_cases.jsonl"
    missing_optional = tmp_path / "missing_overrides.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--required",
            f"case_manifest_jsonl:{missing_required}",
            "--optional",
            f"adjudication_overrides_jsonl:{missing_optional}",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["missing_required"] == [
        {"role": "case_manifest_jsonl", "path": str(missing_required)}
    ]
    assert payload["missing_optional"] == [
        {"role": "adjudication_overrides_jsonl", "path": str(missing_optional)}
    ]
    assert payload["invalid_required"] == []


def test_manuscript_input_preflight_accepts_present_inputs(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    overrides = tmp_path / "overrides.jsonl"
    report = tmp_path / "report.json"
    cases.write_text('{"case_id":"case-1"}\n')
    overrides.write_text('{"case_id":"case-1"}\n')

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--required",
            f"case_manifest_jsonl:{cases}",
            "--optional",
            f"adjudication_overrides_jsonl:{overrides}",
            "--out",
            str(report),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["missing_required"] == []
    assert payload["missing_optional"] == []
    assert payload["invalid_required"] == []
    assert json.loads(report.read_text()) == payload


def test_manuscript_input_preflight_rejects_non_redacted_import_report(
    tmp_path: Path,
) -> None:
    import_report = tmp_path / "scorer_import.json"
    import_report.write_text('{"artifact_kind":"test","valid":true,"issues":[]}\n')

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--required",
            f"scorer_import_report:{import_report}",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["invalid_required"] == [
        {
            "role": "scorer_import_report",
            "path": str(import_report),
            "reason": "non_redacted_import_report",
        }
    ]


def test_manuscript_input_preflight_accepts_redacted_import_report(
    tmp_path: Path,
) -> None:
    import_report = tmp_path / "scorer_import.json"
    import_report.write_text(
        '{"artifact_kind":"test","valid":true,"redacted_input":true,"issues":[]}\n'
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--required",
            f"scorer_import_report:{import_report}",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["invalid_required"] == []
