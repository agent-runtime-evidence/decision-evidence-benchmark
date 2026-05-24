import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.write_manuscript_case_source_template import template_rows

IMPORT_SCRIPT = Path("scripts/import_manuscript_evidence_workqueue.py")
CONVERT_SCRIPT = Path("scripts/convert_manuscript_case_sources.py")


def test_import_workqueue_rejects_unreviewed_placeholder_rows(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    workqueue = tmp_path / "workqueue.csv"
    out = tmp_path / "reviewed.jsonl"
    report = tmp_path / "report.json"
    row = template_rows()[0]
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_workqueue(workqueue, [_workqueue_row(row)])

    result = _run_import(template, workqueue, out, report)

    payload = json.loads(report.read_text())
    issue_codes = {issue["issue"] for issue in payload["issues"]}
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not out.exists()
    assert issue_codes >= {
        "invalid_review_status",
        "missing_source_refs",
        "missing_review_field",
        "invalid_container_flag",
        "invalid_llm_judge_verdict",
    }


def test_import_workqueue_rejects_taxonomy_mismatch(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    workqueue = tmp_path / "workqueue.csv"
    out = tmp_path / "reviewed.jsonl"
    report = tmp_path / "report.json"
    row = template_rows()[0]
    reviewed_row = _reviewed_workqueue_row(row)
    reviewed_row["regime"] = "wrong_regime"
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_workqueue(workqueue, [reviewed_row])

    result = _run_import(template, workqueue, out, report)

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not out.exists()
    assert any(issue["issue"] == "taxonomy_mismatch" for issue in payload["issues"])


def test_import_workqueue_writes_reviewed_case_source_rows(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    workqueue = tmp_path / "workqueue.csv"
    out = tmp_path / "reviewed.jsonl"
    report = tmp_path / "report.json"
    row = template_rows()[0]
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_workqueue(workqueue, [_reviewed_workqueue_row(row)])

    result = _run_import(template, workqueue, out, report)

    payload = json.loads(report.read_text())
    reviewed_row = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["output_row_count"] == 1
    assert reviewed_row["template_status"] == "reviewed_non_fixture_evidence"
    assert reviewed_row["source_requirements"]["native_evidence_refs"] == [
        "native:one",
        "native:two",
    ]
    assert reviewed_row["container_flags"]["trace_present"] is True
    assert reviewed_row["container_flags"]["ledger_present"] is False
    assert reviewed_row["metadata"]["reviewer_id"] == "reviewer_1"


def test_imported_reviewed_rows_can_be_converted_to_unadjudicated_cases(
    tmp_path: Path,
) -> None:
    template = tmp_path / "template.jsonl"
    workqueue = tmp_path / "workqueue.csv"
    reviewed = tmp_path / "reviewed.jsonl"
    import_report = tmp_path / "import_report.json"
    cases = tmp_path / "cases.jsonl"
    convert_report = tmp_path / "convert_report.json"
    row = template_rows()[0]
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_workqueue(workqueue, [_reviewed_workqueue_row(row)])
    import_result = _run_import(template, workqueue, reviewed, import_report)

    convert_result = subprocess.run(
        [
            sys.executable,
            str(CONVERT_SCRIPT),
            "--sources",
            str(reviewed),
            "--out",
            str(cases),
            "--report",
            str(convert_report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    case = json.loads(cases.read_text())
    payload = json.loads(convert_report.read_text())
    assert import_result.returncode == 0
    assert convert_result.returncode == 0
    assert payload["valid"] is True
    assert case["case_id"] == row["case_id"]
    assert case["evidence"]["evidence_plane"] == "reviewed_non_fixture"
    assert case["property_labels"] == []


def _run_import(
    template: Path,
    workqueue: Path,
    out: Path,
    report: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--template",
            str(template),
            "--workqueue",
            str(workqueue),
            "--out",
            str(out),
            "--report",
            str(report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _write_workqueue(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _workqueue_row(template_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": template_row["case_id"],
        "regime": template_row["regime"],
        "degradation_condition": template_row["degradation_condition"],
        "question_family": template_row["question_family"],
        "review_status": "todo",
        "native_evidence_refs": "",
        "reviewed_source_refs": "",
        "evidence_plane_refs": "",
        "provenance_notes": "",
        "trace_present": "__SET_BOOL__",
        "ledger_present": "__SET_BOOL__",
        "schema_valid": "__SET_BOOL__",
        "checklist_complete": "__SET_BOOL__",
        "source_validator_passed": "__SET_BOOL__",
        "llm_judge_verdict": "__SET_VERDICT__",
        "reviewer_id": "",
        "reviewed_at": "",
        "authoring_notes": "",
    }


def _reviewed_workqueue_row(template_row: dict[str, Any]) -> dict[str, Any]:
    row = _workqueue_row(template_row)
    row.update(
        {
            "review_status": "source_reviewed_needs_annotation",
            "native_evidence_refs": "native:one | native:two",
            "reviewed_source_refs": "review:one",
            "evidence_plane_refs": "plane:one",
            "provenance_notes": "Reviewed source evidence chain.",
            "trace_present": "true",
            "ledger_present": "false",
            "schema_valid": "true",
            "checklist_complete": "true",
            "source_validator_passed": "true",
            "llm_judge_verdict": "sufficient",
            "reviewer_id": "reviewer_1",
            "reviewed_at": "2026-05-25T00:00:00Z",
            "authoring_notes": "Ready for annotation.",
        }
    )
    return row
