"""DCC/HDP native evidence adapter."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, PropertyLabel


def _present(value: object) -> bool:
    return value is not None and value != "" and value != []


def _category_from_presence(value: object) -> str:
    return "complete" if _present(value) else "opaque"


def from_native_record(record: dict[str, Any]) -> CaseManifest:
    """Convert one native DCC/HDP record into the benchmark case manifest."""

    token = dict(record.get("dcc_token", {}))
    session = dict(record.get("hdp_session", {}))
    action = dict(record.get("executed_action", {}))
    policy_constraints = token.get("policy_constraints", [])
    signature_valid = bool(token.get("signature_valid", False))
    principal = token.get("principal_id") or session.get("approver_id")
    decision_basis = record.get("decision_basis") or token.get("intent")
    action_boundary = "opaque"
    if _present(action.get("action")) and _present(action.get("resource")):
        action_boundary = "complete"
    principal_authority = "opaque"
    if _present(principal) and _present(token.get("authority_scope")):
        principal_authority = "complete"
    elif _present(principal):
        principal_authority = "partial"
    decision_basis_category = (
        "partial"
        if _present(decision_basis) and not policy_constraints
        else _category_from_presence(decision_basis)
    )

    return CaseManifest(
        case_id=str(record["record_id"]),
        regime="dcc_hdp",
        question_family=str(record.get("question_family", "policy_basis")),
        degradation_condition=str(record.get("degradation_condition", "none")),
        evidence={
            "dcc_token": token,
            "hdp_session": session,
            "executed_action": action,
        },
        container_flags={
            "trace_present": bool(token or session),
            "ledger_present": bool(token.get("parent_hash") or signature_valid),
            "schema_valid": True,
            "checklist_complete": bool(policy_constraints),
            "source_validator_passed": signature_valid,
            "llm_judge_verdict": str(record.get("llm_judge_verdict", "sufficient")),
        },
        property_labels=(
            PropertyLabel(
                "actor_identity",
                _category_from_presence(token.get("agent_id")),
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "principal_authority",
                principal_authority,
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "action_boundary",
                action_boundary,
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "policy_basis",
                _category_from_presence(policy_constraints),
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "decision_basis",
                decision_basis_category,
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "data_resource_touch",
                _category_from_presence(action.get("resource")),
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "lifecycle_context",
                "complete"
                if _present(token.get("expiry")) and _present(session.get("delegated_at"))
                else "partial",
                source="dcc_hdp_adapter",
            ),
            PropertyLabel(
                "verification_strength",
                "complete" if signature_valid else "opaque",
                source="dcc_hdp_adapter",
            ),
        ),
        metadata={
            "adapter": "dcc_hdp",
            "native_record_id": str(record["record_id"]),
            "fixture_status": str(record.get("fixture_status", "adapter_generated")),
        },
    )
