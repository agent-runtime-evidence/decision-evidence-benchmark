"""Build a row-level manuscript evidence intake report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.generation import DEGRADATION_CONDITIONS
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    PROPERTY_CATEGORIES,
    VERDICTS,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_SOURCE_AUDIT = ROOT / "data/results/manuscript_source_root_audit.json"
DEFAULT_OUT = ROOT / "data/results/manuscript_evidence_intake.json"

REVIEWED_STATUS = "reviewed_non_fixture_evidence"
TEMPLATE_STATUS = "requires_non_fixture_evidence"
ANNOTATION_PLACEHOLDER = "__SELECT_CATEGORY__"
REQUIRED_SOURCE_LISTS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)
BOOLEAN_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
ROW_STATUSES = ("ready", "blocked", "needs_source", "needs_annotation")


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


def build_report(
    *,
    template: Path,
    source_audit: Path,
    expected_count: int,
) -> dict[str, Any]:
    rows = read_jsonl(template)
    audit = read_source_audit(source_audit)
    row_reports = [_row_report(row, row_index=index + 1) for index, row in enumerate(rows)]
    report_blockers: list[dict[str, Any]] = []
    if len(rows) != expected_count:
        report_blockers.append(
            {
                "area": "case_template",
                "issue": "unexpected_row_count",
                "expected": expected_count,
                "actual": len(rows),
            }
        )
    if not audit["source_audit_ready"]:
        report_blockers.append(
            {
                "area": "source_audit",
                "issue": "source_audit_not_promotion_ready",
                "details": audit["promotion_blockers"],
            }
        )
    status_counts = _status_counts(row_reports)
    source_ready_rows = status_counts["ready"] + status_counts["needs_annotation"]
    reviewed_case_source_ready = (
        not report_blockers
        and source_ready_rows == expected_count
        and status_counts["blocked"] == 0
        and status_counts["needs_source"] == 0
    )
    annotation_ready = (
        reviewed_case_source_ready
        and status_counts["ready"] == expected_count
        and status_counts["needs_annotation"] == 0
    )
    return {
        "artifact_kind": "decision_evidence_manuscript_evidence_intake",
        "template_path": str(template),
        "source_audit_path": str(source_audit),
        "expected_count": expected_count,
        "row_count": len(rows),
        "status_counts": status_counts,
        "source_audit": audit,
        "reviewed_case_source_ready": reviewed_case_source_ready,
        "annotation_ready": annotation_ready,
        "promotion_blockers": report_blockers,
        "rows": row_reports,
        "result_honesty": (
            "Intake classifies authoring state only. It does not promote rows to "
            "reviewed_non_fixture_evidence and does not create manuscript results."
        ),
    }


def read_source_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "present": False,
            "source_audit_ready": False,
            "promotion_blockers": [
                {"area": "source_audit", "issue": "source_audit_missing", "path": str(path)}
            ],
            "candidate_ref_count": 0,
        }
    payload = json.loads(path.read_text())
    source_roots = payload.get("source_roots", [])
    candidate_ref_count = sum(
        int(root.get("candidate_ref_count", 0))
        for root in source_roots
        if isinstance(root, dict)
    )
    return {
        "present": True,
        "source_audit_ready": bool(payload.get("manuscript_case_source_ready")),
        "promotion_blockers": payload.get("promotion_blockers", []),
        "candidate_ref_count": candidate_ref_count,
    }


def _row_report(row: dict[str, Any], *, row_index: int) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", ""))
    _check_identity_fields(row, issues, case_id=case_id)
    source_issues = _source_issues(row, case_id=case_id)
    annotation_issues = _annotation_issues(row, case_id=case_id)
    issues.extend(source_issues)
    issues.extend(annotation_issues)

    if any(issue["severity"] == "error" for issue in issues):
        status = "blocked"
    elif source_issues:
        status = "needs_source"
    elif annotation_issues:
        status = "needs_annotation"
    else:
        status = "ready"

    return {
        "row_index": row_index,
        "case_id": case_id,
        "regime": row.get("regime"),
        "degradation_condition": row.get("degradation_condition"),
        "question_family": row.get("question_family"),
        "status": status,
        "issues": issues,
        "next_action": _next_action(status),
    }


def _check_identity_fields(
    row: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    case_id: str,
) -> None:
    if not case_id.strip():
        issues.append({"severity": "error", "issue": "missing_case_id"})
    _known_value(row, "regime", set(REGIME_IDS), issues, case_id=case_id)
    _known_value(
        row,
        "degradation_condition",
        set(DEGRADATION_CONDITIONS),
        issues,
        case_id=case_id,
    )
    _known_value(
        row,
        "question_family",
        set(DECISION_EVENT_PROPERTIES),
        issues,
        case_id=case_id,
    )


def _source_issues(row: dict[str, Any], *, case_id: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    status = row.get("template_status")
    if status == TEMPLATE_STATUS:
        issues.append(
            {
                "severity": "warning",
                "case_id": case_id,
                "issue": "row_not_reviewed",
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
            {"severity": "warning", "case_id": case_id, "issue": "missing_source_requirements"}
        )
    else:
        for key in REQUIRED_SOURCE_LISTS:
            values = source_requirements.get(key)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                issues.append(
                    {
                        "severity": "warning",
                        "case_id": case_id,
                        "issue": "missing_source_refs",
                        "field": f"source_requirements.{key}",
                    }
                )
        provenance_notes = source_requirements.get("provenance_notes")
        if not isinstance(provenance_notes, str) or not provenance_notes.strip():
            issues.append(
                {
                    "severity": "warning",
                    "case_id": case_id,
                    "issue": "missing_provenance_notes",
                }
            )

    container_flags = row.get("container_flags")
    if not isinstance(container_flags, dict):
        issues.append(
            {"severity": "warning", "case_id": case_id, "issue": "missing_container_flags"}
        )
    else:
        for flag in BOOLEAN_CONTAINER_FLAGS:
            if not isinstance(container_flags.get(flag), bool):
                issues.append(
                    {
                        "severity": "warning",
                        "case_id": case_id,
                        "issue": "invalid_container_flag",
                        "field": f"container_flags.{flag}",
                    }
                )
        verdict = container_flags.get("llm_judge_verdict")
        if verdict not in VERDICTS:
            issues.append(
                {
                    "severity": "warning",
                    "case_id": case_id,
                    "issue": "invalid_llm_judge_verdict",
                    "actual": verdict,
                }
            )
    return issues


def _annotation_issues(row: dict[str, Any], *, case_id: str) -> list[dict[str, Any]]:
    labels = row.get("property_label_authoring")
    if not isinstance(labels, list):
        return [
            {
                "severity": "warning",
                "case_id": case_id,
                "issue": "missing_property_label_authoring",
            }
        ]
    issues: list[dict[str, Any]] = []
    seen_properties: set[str] = set()
    for label in labels:
        if not isinstance(label, dict):
            issues.append(
                {
                    "severity": "warning",
                    "case_id": case_id,
                    "issue": "invalid_property_label_row",
                }
            )
            continue
        property_name = label.get("property")
        category = label.get("category")
        if property_name not in DECISION_EVENT_PROPERTIES:
            issues.append(
                {
                    "severity": "warning",
                    "case_id": case_id,
                    "issue": "invalid_property_label_property",
                    "actual": property_name,
                }
            )
        else:
            seen_properties.add(str(property_name))
        if category == ANNOTATION_PLACEHOLDER or category not in PROPERTY_CATEGORIES:
            issues.append(
                {
                    "severity": "warning",
                    "case_id": case_id,
                    "issue": "missing_property_label_category",
                    "property": property_name,
                    "actual": category,
                }
            )
    missing_properties = sorted(set(DECISION_EVENT_PROPERTIES) - seen_properties)
    for property_name in missing_properties:
        issues.append(
            {
                "severity": "warning",
                "case_id": case_id,
                "issue": "missing_property_label",
                "property": property_name,
            }
        )
    return issues


def _known_value(
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
                "actual": value,
            }
        )


def _next_action(status: str) -> str:
    if status == "ready":
        return "row is ready for reviewed case-source conversion and annotation packaging"
    if status == "needs_annotation":
        return "complete property_label_authoring or collect separate manuscript annotations"
    if status == "needs_source":
        return "attach reviewed source refs, provenance notes, and concrete container flags"
    return "fix blocking row-shape or taxonomy errors before source review"


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["status"]) for row in rows)
    return {status: counts.get(status, 0) for status in ROW_STATUSES}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_kind": report["artifact_kind"],
        "row_count": report["row_count"],
        "expected_count": report["expected_count"],
        "status_counts": report["status_counts"],
        "reviewed_case_source_ready": report["reviewed_case_source_ready"],
        "annotation_ready": report["annotation_ready"],
        "source_audit_ready": report["source_audit"]["source_audit_ready"],
        "promotion_blocker_count": len(report["promotion_blockers"]),
        "outcome": "full row-level report written to --out",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--source-audit", default=str(DEFAULT_SOURCE_AUDIT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--expected-count", type=int, default=64)
    parser.add_argument("--fail-on-blockers", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report(
        template=Path(args.template),
        source_audit=Path(args.source_audit),
        expected_count=int(args.expected_count),
    )
    write_json(Path(args.out), report)
    print(json.dumps(console_summary(report), indent=2, sort_keys=True))
    if args.fail_on_blockers and not report["reviewed_case_source_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
