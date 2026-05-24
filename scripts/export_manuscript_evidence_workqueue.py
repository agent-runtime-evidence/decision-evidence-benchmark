"""Export a source-authoring workqueue from manuscript evidence intake."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_INTAKE = ROOT / "data/results/manuscript_evidence_intake.json"
DEFAULT_PACKET_INDEX = ROOT / "data/results/manuscript_source_review_packets.csv"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_evidence_workqueue.csv"
DEFAULT_JSONL_OUT = ROOT / "data/results/manuscript_evidence_workqueue.jsonl"

SOURCE_REF_ISSUES = {
    "missing_source_refs",
    "missing_provenance_notes",
    "missing_source_requirements",
    "row_not_reviewed",
}
CONTAINER_FLAG_ISSUES = {
    "invalid_container_flag",
    "invalid_llm_judge_verdict",
    "missing_container_flags",
}
ANNOTATION_ISSUES = {
    "missing_property_label_authoring",
    "missing_property_label_category",
    "missing_property_label",
    "invalid_property_label_property",
    "invalid_property_label_row",
}

CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "status",
    "review_status",
    "next_action",
    "review_packet_path",
    "needed_source_fields",
    "needed_container_flags",
    "needed_annotation_properties",
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
    "reviewer_id",
    "reviewed_at",
    "authoring_notes",
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


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


def read_packet_paths(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        return {
            str(row.get("case_id", "")).strip(): str(row.get("packet_path", "")).strip()
            for row in csv.DictReader(handle)
            if str(row.get("case_id", "")).strip()
        }


def build_workqueue(
    *,
    template: Path,
    intake: Path,
    packet_index: Path,
    expected_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    template_rows = read_jsonl(template)
    intake_report = read_json(intake)
    packet_paths = read_packet_paths(packet_index)
    intake_rows = {
        str(row.get("case_id")): row
        for row in intake_report.get("rows", [])
        if isinstance(row, dict)
    }

    rows = [
        _workqueue_row(
            row,
            intake_rows.get(str(row.get("case_id"))),
            packet_path=packet_paths.get(str(row.get("case_id")), ""),
            row_index=index + 1,
        )
        for index, row in enumerate(template_rows)
    ]
    issues: list[dict[str, Any]] = []
    if len(template_rows) != expected_count:
        issues.append(
            {
                "severity": "warning",
                "issue": "unexpected_template_row_count",
                "expected": expected_count,
                "actual": len(template_rows),
            }
        )
    missing_intake = [
        str(row.get("case_id"))
        for row in template_rows
        if str(row.get("case_id")) not in intake_rows
    ]
    if missing_intake:
        issues.append(
            {
                "severity": "warning",
                "issue": "template_rows_missing_from_intake",
                "case_ids": missing_intake,
            }
        )
    missing_packet_paths = [
        str(row.get("case_id"))
        for row in template_rows
        if str(row.get("case_id")) not in packet_paths
    ]
    if missing_packet_paths:
        issues.append(
            {
                "severity": "warning",
                "issue": "template_rows_missing_review_packet",
                "case_ids": missing_packet_paths,
            }
        )
    status_counts = dict(sorted(Counter(str(row["status"]) for row in rows).items()))
    report = {
        "artifact_kind": "decision_evidence_manuscript_evidence_workqueue_export",
        "template_path": str(template),
        "intake_path": str(intake),
        "packet_index_path": str(packet_index),
        "expected_count": expected_count,
        "row_count": len(rows),
        "status_counts": status_counts,
        "review_status_counts": dict(
            sorted(Counter(str(row["review_status"]) for row in rows).items())
        ),
        "issues": issues,
        "result_honesty": (
            "The workqueue is an authoring aid. It does not mark evidence reviewed, "
            "does not create manuscript cases, and must not be cited as a result."
        ),
    }
    return rows, report


def _workqueue_row(
    template_row: dict[str, Any],
    intake_row: dict[str, Any] | None,
    *,
    packet_path: str,
    row_index: int,
) -> dict[str, Any]:
    issues = _intake_issues(intake_row)
    source_requirements = template_row.get("source_requirements")
    if not isinstance(source_requirements, dict):
        source_requirements = {}
    container_flags = template_row.get("container_flags")
    if not isinstance(container_flags, dict):
        container_flags = {}
    status = str(intake_row.get("status")) if intake_row else "blocked"
    row = {
        "row_index": row_index,
        "case_id": str(template_row.get("case_id", "")),
        "regime": str(template_row.get("regime", "")),
        "degradation_condition": str(template_row.get("degradation_condition", "")),
        "question_family": str(template_row.get("question_family", "")),
        "status": status,
        "review_status": _review_status(status),
        "next_action": str(intake_row.get("next_action", "")) if intake_row else "run intake",
        "review_packet_path": packet_path,
        "needed_source_fields": _pipe_join(_needed_source_fields(issues)),
        "needed_container_flags": _pipe_join(_needed_container_flags(issues)),
        "needed_annotation_properties": _pipe_join(_needed_annotation_properties(issues)),
        "native_evidence_refs": _pipe_join(source_requirements.get("native_evidence_refs", [])),
        "reviewed_source_refs": _pipe_join(
            source_requirements.get("reviewed_source_refs", [])
        ),
        "evidence_plane_refs": _pipe_join(source_requirements.get("evidence_plane_refs", [])),
        "provenance_notes": str(source_requirements.get("provenance_notes", "")),
        "trace_present": _cell(container_flags.get("trace_present", "")),
        "ledger_present": _cell(container_flags.get("ledger_present", "")),
        "schema_valid": _cell(container_flags.get("schema_valid", "")),
        "checklist_complete": _cell(container_flags.get("checklist_complete", "")),
        "source_validator_passed": _cell(container_flags.get("source_validator_passed", "")),
        "llm_judge_verdict": _cell(container_flags.get("llm_judge_verdict", "")),
        "reviewer_id": "",
        "reviewed_at": "",
        "authoring_notes": "",
    }
    row["issue_codes"] = sorted({str(issue.get("issue", "")) for issue in issues})
    return row


def _intake_issues(intake_row: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not intake_row:
        return [{"issue": "missing_intake_row"}]
    issues = intake_row.get("issues", [])
    return [issue for issue in issues if isinstance(issue, dict)]


def _needed_source_fields(issues: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for issue in issues:
        issue_code = str(issue.get("issue", ""))
        if issue_code not in SOURCE_REF_ISSUES:
            continue
        field = issue.get("field")
        if isinstance(field, str) and field:
            fields.append(field)
        elif issue_code == "missing_provenance_notes":
            fields.append("source_requirements.provenance_notes")
        elif issue_code == "row_not_reviewed":
            fields.append("template_status")
        else:
            fields.append(issue_code)
    return sorted(set(fields))


def _needed_container_flags(issues: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for issue in issues:
        issue_code = str(issue.get("issue", ""))
        if issue_code not in CONTAINER_FLAG_ISSUES:
            continue
        field = issue.get("field")
        if isinstance(field, str) and field.startswith("container_flags."):
            fields.append(field.removeprefix("container_flags."))
        elif issue_code == "invalid_llm_judge_verdict":
            fields.append("llm_judge_verdict")
        else:
            fields.append(issue_code)
    return sorted(set(fields))


def _needed_annotation_properties(issues: list[dict[str, Any]]) -> list[str]:
    properties: list[str] = []
    for issue in issues:
        if str(issue.get("issue", "")) not in ANNOTATION_ISSUES:
            continue
        property_name = issue.get("property")
        if isinstance(property_name, str) and property_name:
            properties.append(property_name)
        else:
            properties.append(str(issue.get("issue", "")))
    return sorted(set(properties))


def _review_status(status: str) -> str:
    if status == "ready":
        return "ready_for_conversion"
    if status == "needs_annotation":
        return "source_reviewed_needs_annotation"
    if status == "blocked":
        return "blocked"
    return "todo"


def _pipe_join(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--intake", default=str(DEFAULT_INTAKE))
    parser.add_argument("--packet-index", default=str(DEFAULT_PACKET_INDEX))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--jsonl-out", default=str(DEFAULT_JSONL_OUT))
    parser.add_argument("--expected-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows, report = build_workqueue(
        template=Path(args.template),
        intake=Path(args.intake),
        packet_index=Path(args.packet_index),
        expected_count=int(args.expected_count),
    )
    write_csv(Path(args.csv_out), rows)
    write_jsonl(Path(args.jsonl_out), rows)
    print(
        json.dumps(
            {
                **report,
                "csv_out": str(args.csv_out),
                "jsonl_out": str(args.jsonl_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
