from dataclasses import replace
from pathlib import Path

from decision_evidence_benchmark.evaluation import (
    CANDIDATE_SCORER_METRIC_CONTRACT,
    SCORER_OUTPUT_VALIDATION_CONTRACT,
    evaluate_scorer_outputs,
    validate_scorer_outputs,
)
from decision_evidence_benchmark.io import read_cases_jsonl, read_scorer_outputs_jsonl
from decision_evidence_benchmark.schema import ScorerOutput


def test_candidate_scorer_evaluation_on_smoke_fixture() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    outputs = read_scorer_outputs_jsonl(Path("data/fixtures/smoke_scorer_outputs.jsonl"))

    evaluation = evaluate_scorer_outputs(cases, outputs)
    summary = evaluation["summary"]

    assert summary["valid"] is True
    assert summary["metric_contract"] == CANDIDATE_SCORER_METRIC_CONTRACT
    assert summary["scorers"]["decision_trace_reconstructor"]["overclaim_rate"] == 0.0
    assert summary["scorers"]["decision_trace_reconstructor"]["cases"] == 8
    assert summary["scorers"]["decision_trace_reconstructor"]["fixture_statuses"] == {
        "smoke_only": 8
    }
    assert (
        summary["scorers"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert summary["slices"]["question_family"]["policy_basis"][
        "decision_trace_reconstructor"
    ]["fixture_statuses"] == {"smoke_only": 8}
    assert (
        summary["slices"]["regime"]["prov"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["llm_audit_trails"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["dcc_hdp"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["aer"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["mat"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["ieec"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["aegis_ntc"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )
    assert (
        summary["slices"]["regime"]["dynamic_capabilities"]["decision_trace_reconstructor"][
            "mean_property_sufficiency_accuracy"
        ]
        == 1.0
    )


def test_validate_scorer_outputs_requires_complete_case_and_property_coverage() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    outputs = read_scorer_outputs_jsonl(Path("data/fixtures/smoke_scorer_outputs.jsonl"))

    validation = validate_scorer_outputs(cases, outputs)

    assert validation["valid"] is True
    assert validation["metric_contract"] == SCORER_OUTPUT_VALIDATION_CONTRACT
    assert validation["case_count"] == 8
    assert validation["scorers"]["decision_trace_reconstructor"]["known_cases"] == 8

    incomplete_output = ScorerOutput(
        case_id=outputs[0].case_id,
        scorer=outputs[0].scorer,
        verdict=outputs[0].verdict,
        metadata=outputs[0].metadata,
        property_predictions=outputs[0].property_predictions[:-1],
    )
    invalid = validate_scorer_outputs(cases, [incomplete_output, *outputs[1:-1]])

    assert invalid["valid"] is False
    assert any(
        issue["issue"] == "missing_property_predictions" for issue in invalid["issues"]
    )
    assert any(issue["issue"] == "missing_scorer_case" for issue in invalid["issues"])


def test_validate_scorer_outputs_rejects_duplicate_property_predictions() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    outputs = read_scorer_outputs_jsonl(Path("data/fixtures/smoke_scorer_outputs.jsonl"))
    first = outputs[0]
    duplicated = ScorerOutput(
        case_id=first.case_id,
        scorer=first.scorer,
        verdict=first.verdict,
        metadata=first.metadata,
        property_predictions=(
            *first.property_predictions,
            replace(first.property_predictions[0]),
        ),
    )

    validation = validate_scorer_outputs(cases, [duplicated, *outputs[1:]])

    assert validation["valid"] is False
    assert any(
        issue["issue"] == "duplicate_property_predictions"
        for issue in validation["issues"]
    )
