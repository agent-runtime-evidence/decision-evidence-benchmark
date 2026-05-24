"""AER reasoning-provenance native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native AER reasoning-provenance record into the case manifest."""

    trace = dict(record.get("reasoning_provenance", {}))
    actor = dict(trace.get("actor", {}))
    action = dict(trace.get("final_action", {}))
    lifecycle = dict(trace.get("lifecycle", {}))
    attestation = dict(trace.get("attestation", {}))
    steps = trace.get("reasoning_steps", [])
    policy_basis = trace.get("policy_basis", [])
    principal = actor.get("principal_id")
    authority_scope = actor.get("authority_scope", [])
    resource = action.get("resource")
    trace_valid = bool(trace.get("schema_validated", False))

    principal_authority = "opaque"
    if _present(principal) and _present(authority_scope):
        principal_authority = "complete"
    elif _present(principal):
        principal_authority = "partial"

    verification_strength = "opaque"
    if bool(attestation.get("signature_valid", False)):
        verification_strength = "complete"
    elif _present(attestation.get("trace_hash")):
        verification_strength = "partial"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="aer",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"reasoning_provenance": trace},
        container_flags={
            "trace_present": bool(steps),
            "ledger_present": bool(attestation.get("signature_valid", False)),
            "schema_valid": trace_valid,
            "checklist_complete": bool(policy_basis),
            "source_validator_passed": trace_valid,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(actor.get("agent_id")) else "opaque",
                source="aer_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="aer_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete" if _present(action.get("name")) and _present(resource) else "opaque",
                source="aer_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_basis) else "opaque",
                source="aer_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                "complete" if _present(steps) and _present(trace.get("conclusion")) else "partial",
                source="aer_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(resource) else "opaque",
                source="aer_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(lifecycle.get("started_at")) and _present(lifecycle.get("completed_at"))
                else "partial",
                source="aer_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                verification_strength,
                source="aer_adapter",
            ),
        ),
        metadata={
            "adapter": "aer",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
