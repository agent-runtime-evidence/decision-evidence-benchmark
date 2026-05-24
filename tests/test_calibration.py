from pathlib import Path

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.labels import calibration_summary, read_annotations_jsonl


def test_smoke_label_calibration_is_valid() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))

    summary = calibration_summary(cases, annotations)

    assert summary["valid"] is True
    assert summary["paired_case_count"] == 8
    assert summary["paired_label_count"] == 64
    assert summary["overall"]["agreement_rate"] == 1.0
    assert summary["overall"]["cohen_kappa"] == 1.0


def test_label_calibration_rejects_missing_pair() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))[:1]

    summary = calibration_summary(cases, annotations)

    assert summary["valid"] is False
    assert any(issue["issue"] == "expected_exactly_two_annotators" for issue in summary["issues"])
