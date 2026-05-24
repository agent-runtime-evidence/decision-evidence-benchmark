"""Import reviewed manuscript candidate-scorer workbook rows into JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.manuscript_redaction import SCORER_INPUT_REDACTION_STATUS
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    PROPERTY_CATEGORIES,
    VERDICTS,
    CaseManifest,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_WORKBOOK = ROOT / "data/results/manuscript_scorer_workbook.reviewed.csv"
DEFAULT_OUT = ROOT / "data/scorers/decision_trace_reconstructor_outputs.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_scorer_import.json"
DEFAULT_SCORER = "decision_trace_reconstructor"
ACCEPTED_PREDICTION_STATUS = "reviewed"
PREDICTION_SOURCE = "manuscript_candidate_scorer_prediction"
DISALLOWED_IMPLEMENTATION_STATUSES = {
    "draft_synthetic_oracle",
    "fixture_placeholder",
    "smoke_only",
}

CASE_METADATA_FIELDS = (
    "verdict",
    "implementation_status",
    "run_id",
    "model",
    "prompt_version",
    "reviewer_id",
    "reviewed_at",
)
REQUIRED_METADATA_FIELDS = ("implementation_status", "run_id", "reviewer_id", "reviewed_at")


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


def read_case_id_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    rows = read_jsonl(path)
    mapping: dict[str, str] = {}
    for line_number, row in enumerate(rows, start=1):
        redacted_case_id = str(row.get("case_id", "")).strip()
        original_case_id = str(row.get("original_case_id", "")).strip()
        if not redacted_case_id or not original_case_id:
            raise ValueError(f"{path}:{line_number}: case_id and original_case_id are required")
        mapping[redacted_case_id] = original_case_id
    return mapping


def import_rows(
    *,
    cases: list[CaseManifest],
    workbook_rows: list[dict[str, Any]],
    scorer: str = DEFAULT_SCORER,
    case_id_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    input_to_original_case_id = case_id_map or {}
    redacted_input = bool(input_to_original_case_id)
    case_by_id = {case.case_id: case for case in cases}
    case_by_input_id, mapping_issues = _case_by_input_id(
        case_by_id=case_by_id,
        input_to_original_case_id=input_to_original_case_id,
    )
    issues.extend(mapping_issues)
    rows_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_keys: set[tuple[str, str]] = set()

    for row_index, row in enumerate(workbook_rows, start=1):
        issues.extend(
            _row_issues(
                row,
                case_by_id=case_by_input_id,
                row_index=row_index,
                scorer=scorer,
                redacted_input=redacted_input,
            )
        )
        input_case_id = str(row.get("case_id", "")).strip()
        original_case_id = input_to_original_case_id.get(input_case_id, input_case_id)
        property_name = str(row.get("property", "")).strip()
        key = (input_case_id, property_name)
        if key in seen_keys:
            issues.append(
                {
                    "severity": "error",
                    "issue": "duplicate_scorer_property_row",
                    "row_index": row_index,
                    "case_id": input_case_id,
                    "property": property_name,
                }
            )
        seen_keys.add(key)
        if input_case_id in case_by_input_id and property_name in DECISION_EVENT_PROPERTIES:
            rows_by_case[original_case_id].append(row)

    expected_rows = len(cases) * len(DECISION_EVENT_PROPERTIES)
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
        property_names = {
            str(row.get("property", "")).strip() for row in rows_by_case[case.case_id]
        }
        missing = sorted(set(DECISION_EVENT_PROPERTIES) - property_names)
        if missing:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_scorer_properties",
                    "case_id": case.case_id,
                    "properties": missing,
                }
            )
        issues.extend(_case_consistency_issues(case.case_id, rows_by_case[case.case_id]))

    outputs: list[dict[str, Any]] = []
    if not any(issue["severity"] == "error" for issue in issues):
        outputs = [
            _scorer_output(
                case,
                rows_by_case[case.case_id],
                scorer=scorer,
                redacted_input=redacted_input,
            )
            for case in cases
        ]

    report = {
        "artifact_kind": "decision_evidence_manuscript_scorer_import",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "case_count": len(cases),
        "property_count": len(DECISION_EVENT_PROPERTIES),
        "workbook_row_count": len(workbook_rows),
        "expected_workbook_row_count": expected_rows,
        "scorer": scorer,
        "redacted_input": redacted_input,
        "redaction_status": SCORER_INPUT_REDACTION_STATUS if redacted_input else None,
        "case_id_map_count": len(input_to_original_case_id),
        "output_count": len(outputs),
        "category_counts": dict(
            sorted(Counter(str(row.get("category", "")) for row in workbook_rows).items())
        ),
        "status_counts": dict(
            sorted(Counter(str(row.get("prediction_status", "")) for row in workbook_rows).items())
        ),
        "issues": issues,
        "result_honesty": (
            "The importer writes candidate scorer outputs only after every property "
            "prediction row is reviewed. It does not create labels or manuscript results."
        ),
    }
    return outputs, report


def _case_by_input_id(
    *,
    case_by_id: dict[str, CaseManifest],
    input_to_original_case_id: dict[str, str],
) -> tuple[dict[str, CaseManifest], list[dict[str, Any]]]:
    if not input_to_original_case_id:
        return case_by_id, []
    issues: list[dict[str, Any]] = []
    case_by_input_id: dict[str, CaseManifest] = {}
    for input_case_id, original_case_id in input_to_original_case_id.items():
        case = case_by_id.get(original_case_id)
        if case is None:
            issues.append(
                {
                    "severity": "error",
                    "issue": "case_id_map_unknown_original_case_id",
                    "case_id": input_case_id,
                    "original_case_id": original_case_id,
                }
            )
            continue
        case_by_input_id[input_case_id] = case
    missing_original_case_ids = sorted(set(case_by_id) - set(input_to_original_case_id.values()))
    if missing_original_case_ids:
        issues.append(
            {
                "severity": "error",
                "issue": "case_id_map_missing_original_cases",
                "case_ids": missing_original_case_ids,
            }
        )
    return case_by_input_id, issues


def _row_issues(
    row: dict[str, Any],
    *,
    case_by_id: dict[str, CaseManifest],
    row_index: int,
    scorer: str,
    redacted_input: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", "")).strip()
    property_name = str(row.get("property", "")).strip()
    case = case_by_id.get(case_id)
    if redacted_input:
        redaction_status = str(row.get("redaction_status", "")).strip()
        if redaction_status != SCORER_INPUT_REDACTION_STATUS:
            issues.append(
                {
                    "severity": "error",
                    "issue": "invalid_redaction_status",
                    "row_index": row_index,
                    "case_id": case_id,
                    "expected": SCORER_INPUT_REDACTION_STATUS,
                    "actual": redaction_status,
                }
            )
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
    actual_scorer = str(row.get("scorer", "")).strip()
    if actual_scorer != scorer:
        issues.append(
            {
                "severity": "error",
                "issue": "scorer_mismatch",
                "row_index": row_index,
                "case_id": case_id,
                "expected": scorer,
                "actual": actual_scorer,
            }
        )
    status = str(row.get("prediction_status", "")).strip()
    if status != ACCEPTED_PREDICTION_STATUS:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_prediction_status",
                "row_index": row_index,
                "case_id": case_id,
                "expected": ACCEPTED_PREDICTION_STATUS,
                "actual": status,
            }
        )
    verdict = str(row.get("verdict", "")).strip()
    if _placeholder(verdict) or verdict not in VERDICTS:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_verdict",
                "row_index": row_index,
                "case_id": case_id,
                "actual": verdict,
                "expected": sorted(VERDICTS),
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
    category = str(row.get("category", "")).strip()
    if _placeholder(category) or category not in PROPERTY_CATEGORIES:
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
    issues.extend(_metadata_issues(row, row_index=row_index, case_id=case_id))
    return issues


def _metadata_issues(
    row: dict[str, Any],
    *,
    row_index: int,
    case_id: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field in REQUIRED_METADATA_FIELDS:
        value = str(row.get(field, "")).strip()
        if _placeholder(value):
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_prediction_metadata",
                    "row_index": row_index,
                    "case_id": case_id,
                    "field": field,
                }
            )
    implementation_status = str(row.get("implementation_status", "")).strip()
    if implementation_status in DISALLOWED_IMPLEMENTATION_STATUSES:
        issues.append(
            {
                "severity": "error",
                "issue": "disallowed_implementation_status",
                "row_index": row_index,
                "case_id": case_id,
                "actual": implementation_status,
            }
        )
    return issues


def _case_consistency_issues(case_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not rows:
        return issues
    first = rows[0]
    for row in rows[1:]:
        for field in CASE_METADATA_FIELDS:
            if str(row.get(field, "")).strip() != str(first.get(field, "")).strip():
                issues.append(
                    {
                        "severity": "error",
                        "issue": "case_metadata_mismatch",
                        "case_id": case_id,
                        "field": field,
                    }
                )
    return issues


def _scorer_output(
    case: CaseManifest,
    rows: list[dict[str, Any]],
    *,
    scorer: str,
    redacted_input: bool,
) -> dict[str, Any]:
    rows_by_property = {str(row["property"]): row for row in rows}
    first = rows[0]
    metadata = {
        "implementation_status": str(first.get("implementation_status", "")).strip(),
        "run_id": str(first.get("run_id", "")).strip(),
        "reviewer_id": str(first.get("reviewer_id", "")).strip(),
        "reviewed_at": str(first.get("reviewed_at", "")).strip(),
        "prediction_source": "manuscript_scorer_workbook_import",
        "case_source_status": case.metadata.get("case_source_status"),
        "result_honesty": (
            "Candidate scorer output only. Result claims require labels, baselines, "
            "package validation, and readiness checks."
        ),
    }
    for optional_field in ("model", "prompt_version"):
        value = str(first.get(optional_field, "")).strip()
        if value:
            metadata[optional_field] = value
    if redacted_input:
        metadata["scorer_input_case_id"] = str(first.get("case_id", "")).strip()
        metadata["scorer_input_redaction_status"] = SCORER_INPUT_REDACTION_STATUS
    return {
        "case_id": case.case_id,
        "scorer": scorer,
        "verdict": str(first["verdict"]).strip(),
        "metadata": metadata,
        "property_predictions": [
            {
                "property": property_name,
                "category": str(rows_by_property[property_name]["category"]).strip(),
                "required": _parse_bool(rows_by_property[property_name].get("required", True)),
                "source": PREDICTION_SOURCE,
                "notes": str(rows_by_property[property_name].get("notes", "")).strip(),
            }
            for property_name in DECISION_EVENT_PROPERTIES
        ],
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
        "output_count": report["output_count"],
        "redacted_input": report["redacted_input"],
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
    parser.add_argument("--scorer", default=DEFAULT_SCORER)
    parser.add_argument("--case-id-map", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    outputs, report = import_rows(
        cases=read_cases_jsonl(Path(args.cases)),
        workbook_rows=read_workbook(Path(args.workbook)),
        scorer=str(args.scorer),
        case_id_map=read_case_id_map(Path(args.case_id_map)) if args.case_id_map else None,
    )
    write_json(Path(args.report), report)
    if report["valid"]:
        write_jsonl(Path(args.out), outputs)
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
