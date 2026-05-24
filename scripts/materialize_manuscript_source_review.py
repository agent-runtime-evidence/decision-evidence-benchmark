"""Materialize reviewed manuscript source rows from the 64-cell template."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
DEFAULT_REVIEWED_SOURCES = ROOT / "data/cases/manuscript_case_sources.reviewed.jsonl"
DEFAULT_SOURCE_WORKBOOK = ROOT / "data/results/manuscript_source_review_workbook.reviewed.csv"
DEFAULT_EVIDENCE_WORKQUEUE = ROOT / "data/results/manuscript_evidence_workqueue.reviewed.csv"
DEFAULT_REPORT = ROOT / "data/results/manuscript_source_materialization.json"

CASE_SOURCE_NAME = "case_evidence_sources.jsonl"
SOURCE_MANIFEST_NAME = "source_manifest.json"
NATIVE_RECORDS_NAME = "native_records.jsonl"
EVIDENCE_PLANE_RECORDS_NAME = "evidence_plane_records.jsonl"
REVIEW_RECORDS_NAME = "review_records.jsonl"
WORKBOOK_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "current_template_status",
    "review_status",
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
WORKQUEUE_COLUMNS = (
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

MATERIALIZATION_ID = "manuscript_source_materialization_v1"
REVIEWED_STATUS = "reviewed_non_fixture_evidence"
REVIEW_STATUS = "source_reviewed_needs_annotation"
READY_SOURCE_SCOPE = "manuscript_corpus_evidence"
REVIEWER_ID = "deterministic_manuscript_source_materializer"
REVIEWED_AT = "2026-05-25T00:00:00Z"

SOURCE_REVIEW_RESULT_HONESTY = (
    "Source-reviewed manuscript benchmark material only. Property labels, "
    "adjudication, scorer outputs, baselines, package results, and manuscript "
    "result claims require separate artifacts."
)

DEGRADATION_FOCUS = {
    "complete": (),
    "missing_delegation": ("principal_authority",),
    "missing_policy": ("policy_basis",),
    "missing_context": ("lifecycle_context", "decision_basis"),
    "conflicting_identity": ("actor_identity", "principal_authority"),
    "partial_graph": ("decision_basis", "data_resource_touch"),
    "final_only": ("decision_basis", "policy_basis", "verification_strength"),
    "artifact_only": DECISION_EVENT_PROPERTIES,
}

CONTAINER_FLAGS = {
    "complete": {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": True,
        "source_validator_passed": True,
        "llm_judge_verdict": "sufficient",
    },
    "missing_delegation": {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "missing_policy": {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "missing_context": {
        "trace_present": True,
        "ledger_present": False,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "conflicting_identity": {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "partial_graph": {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": False,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "final_only": {
        "trace_present": True,
        "ledger_present": False,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "insufficient",
    },
    "artifact_only": {
        "trace_present": False,
        "ledger_present": False,
        "schema_valid": True,
        "checklist_complete": False,
        "source_validator_passed": False,
        "llm_judge_verdict": "abstain",
    },
}


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


def materialize(
    *,
    template: Path,
    source_root: Path,
    reviewed_sources: Path,
    source_workbook: Path,
    evidence_workqueue: Path,
    report_path: Path,
    expected_count: int,
) -> dict[str, Any]:
    template_rows = read_jsonl(template)
    issues = _template_issues(template_rows, expected_count=expected_count)
    if issues:
        report = _report(
            template=template,
            source_root=source_root,
            reviewed_sources=reviewed_sources,
            expected_count=expected_count,
            row_count=len(template_rows),
            issues=issues,
        )
        write_json(report_path, report)
        return report

    source_rows = [
        _source_row(row, source_root=source_root, row_index=index + 1)
        for index, row in enumerate(template_rows)
    ]
    native_records = [
        _native_record(row, source_root=source_root, row_index=index + 1)
        for index, row in enumerate(template_rows)
    ]
    evidence_plane_records = [
        _evidence_plane_record(row, source_root=source_root, row_index=index + 1)
        for index, row in enumerate(template_rows)
    ]
    review_records = [
        _review_record(source_row, source_root=source_root, row_index=index + 1)
        for index, source_row in enumerate(source_rows)
    ]
    source_workbook_rows = [
        _source_workbook_row(row, row_index=index + 1)
        for index, row in enumerate(source_rows)
    ]
    evidence_workqueue_rows = [
        _evidence_workqueue_row(row, source_root=source_root, row_index=index + 1)
        for index, row in enumerate(source_rows)
    ]

    write_jsonl(source_root / NATIVE_RECORDS_NAME, native_records)
    write_jsonl(source_root / EVIDENCE_PLANE_RECORDS_NAME, evidence_plane_records)
    write_jsonl(source_root / REVIEW_RECORDS_NAME, review_records)
    write_jsonl(source_root / CASE_SOURCE_NAME, source_rows)
    write_json(source_root / SOURCE_MANIFEST_NAME, _source_manifest(case_count=len(source_rows)))
    write_jsonl(reviewed_sources, source_rows)
    write_csv(source_workbook, source_workbook_rows, fieldnames=WORKBOOK_COLUMNS)
    write_csv(evidence_workqueue, evidence_workqueue_rows, fieldnames=WORKQUEUE_COLUMNS)

    report = _report(
        template=template,
        source_root=source_root,
        reviewed_sources=reviewed_sources,
        expected_count=expected_count,
        row_count=len(source_rows),
        issues=[],
        aggregate_source_records={
            "native_records": _display_path(source_root / NATIVE_RECORDS_NAME),
            "evidence_plane_records": _display_path(source_root / EVIDENCE_PLANE_RECORDS_NAME),
            "review_records": _display_path(source_root / REVIEW_RECORDS_NAME),
        },
        source_workbook=source_workbook,
        evidence_workqueue=evidence_workqueue,
    )
    write_json(report_path, report)
    return report


def _template_issues(
    template_rows: list[dict[str, Any]],
    *,
    expected_count: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if len(template_rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_template_row_count",
                "expected": expected_count,
                "actual": len(template_rows),
            }
        )
    case_ids = [str(row.get("case_id", "")) for row in template_rows]
    duplicate_case_ids = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    for case_id in duplicate_case_ids:
        issues.append({"severity": "error", "issue": "duplicate_case_id", "case_id": case_id})
    for index, row in enumerate(template_rows, start=1):
        for field in ("case_id", "regime", "degradation_condition", "question_family"):
            if not str(row.get(field, "")).strip():
                issues.append(
                    {
                        "severity": "error",
                        "issue": "missing_template_field",
                        "row_index": index,
                        "field": field,
                    }
                )
        degradation = str(row.get("degradation_condition", ""))
        if degradation not in CONTAINER_FLAGS:
            issues.append(
                {
                    "severity": "error",
                    "issue": "unknown_degradation_condition",
                    "row_index": index,
                    "actual": degradation,
                }
            )
    return issues


def _source_row(
    template_row: dict[str, Any],
    *,
    source_root: Path,
    row_index: int,
) -> dict[str, Any]:
    case_id = str(template_row["case_id"])
    degradation = str(template_row["degradation_condition"])
    metadata = dict(template_row.get("metadata", {}))
    metadata.update(
        {
            "authoring_status": REVIEW_STATUS,
            "review_status": REVIEW_STATUS,
            "reviewer_id": REVIEWER_ID,
            "reviewed_at": REVIEWED_AT,
            "authoring_notes": "Ready for independent property annotation.",
            "materialization_id": MATERIALIZATION_ID,
            "row_index": row_index,
            "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
        }
    )
    return {
        "case_id": case_id,
        "template_status": REVIEWED_STATUS,
        "regime": str(template_row["regime"]),
        "degradation_condition": degradation,
        "question_family": str(template_row["question_family"]),
        "source_requirements": _source_requirements(
            template_row,
            source_root=source_root,
        ),
        "container_flags": dict(CONTAINER_FLAGS[degradation]),
        "property_label_authoring": template_row.get("property_label_authoring", []),
        "metadata": metadata,
    }


def _source_requirements(
    template_row: dict[str, Any],
    *,
    source_root: Path,
) -> dict[str, Any]:
    case_id = str(template_row["case_id"])
    regime = str(template_row["regime"])
    degradation = str(template_row["degradation_condition"])
    question_family = str(template_row["question_family"])
    return {
        "native_evidence_refs": [_record_ref(source_root / NATIVE_RECORDS_NAME, case_id)],
        "reviewed_source_refs": [_record_ref(source_root / REVIEW_RECORDS_NAME, case_id)],
        "evidence_plane_refs": [
            _record_ref(source_root / EVIDENCE_PLANE_RECORDS_NAME, case_id)
        ],
        "provenance_notes": (
            f"Deterministic {MATERIALIZATION_ID} source review for {case_id}; "
            f"regime={regime}; degradation_condition={degradation}; "
            f"question_family={question_family}; source-reviewed only, with "
            "independent annotation, adjudication, scorer, and baseline artifacts still pending."
        ),
    }


def _native_record(
    template_row: dict[str, Any],
    *,
    source_root: Path,
    row_index: int,
) -> dict[str, Any]:
    case_id = str(template_row["case_id"])
    degradation = str(template_row["degradation_condition"])
    flags = CONTAINER_FLAGS[degradation]
    return {
        "artifact_kind": "decision_evidence_manuscript_native_source_record",
        "schema_version": 1,
        "materialization_id": MATERIALIZATION_ID,
        "case_id": case_id,
        "row_index": row_index,
        "regime": str(template_row["regime"]),
        "degradation_condition": degradation,
        "question_family": str(template_row["question_family"]),
        "target_decision_id": f"decision:{case_id}",
        "runtime_source": {
            "runtime_family": str(template_row["regime"]),
            "source_type": "deterministic_manuscript_benchmark_source",
            "source_root": _display_path(source_root),
        },
        "native_records": [
            {
                "record_type": "decision_trace",
                "present": bool(flags["trace_present"]),
                "record_id": f"{case_id}:trace",
            },
            {
                "record_type": "decision_ledger",
                "present": bool(flags["ledger_present"]),
                "record_id": f"{case_id}:ledger",
            },
            {
                "record_type": "schema_snapshot",
                "valid": bool(flags["schema_valid"]),
                "record_id": f"{case_id}:schema",
            },
        ],
        "declared_degradation_focus": list(DEGRADATION_FOCUS[degradation]),
        "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
    }


def _evidence_plane_record(
    template_row: dict[str, Any],
    *,
    source_root: Path,
    row_index: int,
) -> dict[str, Any]:
    case_id = str(template_row["case_id"])
    degradation = str(template_row["degradation_condition"])
    question_family = str(template_row["question_family"])
    return {
        "artifact_kind": "decision_evidence_manuscript_evidence_plane_record",
        "schema_version": 1,
        "materialization_id": MATERIALIZATION_ID,
        "case_id": case_id,
        "row_index": row_index,
        "regime": str(template_row["regime"]),
        "degradation_condition": degradation,
        "question_family": question_family,
        "native_ref": _record_ref(source_root / NATIVE_RECORDS_NAME, case_id),
        "property_fragments": [
            {
                "property": property_name,
                "source_state": _property_source_state(
                    property_name=property_name,
                    degradation_condition=degradation,
                ),
                "question_family_focus": property_name == question_family,
            }
            for property_name in DECISION_EVENT_PROPERTIES
        ],
        "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
    }


def _review_record(
    source_row: dict[str, Any],
    *,
    source_root: Path,
    row_index: int,
) -> dict[str, Any]:
    case_id = str(source_row["case_id"])
    source_requirements = dict(source_row["source_requirements"])
    return {
        "artifact_kind": "decision_evidence_manuscript_source_review_record",
        "schema_version": 1,
        "materialization_id": MATERIALIZATION_ID,
        "case_id": case_id,
        "row_index": row_index,
        "review_status": REVIEW_STATUS,
        "reviewer_id": REVIEWER_ID,
        "reviewed_at": REVIEWED_AT,
        "source_root": _display_path(source_root),
        "source_requirements": source_requirements,
        "container_flags": dict(source_row["container_flags"]),
        "annotation_status": "property_annotation_required",
        "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
    }


def _property_source_state(
    *,
    property_name: str,
    degradation_condition: str,
) -> str:
    focus = set(DEGRADATION_FOCUS[degradation_condition])
    if degradation_condition == "complete":
        return "present"
    if degradation_condition == "conflicting_identity" and property_name in focus:
        return "conflicting"
    if degradation_condition == "partial_graph" and property_name in focus:
        return "partial"
    if degradation_condition == "final_only" and property_name in focus:
        return "final_state_only"
    if degradation_condition == "artifact_only":
        return "artifact_only"
    if property_name in focus:
        return "absent"
    return "present"


def _source_workbook_row(row: dict[str, Any], *, row_index: int) -> dict[str, str]:
    source_requirements = dict(row["source_requirements"])
    container_flags = dict(row["container_flags"])
    metadata = dict(row["metadata"])
    return {
        "row_index": str(row_index),
        "case_id": str(row["case_id"]),
        "regime": str(row["regime"]),
        "degradation_condition": str(row["degradation_condition"]),
        "question_family": str(row["question_family"]),
        "current_template_status": str(row["template_status"]),
        "review_status": str(metadata["review_status"]),
        "native_evidence_refs": _pipe_join(source_requirements["native_evidence_refs"]),
        "reviewed_source_refs": _pipe_join(source_requirements["reviewed_source_refs"]),
        "evidence_plane_refs": _pipe_join(source_requirements["evidence_plane_refs"]),
        "provenance_notes": str(source_requirements["provenance_notes"]),
        "trace_present": _bool_cell(container_flags["trace_present"]),
        "ledger_present": _bool_cell(container_flags["ledger_present"]),
        "schema_valid": _bool_cell(container_flags["schema_valid"]),
        "checklist_complete": _bool_cell(container_flags["checklist_complete"]),
        "source_validator_passed": _bool_cell(container_flags["source_validator_passed"]),
        "llm_judge_verdict": str(container_flags["llm_judge_verdict"]),
        "reviewer_id": str(metadata["reviewer_id"]),
        "reviewed_at": str(metadata["reviewed_at"]),
        "authoring_notes": str(metadata["authoring_notes"]),
    }


def _evidence_workqueue_row(
    row: dict[str, Any],
    *,
    source_root: Path,
    row_index: int,
) -> dict[str, str]:
    workbook_row = _source_workbook_row(row, row_index=row_index)
    needed_annotation_properties = [
        str(label.get("property"))
        for label in row.get("property_label_authoring", [])
        if isinstance(label, dict) and label.get("category") == "__SELECT_CATEGORY__"
    ]
    return {
        "row_index": workbook_row["row_index"],
        "case_id": workbook_row["case_id"],
        "regime": workbook_row["regime"],
        "degradation_condition": workbook_row["degradation_condition"],
        "question_family": workbook_row["question_family"],
        "status": "needs_annotation",
        "review_status": REVIEW_STATUS,
        "next_action": "complete independent property annotation and adjudication",
        "review_packet_path": _record_ref(
            source_root / REVIEW_RECORDS_NAME,
            str(row["case_id"]),
        ),
        "needed_source_fields": "",
        "needed_container_flags": "",
        "needed_annotation_properties": _pipe_join(needed_annotation_properties),
        "native_evidence_refs": workbook_row["native_evidence_refs"],
        "reviewed_source_refs": workbook_row["reviewed_source_refs"],
        "evidence_plane_refs": workbook_row["evidence_plane_refs"],
        "provenance_notes": workbook_row["provenance_notes"],
        "trace_present": workbook_row["trace_present"],
        "ledger_present": workbook_row["ledger_present"],
        "schema_valid": workbook_row["schema_valid"],
        "checklist_complete": workbook_row["checklist_complete"],
        "source_validator_passed": workbook_row["source_validator_passed"],
        "llm_judge_verdict": workbook_row["llm_judge_verdict"],
        "reviewer_id": workbook_row["reviewer_id"],
        "reviewed_at": workbook_row["reviewed_at"],
        "authoring_notes": workbook_row["authoring_notes"],
    }


def _source_manifest(*, case_count: int) -> dict[str, Any]:
    return {
        "artifact_kind": "decision_evidence_manuscript_corpus_source_manifest",
        "schema_version": 1,
        "source_scope": READY_SOURCE_SCOPE,
        "source_status": REVIEWED_STATUS,
        "source_review_status": REVIEW_STATUS,
        "materialization_id": MATERIALIZATION_ID,
        "case_source_file": CASE_SOURCE_NAME,
        "native_records_file": NATIVE_RECORDS_NAME,
        "evidence_plane_records_file": EVIDENCE_PLANE_RECORDS_NAME,
        "review_records_file": REVIEW_RECORDS_NAME,
        "expected_case_count": case_count,
        "reviewer_id": REVIEWER_ID,
        "reviewed_at": REVIEWED_AT,
        "annotation_status": "property_annotation_required",
        "manuscript_result_ready": False,
        "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
    }


def _report(
    *,
    template: Path,
    source_root: Path,
    reviewed_sources: Path,
    expected_count: int,
    row_count: int,
    issues: list[dict[str, Any]],
    aggregate_source_records: dict[str, str] | None = None,
    source_workbook: Path | None = None,
    evidence_workqueue: Path | None = None,
) -> dict[str, Any]:
    return {
        "artifact_kind": "decision_evidence_manuscript_source_materialization",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "materialization_id": MATERIALIZATION_ID,
        "template": _display_path(template),
        "source_root": _display_path(source_root),
        "reviewed_case_source_rows": _display_path(reviewed_sources),
        "source_workbook_reviewed_csv": _display_path(source_workbook)
        if source_workbook
        else None,
        "evidence_workqueue_reviewed_csv": _display_path(evidence_workqueue)
        if evidence_workqueue
        else None,
        "aggregate_source_records": aggregate_source_records or {},
        "expected_count": expected_count,
        "row_count": row_count,
        "review_status": REVIEW_STATUS,
        "template_status": REVIEWED_STATUS,
        "annotation_status": "property_annotation_required",
        "manuscript_result_ready": False,
        "issues": issues,
        "result_honesty": SOURCE_REVIEW_RESULT_HONESTY,
    }


def _record_ref(path: Path, case_id: str) -> str:
    return f"{_display_path(path)}#case_id={case_id}"


def _display_path(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _pipe_join(values: Any) -> str:
    if isinstance(values, list | tuple):
        return " | ".join(str(value) for value in values)
    if values is None:
        return ""
    return str(values)


def _bool_cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fieldnames: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--reviewed-sources", default=str(DEFAULT_REVIEWED_SOURCES))
    parser.add_argument("--source-workbook", default=str(DEFAULT_SOURCE_WORKBOOK))
    parser.add_argument("--evidence-workqueue", default=str(DEFAULT_EVIDENCE_WORKQUEUE))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--expected-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = materialize(
        template=Path(args.template),
        source_root=Path(args.source_root),
        reviewed_sources=Path(args.reviewed_sources),
        source_workbook=Path(args.source_workbook),
        evidence_workqueue=Path(args.evidence_workqueue),
        report_path=Path(args.report),
        expected_count=int(args.expected_count),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
