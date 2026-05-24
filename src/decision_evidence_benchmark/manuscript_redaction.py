"""Redaction helpers for scorer-facing manuscript inputs."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

SCORER_INPUT_REDACTION_STATUS = "scorer_input_redacted_v1"
SCORER_INPUT_REDACTION_VERSION = "v1"
ALLOWED_SCORER_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
EVIDENCE_REF_FIELDS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)


def redacted_case_id(index: int) -> str:
    """Return a stable opaque scorer-facing case identifier."""

    if index < 1:
        raise ValueError("redacted case index must be one-based")
    return f"case-{index:06d}"


def redacted_case_row(case: CaseManifest, *, index: int) -> dict[str, Any]:
    """Build the scorer-facing redacted case row for one manuscript case."""

    evidence = dict(case.evidence)
    return {
        "case_id": redacted_case_id(index),
        "regime": case.regime,
        "question_family": case.question_family,
        "evidence": {
            "evidence_plane": str(evidence.get("evidence_plane", "")),
            "source_ref_counts": {
                field: _sequence_count(evidence.get(field, [])) for field in EVIDENCE_REF_FIELDS
            },
        },
        "container_flags": {
            flag: bool(case.container_flags.get(flag, False))
            for flag in ALLOWED_SCORER_CONTAINER_FLAGS
            if flag in case.container_flags
        },
        "scorer_properties": list(DECISION_EVENT_PROPERTIES),
        "metadata": {
            "redaction_status": SCORER_INPUT_REDACTION_STATUS,
            "redaction_version": SCORER_INPUT_REDACTION_VERSION,
            "case_source_status": case.metadata.get("case_source_status", ""),
            "result_honesty": (
                "Scorer-facing redacted case metadata. Original case identifiers, "
                "degradation conditions, labels, and source references are retained "
                "only in the private case-id map and internal evaluation artifacts."
            ),
        },
    }


def case_id_map_row(case: CaseManifest, *, index: int) -> dict[str, Any]:
    """Build a private mapping row from scorer-facing ID to original case ID."""

    return {
        "case_id": redacted_case_id(index),
        "original_case_id": case.case_id,
        "ordinal": index,
    }


def is_redacted_scorer_input_row(row: dict[str, Any]) -> bool:
    metadata = row.get("metadata", {})
    return (
        isinstance(metadata, dict)
        and metadata.get("redaction_status") == SCORER_INPUT_REDACTION_STATUS
    )


def _sequence_count(value: Any) -> int:
    if isinstance(value, list | tuple):
        return len(value)
    if value:
        return 1
    return 0
