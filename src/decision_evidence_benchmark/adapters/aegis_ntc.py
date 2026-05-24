"""AEGIS-NTC tool-firewall native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native AEGIS-NTC record into the case manifest."""

    firewall = dict(record.get("tool_firewall_decision", {}))
    actor = dict(firewall.get("actor", {}))
    tool_call = dict(firewall.get("tool_call", {}))
    decision = dict(firewall.get("decision", {}))
    lifecycle = dict(firewall.get("lifecycle", {}))
    validation = dict(firewall.get("validation", {}))
    policy_basis = firewall.get("policy_basis", [])
    resource = tool_call.get("resource")
    firewall_passed = bool(validation.get("firewall_decision_logged", False)) and bool(
        validation.get("ruleset_validated", False)
    )

    principal_authority = "opaque"
    if _present(actor.get("principal_id")) and _present(actor.get("authority_scope")):
        principal_authority = "complete"
    elif _present(actor.get("principal_id")):
        principal_authority = "partial"

    decision_basis = "partial"
    if _present(tool_call) and _present(decision.get("outcome")) and _present(
        decision.get("reason")
    ):
        decision_basis = "complete"

    verification_strength = "opaque"
    if bool(validation.get("signature_valid", False)):
        verification_strength = "complete"
    elif _present(validation.get("decision_hash")):
        verification_strength = "partial"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="aegis_ntc",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"tool_firewall_decision": firewall},
        container_flags={
            "trace_present": bool(decision or tool_call),
            "ledger_present": bool(validation.get("signature_valid", False)),
            "schema_valid": bool(firewall.get("schema_validated", False)),
            "checklist_complete": bool(policy_basis),
            "source_validator_passed": firewall_passed,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(actor.get("agent_id")) else "opaque",
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete"
                if _present(tool_call.get("name")) and _present(resource)
                else "opaque",
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_basis) else "opaque",
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis,
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(resource) else "opaque",
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(lifecycle.get("observed_at")) and _present(lifecycle.get("decided_at"))
                else "partial",
                source="aegis_ntc_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                verification_strength,
                source="aegis_ntc_adapter",
            ),
        ),
        metadata={
            "adapter": "aegis_ntc",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
