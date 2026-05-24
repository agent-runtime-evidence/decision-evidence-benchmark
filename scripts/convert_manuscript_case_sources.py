"""Convert reviewed manuscript case source rows into unadjudicated cases."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.generation import DEGRADATION_CONDITIONS
from decision_evidence_benchmark.io import write_cases_jsonl, write_json
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    VERDICTS,
    CaseManifest,
)

REVIEWED_STATUS = "reviewed_non_fixture_evidence"
TEMPLATE_STATUS = "requires_non_fixture_evidence"
BOOLEAN_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
REQUIRED_SOURCE_LISTS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)


def read_source_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row must be a JSON object")
            rows.append(value)
    return rows


def convert_rows(
    rows: list[dict[str, Any]],
    *,
    expected_count: int = 64,
) -> tuple[list[CaseManifest], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    cases: list[CaseManifest] = []

    if len(rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_case_source_count",
                "expected": expected_count,
                "actual": len(rows),
            }
        )

    for row in rows:
        row_issues = _row_issues(row)
        issues.extend(row_issues)
        if row_issues:
            continue
        cases.append(_case_from_row(row))

    for case_id, count in Counter(case.case_id for case in cases).items():
        if count > 1:
            issues.append({"severity": "error", "issue": "duplicate_case_id", "case_id": case_id})

    report = {
        "artifact_kind": "decision_evidence_manuscript_case_source_conversion",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "input_row_count": len(rows),
        "output_case_count": len(cases),
        "expected_count": expected_count,
        "regime_counts": _counter_dict(case.regime for case in cases),
        "degradation_condition_counts": _counter_dict(
            case.degradation_condition for case in cases
        ),
        "question_family_counts": _counter_dict(case.question_family for case in cases),
        "issues": issues,
    }
    return cases, report


def _row_issues(row: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", ""))
    _require_string(row, "case_id", issues)
    _require_known(row, "regime", set(REGIME_IDS), issues, case_id=case_id)
    _require_known(
        row,
        "degradation_condition",
        set(DEGRADATION_CONDITIONS),
        issues,
        case_id=case_id,
    )
    _require_known(
        row,
        "question_family",
        set(DECISION_EVENT_PROPERTIES),
        issues,
        case_id=case_id,
    )

    status = row.get("template_status")
    if status == TEMPLATE_STATUS:
        issues.append(
            {
                "severity": "error",
                "case_id": case_id,
                "issue": "template_row_not_reviewed",
                "template_status": status,
            }
        )
    elif status != REVIEWED_STATUS:
        issues.append(
            {
                "severity": "error",
                "case_id": case_id,
                "issue": "invalid_template_status",
                "expected": REVIEWED_STATUS,
                "actual": status,
            }
        )

    source_requirements = row.get("source_requirements")
    if not isinstance(source_requirements, dict):
        issues.append(
            {"severity": "error", "case_id": case_id, "issue": "missing_source_requirements"}
        )
    else:
        for key in REQUIRED_SOURCE_LISTS:
            values = source_requirements.get(key)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                issues.append(
                    {
                        "severity": "error",
                        "case_id": case_id,
                        "issue": "missing_source_refs",
                        "field": f"source_requirements.{key}",
                    }
                )
        provenance_notes = source_requirements.get("provenance_notes")
        if not isinstance(provenance_notes, str) or not provenance_notes.strip():
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "missing_provenance_notes",
                }
            )

    container_flags = row.get("container_flags")
    if not isinstance(container_flags, dict):
        issues.append(
            {"severity": "error", "case_id": case_id, "issue": "missing_container_flags"}
        )
    else:
        for flag in BOOLEAN_CONTAINER_FLAGS:
            if not isinstance(container_flags.get(flag), bool):
                issues.append(
                    {
                        "severity": "error",
                        "case_id": case_id,
                        "issue": "invalid_container_flag",
                        "field": f"container_flags.{flag}",
                        "expected": "bool",
                        "actual": container_flags.get(flag),
                    }
                )
        verdict = container_flags.get("llm_judge_verdict")
        if verdict not in VERDICTS:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "invalid_llm_judge_verdict",
                    "expected": sorted(VERDICTS),
                    "actual": verdict,
                }
            )
    return issues


def _require_string(row: dict[str, Any], field: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(row.get(field), str) or not str(row.get(field)).strip():
        issues.append({"severity": "error", "issue": "missing_required_string", "field": field})


def _require_known(
    row: dict[str, Any],
    field: str,
    known_values: set[str],
    issues: list[dict[str, Any]],
    *,
    case_id: str,
) -> None:
    value = row.get(field)
    if value not in known_values:
        issues.append(
            {
                "severity": "error",
                "case_id": case_id,
                "issue": "unknown_field_value",
                "field": field,
                "known_values": sorted(known_values),
                "actual": value,
            }
        )


def _case_from_row(row: dict[str, Any]) -> CaseManifest:
    source_requirements = dict(row["source_requirements"])
    return CaseManifest(
        case_id=str(row["case_id"]),
        regime=str(row["regime"]),
        question_family=str(row["question_family"]),
        degradation_condition=str(row["degradation_condition"]),
        evidence={
            "evidence_plane": "reviewed_non_fixture",
            "native_evidence_refs": source_requirements["native_evidence_refs"],
            "reviewed_source_refs": source_requirements["reviewed_source_refs"],
            "evidence_plane_refs": source_requirements["evidence_plane_refs"],
            "provenance_notes": source_requirements["provenance_notes"],
        },
        container_flags=dict(row["container_flags"]),
        property_labels=(),
        metadata={
            "case_source_status": REVIEWED_STATUS,
            "result_honesty": (
                "Unadjudicated manuscript candidate case. Property labels must come from "
                "independent annotation records and adjudication."
            ),
        },
    )


def _counter_dict(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = read_source_rows(Path(args.sources))
    cases, report = convert_rows(rows, expected_count=int(args.expected_count))
    write_json(Path(args.report), report)
    if report["valid"]:
        write_cases_jsonl(Path(args.out), cases)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
