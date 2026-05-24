import json
from pathlib import Path

from decision_evidence_benchmark.adapters.dcc_hdp import from_native_record


def test_dcc_hdp_adapter_marks_missing_policy_basis() -> None:
    record = json.loads(Path("data/cases/dcc_hdp/missing_policy_001.native.json").read_text())
    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert case.regime == "dcc_hdp"
    assert case.container_flags["trace_present"] is True
    assert case.container_flags["checklist_complete"] is False
    assert labels["policy_basis"] == "opaque"
    assert labels["decision_basis"] == "partial"
    assert labels["verification_strength"] == "complete"


def test_dcc_hdp_adapter_requires_authority_scope_for_complete_authority() -> None:
    record = json.loads(Path("data/cases/dcc_hdp/missing_policy_001.native.json").read_text())
    record["dcc_token"]["authority_scope"] = []

    case = from_native_record(record)
    labels = {label.property: label.category for label in case.property_labels}

    assert labels["principal_authority"] == "partial"
