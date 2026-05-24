"""Regression tests pinning paper24 §7 headline numbers.

The deterministic manuscript package at
`data/cases/manuscript_cases.jsonl` is folded against the construction-oracle
ground truth and the five default container-presence baselines plus the
redacted property-rule candidate scorer at
`data/scorers/decision_trace_reconstructor_outputs.jsonl`. The numbers
asserted here are the headline values reported in paper24 §7 and in the
README's Compute Requirements block. They must reproduce bit-exactly across
the supported Python versions; any drift indicates either a label change, a
baseline change, or a scorer change and must be reviewed before publication.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from decision_evidence_benchmark.baselines import run_baseline
from decision_evidence_benchmark.evaluation import evaluate_scorer_outputs
from decision_evidence_benchmark.io import read_cases_jsonl, read_scorer_outputs_jsonl
from decision_evidence_benchmark.labels import calibration_summary, read_annotations_jsonl
from decision_evidence_benchmark.metrics.overclaim import result_row, summarize_outputs
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

MANUSCRIPT_CASES_PATH = Path("data/cases/manuscript_cases.jsonl")
MANUSCRIPT_UNADJUDICATED_CASES_PATH = Path("data/cases/manuscript_cases.unadjudicated.jsonl")
MANUSCRIPT_ANNOTATIONS_PATH = Path("data/annotations/manuscript_annotations.jsonl")
MANUSCRIPT_SCORER_OUTPUTS_PATH = Path("data/scorers/decision_trace_reconstructor_outputs.jsonl")

DEFAULT_BASELINES = (
    "trace_present",
    "ledger_present",
    "schema_present",
    "container_checklist",
    "source_specific_validator",
)


def test_manuscript_case_count_and_axis_balance_match_paper_section_7() -> None:
    """64 cases, 8 cases per regime, per condition, per question family."""

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)

    assert len(cases) == 64

    assert Counter(case.regime for case in cases) == {
        "aegis_ntc": 8,
        "aer": 8,
        "dcc_hdp": 8,
        "dynamic_capabilities": 8,
        "ieec": 8,
        "llm_audit_trails": 8,
        "mat": 8,
        "prov": 8,
    }
    assert Counter(case.degradation_condition for case in cases) == {
        "artifact_only": 8,
        "complete": 8,
        "conflicting_identity": 8,
        "final_only": 8,
        "missing_context": 8,
        "missing_delegation": 8,
        "missing_policy": 8,
        "partial_graph": 8,
    }
    assert Counter(case.question_family for case in cases) == {
        "action_boundary": 8,
        "actor_identity": 8,
        "data_resource_touch": 8,
        "decision_basis": 8,
        "lifecycle_context": 8,
        "policy_basis": 8,
        "principal_authority": 8,
        "verification_strength": 8,
    }


def test_manuscript_strict_sufficient_distribution_matches_paper_section_7() -> None:
    """Exactly the 8 complete-condition cases are strictly sufficient."""

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)

    sufficient_case_ids = {
        case.case_id for case in cases if case.ground_truth_sufficient(strict=True)
    }
    complete_case_ids = {
        case.case_id for case in cases if case.degradation_condition == "complete"
    }
    assert sufficient_case_ids == complete_case_ids
    assert len(sufficient_case_ids) == 8

    insufficient_case_ids = {
        case.case_id for case in cases if not case.ground_truth_sufficient(strict=True)
    }
    assert len(insufficient_case_ids) == 56


def test_manuscript_paired_property_label_count_is_512() -> None:
    """64 cases x 8 property families = 512 paired property labels."""

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)
    total_labels = sum(len(case.property_labels) for case in cases)
    assert total_labels == 64 * len(DECISION_EVENT_PROPERTIES)
    assert total_labels == 512


def test_manuscript_property_label_category_distribution_matches_paper_section_7() -> None:
    """Per-property label counts pin paper24 §7 fixed-distribution language.

    `verification_strength`: 32 complete / 24 partial / 8 opaque.
    `actor_identity`: 48 complete / 8 conflicting / 8 opaque.
    Other families round out the 512-label denominator.
    """

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)
    per_property: dict[str, Counter[str]] = {
        property_name: Counter() for property_name in DECISION_EVENT_PROPERTIES
    }
    for case in cases:
        for label in case.property_labels:
            per_property[label.property][label.category] += 1

    assert per_property["actor_identity"] == Counter(
        {"complete": 48, "conflicting": 8, "opaque": 8}
    )
    assert per_property["principal_authority"] == Counter(
        {"complete": 40, "conflicting": 8, "opaque": 16}
    )
    assert per_property["action_boundary"] == Counter({"complete": 56, "opaque": 8})
    assert per_property["policy_basis"] == Counter(
        {"complete": 40, "opaque": 16, "partial": 8}
    )
    assert per_property["decision_basis"] == Counter(
        {"complete": 40, "partial": 16, "opaque": 8}
    )
    assert per_property["data_resource_touch"] == Counter({"complete": 56, "opaque": 8})
    assert per_property["lifecycle_context"] == Counter(
        {"complete": 40, "opaque": 16, "partial": 8}
    )
    assert per_property["verification_strength"] == Counter(
        {"complete": 32, "partial": 24, "opaque": 8}
    )


def test_manuscript_default_baselines_match_paper_section_7_headline_overclaim() -> None:
    """Five default baselines reproduce paper24 §7 Overclaim Rate headline."""

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)
    expected: dict[str, dict[str, float | int]] = {
        "trace_present": {
            "overclaim_rate": 0.75,
            "overclaim_cases": 48,
            "sufficient_cases": 56,
        },
        "schema_present": {
            "overclaim_rate": 0.75,
            "overclaim_cases": 48,
            "sufficient_cases": 56,
        },
        "ledger_present": {
            "overclaim_rate": 0.50,
            "overclaim_cases": 32,
            "sufficient_cases": 40,
        },
        "container_checklist": {
            "overclaim_rate": 0.00,
            "overclaim_cases": 0,
            "sufficient_cases": 8,
        },
        "source_specific_validator": {
            "overclaim_rate": 0.00,
            "overclaim_cases": 0,
            "sufficient_cases": 8,
        },
    }

    for name in DEFAULT_BASELINES:
        outputs = [run_baseline(name, case) for case in cases]
        rows = [
            result_row(case, output, strict=True)
            for case, output in zip(cases, outputs, strict=True)
        ]
        summary = summarize_outputs(rows)["scorers"][name]

        assert summary["cases"] == 64, name
        assert summary["verdict_cases"] == 64, name
        assert summary["overclaim_rate"] == expected[name]["overclaim_rate"], name
        assert summary["overclaim_cases"] == expected[name]["overclaim_cases"], name
        assert summary["sufficient_cases"] == expected[name]["sufficient_cases"], name


def test_manuscript_candidate_scorer_matches_paper_section_7_headline() -> None:
    """Redacted property-rule candidate scorer reproduces paper24 §7 headline.

    Mean Property Sufficiency Accuracy 0.5625, zero overclaim cases,
    Overclaim Rate 0.00 over all 64 cases.
    """

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)
    scorer_outputs = read_scorer_outputs_jsonl(MANUSCRIPT_SCORER_OUTPUTS_PATH)
    assert len(scorer_outputs) == 64

    evaluation = evaluate_scorer_outputs(cases, scorer_outputs, strict=True)
    scorer_summary = evaluation["summary"]["scorers"]["decision_trace_reconstructor"]

    assert scorer_summary["cases"] == 64
    assert scorer_summary["mean_property_sufficiency_accuracy"] == 0.5625
    assert scorer_summary["overclaim_rate"] == 0.0
    assert scorer_summary["overclaim_cases"] == 0


def test_manuscript_candidate_scorer_per_degradation_psa_matches_paper_table_3() -> None:
    """Per-degradation PSA reproduces paper24 §7 Table 3 exactly."""

    cases = read_cases_jsonl(MANUSCRIPT_CASES_PATH)
    scorer_outputs = read_scorer_outputs_jsonl(MANUSCRIPT_SCORER_OUTPUTS_PATH)
    evaluation = evaluate_scorer_outputs(cases, scorer_outputs, strict=True)

    expected_psa_by_condition: dict[str, float] = {
        "complete": 1.000,
        "final_only": 0.875,
        "artifact_only": 0.750,
        "missing_delegation": 0.500,
        "missing_context": 0.375,
        "missing_policy": 0.375,
        "partial_graph": 0.375,
        "conflicting_identity": 0.250,
    }
    by_condition = evaluation["summary"]["slices"]["degradation_condition"]
    for condition, expected_psa in expected_psa_by_condition.items():
        scorer_slice = by_condition[condition]["decision_trace_reconstructor"]
        assert scorer_slice["mean_property_sufficiency_accuracy"] == expected_psa, condition


def test_manuscript_paired_oracle_kappa_is_one_overall_and_per_property() -> None:
    """Paired-oracle Cohen kappa is exactly 1.0 overall and per property family.

    This is rule-reproducibility (paper24 §7 T3), not human inter-rater
    agreement: the construction-oracle is deterministic by design.
    """

    cases = read_cases_jsonl(MANUSCRIPT_UNADJUDICATED_CASES_PATH)
    annotations = read_annotations_jsonl(MANUSCRIPT_ANNOTATIONS_PATH)
    summary = calibration_summary(cases, annotations)

    assert summary["valid"] is True
    assert summary["paired_case_count"] == 64
    assert summary["paired_label_count"] == 512
    assert summary["overall"]["cohen_kappa"] == 1.0

    for property_name in DECISION_EVENT_PROPERTIES:
        property_metrics = summary["properties"][property_name]
        assert property_metrics["labels"] == 64, property_name
        assert property_metrics["cohen_kappa"] == 1.0, property_name
