import pytest

from decision_evidence_benchmark.construction_oracle import (
    CONSTRUCTION_ORACLE_LABEL_SOURCE,
    DEFAULT_ORACLE_SPEC_PATH,
    categories_for_degradation,
    labels_for_degradation,
    load_oracle_spec,
    oracle_spec_sha256,
    verdict_for_labels,
)
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES


def test_default_oracle_spec_is_machine_readable_and_hashed() -> None:
    spec = load_oracle_spec(DEFAULT_ORACLE_SPEC_PATH)

    assert spec.oracle_version == "construction_oracle_v1"
    assert spec.properties == DECISION_EVENT_PROPERTIES
    assert set(spec.degradation_conditions) == {
        "complete",
        "missing_delegation",
        "missing_policy",
        "missing_context",
        "conflicting_identity",
        "partial_graph",
        "final_only",
        "artifact_only",
    }
    assert len(oracle_spec_sha256(DEFAULT_ORACLE_SPEC_PATH)) == 64


def test_categories_for_degradation_returns_complete_vector_with_rule_overrides() -> None:
    categories = categories_for_degradation("artifact_only")

    assert set(categories) == set(DECISION_EVENT_PROPERTIES)
    assert categories["actor_identity"] == "opaque"
    assert categories["action_boundary"] == "opaque"
    assert categories["policy_basis"] == "partial"
    assert categories["data_resource_touch"] == "opaque"
    assert categories["principal_authority"] == "complete"


def test_construction_oracle_verdicts_follow_strict_sufficiency() -> None:
    complete_labels = labels_for_degradation("complete")
    missing_policy_labels = labels_for_degradation("missing_policy")

    assert all(label.source == CONSTRUCTION_ORACLE_LABEL_SOURCE for label in complete_labels)
    assert verdict_for_labels(complete_labels) == "sufficient"
    assert verdict_for_labels(missing_policy_labels) == "insufficient"


def test_unknown_degradation_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown degradation condition"):
        categories_for_degradation("not_a_condition")
