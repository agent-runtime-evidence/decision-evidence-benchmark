import json
from pathlib import Path

from decision_evidence_benchmark.adapters.aer import from_native_record


def test_aer_adapter_marks_reasoning_present_but_policy_missing() -> None:
    record = json.loads(Path("data/cases/aer/missing_policy_001.native.json").read_text())
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "aer"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["ledger_present"] is False
    assert case.container_flags["source_validator_passed"] is True
    assert labels["actor_identity"] == "complete"
    assert labels["principal_authority"] == "opaque"
    assert labels["policy_basis"] == "opaque"
    assert labels["decision_basis"] == "complete"
    assert labels["verification_strength"] == "partial"


def test_aer_adapter_marks_principal_authority_complete_when_scope_present() -> None:
    record = json.loads(Path("data/cases/aer/missing_policy_001.native.json").read_text())
    record["reasoning_provenance"]["actor"]["principal_id"] = "human.reviewer"
    record["reasoning_provenance"]["actor"]["authority_scope"] = ["comment:write"]

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "complete"
