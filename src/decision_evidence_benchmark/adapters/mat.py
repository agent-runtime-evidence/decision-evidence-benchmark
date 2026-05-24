"""MAT contract-trace native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native MAT contract-trace record into the case manifest."""

    contract_trace = dict(record.get("contract_trace", {}))
    actor = dict(contract_trace.get("actor", {}))
    action = dict(contract_trace.get("action", {}))
    contract = dict(contract_trace.get("contract", {}))
    lifecycle = dict(contract_trace.get("lifecycle", {}))
    validator = dict(contract_trace.get("validator", {}))
    policy_basis = contract_trace.get("policy_basis", [])
    obligations = contract.get("obligations", [])
    resource = action.get("resource")
    contract_passed = bool(validator.get("contract_passed", False))

    principal_authority = "opaque"
    if _present(actor.get("principal_id")) and _present(actor.get("authority_scope")):
        principal_authority = "complete"
    elif _present(actor.get("principal_id")):
        principal_authority = "partial"

    decision_basis = "partial"
    if _present(contract.get("contract_id")) and _present(obligations):
        decision_basis = "complete"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="mat",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"contract_trace": contract_trace},
        container_flags={
            "trace_present": bool(contract_trace),
            "ledger_present": bool(validator.get("signature_valid", False)),
            "schema_valid": bool(contract_trace.get("schema_validated", False)),
            "checklist_complete": bool(policy_basis),
            "source_validator_passed": contract_passed,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(actor.get("agent_id")) else "opaque",
                source="mat_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="mat_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete" if _present(action.get("name")) and _present(resource) else "opaque",
                source="mat_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_basis) else "opaque",
                source="mat_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis,
                source="mat_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(resource) else "opaque",
                source="mat_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(lifecycle.get("started_at")) and _present(lifecycle.get("completed_at"))
                else "partial",
                source="mat_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                "complete" if bool(validator.get("signature_valid", False)) else "partial",
                source="mat_adapter",
            ),
        ),
        metadata={
            "adapter": "mat",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
