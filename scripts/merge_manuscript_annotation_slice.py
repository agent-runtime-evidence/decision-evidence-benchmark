"""Validate and merge a reviewed manuscript annotation slice."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from export_manuscript_annotation_workbook import CSV_COLUMNS as WORKBOOK_COLUMNS
from import_manuscript_annotation_workbook import _row_issues

from decision_evidence_benchmark.io import read_cases_jsonl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_EXPECTED_SLICE = ROOT / "data/results/manuscript_annotation_slice.csv"
DEFAULT_REVIEWED_SLICE = ROOT / "data/results/manuscript_annotation_slice.reviewed.csv"
DEFAULT_BASE_WORKBOOK = ROOT / "data/results/manuscript_annotation_workbook.csv"
DEFAULT_MERGED_WORKBOOK = (
    ROOT / "data/results/manuscript_annotation_workbook.merged_from_slice.csv"
)
DEFAULT_REPORT = ROOT / "data/results/manuscript_annotation_slice_validation.json"

CONTEXT_FIELDS = (
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "property",
    "annotator_id",
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
    "provenance_notes",
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
    "llm_judge_verdict",
)

RESULT_HONESTY = (
    "The annotation slice validator checks only the reviewed slice rows. The "
    "merge output is a full workbook authoring aid; it does not import labels, "
    "adjudicate labels, or create manuscript results."
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_slice(
    *,
    case_rows: list[Any],
    expected_slice_rows: list[dict[str, str]],
    reviewed_slice_rows: list[dict[str, str]],
    base_workbook_rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    case_by_id = {case.case_id: case for case in case_rows}
    expected_keys = [_row_key(row) for row in expected_slice_rows]
    reviewed_keys = [_row_key(row) for row in reviewed_slice_rows]

    issues.extend(_key_issues(expected_keys, reviewed_keys))
    expected_by_key = {_row_key(row): row for row in expected_slice_rows}
    for row_index, row in enumerate(reviewed_slice_rows, start=1):
        key = _row_key(row)
        expected_row = expected_by_key.get(key)
        if expected_row:
            issues.extend(
                _context_mismatch_issues(
                    row=row,
                    expected_row=expected_row,
                    row_index=row_index,
                )
            )
        for issue in _row_issues(row, case_by_id=case_by_id, row_index=row_index):
            issues.append({**issue, "slice_row_index": row_index})

    if base_workbook_rows is not None:
        issues.extend(
            _base_workbook_issues(
                case_rows=case_rows,
                base_workbook_rows=base_workbook_rows,
                reviewed_keys=reviewed_keys,
            )
        )

    issue_counts = Counter(str(issue["issue"]) for issue in issues)
    return {
        "artifact_kind": "decision_evidence_manuscript_annotation_slice_validation",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "case_count": len(case_rows),
        "expected_slice_row_count": len(expected_slice_rows),
        "reviewed_slice_row_count": len(reviewed_slice_rows),
        "base_workbook_row_count": (
            len(base_workbook_rows) if base_workbook_rows is not None else None
        ),
        "selected_annotation_keys": [_format_key(key) for key in expected_keys],
        "reviewed_annotation_keys": [_format_key(key) for key in reviewed_keys],
        "annotation_status_counts": dict(
            sorted(
                Counter(
                    str(row.get("annotation_status", "")) for row in reviewed_slice_rows
                ).items()
            )
        ),
        "category_counts": dict(
            sorted(Counter(str(row.get("category", "")) for row in reviewed_slice_rows).items())
        ),
        "issue_counts": dict(sorted(issue_counts.items())),
        "issues": issues,
        "merge_written": False,
        "result_honesty": RESULT_HONESTY,
    }


def merge_slice_into_workbook(
    *,
    base_workbook_rows: list[dict[str, str]],
    reviewed_slice_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    reviewed_by_key = {_row_key(row): row for row in reviewed_slice_rows}
    merged_rows: list[dict[str, str]] = []
    for row in base_workbook_rows:
        key = _row_key(row)
        merged = _workbook_row(row)
        if key not in reviewed_by_key:
            merged_rows.append(merged)
            continue
        reviewed_row = reviewed_by_key[key]
        for field in WORKBOOK_COLUMNS:
            if field == "row_index":
                continue
            if field in reviewed_row:
                merged[field] = str(reviewed_row.get(field, ""))
        merged_rows.append(merged)
    return merged_rows


def _key_issues(
    expected_keys: list[tuple[str, str, str]],
    reviewed_keys: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not expected_keys:
        issues.append({"severity": "error", "issue": "empty_expected_slice"})
    if not reviewed_keys:
        issues.append({"severity": "error", "issue": "empty_reviewed_slice"})

    expected_counts = Counter(expected_keys)
    reviewed_counts = Counter(reviewed_keys)
    duplicate_expected = sorted(key for key, count in expected_counts.items() if count > 1)
    duplicate_reviewed = sorted(key for key, count in reviewed_counts.items() if count > 1)
    if duplicate_expected:
        issues.append(
            {
                "severity": "error",
                "issue": "duplicate_expected_annotation_key",
                "keys": [_format_key(key) for key in duplicate_expected],
            }
        )
    if duplicate_reviewed:
        issues.append(
            {
                "severity": "error",
                "issue": "duplicate_reviewed_annotation_key",
                "keys": [_format_key(key) for key in duplicate_reviewed],
            }
        )

    missing = [key for key in expected_keys if key not in reviewed_counts]
    extra = [key for key in reviewed_keys if key not in expected_counts]
    if missing:
        issues.append(
            {
                "severity": "error",
                "issue": "missing_reviewed_annotation_key",
                "keys": [_format_key(key) for key in missing],
            }
        )
    if extra:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_reviewed_annotation_key",
                "keys": [_format_key(key) for key in extra],
            }
        )
    if expected_keys and reviewed_keys and expected_keys != reviewed_keys:
        issues.append(
            {
                "severity": "error",
                "issue": "annotation_slice_order_mismatch",
                "expected": [_format_key(key) for key in expected_keys],
                "actual": [_format_key(key) for key in reviewed_keys],
            }
        )
    return issues


def _context_mismatch_issues(
    *,
    row: dict[str, str],
    expected_row: dict[str, str],
    row_index: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field in CONTEXT_FIELDS:
        expected = str(expected_row.get(field, ""))
        actual = str(row.get(field, ""))
        if expected != actual:
            issues.append(
                {
                    "severity": "error",
                    "issue": "annotation_slice_context_mismatch",
                    "key": _format_key(_row_key(row)),
                    "slice_row_index": row_index,
                    "field": field,
                    "expected": expected,
                    "actual": actual,
                }
            )
    return issues


def _base_workbook_issues(
    *,
    case_rows: list[Any],
    base_workbook_rows: list[dict[str, str]],
    reviewed_keys: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    expected_row_count = len(case_rows) * 16
    base_keys = [_row_key(row) for row in base_workbook_rows]
    if len(base_workbook_rows) != expected_row_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_base_workbook_row_count",
                "expected": expected_row_count,
                "actual": len(base_workbook_rows),
            }
        )
    missing_reviewed_keys = [key for key in reviewed_keys if key not in set(base_keys)]
    if missing_reviewed_keys:
        issues.append(
            {
                "severity": "error",
                "issue": "reviewed_slice_key_not_in_base_workbook",
                "keys": [_format_key(key) for key in missing_reviewed_keys],
            }
        )
    duplicate_base = sorted(key for key, count in Counter(base_keys).items() if count > 1)
    if duplicate_base:
        issues.append(
            {
                "severity": "error",
                "issue": "duplicate_base_workbook_annotation_key",
                "keys": [_format_key(key) for key in duplicate_base],
            }
        )
    return issues


def _row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("case_id", "")),
        str(row.get("annotator_id", "")),
        str(row.get("property", "")),
    )


def _format_key(key: tuple[str, str, str]) -> str:
    case_id, annotator_id, property_name = key
    return f"{case_id}|{annotator_id}|{property_name}"


def _workbook_row(row: dict[str, Any]) -> dict[str, str]:
    return {field: str(row.get(field, "")) for field in WORKBOOK_COLUMNS}


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WORKBOOK_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--expected-slice", default=str(DEFAULT_EXPECTED_SLICE))
    parser.add_argument("--reviewed-slice", default=str(DEFAULT_REVIEWED_SLICE))
    parser.add_argument("--base-workbook", default=str(DEFAULT_BASE_WORKBOOK))
    parser.add_argument("--merged-workbook-out", default="")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    reviewed_slice = Path(args.reviewed_slice)
    if not reviewed_slice.exists():
        report = {
            "artifact_kind": "decision_evidence_manuscript_annotation_slice_validation",
            "valid": False,
            "issues": [
                {
                    "severity": "error",
                    "issue": "reviewed_slice_missing",
                    "path": str(reviewed_slice),
                }
            ],
            "issue_counts": {"reviewed_slice_missing": 1},
            "merge_written": False,
            "result_honesty": RESULT_HONESTY,
        }
        write_json(Path(args.report), report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    merged_workbook_out = str(args.merged_workbook_out).strip()
    base_workbook_rows = read_csv(Path(args.base_workbook)) if merged_workbook_out else None
    reviewed_slice_rows = read_csv(reviewed_slice)
    report = validate_slice(
        case_rows=read_cases_jsonl(Path(args.cases)),
        expected_slice_rows=read_csv(Path(args.expected_slice)),
        reviewed_slice_rows=reviewed_slice_rows,
        base_workbook_rows=base_workbook_rows,
    )

    if report["valid"] and merged_workbook_out:
        assert base_workbook_rows is not None
        merged_rows = merge_slice_into_workbook(
            base_workbook_rows=base_workbook_rows,
            reviewed_slice_rows=reviewed_slice_rows,
        )
        write_csv(Path(merged_workbook_out), merged_rows)
        report = {
            **report,
            "merge_written": True,
            "merged_workbook_out": merged_workbook_out,
            "merged_workbook_row_count": len(merged_rows),
        }
    elif merged_workbook_out:
        report = {**report, "merged_workbook_out": merged_workbook_out}

    write_json(Path(args.report), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
