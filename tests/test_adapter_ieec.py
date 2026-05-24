import json
from pathlib import Path

from decision_evidence_benchmark.adapters.ieec import from_native_record


def test_ieec_adapter_marks_valid_chain_but_policy_missing() -> None:
    record = json.loads(Path("data/cases/ieec/missing_policy_001.native.json").read_text())
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "ieec"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["ledger_present"] is False
    assert case.container_flags["source_validator_passed"] is True
    assert labels["actor_identity"] == "complete"
    assert labels["principal_authority"] == "partial"
    assert labels["policy_basis"] == "opaque"
    assert labels["decision_basis"] == "complete"
    assert labels["verification_strength"] == "partial"


def test_ieec_adapter_marks_authority_complete_when_scope_present() -> None:
    record = json.loads(Path("data/cases/ieec/missing_policy_001.native.json").read_text())
    record["intent_execution_chain"]["actor"]["authority_scope"] = ["comment:write"]

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "complete"
