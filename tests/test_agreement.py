from pytest import approx, raises

from decision_evidence_benchmark.labels import cohen_kappa


def test_cohen_kappa_nominal_labels() -> None:
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "a", "b", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == approx(0.5)


def test_cohen_kappa_rejects_bad_inputs() -> None:
    with raises(ValueError):
        cohen_kappa(["a"], ["a", "b"])

