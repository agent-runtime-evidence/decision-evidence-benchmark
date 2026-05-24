import json
from pathlib import Path

from decision_evidence_benchmark.adapters.llm_audit_trails import from_native_record


def test_llm_audit_trails_adapter_marks_missing_policy_and_weak_verification() -> None:
    record = json.loads(
        Path("data/cases/llm_audit_trails/missing_policy_001.native.json").read_text()
    )
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "llm_audit_trails"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["ledger_present"] is False
    assert case.container_flags["source_validator_passed"] is False
    assert labels["actor_identity"] == "complete"
    assert labels["principal_authority"] == "partial"
    assert labels["policy_basis"] == "opaque"
    assert labels["verification_strength"] == "opaque"


def test_llm_audit_trails_adapter_marks_authority_complete_when_scope_present() -> None:
    record = json.loads(
        Path("data/cases/llm_audit_trails/missing_policy_001.native.json").read_text()
    )
    record["audit_trail"]["actor"]["authority_scope"] = ["comment:write"]

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "complete"
