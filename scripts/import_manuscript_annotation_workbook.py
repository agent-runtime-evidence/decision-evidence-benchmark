"""Import reviewed manuscript annotation workbook rows into annotation JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    PROPERTY_CATEGORIES,
    CaseManifest,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_WORKBOOK = ROOT / "data/results/manuscript_annotation_workbook.reviewed.csv"
DEFAULT_OUT = ROOT / "data/annotations/manuscript_annotations.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_annotation_import.json"

ACCEPTED_ANNOTATION_STATUS = "annotated"
ANNOTATION_CATEGORY_PLACEHOLDER = "__SELECT_CATEGORY__"
ANNOTATION_SOURCE = "manuscript_two_annotator_annotation"


def read_workbook(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row must be a JSON object")
            rows.append(value)
    return rows


def import_rows(
    *,
    cases: list[CaseManifest],
    workbook_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_by_id = {case.case_id: case for case in cases}
    rows_by_annotation: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_keys: set[tuple[str, str, str]] = set()

    annotators = sorted(
        {
            str(row.get("annotator_id", "")).strip()
            for row in workbook_rows
            if str(row.get("annotator_id", "")).strip()
        }
    )
    if len(annotators) != 2:
        issues.append(
            {
                "severity": "error",
                "issue": "expected_exactly_two_annotators",
                "annotators": annotators,
            }
        )

    for row_index, row in enumerate(workbook_rows, start=1):
        row_issues = _row_issues(row, case_by_id=case_by_id, row_index=row_index)
        issues.extend(row_issues)
        case_id = str(row.get("case_id", "")).strip()
        annotator_id = str(row.get("annotator_id", "")).strip()
        property_name = str(row.get("property", "")).strip()
        key = (case_id, annotator_id, property_name)
        if key in seen_keys:
            issues.append(
                {
                    "severity": "error",
                    "issue": "duplicate_annotation_property_row",
                    "row_index": row_index,
                    "case_id": case_id,
                    "annotator_id": annotator_id,
                    "property": property_name,
                }
            )
        seen_keys.add(key)
        if (
            case_id in case_by_id
            and not _placeholder(annotator_id)
            and property_name in DECISION_EVENT_PROPERTIES
        ):
            rows_by_annotation[(case_id, annotator_id)].append(row)

    expected_rows = len(cases) * len(DECISION_EVENT_PROPERTIES) * 2
    if len(workbook_rows) != expected_rows:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_workbook_row_count",
                "expected": expected_rows,
                "actual": len(workbook_rows),
            }
        )

    for case in cases:
        for annotator_id in annotators:
            property_names = {
                str(row.get("property", "")).strip()
                for row in rows_by_annotation.get((case.case_id, annotator_id), [])
            }
            missing = sorted(set(DECISION_EVENT_PROPERTIES) - property_names)
            if missing:
                issues.append(
                    {
                        "severity": "error",
                        "issue": "missing_annotation_properties",
                        "case_id": case.case_id,
                        "annotator_id": annotator_id,
                        "properties": missing,
                    }
                )

    annotations: list[dict[str, Any]] = []
    if not any(issue["severity"] == "error" for issue in issues):
        annotations = [
            _annotation_record(case, annotator_id, rows_by_annotation[(case.case_id, annotator_id)])
            for case in cases
            for annotator_id in annotators
        ]

    report = {
        "artifact_kind": "decision_evidence_manuscript_annotation_import",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "case_count": len(cases),
        "annotators": annotators,
        "property_count": len(DECISION_EVENT_PROPERTIES),
        "workbook_row_count": len(workbook_rows),
        "expected_workbook_row_count": expected_rows,
        "annotation_record_count": len(annotations),
        "category_counts": dict(
            sorted(Counter(str(row.get("category", "")) for row in workbook_rows).items())
        ),
        "status_counts": dict(
            sorted(Counter(str(row.get("annotation_status", "")) for row in workbook_rows).items())
        ),
        "issues": issues,
        "result_honesty": (
            "The importer writes annotation records only after every workbook row is "
            "explicitly annotated. It does not adjudicate labels or create results."
        ),
    }
    return annotations, report


def _row_issues(
    row: dict[str, Any],
    *,
    case_by_id: dict[str, CaseManifest],
    row_index: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", "")).strip()
    annotator_id = str(row.get("annotator_id", "")).strip()
    property_name = str(row.get("property", "")).strip()

    case = case_by_id.get(case_id)
    if not case:
        issues.append(
            {
                "severity": "error",
                "issue": "unknown_case_id",
                "row_index": row_index,
                "case_id": case_id,
            }
        )
    else:
        for field in ("regime", "degradation_condition", "question_family"):
            value = str(row.get(field, "")).strip()
            expected = str(getattr(case, field))
            if value and value != expected:
                issues.append(
                    {
                        "severity": "error",
                        "issue": "taxonomy_mismatch",
                        "row_index": row_index,
                        "case_id": case_id,
                        "field": field,
                        "expected": expected,
                        "actual": value,
                    }
                )

    if _placeholder(annotator_id):
        issues.append(
            {
                "severity": "error",
                "issue": "missing_annotator_id",
                "row_index": row_index,
                "case_id": case_id,
            }
        )
    if property_name not in DECISION_EVENT_PROPERTIES:
        issues.append(
            {
                "severity": "error",
                "issue": "unknown_property",
                "row_index": row_index,
                "case_id": case_id,
                "property": property_name,
            }
        )
    status = str(row.get("annotation_status", "")).strip()
    if status != ACCEPTED_ANNOTATION_STATUS:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_annotation_status",
                "row_index": row_index,
                "case_id": case_id,
                "expected": ACCEPTED_ANNOTATION_STATUS,
                "actual": status,
            }
        )
    category = str(row.get("category", "")).strip()
    if category == ANNOTATION_CATEGORY_PLACEHOLDER or category not in PROPERTY_CATEGORIES:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_property_category",
                "row_index": row_index,
                "case_id": case_id,
                "property": property_name,
                "actual": category,
                "expected": sorted(PROPERTY_CATEGORIES),
            }
        )
    try:
        _parse_bool(row.get("required", True))
    except ValueError:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_required_flag",
                "row_index": row_index,
                "case_id": case_id,
                "actual": row.get("required"),
            }
        )
    return issues


def _annotation_record(
    case: CaseManifest,
    annotator_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows_by_property = {str(row["property"]): row for row in rows}
    return {
        "case_id": case.case_id,
        "annotator_id": annotator_id,
        "property_labels": [
            {
                "property": property_name,
                "category": str(rows_by_property[property_name]["category"]).strip(),
                "required": _parse_bool(rows_by_property[property_name].get("required", True)),
                "source": ANNOTATION_SOURCE,
                "notes": str(rows_by_property[property_name].get("notes", "")).strip(),
            }
            for property_name in DECISION_EVENT_PROPERTIES
        ],
        "metadata": {
            "annotation_status": "manuscript_two_annotator_candidate",
            "annotation_source": "manuscript_annotation_workbook_import",
            "case_source_status": case.metadata.get("case_source_status"),
            "result_honesty": (
                "Two-annotator manuscript annotation record only. Result claims require "
                "adjudication, scorer outputs, baseline outputs, and package validation."
            ),
        },
    }


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"expected true/false, got {value!r}")


def _placeholder(value: str) -> bool:
    stripped = value.strip()
    return not stripped or stripped.startswith("__") or stripped.endswith("__")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def console_summary(report: dict[str, Any], *, report_path: Path) -> dict[str, Any]:
    issues = [issue for issue in report.get("issues", []) if isinstance(issue, dict)]
    return {
        "artifact_kind": report["artifact_kind"],
        "valid": report["valid"],
        "case_count": report["case_count"],
        "workbook_row_count": report["workbook_row_count"],
        "annotation_record_count": report["annotation_record_count"],
        "status_counts": report["status_counts"],
        "category_counts": report["category_counts"],
        "issue_count": len(issues),
        "issue_counts": dict(
            sorted(Counter(str(issue.get("issue", "")) for issue in issues).items())
        ),
        "report": str(report_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    annotations, report = import_rows(
        cases=read_cases_jsonl(Path(args.cases)),
        workbook_rows=read_workbook(Path(args.workbook)),
    )
    write_json(Path(args.report), report)
    if report["valid"]:
        write_jsonl(Path(args.out), annotations)
    print(
        json.dumps(
            console_summary(report, report_path=Path(args.report)),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
