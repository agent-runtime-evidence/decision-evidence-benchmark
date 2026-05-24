"""Result readiness report assembly."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.artifacts import validate_run_manifest
from decision_evidence_benchmark.baselines import (
    BASELINE_OUTPUT_VALIDATION_CONTRACT,
    BASELINE_REGISTRY,
)
from decision_evidence_benchmark.evaluation import (
    CANDIDATE_SCORER_METRIC_CONTRACT,
    SCORER_OUTPUT_VALIDATION_CONTRACT,
)
from decision_evidence_benchmark.labels import (
    ADJUDICATION_REPORT_METRIC_CONTRACT,
    LABEL_REVIEW_METRIC_CONTRACT,
)
from decision_evidence_benchmark.metrics.overclaim import OVERCLAIM_SUMMARY_METRIC_CONTRACT

DEFAULT_REQUIRED_CANDIDATE_SCORERS = ("decision_trace_reconstructor",)
DEFAULT_DISALLOWED_BASELINE_IMPLEMENTATION_STATUSES = ("fixture_placeholder",)
DEFAULT_DISALLOWED_CANDIDATE_FIXTURE_STATUSES = (
    "draft_synthetic_oracle",
    "smoke_only",
)
DEFAULT_REQUIRED_CORPUS_CLAIM_STATUS = "manuscript_result_candidate"
DEFAULT_REQUIRED_RUN_CLAIM_STATUS = "manuscript_result_candidate"
DEFAULT_DISALLOWED_LABEL_CALIBRATION_STATUSES = (
    "draft_two_annotator_fixture",
    "smoke_two_annotator_fixture",
)


def build_readiness_report(
    *,
    corpus_validation_path: Path,
    label_calibration_path: Path,
    label_review_path: Path | None = None,
    label_adjudication_path: Path | None = None,
    scorer_validation_path: Path | None = None,
    scorer_summary_path: Path,
    baseline_validation_path: Path | None = None,
    baseline_summary_path: Path,
    run_manifest_path: Path,
    min_cases: int = 64,
    min_regimes: int = 8,
    min_degradation_conditions: int = 8,
    min_question_families: int = 8,
    min_cases_per_regime: int = 8,
    min_cases_per_degradation_condition: int = 8,
    min_cases_per_question_family: int = 8,
    min_strict_sufficient_cases: int = 8,
    min_strict_insufficient_cases: int = 8,
    min_complete_labels_per_property: int = 1,
    min_non_complete_labels_per_property: int = 1,
    min_label_cohen_kappa: float = 0.6,
    min_label_property_cohen_kappa: float = 0.6,
    required_corpus_claim_status: str = DEFAULT_REQUIRED_CORPUS_CLAIM_STATUS,
    required_run_claim_status: str = DEFAULT_REQUIRED_RUN_CLAIM_STATUS,
    required_baselines: Sequence[str] | None = None,
    required_candidate_scorers: Sequence[str] | None = None,
    disallowed_baseline_implementation_statuses: Sequence[str] | None = None,
    disallowed_candidate_fixture_statuses: Sequence[str] | None = None,
    disallowed_label_calibration_statuses: Sequence[str] | None = None,
) -> dict[str, Any]:
    required_baseline_names = _normalized_names(
        required_baselines,
        default=BASELINE_REGISTRY,
    )
    required_candidate_scorer_names = _normalized_names(
        required_candidate_scorers,
        default=DEFAULT_REQUIRED_CANDIDATE_SCORERS,
    )
    disallowed_baseline_status_names = _normalized_names(
        disallowed_baseline_implementation_statuses,
        default=DEFAULT_DISALLOWED_BASELINE_IMPLEMENTATION_STATUSES,
    )
    disallowed_candidate_fixture_status_names = _normalized_names(
        disallowed_candidate_fixture_statuses,
        default=DEFAULT_DISALLOWED_CANDIDATE_FIXTURE_STATUSES,
    )
    disallowed_label_calibration_status_names = _normalized_names(
        disallowed_label_calibration_statuses,
        default=DEFAULT_DISALLOWED_LABEL_CALIBRATION_STATUSES,
    )
    corpus_validation = _read_json(corpus_validation_path)
    label_calibration = _read_json(label_calibration_path)
    label_review = _read_json(label_review_path) if label_review_path else None
    label_adjudication = (
        _read_json(label_adjudication_path) if label_adjudication_path else None
    )
    scorer_validation = _read_json(scorer_validation_path) if scorer_validation_path else None
    scorer_summary = _read_json(scorer_summary_path)
    baseline_validation = (
        _read_json(baseline_validation_path) if baseline_validation_path else None
    )
    baseline_summary = _read_json(baseline_summary_path)
    run_manifest = _read_json(run_manifest_path)
    run_manifest_validation = validate_run_manifest(
        run_manifest,
        expected_input_paths=(
            corpus_validation_path,
            label_calibration_path,
            *((label_review_path,) if label_review_path else ()),
            *((label_adjudication_path,) if label_adjudication_path else ()),
            *((scorer_validation_path,) if scorer_validation_path else ()),
            scorer_summary_path,
            *((baseline_validation_path,) if baseline_validation_path else ()),
        ),
        expected_output_paths=(baseline_summary_path,),
    )
    consistency_issues = _consistency_issues(
        corpus_validation=corpus_validation,
        label_calibration=label_calibration,
        label_review=label_review,
        label_adjudication=label_adjudication,
        scorer_validation=scorer_validation,
        scorer_summary=scorer_summary,
        baseline_validation=baseline_validation,
        baseline_summary=baseline_summary,
        run_manifest=run_manifest,
    )

    components = {
        "corpus_validation": _component(corpus_validation_path, corpus_validation.get("valid")),
        "label_calibration": _component(label_calibration_path, label_calibration.get("valid")),
        **(
            {
                "label_review": _component(
                    label_review_path,
                    label_review.get("valid") if label_review else False,
                )
            }
            if label_review_path
            else {}
        ),
        **(
            {
                "label_adjudication": _component(
                    label_adjudication_path,
                    label_adjudication.get("valid") if label_adjudication else False,
                )
            }
            if label_adjudication_path
            else {}
        ),
        **(
            {
                "scorer_validation": _component(
                    scorer_validation_path,
                    scorer_validation.get("valid") if scorer_validation else False,
                )
            }
            if scorer_validation_path
            else {}
        ),
        "scorer_summary": _component(scorer_summary_path, scorer_summary.get("valid", True)),
        **(
            {
                "baseline_validation": _component(
                    baseline_validation_path,
                    baseline_validation.get("valid") if baseline_validation else False,
                )
            }
            if baseline_validation_path
            else {}
        ),
        "baseline_summary": _component(baseline_summary_path, True),
        "run_manifest": _component(
            run_manifest_path,
            run_manifest_validation["valid"],
            issues=run_manifest_validation["issues"],
        ),
        "cross_artifact_consistency": _virtual_component(
            not consistency_issues,
            issues=consistency_issues,
        ),
    }
    mechanics_valid = all(bool(component["valid"]) for component in components.values())
    blocking_reasons = _blocking_reasons(
        corpus_validation=corpus_validation,
        label_calibration=label_calibration,
        scorer_summary=scorer_summary,
        baseline_summary=baseline_summary,
        run_manifest=run_manifest,
        min_cases=min_cases,
        min_regimes=min_regimes,
        min_degradation_conditions=min_degradation_conditions,
        min_question_families=min_question_families,
        min_cases_per_regime=min_cases_per_regime,
        min_cases_per_degradation_condition=min_cases_per_degradation_condition,
        min_cases_per_question_family=min_cases_per_question_family,
        min_strict_sufficient_cases=min_strict_sufficient_cases,
        min_strict_insufficient_cases=min_strict_insufficient_cases,
        min_complete_labels_per_property=min_complete_labels_per_property,
        min_non_complete_labels_per_property=min_non_complete_labels_per_property,
        min_label_cohen_kappa=min_label_cohen_kappa,
        min_label_property_cohen_kappa=min_label_property_cohen_kappa,
        required_corpus_claim_status=required_corpus_claim_status,
        required_run_claim_status=required_run_claim_status,
        required_baselines=required_baseline_names,
        required_candidate_scorers=required_candidate_scorer_names,
        disallowed_baseline_implementation_statuses=disallowed_baseline_status_names,
        disallowed_candidate_fixture_statuses=disallowed_candidate_fixture_status_names,
        disallowed_label_calibration_statuses=disallowed_label_calibration_status_names,
    )

    return {
        "metric_contract": "decision_evidence_result_readiness",
        "readiness_policy": {
            "required_corpus_claim_status": required_corpus_claim_status,
            "required_run_claim_status": required_run_claim_status,
            "min_cases": min_cases,
            "min_regimes": min_regimes,
            "min_degradation_conditions": min_degradation_conditions,
            "min_question_families": min_question_families,
            "min_cases_per_regime": min_cases_per_regime,
            "min_cases_per_degradation_condition": min_cases_per_degradation_condition,
            "min_cases_per_question_family": min_cases_per_question_family,
            "min_strict_sufficient_cases": min_strict_sufficient_cases,
            "min_strict_insufficient_cases": min_strict_insufficient_cases,
            "min_complete_labels_per_property": min_complete_labels_per_property,
            "min_non_complete_labels_per_property": min_non_complete_labels_per_property,
            "min_label_cohen_kappa": min_label_cohen_kappa,
            "min_label_property_cohen_kappa": min_label_property_cohen_kappa,
            "required_baselines": list(required_baseline_names),
            "required_candidate_scorers": list(required_candidate_scorer_names),
            "disallowed_baseline_implementation_statuses": list(
                disallowed_baseline_status_names
            ),
            "disallowed_candidate_fixture_statuses": list(
                disallowed_candidate_fixture_status_names
            ),
            "disallowed_label_calibration_statuses": list(
                disallowed_label_calibration_status_names
            ),
        },
        "components": components,
        "observed": {
            "baseline_metric_contract": baseline_summary.get("metric_contract"),
            "baseline_validation_metric_contract": (
                baseline_validation.get("metric_contract") if baseline_validation else None
            ),
            "baseline_implementation_statuses": _scorer_implementation_statuses(
                baseline_summary.get("scorers", {})
            ),
            "candidate_metric_contract": scorer_summary.get("metric_contract"),
            "scorer_validation_metric_contract": (
                scorer_validation.get("metric_contract") if scorer_validation else None
            ),
            "candidate_fixture_statuses": _scorer_statuses(
                scorer_summary.get("scorers", {}),
                "fixture_statuses",
            ),
            "corpus_claim_status": corpus_validation.get("claim_status"),
            "run_claim_status": run_manifest.get("claim_status"),
            "label_calibration_status": corpus_validation.get("label_contract", {}).get(
                "calibration_status"
            ),
            "case_count": corpus_validation.get("case_count"),
            "regime_count": len(corpus_validation.get("regime_counts", {})),
            "regime_case_count_min": _min_count(corpus_validation.get("regime_counts", {})),
            "degradation_condition_count": len(
                corpus_validation.get("degradation_condition_counts", {})
            ),
            "degradation_condition_case_count_min": _min_count(
                corpus_validation.get("degradation_condition_counts", {})
            ),
            "question_family_count": len(corpus_validation.get("question_family_counts", {})),
            "question_family_case_count_min": _min_count(
                corpus_validation.get("question_family_counts", {})
            ),
            "strict_sufficiency_counts": corpus_validation.get("strict_sufficiency_counts", {}),
            "property_category_counts": corpus_validation.get("property_category_counts", {}),
            "baseline_scorers": sorted(baseline_summary.get("scorers", {})),
            "candidate_scorers": sorted(scorer_summary.get("scorers", {})),
            "paired_label_count": label_calibration.get("paired_label_count"),
            "label_review_property_row_count": (
                label_review.get("property_row_count") if label_review else None
            ),
            "label_review_disagreed_property_count": (
                label_review.get("disagreed_property_count") if label_review else None
            ),
            "label_adjudication_unresolved_label_count": (
                label_adjudication.get("unresolved_label_count")
                if label_adjudication
                else None
            ),
            "label_adjudication_override_label_count": (
                label_adjudication.get("override_label_count") if label_adjudication else None
            ),
            "label_cohen_kappa": label_calibration.get("overall", {}).get("cohen_kappa"),
            "label_property_cohen_kappas": _label_property_cohen_kappas(
                label_calibration.get("properties", {})
            ),
        },
        "mechanics_valid": mechanics_valid,
        "manuscript_result_ready": mechanics_valid and not blocking_reasons,
        "blocking_reasons": blocking_reasons,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _normalized_names(
    names: Sequence[str] | None,
    *,
    default: Iterable[str],
) -> tuple[str, ...]:
    source = default if names is None else names
    return tuple(sorted(str(name) for name in source))


def _component(
    path: Path,
    valid: object,
    *,
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    component = {
        "path": str(path),
        "valid": bool(valid),
    }
    if issues:
        component["issues"] = issues
    return component


def _virtual_component(
    valid: object,
    *,
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    component: dict[str, Any] = {"valid": bool(valid)}
    if issues:
        component["issues"] = issues
    return component


def _consistency_issues(
    *,
    corpus_validation: dict[str, Any],
    label_calibration: dict[str, Any],
    label_review: dict[str, Any] | None,
    label_adjudication: dict[str, Any] | None,
    scorer_validation: dict[str, Any] | None,
    scorer_summary: dict[str, Any],
    baseline_validation: dict[str, Any] | None,
    baseline_summary: dict[str, Any],
    run_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    corpus_case_count = _int_value(corpus_validation.get("case_count"))
    if corpus_case_count is None:
        return [
            {
                "severity": "error",
                "issue": "missing_corpus_case_count",
            }
        ]

    _require_metric_contract(
        issues,
        summary=scorer_summary,
        expected=CANDIDATE_SCORER_METRIC_CONTRACT,
        summary_name="scorer_summary",
    )
    if scorer_validation is not None:
        _require_metric_contract(
            issues,
            summary=scorer_validation,
            expected=SCORER_OUTPUT_VALIDATION_CONTRACT,
            summary_name="scorer_validation",
        )
    _require_metric_contract(
        issues,
        summary=baseline_summary,
        expected=OVERCLAIM_SUMMARY_METRIC_CONTRACT,
        summary_name="baseline_summary",
    )
    if baseline_validation is not None:
        _require_metric_contract(
            issues,
            summary=baseline_validation,
            expected=BASELINE_OUTPUT_VALIDATION_CONTRACT,
            summary_name="baseline_validation",
        )
    if label_review is not None:
        _require_metric_contract(
            issues,
            summary=label_review,
            expected=LABEL_REVIEW_METRIC_CONTRACT,
            summary_name="label_review",
        )
    if label_adjudication is not None:
        _require_metric_contract(
            issues,
            summary=label_adjudication,
            expected=ADJUDICATION_REPORT_METRIC_CONTRACT,
            summary_name="label_adjudication",
        )

    _require_equal_int(
        issues,
        actual=label_calibration.get("case_count"),
        expected=corpus_case_count,
        issue="label_calibration_case_count_mismatch",
    )
    _require_equal_int(
        issues,
        actual=label_calibration.get("paired_case_count"),
        expected=corpus_case_count,
        issue="label_calibration_paired_case_count_mismatch",
    )
    required_properties = corpus_validation.get("label_contract", {}).get(
        "required_properties",
        [],
    )
    if isinstance(required_properties, list):
        _require_equal_int(
            issues,
            actual=label_calibration.get("paired_label_count"),
            expected=corpus_case_count * len(required_properties),
            issue="label_calibration_paired_label_count_mismatch",
        )
        if label_review is not None:
            _require_equal_int(
                issues,
                actual=label_review.get("property_row_count"),
                expected=corpus_case_count * len(required_properties),
                issue="label_review_property_row_count_mismatch",
            )
        if label_adjudication is not None:
            _require_equal_int(
                issues,
                actual=label_adjudication.get("property_count"),
                expected=corpus_case_count * len(required_properties),
                issue="label_adjudication_property_count_mismatch",
            )
    if label_review is not None:
        _require_equal_int(
            issues,
            actual=label_review.get("case_count"),
            expected=corpus_case_count,
            issue="label_review_case_count_mismatch",
        )
    if label_adjudication is not None:
        _require_equal_int(
            issues,
            actual=label_adjudication.get("case_count"),
            expected=corpus_case_count,
            issue="label_adjudication_case_count_mismatch",
        )

    _require_equal_int(
        issues,
        actual=run_manifest.get("case_count"),
        expected=corpus_case_count,
        issue="run_manifest_case_count_mismatch",
    )
    _require_scorer_case_counts(
        issues,
        summary=scorer_summary,
        expected=corpus_case_count,
        summary_name="scorer_summary",
    )
    if scorer_validation is not None:
        _require_equal_int(
            issues,
            actual=scorer_validation.get("case_count"),
            expected=corpus_case_count,
            issue="scorer_validation_case_count_mismatch",
        )
    if baseline_validation is not None:
        _require_equal_int(
            issues,
            actual=baseline_validation.get("case_count"),
            expected=corpus_case_count,
            issue="baseline_validation_case_count_mismatch",
        )
    _require_scorer_case_counts(
        issues,
        summary=baseline_summary,
        expected=corpus_case_count,
        summary_name="baseline_summary",
    )

    run_baselines = sorted(str(item) for item in run_manifest.get("baselines", []))
    baseline_scorers = sorted(str(item) for item in baseline_summary.get("scorers", {}))
    if run_baselines != baseline_scorers:
        issues.append(
            {
                "severity": "error",
                "issue": "run_manifest_baselines_mismatch",
                "expected": baseline_scorers,
                "actual": run_baselines,
            }
        )
    return issues


def _require_metric_contract(
    issues: list[dict[str, Any]],
    *,
    summary: dict[str, Any],
    expected: str,
    summary_name: str,
) -> None:
    actual = summary.get("metric_contract")
    if actual != expected:
        issues.append(
            {
                "severity": "error",
                "issue": "metric_contract_mismatch",
                "summary": summary_name,
                "expected": expected,
                "actual": actual,
            }
        )


def _require_scorer_case_counts(
    issues: list[dict[str, Any]],
    *,
    summary: dict[str, Any],
    expected: int,
    summary_name: str,
) -> None:
    scorers = summary.get("scorers", {})
    if not isinstance(scorers, dict):
        issues.append(
            {
                "severity": "error",
                "issue": "scorers_not_mapping",
                "summary": summary_name,
            }
        )
        return
    for scorer_name, scorer_summary in scorers.items():
        if not isinstance(scorer_summary, dict):
            issues.append(
                {
                    "severity": "error",
                    "issue": "scorer_summary_not_mapping",
                    "summary": summary_name,
                    "scorer": str(scorer_name),
                }
            )
            continue
        _require_equal_int(
            issues,
            actual=scorer_summary.get("cases"),
            expected=expected,
            issue="scorer_case_count_mismatch",
            context={"summary": summary_name, "scorer": str(scorer_name)},
        )


def _require_equal_int(
    issues: list[dict[str, Any]],
    *,
    actual: object,
    expected: int,
    issue: str,
    context: dict[str, Any] | None = None,
) -> None:
    actual_int = _int_value(actual)
    if actual_int != expected:
        payload: dict[str, Any] = {
            "severity": "error",
            "issue": issue,
            "expected": expected,
            "actual": actual,
        }
        if context:
            payload.update(context)
        issues.append(payload)


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, int | str):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _min_count(counts: object) -> int | None:
    if not isinstance(counts, dict) or not counts:
        return None
    parsed_counts: list[int] = []
    for value in counts.values():
        parsed_count = _int_value(value)
        if parsed_count is None:
            return None
        parsed_counts.append(parsed_count)
    return min(parsed_counts)


def _float_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, int | float | str):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _label_property_cohen_kappas(properties: object) -> dict[str, float | None]:
    if not isinstance(properties, dict):
        return {}
    result: dict[str, float | None] = {}
    for property_name, metrics in sorted(properties.items()):
        if not isinstance(metrics, dict):
            result[str(property_name)] = None
            continue
        result[str(property_name)] = _float_value(metrics.get("cohen_kappa"))
    return result


def _blocking_reasons(
    *,
    corpus_validation: dict[str, Any],
    label_calibration: dict[str, Any],
    scorer_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
    run_manifest: dict[str, Any],
    min_cases: int,
    min_regimes: int,
    min_degradation_conditions: int,
    min_question_families: int,
    min_cases_per_regime: int,
    min_cases_per_degradation_condition: int,
    min_cases_per_question_family: int,
    min_strict_sufficient_cases: int,
    min_strict_insufficient_cases: int,
    min_complete_labels_per_property: int,
    min_non_complete_labels_per_property: int,
    min_label_cohen_kappa: float,
    min_label_property_cohen_kappa: float,
    required_corpus_claim_status: str,
    required_run_claim_status: str,
    required_baselines: Sequence[str],
    required_candidate_scorers: Sequence[str],
    disallowed_baseline_implementation_statuses: Sequence[str],
    disallowed_candidate_fixture_statuses: Sequence[str],
    disallowed_label_calibration_statuses: Sequence[str],
) -> list[str]:
    reasons: list[str] = []
    claim_status = str(corpus_validation.get("claim_status", ""))
    if claim_status != required_corpus_claim_status:
        reasons.append(
            f"corpus_claim_status={claim_status}!=required_corpus_claim_status="
            f"{required_corpus_claim_status}"
        )
    label_calibration_status = str(
        corpus_validation.get("label_contract", {}).get("calibration_status", "")
    )
    if label_calibration_status in set(disallowed_label_calibration_statuses):
        reasons.append(f"label_calibration_status={label_calibration_status}")
    run_claim_status = str(run_manifest.get("claim_status", ""))
    if run_claim_status != required_run_claim_status:
        reasons.append(
            f"run_claim_status={run_claim_status}!=required_run_claim_status="
            f"{required_run_claim_status}"
        )
    case_count = _int_value(corpus_validation.get("case_count"))
    if case_count is None or case_count < min_cases:
        actual = "missing" if case_count is None else case_count
        reasons.append(f"case_count={actual}<min_cases={min_cases}")
    regime_count = len(corpus_validation.get("regime_counts", {}))
    if regime_count < min_regimes:
        reasons.append(f"regime_count={regime_count}<min_regimes={min_regimes}")
    degradation_condition_count = len(corpus_validation.get("degradation_condition_counts", {}))
    if degradation_condition_count < min_degradation_conditions:
        reasons.append(
            "degradation_condition_count="
            f"{degradation_condition_count}<min_degradation_conditions="
            f"{min_degradation_conditions}"
        )
    question_family_count = len(corpus_validation.get("question_family_counts", {}))
    if question_family_count < min_question_families:
        reasons.append(
            f"question_family_count={question_family_count}<min_question_families="
            f"{min_question_families}"
        )
    _append_low_slice_count_reason(
        reasons,
        counts=corpus_validation.get("regime_counts", {}),
        reason_prefix="regime_case_counts_below_min",
        threshold_name="min_cases_per_regime",
        threshold=min_cases_per_regime,
    )
    _append_low_slice_count_reason(
        reasons,
        counts=corpus_validation.get("degradation_condition_counts", {}),
        reason_prefix="degradation_condition_case_counts_below_min",
        threshold_name="min_cases_per_degradation_condition",
        threshold=min_cases_per_degradation_condition,
    )
    _append_low_slice_count_reason(
        reasons,
        counts=corpus_validation.get("question_family_counts", {}),
        reason_prefix="question_family_case_counts_below_min",
        threshold_name="min_cases_per_question_family",
        threshold=min_cases_per_question_family,
    )
    strict_sufficiency_counts = corpus_validation.get("strict_sufficiency_counts", {})
    _append_low_count_reason(
        reasons,
        counts=strict_sufficiency_counts,
        count_name="sufficient",
        reason_name="strict_sufficient_cases",
        threshold_name="min_strict_sufficient_cases",
        threshold=min_strict_sufficient_cases,
    )
    _append_low_count_reason(
        reasons,
        counts=strict_sufficiency_counts,
        count_name="insufficient",
        reason_name="strict_insufficient_cases",
        threshold_name="min_strict_insufficient_cases",
        threshold=min_strict_insufficient_cases,
    )
    _append_low_property_category_balance_reasons(
        reasons,
        corpus_validation=corpus_validation,
        min_complete_labels_per_property=min_complete_labels_per_property,
        min_non_complete_labels_per_property=min_non_complete_labels_per_property,
    )
    label_cohen_kappa = _float_value(label_calibration.get("overall", {}).get("cohen_kappa"))
    if label_cohen_kappa is None or label_cohen_kappa < min_label_cohen_kappa:
        actual_kappa = "missing" if label_cohen_kappa is None else label_cohen_kappa
        reasons.append(
            f"label_cohen_kappa={actual_kappa}<min_label_cohen_kappa={min_label_cohen_kappa}"
        )
    _append_low_property_kappa_reason(
        reasons,
        corpus_validation=corpus_validation,
        label_calibration=label_calibration,
        threshold=min_label_property_cohen_kappa,
    )
    missing_baselines = _missing_names(required_baselines, baseline_summary.get("scorers", {}))
    if missing_baselines:
        reasons.append(f"missing_baselines={','.join(missing_baselines)}")
    missing_candidate_scorers = _missing_names(
        required_candidate_scorers,
        scorer_summary.get("scorers", {}),
    )
    if missing_candidate_scorers:
        reasons.append(f"missing_candidate_scorers={','.join(missing_candidate_scorers)}")
    disallowed_baseline_statuses = _disallowed_implementation_statuses(
        baseline_summary.get("scorers", {}),
        disallowed_baseline_implementation_statuses,
    )
    if disallowed_baseline_statuses:
        reasons.append(
            "disallowed_baseline_implementation_statuses="
            f"{','.join(disallowed_baseline_statuses)}"
        )
    disallowed_candidate_fixture_status_pairs = _disallowed_scorer_statuses(
        scorer_summary.get("scorers", {}),
        status_key="fixture_statuses",
        disallowed_statuses=disallowed_candidate_fixture_statuses,
    )
    if disallowed_candidate_fixture_status_pairs:
        reasons.append(
            "disallowed_candidate_fixture_statuses="
            f"{','.join(disallowed_candidate_fixture_status_pairs)}"
        )
    return reasons


def _missing_names(required: Sequence[str], observed: object) -> tuple[str, ...]:
    if not isinstance(observed, dict):
        return tuple(sorted(required))
    observed_names = {str(name) for name in observed}
    return tuple(name for name in sorted(required) if name not in observed_names)


def _scorer_implementation_statuses(scorers: object) -> dict[str, dict[str, int]]:
    return _scorer_statuses(scorers, "implementation_statuses")


def _scorer_statuses(scorers: object, status_key: str) -> dict[str, dict[str, int]]:
    if not isinstance(scorers, dict):
        return {}
    result: dict[str, dict[str, int]] = {}
    for scorer_name, scorer_summary in sorted(scorers.items()):
        if not isinstance(scorer_summary, dict):
            continue
        statuses = scorer_summary.get(status_key, {})
        if not isinstance(statuses, dict) or not statuses:
            continue
        parsed_statuses: dict[str, int] = {}
        for status, count in statuses.items():
            parsed_count = _int_value(count)
            if parsed_count is not None:
                parsed_statuses[str(status)] = parsed_count
        if parsed_statuses:
            result[str(scorer_name)] = dict(sorted(parsed_statuses.items()))
    return result


def _disallowed_implementation_statuses(
    scorers: object,
    disallowed_statuses: Sequence[str],
) -> tuple[str, ...]:
    return _disallowed_scorer_statuses(
        scorers,
        status_key="implementation_statuses",
        disallowed_statuses=disallowed_statuses,
    )


def _disallowed_scorer_statuses(
    scorers: object,
    *,
    status_key: str,
    disallowed_statuses: Sequence[str],
) -> tuple[str, ...]:
    disallowed = set(disallowed_statuses)
    if not disallowed:
        return ()
    status_pairs: list[str] = []
    for scorer, statuses in _scorer_statuses(scorers, status_key).items():
        for status in statuses:
            if status in disallowed:
                status_pairs.append(f"{scorer}:{status}")
    return tuple(sorted(status_pairs))


def _append_low_slice_count_reason(
    reasons: list[str],
    *,
    counts: object,
    reason_prefix: str,
    threshold_name: str,
    threshold: int,
) -> None:
    if not isinstance(counts, dict):
        reasons.append(f"{reason_prefix}=missing<{threshold_name}={threshold}")
        return
    low_counts: list[str] = []
    for name, count in counts.items():
        parsed_count = _int_value(count)
        if parsed_count is None or parsed_count < threshold:
            actual = "missing" if parsed_count is None else parsed_count
            low_counts.append(f"{name}:{actual}")
    if low_counts:
        reasons.append(
            f"{reason_prefix}={','.join(sorted(low_counts))}<{threshold_name}={threshold}"
        )


def _append_low_count_reason(
    reasons: list[str],
    *,
    counts: object,
    count_name: str,
    reason_name: str,
    threshold_name: str,
    threshold: int,
) -> None:
    if not isinstance(counts, dict):
        reasons.append(f"{reason_name}=missing<{threshold_name}={threshold}")
        return
    count = _int_value(counts.get(count_name))
    if count is None or count < threshold:
        actual = "missing" if count is None else count
        reasons.append(f"{reason_name}={actual}<{threshold_name}={threshold}")


def _append_low_property_category_balance_reasons(
    reasons: list[str],
    *,
    corpus_validation: dict[str, Any],
    min_complete_labels_per_property: int,
    min_non_complete_labels_per_property: int,
) -> None:
    property_category_counts = corpus_validation.get("property_category_counts", {})
    if not isinstance(property_category_counts, dict):
        reasons.append("property_category_counts=missing")
        return
    required_properties = _required_property_names(corpus_validation, property_category_counts)
    low_complete: list[str] = []
    low_non_complete: list[str] = []
    for property_name in required_properties:
        category_counts = property_category_counts.get(property_name, {})
        complete_count = _property_category_count(category_counts, "complete")
        non_complete_count = _property_non_complete_count(category_counts)
        if complete_count < min_complete_labels_per_property:
            low_complete.append(f"{property_name}:{complete_count}")
        if non_complete_count < min_non_complete_labels_per_property:
            low_non_complete.append(f"{property_name}:{non_complete_count}")
    if low_complete:
        reasons.append(
            "property_complete_counts_below_min="
            f"{','.join(sorted(low_complete))}<min_complete_labels_per_property="
            f"{min_complete_labels_per_property}"
        )
    if low_non_complete:
        reasons.append(
            "property_non_complete_counts_below_min="
            f"{','.join(sorted(low_non_complete))}<min_non_complete_labels_per_property="
            f"{min_non_complete_labels_per_property}"
        )


def _required_property_names(
    corpus_validation: dict[str, Any],
    property_category_counts: dict[Any, Any],
) -> tuple[str, ...]:
    required_properties = corpus_validation.get("label_contract", {}).get("required_properties", [])
    if isinstance(required_properties, list) and required_properties:
        return tuple(str(property_name) for property_name in required_properties)
    return tuple(sorted(str(property_name) for property_name in property_category_counts))


def _property_category_count(category_counts: object, category: str) -> int:
    if not isinstance(category_counts, dict):
        return 0
    count = _int_value(category_counts.get(category))
    return 0 if count is None else count


def _property_non_complete_count(category_counts: object) -> int:
    if not isinstance(category_counts, dict):
        return 0
    total = 0
    for category, count in category_counts.items():
        if str(category) == "complete":
            continue
        parsed_count = _int_value(count)
        if parsed_count is not None:
            total += parsed_count
    return total


def _append_low_property_kappa_reason(
    reasons: list[str],
    *,
    corpus_validation: dict[str, Any],
    label_calibration: dict[str, Any],
    threshold: float,
) -> None:
    properties = label_calibration.get("properties", {})
    required_properties = _required_property_names(
        corpus_validation,
        properties if isinstance(properties, dict) else {},
    )
    low_properties: list[str] = []
    for property_name in required_properties:
        property_metrics = properties.get(property_name, {}) if isinstance(properties, dict) else {}
        property_kappa = (
            _float_value(property_metrics.get("cohen_kappa"))
            if isinstance(property_metrics, dict)
            else None
        )
        if property_kappa is None or property_kappa < threshold:
            actual = "missing" if property_kappa is None else property_kappa
            low_properties.append(f"{property_name}:{actual}")
    if low_properties:
        reasons.append(
            "label_property_cohen_kappa_below_min="
            f"{','.join(sorted(low_properties))}<min_label_property_cohen_kappa={threshold}"
        )
