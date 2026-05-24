"""PROV native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def _first(values: object) -> dict[str, Any]:
    if isinstance(values, list) and values and isinstance(values[0], dict):
        return dict(values[0])
    return {}


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native PROV-style record into the benchmark case manifest."""

    bundle = dict(record.get("prov_bundle", {}))
    activity = _first(bundle.get("activities"))
    association = _first(bundle.get("wasAssociatedWith"))
    usage = _first(bundle.get("used"))
    signature = _first(bundle.get("signatures"))
    policy_basis = bundle.get("policy_basis", [])
    principal = association.get("principal") or association.get("delegate")
    role = association.get("role")
    used_entity = usage.get("entity")
    action = activity.get("action") or activity.get("type")
    rationale = activity.get("rationale") or bundle.get("decision_rationale")
    signature_valid = bool(signature.get("valid", False))

    principal_authority = "opaque"
    if _present(principal) and _present(role):
        principal_authority = "complete"
    elif _present(role):
        principal_authority = "partial"

    decision_basis = "opaque"
    if _present(rationale):
        decision_basis = "complete"
    elif _present(activity):
        decision_basis = "partial"

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="prov",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={"prov_bundle": bundle},
        container_flags={
            "trace_present": bool(bundle),
            "ledger_present": False,
            "schema_valid": True,
            "checklist_complete": bool(policy_basis),
            "source_validator_passed": signature_valid,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                "complete" if _present(association.get("agent")) else "opaque",
                source="prov_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="prov_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                "complete" if _present(action) and _present(used_entity) else "opaque",
                source="prov_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                "complete" if _present(policy_basis) else "opaque",
                source="prov_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis,
                source="prov_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                "complete" if _present(used_entity) else "opaque",
                source="prov_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(activity.get("started_at")) and _present(activity.get("ended_at"))
                else "partial",
                source="prov_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                "complete" if signature_valid else "opaque",
                source="prov_adapter",
            ),
        ),
        metadata={
            "adapter": "prov",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
