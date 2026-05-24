import csv
import json
import subprocess
import sys
from pathlib import Path

from decision_evidence_benchmark.io import write_cases_jsonl
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

EXPORT_WORKBOOK_SCRIPT = Path("scripts/export_manuscript_annotation_workbook.py")
EXPORT_SLICE_SCRIPT = Path("scripts/export_manuscript_annotation_slice.py")
MERGE_SCRIPT = Path("scripts/merge_manuscript_annotation_slice.py")


def test_export_annotation_slice_selects_full_grid_for_one_case_per_regime(
    tmp_path: Path,
) -> None:
    paths = _exported_workbook(tmp_path, case_count=3)
    slice_csv = tmp_path / "annotation_slice.csv"
    summary = tmp_path / "annotation_slice.json"

    result = _run_export_slice(paths["workbook"], slice_csv, summary, "--slice-size", "2")

    rows = list(csv.DictReader(slice_csv.open()))
    payload = json.loads(summary.read_text())
    assert result.returncode == 0
    assert len(rows) == len(DECISION_EVENT_PROPERTIES) * 2 * 2
    assert [case["case_id"] for case in payload["selected_cases"]] == [
        "case-aer-001",
        "case-mat-002",
    ]
    assert payload["slice_strategy"] == "one_per_regime"
    assert payload["selected_annotation_row_count"] == 32
    assert rows[0]["annotation_status"] == "todo"
    assert rows[0]["category"] == "__SELECT_CATEGORY__"
    assert rows[0]["slice_status"] == "annotation_slice_not_importable"


def test_export_annotation_slice_preserves_explicit_case_order(tmp_path: Path) -> None:
    paths = _exported_workbook(tmp_path, case_count=3)
    slice_csv = tmp_path / "annotation_slice.csv"
    summary = tmp_path / "annotation_slice.json"

    result = _run_export_slice(
        paths["workbook"],
        slice_csv,
        summary,
        "--case-id",
        "case-ieec-003",
        "--case-id",
        "case-aer-001",
    )

    rows = list(csv.DictReader(slice_csv.open()))
    payload = json.loads(summary.read_text())
    assert result.returncode == 0
    assert [case["case_id"] for case in payload["selected_cases"]] == [
        "case-ieec-003",
        "case-aer-001",
    ]
    assert _unique_case_ids(rows) == ["case-ieec-003", "case-aer-001"]
    assert payload["slice_strategy"] == "explicit_case_ids"


def test_validate_annotation_slice_rejects_unfilled_slice(tmp_path: Path) -> None:
    paths = _exported_workbook(tmp_path, case_count=2)
    slice_csv = tmp_path / "annotation_slice.csv"
    report = tmp_path / "annotation_slice_validation.json"
    _export_slice(paths["workbook"], slice_csv, tmp_path / "annotation_slice.json", slice_size=1)

    result = _run_merge(
        cases=paths["cases"],
        expected_slice=slice_csv,
        reviewed_slice=slice_csv,
        report=report,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["merge_written"] is False
    assert payload["issue_counts"]["invalid_annotation_status"] == 16
    assert payload["issue_counts"]["invalid_property_category"] == 16
    assert "checks only the reviewed slice rows" in payload["result_honesty"]


def test_merge_annotation_slice_writes_full_workbook_without_importing_annotations(
    tmp_path: Path,
) -> None:
    paths = _exported_workbook(tmp_path, case_count=2)
    slice_csv = tmp_path / "annotation_slice.csv"
    reviewed_slice = tmp_path / "annotation_slice.reviewed.csv"
    merged_workbook = tmp_path / "annotation_workbook.merged.csv"
    report = tmp_path / "annotation_slice_validation.json"
    _export_slice(paths["workbook"], slice_csv, tmp_path / "annotation_slice.json", slice_size=1)
    rows = list(csv.DictReader(slice_csv.open()))
    for row in rows:
        row.update(_reviewed_values())
    _write_csv(reviewed_slice, rows)

    result = _run_merge(
        cases=paths["cases"],
        expected_slice=slice_csv,
        reviewed_slice=reviewed_slice,
        report=report,
        base_workbook=paths["workbook"],
        merged_workbook=merged_workbook,
    )

    payload = json.loads(report.read_text())
    merged_rows = list(csv.DictReader(merged_workbook.open()))
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["merge_written"] is True
    assert payload["reviewed_slice_row_count"] == 16
    assert len(merged_rows) == 32
    assert all(row["annotation_status"] == "annotated" for row in merged_rows[:16])
    assert all(row["category"] == "complete" for row in merged_rows[:16])
    assert all(row["annotation_status"] == "todo" for row in merged_rows[16:])
    assert "slice_status" not in merged_rows[0]


def _exported_workbook(tmp_path: Path, *, case_count: int) -> dict[str, Path]:
    cases = tmp_path / "cases.jsonl"
    workbook = tmp_path / "annotation_workbook.csv"
    jsonl = tmp_path / "annotation_workbook.jsonl"
    write_cases_jsonl(cases, _cases()[:case_count])
    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_WORKBOOK_SCRIPT),
            "--cases",
            str(cases),
            "--csv-out",
            str(workbook),
            "--jsonl-out",
            str(jsonl),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return {"cases": cases, "workbook": workbook, "jsonl": jsonl}


def _run_export_slice(
    workbook: Path,
    csv_out: Path,
    summary: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXPORT_SLICE_SCRIPT),
            "--workbook",
            str(workbook),
            "--csv-out",
            str(csv_out),
            "--summary",
            str(summary),
            *extra_args,
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _export_slice(
    workbook: Path,
    csv_out: Path,
    summary: Path,
    *,
    slice_size: int,
) -> None:
    result = _run_export_slice(
        workbook,
        csv_out,
        summary,
        "--slice-size",
        str(slice_size),
    )
    assert result.returncode == 0


def _run_merge(
    *,
    cases: Path,
    expected_slice: Path,
    reviewed_slice: Path,
    report: Path,
    base_workbook: Path | None = None,
    merged_workbook: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(MERGE_SCRIPT),
        "--cases",
        str(cases),
        "--expected-slice",
        str(expected_slice),
        "--reviewed-slice",
        str(reviewed_slice),
        "--report",
        str(report),
    ]
    if base_workbook is not None:
        args.extend(["--base-workbook", str(base_workbook)])
    if merged_workbook is not None:
        args.extend(["--merged-workbook-out", str(merged_workbook)])
    return subprocess.run(args, capture_output=True, check=False, text=True)


def _cases() -> list[CaseManifest]:
    return [
        _case("case-aer-001", "aer", "actor_identity"),
        _case("case-mat-002", "mat", "principal_authority"),
        _case("case-ieec-003", "ieec", "action_boundary"),
    ]


def _case(case_id: str, regime: str, question_family: str) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        regime=regime,
        degradation_condition="complete",
        question_family=question_family,
        evidence={
            "native_evidence_refs": [f"data/sources/native.jsonl#case_id={case_id}"],
            "reviewed_source_refs": [f"data/sources/review.jsonl#case_id={case_id}"],
            "evidence_plane_refs": [f"data/sources/plane.jsonl#case_id={case_id}"],
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


def _reviewed_values() -> dict[str, str]:
    return {
        "annotation_status": "annotated",
        "category": "complete",
        "required": "true",
        "notes": "independent annotation slice pass",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _unique_case_ids(rows: list[dict[str, str]]) -> list[str]:
    case_ids: list[str] = []
    for row in rows:
        case_id = row["case_id"]
        if case_id not in case_ids:
            case_ids.append(case_id)
    return case_ids
