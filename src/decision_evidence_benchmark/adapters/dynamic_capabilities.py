"""Dynamic Capabilities replay native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native Dynamic Capabilities replay record into the case manifest."""

    replay = dict(record.get("capability_replay", {}))
    actor = dict(replay.get("actor", {}))
    capability = dict(replay.get("capability", {}))
    replay_run = dict(replay.get("replay_run", {}))
    lifecycle = dict(replay.get("lifecycle", {}))
    validation = dict(replay.get("validation", {}))
    policy_basis = replay.get("policy_basis", [])
    resource = capability.get("resource")
    replay_attested = bool(validation.get("replay_attested", False)) and bool(
        validation.get("capability_graph_validated", False)
    )

    principal_authority = "opaque"
    if _present(actor.get("principal_id")) and _present(actor.get("authority_scope")):
        principal_authority = "complete"
    elif _present(actor.get("principal_id")):
        principal_authority = "partial"

    decision_basis = "partial"
    if _present(capability.get("name")) and _present(replay_run.get("decision_outcome")):
        decision_basis = "complete"

    verification_strength = "opaque"
    if bool(validation.get("signature_valid", False)):
        verification_strength = "complete"
    elif _present(validation.get("replay_hash")):
        verification_strength = "partial"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="dynamic_capabilities",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"capability_replay": replay},
        container_flags={
            "trace_present": bool(capability or replay_run),
            "ledger_present": bool(validation.get("signature_valid", False)),
            "schema_valid": bool(replay.get("schema_validated", False)),
            "checklist_complete": bool(policy_basis),
            "source_validator_passed": replay_attested,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(actor.get("agent_id")) else "opaque",
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete"
                if _present(capability.get("name")) and _present(resource)
                else "opaque",
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_basis) else "opaque",
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis,
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(resource) else "opaque",
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(lifecycle.get("recorded_at")) and _present(lifecycle.get("replayed_at"))
                else "partial",
                source="dynamic_capabilities_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                verification_strength,
                source="dynamic_capabilities_adapter",
            ),
        ),
        metadata={
            "adapter": "dynamic_capabilities",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
