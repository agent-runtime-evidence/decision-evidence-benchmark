import json
from pathlib import Path

from decision_evidence_benchmark.adapters.aegis_ntc import from_native_record


def test_aegis_ntc_adapter_marks_firewall_passed_but_policy_missing() -> None:
    record = json.loads(Path("data/cases/aegis_ntc/missing_policy_001.native.json").read_text())
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "aegis_ntc"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["ledger_present"] is False
    assert case.container_flags["source_validator_passed"] is True
    assert labels["actor_identity"] == "complete"
    assert labels["principal_authority"] == "partial"
    assert labels["action_boundary"] == "complete"
    assert labels["policy_basis"] == "opaque"
    assert labels["decision_basis"] == "complete"
    assert labels["verification_strength"] == "partial"


def test_aegis_ntc_adapter_marks_authority_complete_when_scope_present() -> None:
    record = json.loads(Path("data/cases/aegis_ntc/missing_policy_001.native.json").read_text())
    record["tool_firewall_decision"]["actor"]["authority_scope"] = ["comment:write"]

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "complete"
