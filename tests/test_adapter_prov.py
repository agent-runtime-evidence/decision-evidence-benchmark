import json
from pathlib import Path

from decision_evidence_benchmark.adapters.prov import from_native_record


def test_prov_adapter_marks_missing_policy_basis() -> None:
    record = json.loads(Path("data/cases/prov/missing_policy_001.native.json").read_text())
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "prov"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["ledger_present"] is False
    assert case.container_flags["checklist_complete"] is False
    assert labels["actor_identity"] == "complete"
    assert labels["principal_authority"] == "partial"
    assert labels["policy_basis"] == "opaque"
    assert labels["decision_basis"] == "partial"


def test_prov_adapter_marks_principal_authority_complete_when_principal_present() -> None:
    record = json.loads(Path("data/cases/prov/missing_policy_001.native.json").read_text())
    record["prov_bundle"]["wasAssociatedWith"][0]["principal"] = "human:reviewer"

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "complete"
