from decision_evidence_benchmark.metrics import property_sufficiency_accuracy
from decision_evidence_benchmark.schema import PropertyLabel


def test_property_sufficiency_accuracy() -> None:
    truth = (
        PropertyLabel(property="policy_basis", category="opaque"),
        PropertyLabel(property="actor_identity", category="complete"),
    )
    predicted = (
        PropertyLabel(property="policy_basis", category="complete"),
        PropertyLabel(property="actor_identity", category="complete"),
    )

    result = property_sufficiency_accuracy(truth, predicted)

    assert result["correct"] == 1
    assert result["total"] == 2
    assert result["accuracy"] == 0.5

