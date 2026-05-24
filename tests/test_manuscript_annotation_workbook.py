import csv
import json
import subprocess
import sys
from pathlib import Path

from decision_evidence_benchmark.io import write_cases_jsonl
from decision_evidence_benchmark.labels import (
    adjudicate_cases,
    calibration_summary,
    read_annotations_jsonl,
)
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

EXPORT_SCRIPT = Path("scripts/export_manuscript_annotation_workbook.py")
IMPORT_SCRIPT = Path("scripts/import_manuscript_annotation_workbook.py")


def test_export_manuscript_annotation_workbook_writes_two_annotator_grid(
    tmp_path: Path,
) -> None:
    cases = tmp_path / "cases.jsonl"
    csv_out = tmp_path / "annotation_workbook.csv"
    jsonl_out = tmp_path / "annotation_workbook.jsonl"
    write_cases_jsonl(cases, [_case()])

    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--cases",
            str(cases),
            "--csv-out",
            str(csv_out),
            "--jsonl-out",
            str(jsonl_out),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    csv_rows = list(csv.DictReader(csv_out.open()))
    jsonl_rows = [json.loads(line) for line in jsonl_out.read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == len(DECISION_EVENT_PROPERTIES) * 2
    assert len(jsonl_rows) == len(csv_rows)
    assert csv_rows[0]["annotation_status"] == "todo"
    assert csv_rows[0]["category"] == "__SELECT_CATEGORY__"
    assert {row["annotator_id"] for row in csv_rows} == {
        "manuscript_annotator_a",
        "manuscript_annotator_b",
    }


def test_import_manuscript_annotation_workbook_rejects_placeholders(
    tmp_path: Path,
) -> None:
    paths = _exported_workbook(tmp_path)

    result = _run_import(paths)

    payload = json.loads(paths["report"].read_text())
    issue_codes = {issue["issue"] for issue in payload["issues"]}
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not paths["annotations"].exists()
    assert issue_codes >= {"invalid_annotation_status", "invalid_property_category"}


def test_import_manuscript_annotation_workbook_writes_calibratable_annotations(
    tmp_path: Path,
) -> None:
    paths = _exported_workbook(tmp_path)
    _write_reviewed_workbook(paths["workbook"])

    result = _run_import(paths)

    payload = json.loads(paths["report"].read_text())
    annotations = read_annotations_jsonl(paths["annotations"])
    cases = [_case()]
    calibration = calibration_summary(cases, annotations)
    adjudicated_cases, adjudication = adjudicate_cases(cases, annotations)
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["annotation_record_count"] == 2
    assert len(annotations) == 2
    assert annotations[0].property_labels[0].source == "manuscript_two_annotator_annotation"
    assert calibration["valid"] is True
    assert calibration["paired_label_count"] == len(DECISION_EVENT_PROPERTIES)
    assert adjudication["valid"] is True
    assert adjudicated_cases[0].metadata["label_status"] == "adjudicated"


def _case() -> CaseManifest:
    return CaseManifest(
        case_id="manuscript-aer-complete-actor_identity-001",
        regime="aer",
        degradation_condition="complete",
        question_family="actor_identity",
        evidence={
            "native_evidence_refs": ["data/sources/native.jsonl#case_id=case"],
            "reviewed_source_refs": ["data/sources/review.jsonl#case_id=case"],
            "evidence_plane_refs": ["data/sources/plane.jsonl#case_id=case"],
            "provenance_notes": "reviewed source row",
        },
        container_flags={
            "trace_present": True,
            "ledger_present": True,
            "schema_valid": True,
            "checklist_complete": True,
            "source_validator_passed": True,
            "llm_judge_verdict": "sufficient",
        },
        property_labels=(),
        metadata={"case_source_status": "reviewed_non_fixture_evidence"},
    )


def _exported_workbook(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "cases": tmp_path / "cases.jsonl",
        "workbook": tmp_path / "annotation_workbook.csv",
        "jsonl": tmp_path / "annotation_workbook.jsonl",
        "annotations": tmp_path / "annotations.jsonl",
        "report": tmp_path / "report.json",
    }
    write_cases_jsonl(paths["cases"], [_case()])
    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return paths


def _run_import(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--workbook",
            str(paths["workbook"]),
            "--out",
            str(paths["annotations"]),
            "--report",
            str(paths["report"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _write_reviewed_workbook(path: Path) -> None:
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        row["annotation_status"] = "annotated"
        row["category"] = "complete"
        row["notes"] = "independent annotation pass"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
