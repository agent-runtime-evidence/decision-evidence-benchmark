"""Explain readiness blockers as actionable manuscript gaps."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

READINESS_GAP_REPORT_METRIC_CONTRACT = "decision_evidence_readiness_gap_report"
EXPECTED_READINESS_REPORT_METRIC_CONTRACT = "decision_evidence_result_readiness"


def build_readiness_gap_report(readiness_report: dict[str, Any]) -> dict[str, Any]:
    """Build an actionable gap report from an existing readiness report."""

    reasons, issues = _blocking_reason_strings(readiness_report)
    blockers = [
        {
            "reason": reason,
            **_classify_blocker(reason),
            "manuscript_blocking": True,
        }
        for reason in reasons
    ]
    source_metric_contract = readiness_report.get("metric_contract")
    if source_metric_contract != EXPECTED_READINESS_REPORT_METRIC_CONTRACT:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_readiness_metric_contract",
                "expected": EXPECTED_READINESS_REPORT_METRIC_CONTRACT,
                "actual": source_metric_contract,
            }
        )

    return {
        "metric_contract": READINESS_GAP_REPORT_METRIC_CONTRACT,
        "source_metric_contract": source_metric_contract,
        "mechanics_valid": bool(readiness_report.get("mechanics_valid")),
        "manuscript_result_ready": bool(readiness_report.get("manuscript_result_ready")),
        "blocker_count": len(blockers),
        "artifact_area_counts": _counts(str(blocker["artifact_area"]) for blocker in blockers),
        "category_counts": _counts(str(blocker["category"]) for blocker in blockers),
        "blockers": blockers,
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _blocking_reason_strings(
    readiness_report: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    reasons = readiness_report.get("blocking_reasons")
    if not isinstance(reasons, list):
        return [], [{"severity": "error", "issue": "blocking_reasons_not_list"}]

    parsed_reasons: list[str] = []
    issues: list[dict[str, Any]] = []
    for index, reason in enumerate(reasons):
        if isinstance(reason, str):
            parsed_reasons.append(reason)
        else:
            issues.append(
                {
                    "severity": "error",
                    "issue": "blocking_reason_not_string",
                    "index": index,
                    "actual_type": type(reason).__name__,
                }
            )
    return parsed_reasons, issues


def _classify_blocker(reason: str) -> dict[str, str]:
    for prefix, category, artifact_area, action in _CLASSIFICATION_RULES:
        if reason.startswith(prefix):
            return {
                "category": category,
                "artifact_area": artifact_area,
                "action": action,
            }
    return {
        "category": "unknown_readiness_blocker",
        "artifact_area": "unknown",
        "action": "Inspect the readiness report and resolve the blocker before Section 7 use.",
    }


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


_CLASSIFICATION_RULES: tuple[tuple[str, str, str, str], ...] = (
    (
        "corpus_claim_status=",
        "corpus_claim_status",
        "corpus",
        (
            "Promote the corpus manifest only after manuscript-scale, non-fixture "
            "cases and labels are complete and reviewed."
        ),
    ),
    (
        "run_claim_status=",
        "run_claim_status",
        "run_manifest",
        (
            "Run the audited manuscript-scale package with "
            "--run-claim-status manuscript_result_candidate after inputs are ready."
        ),
    ),
    (
        "label_calibration_status=",
        "label_fixture_status",
        "labels",
        "Replace smoke or draft label fixtures with reviewed manuscript annotations.",
    ),
    (
        "case_count=",
        "case_coverage",
        "corpus",
        "Add or adapt manuscript cases until the minimum case count is satisfied.",
    ),
    (
        "regime_count=",
        "regime_coverage",
        "corpus",
        "Add or adapt cases until all required regimes are represented.",
    ),
    (
        "degradation_condition_count=",
        "degradation_condition_coverage",
        "corpus",
        "Add or adapt cases until all degradation conditions are represented.",
    ),
    (
        "question_family_count=",
        "question_family_coverage",
        "corpus",
        "Add or adapt cases until all governance question families are represented.",
    ),
    (
        "regime_case_counts_below_min=",
        "regime_slice_coverage",
        "corpus",
        "Rebalance the corpus so every regime meets the per-slice minimum.",
    ),
    (
        "degradation_condition_case_counts_below_min=",
        "degradation_condition_slice_coverage",
        "corpus",
        (
            "Rebalance the corpus so every degradation condition meets the "
            "per-slice minimum."
        ),
    ),
    (
        "question_family_case_counts_below_min=",
        "question_family_slice_coverage",
        "corpus",
        "Rebalance the corpus so every question family meets the per-slice minimum.",
    ),
    (
        "strict_sufficient_cases=",
        "strict_sufficiency_balance",
        "labels",
        "Add or adjudicate enough strictly sufficient cases to support the metric gate.",
    ),
    (
        "strict_insufficient_cases=",
        "strict_sufficiency_balance",
        "labels",
        "Add or adjudicate enough strictly insufficient cases to support the metric gate.",
    ),
    (
        "property_category_counts=",
        "property_label_balance",
        "labels",
        "Populate property-category counts from validated adjudicated labels.",
    ),
    (
        "property_complete_counts_below_min=",
        "property_label_balance",
        "labels",
        "Add or adjudicate complete labels for properties below the balance threshold.",
    ),
    (
        "property_non_complete_counts_below_min=",
        "property_label_balance",
        "labels",
        (
            "Add or adjudicate non-complete labels for properties below the "
            "balance threshold."
        ),
    ),
    (
        "label_cohen_kappa=",
        "label_agreement",
        "labels",
        "Resolve annotation disagreement or rerun calibration before aggregating results.",
    ),
    (
        "label_property_cohen_kappa_below_min=",
        "property_label_agreement",
        "labels",
        "Resolve per-property annotation disagreement before aggregating results.",
    ),
    (
        "missing_baselines=",
        "missing_baselines",
        "baselines",
        "Run or import every required baseline output for the adjudicated case set.",
    ),
    (
        "missing_candidate_scorers=",
        "missing_candidate_scorers",
        "candidate_scorer",
        "Provide required Decision Trace Reconstructor outputs for every case.",
    ),
    (
        "disallowed_baseline_implementation_statuses=",
        "baseline_fixture_status",
        "baselines",
        "Replace fixture baseline outputs with pinned non-fixture baseline artifacts.",
    ),
    (
        "disallowed_candidate_fixture_statuses=",
        "candidate_fixture_status",
        "candidate_scorer",
        "Replace smoke or draft candidate scorer outputs with audited non-fixture outputs.",
    ),
)
