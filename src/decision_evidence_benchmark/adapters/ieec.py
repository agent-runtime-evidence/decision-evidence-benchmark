"""IEEC intent-to-execution native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native IEEC record into the case manifest."""

    chain = dict(record.get("intent_execution_chain", {}))
    intent = dict(chain.get("intent", {}))
    actor = dict(chain.get("actor", {}))
    plan = dict(chain.get("plan", {}))
    execution = dict(chain.get("execution", {}))
    validation = dict(chain.get("validation", {}))
    policy_binding = chain.get("policy_binding", [])
    resource = execution.get("resource")
    chain_valid = bool(validation.get("chain_valid", False))

    principal_authority = "opaque"
    if _present(actor.get("principal_id")) and _present(actor.get("authority_scope")):
        principal_authority = "complete"
    elif _present(actor.get("principal_id")):
        principal_authority = "partial"

    decision_basis = "partial"
    if _present(intent.get("objective")) and _present(plan.get("steps")) and _present(execution):
        decision_basis = "complete"

    verification_strength = "opaque"
    if bool(validation.get("signature_valid", False)):
        verification_strength = "complete"
    elif _present(validation.get("chain_hash")):
        verification_strength = "partial"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="ieec",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"intent_execution_chain": chain},
        container_flags={
            "trace_present": bool(intent or execution),
            "ledger_present": bool(validation.get("signature_valid", False)),
            "schema_valid": bool(chain.get("schema_validated", False)),
            "checklist_complete": bool(policy_binding),
            "source_validator_passed": chain_valid,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(actor.get("agent_id")) else "opaque",
                source="ieec_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="ieec_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete"
                if _present(execution.get("action")) and _present(resource)
                else "opaque",
                source="ieec_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_binding) else "opaque",
                source="ieec_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis,
                source="ieec_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(resource) else "opaque",
                source="ieec_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(intent.get("created_at")) and _present(execution.get("completed_at"))
                else "partial",
                source="ieec_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                verification_strength,
                source="ieec_adapter",
            ),
        ),
        metadata={
            "adapter": "ieec",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
