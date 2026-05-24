import json
from pathlib import Path

from decision_evidence_benchmark.artifacts import build_run_manifest
from decision_evidence_benchmark.baselines import BASELINE_REGISTRY, run_baseline
from decision_evidence_benchmark.corpus import validate_corpus_manifest
from decision_evidence_benchmark.evaluation import evaluate_scorer_outputs
from decision_evidence_benchmark.generation import (
    DEGRADATION_CONDITIONS,
    DRAFT_CASE_FIXTURE_STATUS,
    DRAFT_CLAIM_STATUS,
    DRAFT_LABEL_CALIBRATION_STATUS,
    DRAFT_SCORER_FIXTURE_STATUS,
    QUESTION_FAMILIES,
    draft_scorer_outputs,
    generate_balanced_draft_cases,
    write_draft_corpus_artifacts,
)
from decision_evidence_benchmark.io import read_cases_jsonl, read_scorer_outputs_jsonl
from decision_evidence_benchmark.labels import calibration_summary, read_annotations_jsonl
from decision_evidence_benchmark.metrics.overclaim import result_row, summarize_outputs
from decision_evidence_benchmark.readiness import build_readiness_report
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES


def test_generate_balanced_draft_cases_meets_slice_and_label_balance() -> None:
    cases = generate_balanced_draft_cases()

    assert len(cases) == 64
    assert {case.regime for case in cases} == {
        "aegis_ntc",
        "aer",
        "dcc_hdp",
        "dynamic_capabilities",
        "ieec",
        "llm_audit_trails",
        "mat",
        "prov",
    }
    assert {case.degradation_condition for case in cases} == set(DEGRADATION_CONDITIONS)
    assert {case.question_family for case in cases} == set(QUESTION_FAMILIES)
    assert sum(case.ground_truth_sufficient() for case in cases) == 8
    assert sum(not case.ground_truth_sufficient() for case in cases) == 56
    assert all(case.metadata["fixture_status"] == DRAFT_CASE_FIXTURE_STATUS for case in cases)

    for property_name in DECISION_EVENT_PROPERTIES:
        categories = {
            label.category
            for case in cases
            for label in case.property_labels
            if label.property == property_name
        }
        assert "complete" in categories
        assert categories - {"complete"}


def test_write_draft_corpus_artifacts_round_trips_and_validates(tmp_path: Path) -> None:
    paths = write_draft_corpus_artifacts(
        cases_path=tmp_path / "cases.jsonl",
        annotations_path=tmp_path / "annotations.jsonl",
        scorer_outputs_path=tmp_path / "scorer_outputs.jsonl",
        manifest_path=tmp_path / "corpus.yaml",
    )

    corpus = validate_corpus_manifest(paths.manifest)
    cases = read_cases_jsonl(paths.cases)
    annotations = read_annotations_jsonl(paths.annotations)
    calibration = calibration_summary(cases, annotations)
    scorer_outputs = read_scorer_outputs_jsonl(paths.scorer_outputs)
    scorer_evaluation = evaluate_scorer_outputs(cases, scorer_outputs)

    assert corpus["valid"] is True
    assert corpus["claim_status"] == DRAFT_CLAIM_STATUS
    assert corpus["case_count"] == 64
    assert min(corpus["regime_counts"].values()) == 8
    assert min(corpus["degradation_condition_counts"].values()) == 8
    assert min(corpus["question_family_counts"].values()) == 8
    assert corpus["strict_sufficiency_counts"] == {"insufficient": 56, "sufficient": 8}
    assert corpus["label_contract"]["calibration_status"] == DRAFT_LABEL_CALIBRATION_STATUS
    assert calibration["valid"] is True
    assert calibration["paired_case_count"] == 64
    assert calibration["overall"]["cohen_kappa"] == 1.0
    assert scorer_evaluation["summary"]["valid"] is True
    assert scorer_evaluation["summary"]["scorers"]["decision_trace_reconstructor"][
        "fixture_statuses"
    ] == {DRAFT_SCORER_FIXTURE_STATUS: 64}


def test_readiness_blocks_generated_draft_statuses(tmp_path: Path) -> None:
    paths = write_draft_corpus_artifacts(
        cases_path=tmp_path / "cases.jsonl",
        annotations_path=tmp_path / "annotations.jsonl",
        scorer_outputs_path=tmp_path / "scorer_outputs.jsonl",
        manifest_path=tmp_path / "corpus.yaml",
    )
    cases = read_cases_jsonl(paths.cases)
    corpus_validation = validate_corpus_manifest(paths.manifest)
    calibration = calibration_summary(cases, read_annotations_jsonl(paths.annotations))
    scorer_evaluation = evaluate_scorer_outputs(cases, draft_scorer_outputs(cases))

    baseline_rows = [
        result_row(case, run_baseline(baseline, case))
        for case in cases
        for baseline in sorted(BASELINE_REGISTRY)
    ]
    baseline_summary = summarize_outputs(baseline_rows)

    corpus_path = tmp_path / "corpus_validation.json"
    calibration_path = tmp_path / "calibration.json"
    scorer_summary_path = tmp_path / "scorer_summary.json"
    baseline_summary_path = tmp_path / "baseline_summary.json"
    baseline_results_path = tmp_path / "baseline_results.jsonl"
    run_manifest_path = tmp_path / "run_manifest.json"
    corpus_path.write_text(json.dumps(corpus_validation))
    calibration_path.write_text(json.dumps(calibration))
    scorer_summary_path.write_text(json.dumps(scorer_evaluation["summary"]))
    baseline_summary_path.write_text(json.dumps(baseline_summary))
    baseline_results_path.write_text("{}\n")
    run_manifest = build_run_manifest(
        cases_path=paths.cases,
        output_paths=(baseline_results_path, baseline_summary_path),
        case_count=len(cases),
        baselines=tuple(sorted(BASELINE_REGISTRY)),
        supporting_input_paths=(corpus_path, calibration_path, scorer_summary_path),
        claim_status="manuscript_result_candidate",
    )
    run_manifest_path.write_text(json.dumps(run_manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus_path,
        label_calibration_path=calibration_path,
        scorer_summary_path=scorer_summary_path,
        baseline_summary_path=baseline_summary_path,
        run_manifest_path=run_manifest_path,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "label_calibration_status=draft_two_annotator_fixture" in report[
        "blocking_reasons"
    ]
    assert (
        "disallowed_candidate_fixture_statuses="
        "decision_trace_reconstructor:draft_synthetic_oracle"
    ) in report["blocking_reasons"]
    assert any(
        reason.startswith(
            "disallowed_baseline_implementation_statuses=llm_judge:fixture_placeholder"
        )
        for reason in report["blocking_reasons"]
    )
