import json
from pathlib import Path

from decision_evidence_benchmark.artifacts import build_run_manifest
from decision_evidence_benchmark.baselines import BASELINE_REGISTRY
from decision_evidence_benchmark.evaluation import CANDIDATE_SCORER_METRIC_CONTRACT
from decision_evidence_benchmark.metrics.overclaim import OVERCLAIM_SUMMARY_METRIC_CONTRACT
from decision_evidence_benchmark.readiness import build_readiness_report
from decision_evidence_benchmark.readiness_gaps import build_readiness_gap_report
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES


def _candidate_scorer_summary(scorers: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "metric_contract": CANDIDATE_SCORER_METRIC_CONTRACT,
        "valid": True,
        "scorers": scorers,
    }


def _baseline_summary(scorers: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "metric_contract": OVERCLAIM_SUMMARY_METRIC_CONTRACT,
        "scorers": scorers,
    }


def _balanced_property_category_counts() -> dict[str, dict[str, int]]:
    return {
        property_name: {"complete": 1, "opaque": 1}
        for property_name in DECISION_EVENT_PROPERTIES
    }


def _label_property_metrics(
    *,
    cohen_kappa: float = 1.0,
    overrides: dict[str, float] | None = None,
) -> dict[str, dict[str, float | int]]:
    values = {
        property_name: {
            "agreement_rate": 1.0,
            "cohen_kappa": cohen_kappa,
            "labels": 2,
        }
        for property_name in DECISION_EVENT_PROPERTIES
    }
    for property_name, property_kappa in (overrides or {}).items():
        values[property_name]["cohen_kappa"] = property_kappa
    return values


def test_readiness_gap_report_classifies_blocking_reasons() -> None:
    report = {
        "metric_contract": "decision_evidence_result_readiness",
        "mechanics_valid": True,
        "manuscript_result_ready": False,
        "blocking_reasons": [
            (
                "corpus_claim_status=smoke_only_not_empirical_evidence!="
                "required_corpus_claim_status=manuscript_result_candidate"
            ),
            "label_calibration_status=draft_two_annotator_fixture",
            "missing_candidate_scorers=decision_trace_reconstructor",
            "disallowed_baseline_implementation_statuses=llm_judge:fixture_placeholder",
        ],
    }

    gap_report = build_readiness_gap_report(report)

    assert gap_report["valid"] is True
    assert gap_report["blocker_count"] == 4
    assert gap_report["artifact_area_counts"] == {
        "baselines": 1,
        "candidate_scorer": 1,
        "corpus": 1,
        "labels": 1,
    }
    assert [blocker["reason"] for blocker in gap_report["blockers"]] == report[
        "blocking_reasons"
    ]
    assert gap_report["blockers"][0]["category"] == "corpus_claim_status"
    assert gap_report["blockers"][1]["artifact_area"] == "labels"
    assert gap_report["blockers"][2]["category"] == "missing_candidate_scorers"


def test_smoke_readiness_distinguishes_mechanics_from_result_readiness(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "smoke_only_not_empirical_evidence",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 8,
                },
                "question_family_counts": {
                    "policy_basis": 8,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=8,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "corpus_claim_status=smoke_only_not_empirical_evidence!="
        "required_corpus_claim_status=manuscript_result_candidate"
    ) in report["blocking_reasons"]
    assert (
        "run_claim_status=mechanical_run_only!=required_run_claim_status="
        "manuscript_result_candidate"
    ) in report["blocking_reasons"]
    assert not any(reason.startswith("regime_count=") for reason in report["blocking_reasons"])
    assert (
        "degradation_condition_count=1<min_degradation_conditions=8"
        in report["blocking_reasons"]
    )
    assert "question_family_count=1<min_question_families=8" in report["blocking_reasons"]


def test_readiness_marks_corrupt_run_manifest_invalid(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 1,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 1,
                },
                "question_family_counts": {
                    "policy_basis": 1,
                },
                "regime_counts": {"dcc_hdp": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 1,
                "paired_case_count": 1,
                "paired_label_count": 8,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 1}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 1}})))
    run_manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_kind": "decision_evidence_benchmark_run",
                "claim_status": "mechanical_run_only",
                "inputs": [],
                "outputs": [],
            }
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_degradation_conditions=1,
        min_question_families=1,
    )

    assert report["mechanics_valid"] is False
    assert report["components"]["run_manifest"]["valid"] is False
    assert report["components"]["run_manifest"]["issues"]


def test_readiness_requires_run_manifest_to_reference_supporting_artifacts(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 8,
                },
                "question_family_counts": {
                    "policy_basis": 8,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output,),
                case_count=8,
                baselines=("trace_present",),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_degradation_conditions=1,
        min_question_families=1,
    )

    assert report["mechanics_valid"] is False
    assert any(
        issue["issue"] == "missing_expected_artifact_path"
        for issue in report["components"]["run_manifest"]["issues"]
    )


def test_readiness_rejects_cross_artifact_case_count_mismatch(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 8,
                },
                "question_family_counts": {
                    "policy_basis": 8,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 63,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=8,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_degradation_conditions=1,
        min_question_families=1,
    )

    assert report["mechanics_valid"] is False
    assert report["components"]["cross_artifact_consistency"]["valid"] is False
    assert any(
        issue["issue"] == "label_calibration_paired_label_count_mismatch"
        for issue in report["components"]["cross_artifact_consistency"]["issues"]
    )


def test_readiness_rejects_metric_contract_mismatch(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 1,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 1,
                },
                "question_family_counts": {
                    "policy_basis": 1,
                },
                "regime_counts": {"dcc_hdp": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 1,
                "paired_case_count": 1,
                "paired_label_count": 8,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(
        json.dumps(
            {
                "metric_contract": "wrong_contract",
                "valid": True,
                "scorers": {"candidate": {"cases": 1}},
            }
        )
    )
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 1}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=1,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=1,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=1,
        min_cases_per_degradation_condition=1,
        min_cases_per_question_family=1,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is False
    assert any(
        issue["issue"] == "metric_contract_mismatch" and issue["summary"] == "scorer_summary"
        for issue in report["components"]["cross_artifact_consistency"]["issues"]
    )


def test_readiness_blocks_non_manuscript_corpus_claim_status(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 2,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {"missing_policy": 2},
                "question_family_counts": {"policy_basis": 2},
                "regime_counts": {"dcc_hdp": 2},
                "property_category_counts": _balanced_property_category_counts(),
                "strict_sufficiency_counts": {"sufficient": 1, "insufficient": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 2,
                "paired_case_count": 2,
                "paired_label_count": 16,
                "overall": {"cohen_kappa": 1.0},
                "properties": _label_property_metrics(),
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 2}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 2}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=2,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=2,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=2,
        min_cases_per_degradation_condition=2,
        min_cases_per_question_family=2,
        min_strict_sufficient_cases=1,
        min_strict_insufficient_cases=1,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "corpus_claim_status=test_only!=required_corpus_claim_status="
        "manuscript_result_candidate"
    ) in report["blocking_reasons"]


def test_readiness_blocks_smoke_label_calibration_status(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "manuscript_result_candidate",
                "case_count": 2,
                "label_contract": {
                    "calibration_status": "smoke_two_annotator_fixture",
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {"missing_policy": 2},
                "question_family_counts": {"policy_basis": 2},
                "regime_counts": {"dcc_hdp": 2},
                "property_category_counts": _balanced_property_category_counts(),
                "strict_sufficiency_counts": {"sufficient": 1, "insufficient": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 2,
                "paired_case_count": 2,
                "paired_label_count": 16,
                "overall": {"cohen_kappa": 1.0},
                "properties": _label_property_metrics(),
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 2}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 2}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=2,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=2,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=2,
        min_cases_per_degradation_condition=2,
        min_cases_per_question_family=2,
        min_strict_sufficient_cases=1,
        min_strict_insufficient_cases=1,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "label_calibration_status=smoke_two_annotator_fixture" in report[
        "blocking_reasons"
    ]


def test_readiness_blocks_low_property_label_calibration_kappa(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "manuscript_result_candidate",
                "case_count": 2,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {"missing_policy": 2},
                "question_family_counts": {"policy_basis": 2},
                "regime_counts": {"dcc_hdp": 2},
                "property_category_counts": _balanced_property_category_counts(),
                "strict_sufficiency_counts": {"sufficient": 1, "insufficient": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 2,
                "paired_case_count": 2,
                "paired_label_count": 16,
                "overall": {"cohen_kappa": 1.0},
                "properties": _label_property_metrics(overrides={"policy_basis": 0.59}),
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 2}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 2}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=2,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=2,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=2,
        min_cases_per_degradation_condition=2,
        min_cases_per_question_family=2,
        min_strict_sufficient_cases=1,
        min_strict_insufficient_cases=1,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "label_property_cohen_kappa_below_min=policy_basis:0.59<"
        "min_label_property_cohen_kappa=0.6"
    ) in report["blocking_reasons"]


def test_readiness_blocks_placeholder_baseline_implementation_status(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 1,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 1,
                },
                "question_family_counts": {
                    "policy_basis": 1,
                },
                "regime_counts": {"dcc_hdp": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 1,
                "paired_case_count": 1,
                "paired_label_count": 8,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 1}})))
    baseline.write_text(
        json.dumps(
            _baseline_summary(
                {
                    "llm_judge": {
                        "cases": 1,
                        "implementation_statuses": {"fixture_placeholder": 1},
                    }
                }
            )
        )
    )
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=1,
        baselines=("llm_judge",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=1,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=1,
        min_cases_per_degradation_condition=1,
        min_cases_per_question_family=1,
        required_baselines=("llm_judge",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "disallowed_baseline_implementation_statuses=llm_judge:fixture_placeholder"
        in report["blocking_reasons"]
    )


def test_readiness_blocks_candidate_fixture_status(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 1,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 1,
                },
                "question_family_counts": {
                    "policy_basis": 1,
                },
                "regime_counts": {"dcc_hdp": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 1,
                "paired_case_count": 1,
                "paired_label_count": 8,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(
        json.dumps(
            _candidate_scorer_summary(
                {
                    "decision_trace_reconstructor": {
                        "cases": 1,
                        "fixture_statuses": {"smoke_only": 1},
                    }
                }
            )
        )
    )
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 1}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=1,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=1,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=1,
        min_cases_per_degradation_condition=1,
        min_cases_per_question_family=1,
        required_baselines=("trace_present",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "disallowed_candidate_fixture_statuses=decision_trace_reconstructor:smoke_only"
        in report["blocking_reasons"]
    )


def test_readiness_blocks_when_degradation_condition_coverage_is_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 8,
                },
                "question_family_counts": {
                    "policy_basis": 8,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=8,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_question_families=1,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "degradation_condition_count=1<min_degradation_conditions=8"
        in report["blocking_reasons"]
    )


def test_readiness_blocks_when_question_family_coverage_is_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 8,
                },
                "question_family_counts": {
                    "policy_basis": 8,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=8,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_degradation_conditions=1,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "question_family_count=1<min_question_families=8" in report["blocking_reasons"]


def test_readiness_blocks_when_label_calibration_kappa_is_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "complete": 1,
                    "conflicting_identity": 1,
                    "final_only": 1,
                    "artifact_only": 1,
                    "missing_context": 1,
                    "missing_delegation": 1,
                    "missing_policy": 1,
                    "partial_graph": 1,
                },
                "question_family_counts": {
                    "action_boundary": 1,
                    "actor_identity": 1,
                    "data_resource_touch": 1,
                    "decision_basis": 1,
                    "lifecycle_context": 1,
                    "policy_basis": 1,
                    "principal_authority": 1,
                    "verification_strength": 1,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 0.59},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(run_output, baseline),
                case_count=8,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "label_cohen_kappa=0.59<min_label_cohen_kappa=0.6" in report["blocking_reasons"]


def test_readiness_blocks_when_case_and_slice_counts_are_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "complete": 1,
                    "conflicting_identity": 1,
                    "final_only": 1,
                    "artifact_only": 1,
                    "missing_context": 1,
                    "missing_delegation": 1,
                    "missing_policy": 1,
                    "partial_graph": 1,
                },
                "question_family_counts": {
                    "action_boundary": 1,
                    "actor_identity": 1,
                    "data_resource_touch": 1,
                    "decision_basis": 1,
                    "lifecycle_context": 1,
                    "policy_basis": 1,
                    "principal_authority": 1,
                    "verification_strength": 1,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(
        json.dumps(
            _candidate_scorer_summary({"decision_trace_reconstructor": {"cases": 8}})
        )
    )
    baseline.write_text(
        json.dumps(_baseline_summary({name: {"cases": 8} for name in BASELINE_REGISTRY}))
    )
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=8,
        baselines=tuple(sorted(BASELINE_REGISTRY)),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "case_count=8<min_cases=64" in report["blocking_reasons"]
    assert any(
        reason.startswith("regime_case_counts_below_min=")
        for reason in report["blocking_reasons"]
    )
    assert any(
        reason.startswith("degradation_condition_case_counts_below_min=")
        for reason in report["blocking_reasons"]
    )
    assert any(
        reason.startswith("question_family_case_counts_below_min=")
        for reason in report["blocking_reasons"]
    )


def test_readiness_blocks_when_strict_sufficient_cases_are_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 16,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 16,
                },
                "question_family_counts": {
                    "policy_basis": 16,
                },
                "regime_counts": {"dcc_hdp": 16},
                "strict_sufficiency_counts": {
                    "sufficient": 0,
                    "insufficient": 16,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 16,
                "paired_case_count": 16,
                "paired_label_count": 128,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 16}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 16}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=16,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=16,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=16,
        min_cases_per_degradation_condition=16,
        min_cases_per_question_family=16,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert "strict_sufficient_cases=0<min_strict_sufficient_cases=8" in report[
        "blocking_reasons"
    ]
    assert report["observed"]["strict_sufficiency_counts"] == {
        "sufficient": 0,
        "insufficient": 16,
    }


def test_readiness_blocks_when_property_category_balance_is_low(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"
    property_category_counts = {
        property_name: {"complete": 1, "opaque": 1}
        for property_name in DECISION_EVENT_PROPERTIES
    }
    property_category_counts["actor_identity"] = {"complete": 2}
    property_category_counts["policy_basis"] = {"opaque": 2}

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 2,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 2,
                },
                "question_family_counts": {
                    "policy_basis": 2,
                },
                "regime_counts": {"dcc_hdp": 2},
                "property_category_counts": property_category_counts,
                "strict_sufficiency_counts": {
                    "sufficient": 1,
                    "insufficient": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 2,
                "paired_case_count": 2,
                "paired_label_count": 16,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 2}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 2}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=2,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
        min_cases=2,
        min_regimes=1,
        min_degradation_conditions=1,
        min_question_families=1,
        min_cases_per_regime=2,
        min_cases_per_degradation_condition=2,
        min_cases_per_question_family=2,
        min_strict_sufficient_cases=1,
        min_strict_insufficient_cases=1,
        required_baselines=("trace_present",),
        required_candidate_scorers=("candidate",),
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert any(
        reason.startswith("property_complete_counts_below_min=policy_basis:0")
        for reason in report["blocking_reasons"]
    )
    assert any(
        reason.startswith("property_non_complete_counts_below_min=actor_identity:0")
        for reason in report["blocking_reasons"]
    )


def test_readiness_blocks_when_required_scorers_are_missing(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    cases = tmp_path / "cases.jsonl"
    run_output = tmp_path / "results.jsonl"

    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "test_only",
                "case_count": 8,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "complete": 1,
                    "conflicting_identity": 1,
                    "final_only": 1,
                    "artifact_only": 1,
                    "missing_context": 1,
                    "missing_delegation": 1,
                    "missing_policy": 1,
                    "partial_graph": 1,
                },
                "question_family_counts": {
                    "action_boundary": 1,
                    "actor_identity": 1,
                    "data_resource_touch": 1,
                    "decision_basis": 1,
                    "lifecycle_context": 1,
                    "policy_basis": 1,
                    "principal_authority": 1,
                    "verification_strength": 1,
                },
                "regime_counts": {
                    "aegis_ntc": 1,
                    "aer": 1,
                    "dcc_hdp": 1,
                    "dynamic_capabilities": 1,
                    "ieec": 1,
                    "llm_audit_trails": 1,
                    "mat": 1,
                    "prov": 1,
                },
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 8,
                "paired_case_count": 8,
                "paired_label_count": 64,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(json.dumps(_candidate_scorer_summary({"candidate": {"cases": 8}})))
    baseline.write_text(json.dumps(_baseline_summary({"trace_present": {"cases": 8}})))
    cases.write_text('{"case_id":"a"}\n')
    run_output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(run_output, baseline),
        case_count=8,
        baselines=("trace_present",),
        supporting_input_paths=(corpus, calibration, scorer),
    )
    manifest["claim_status"] = "manuscript_result_candidate"
    run_manifest.write_text(json.dumps(manifest))

    report = build_readiness_report(
        corpus_validation_path=corpus,
        label_calibration_path=calibration,
        scorer_summary_path=scorer,
        baseline_summary_path=baseline,
        run_manifest_path=run_manifest,
    )

    assert report["mechanics_valid"] is True
    assert report["manuscript_result_ready"] is False
    assert (
        "missing_baselines=container_checklist,ledger_present,llm_judge,"
        "schema_present,source_specific_validator"
    ) in report["blocking_reasons"]
    assert "missing_candidate_scorers=decision_trace_reconstructor" in report[
        "blocking_reasons"
    ]
