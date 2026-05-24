import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

INIT_SCRIPT = Path("scripts/init_manuscript_evidence_source.py")
EXPORT_WORKBOOK_SCRIPT = Path("scripts/export_manuscript_source_review_workbook.py")
EXPORT_SLICE_SCRIPT = Path("scripts/export_manuscript_source_review_slice.py")
MERGE_SCRIPT = Path("scripts/merge_manuscript_source_review_slice.py")


def test_validate_source_review_slice_rejects_unfilled_slice(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path, row_count=3)
    expected_slice = tmp_path / "slice.csv"
    report = tmp_path / "report.json"
    _export_slice(source_root, expected_slice, tmp_path / "slice.json", slice_size=2)

    result = _run_merge(
        source_root=source_root,
        expected_slice=expected_slice,
        reviewed_slice=expected_slice,
        report=report,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["merge_written"] is False
    assert payload["issue_counts"]["invalid_review_status"] == 2
    assert payload["issue_counts"]["missing_source_refs"] == 6
    assert payload["issue_counts"]["missing_review_field"] == 6
    assert "slice validator checks only the reviewed slice rows" in payload["result_honesty"]


def test_merge_source_review_slice_writes_full_workbook_without_importing_source_root(
    tmp_path: Path,
) -> None:
    source_root = _initialized_source_root(tmp_path, row_count=3)
    expected_slice = tmp_path / "slice.csv"
    reviewed_slice = tmp_path / "slice.reviewed.csv"
    base_workbook = tmp_path / "workbook.csv"
    merged_workbook = tmp_path / "workbook.merged.csv"
    report = tmp_path / "report.json"
    _export_slice(source_root, expected_slice, tmp_path / "slice.json", slice_size=2)
    _export_workbook(source_root, base_workbook, tmp_path / "workbook.jsonl")
    rows = list(csv.DictReader(expected_slice.open()))
    for index, row in enumerate(rows, start=1):
        row.update(_reviewed_values(index))
    _write_csv(reviewed_slice, rows)

    result = _run_merge(
        source_root=source_root,
        expected_slice=expected_slice,
        reviewed_slice=reviewed_slice,
        report=report,
        base_workbook=base_workbook,
        merged_workbook=merged_workbook,
    )

    payload = json.loads(report.read_text())
    merged_rows = list(csv.DictReader(merged_workbook.open()))
    source_rows = [
        json.loads(line)
        for line in (source_root / "case_evidence_sources.jsonl").read_text().splitlines()
    ]
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["merge_written"] is True
    assert payload["reviewed_slice_row_count"] == 2
    assert len(merged_rows) == 3
    assert merged_rows[0]["review_status"] == "source_reviewed_needs_annotation"
    assert merged_rows[0]["native_evidence_refs"] == "native:1"
    assert merged_rows[1]["reviewer_id"] == "reviewer_2"
    assert merged_rows[2]["review_status"] == "todo"
    assert "packet_path" not in merged_rows[0]
    assert source_rows[0]["template_status"] == "requires_non_fixture_evidence"


def _initialized_source_root(tmp_path: Path, *, row_count: int) -> Path:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "source_root"
    rows = template_rows()[:row_count]
    template.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    result = subprocess.run(
        [
            sys.executable,
            str(INIT_SCRIPT),
            "--template",
            str(template),
            "--source-root",
            str(source_root),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return source_root


def _export_slice(
    source_root: Path,
    csv_out: Path,
    summary: Path,
    *,
    slice_size: int,
) -> None:
    packet_index = csv_out.parent / "packet_index.csv"
    _write_packet_index(packet_index, template_rows()[:3])
    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SLICE_SCRIPT),
            "--source-root",
            str(source_root),
            "--packet-index",
            str(packet_index),
            "--csv-out",
            str(csv_out),
            "--summary",
            str(summary),
            "--slice-size",
            str(slice_size),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0


def _export_workbook(source_root: Path, csv_out: Path, jsonl_out: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_WORKBOOK_SCRIPT),
            "--source-root",
            str(source_root),
            "--csv-out",
            str(csv_out),
            "--jsonl-out",
            str(jsonl_out),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0


def _run_merge(
    *,
    source_root: Path,
    expected_slice: Path,
    reviewed_slice: Path,
    report: Path,
    base_workbook: Path | None = None,
    merged_workbook: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(MERGE_SCRIPT),
        "--source-root",
        str(source_root),
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


def _write_packet_index(path: Path, source_rows: list[dict[str, object]]) -> None:
    rows = [
        {
            "row_index": str(index + 1),
            "case_id": str(row["case_id"]),
            "regime": str(row["regime"]),
            "degradation_condition": str(row["degradation_condition"]),
            "question_family": str(row["question_family"]),
            "packet_path": str(path.parent / f"packet_{index + 1}.md"),
            "template_status": "requires_non_fixture_evidence",
            "review_status": "todo",
            "missing_source_fields": "native_evidence_refs",
            "missing_container_flags": "trace_present",
            "missing_review_fields": "review_status",
            "required_candidate_ref_count": "2",
            "advisory_ref_count": "23",
            "candidate_ref_count": "25",
        }
        for index, row in enumerate(source_rows)
    ]
    _write_csv(path, rows)


def _reviewed_values(index: int) -> dict[str, str]:
    return {
        "review_status": "source_reviewed_needs_annotation",
        "native_evidence_refs": f"native:{index}",
        "reviewed_source_refs": f"review:{index}",
        "evidence_plane_refs": f"plane:{index}",
        "provenance_notes": f"Reviewed source chain {index}.",
        "trace_present": "true",
        "ledger_present": "false",
        "schema_valid": "true",
        "checklist_complete": "true",
        "source_validator_passed": "true",
        "llm_judge_verdict": "sufficient",
        "reviewer_id": f"reviewer_{index}",
        "reviewed_at": "2026-05-25T00:00:00Z",
        "authoring_notes": f"Reviewed slice row {index}.",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
