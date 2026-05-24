"""Candidate scorer evaluation helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from decision_evidence_benchmark.metrics.overclaim import result_row, summarize_outputs
from decision_evidence_benchmark.metrics.property_accuracy import property_sufficiency_accuracy
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    CaseManifest,
    ScorerOutput,
)

CANDIDATE_SCORER_METRIC_CONTRACT = "decision_evidence_candidate_scorer_evaluation"
SCORER_OUTPUT_VALIDATION_CONTRACT = "decision_evidence_scorer_output_validation"
DEFAULT_REQUIRED_SCORERS = ("decision_trace_reconstructor",)


def evaluate_scorer_outputs(
    cases: list[CaseManifest],
    outputs: list[ScorerOutput],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    cases_by_id = {case.case_id: case for case in cases}
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for output in outputs:
        case = cases_by_id.get(output.case_id)
        if case is None:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "scorer": output.scorer,
                    "issue": "unknown_case_id",
                }
            )
            continue

        pair = (output.case_id, output.scorer)
        if pair in seen_pairs:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "scorer": output.scorer,
                    "issue": "duplicate_scorer_output",
                }
            )
            continue
        seen_pairs.add(pair)

        property_result = property_sufficiency_accuracy(
            case.property_labels,
            output.property_predictions,
            strict=strict,
        )
        rows.append(
            {
                **result_row(case, output, strict=strict),
                "property_sufficiency_correct": property_result["correct"],
                "property_sufficiency_total": property_result["total"],
                "property_sufficiency_accuracy": property_result["accuracy"],
                "property_sufficiency_properties": property_result["properties"],
            }
        )

    return {
        "rows": rows,
        "summary": summarize_scorer_evaluation(rows, issues),
    }


def validate_scorer_outputs(
    cases: list[CaseManifest],
    outputs: list[ScorerOutput],
    *,
    required_scorers: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate candidate scorer output coverage before metric use."""

    required = tuple(sorted(required_scorers or DEFAULT_REQUIRED_SCORERS))
    case_ids = {case.case_id for case in cases}
    outputs_by_pair: dict[tuple[str, str], ScorerOutput] = {}
    issues: list[dict[str, Any]] = []

    for output in outputs:
        if output.case_id not in case_ids:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "scorer": output.scorer,
                    "issue": "unknown_case_id",
                }
            )
            continue
        pair = (output.case_id, output.scorer)
        if pair in outputs_by_pair:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "scorer": output.scorer,
                    "issue": "duplicate_scorer_output",
                }
            )
            continue
        outputs_by_pair[pair] = output
        issues.extend(_property_prediction_issues(output))

    observed_scorers = sorted({output.scorer for output in outputs if output.case_id in case_ids})
    for scorer in required:
        if scorer not in observed_scorers:
            issues.append(
                {
                    "severity": "error",
                    "scorer": scorer,
                    "issue": "missing_required_scorer",
                }
            )
            continue
        for case_id in sorted(case_ids):
            if (case_id, scorer) not in outputs_by_pair:
                issues.append(
                    {
                        "severity": "error",
                        "case_id": case_id,
                        "scorer": scorer,
                        "issue": "missing_scorer_case",
                    }
                )

    return {
        "metric_contract": SCORER_OUTPUT_VALIDATION_CONTRACT,
        "case_count": len(cases),
        "output_count": len(outputs),
        "required_scorers": list(required),
        "observed_scorers": observed_scorers,
        "scorers": {
            scorer: {
                "cases": sum(1 for output in outputs if output.scorer == scorer),
                "known_cases": sum(
                    1
                    for output in outputs
                    if output.scorer == scorer and output.case_id in case_ids
                ),
            }
            for scorer in observed_scorers
        },
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def summarize_scorer_evaluation(
    rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    overclaim_summary = summarize_outputs(rows)
    by_scorer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scorer[str(row["scorer"])].append(row)

    scorers: dict[str, dict[str, Any]] = {}
    for scorer, scorer_rows in sorted(by_scorer.items()):
        accuracies = [
            float(row["property_sufficiency_accuracy"])
            for row in scorer_rows
            if row["property_sufficiency_accuracy"] is not None
        ]
        overclaim_metrics = overclaim_summary["scorers"].get(scorer, {})
        summary: dict[str, Any] = {
            "cases": len(scorer_rows),
            "mean_property_sufficiency_accuracy": (
                sum(accuracies) / len(accuracies) if accuracies else None
            ),
            "overclaim_rate": overclaim_metrics.get("overclaim_rate"),
            "overclaim_cases": overclaim_metrics.get("overclaim_cases", 0),
        }
        fixture_statuses = _metadata_value_counts(scorer_rows, "fixture_status")
        if fixture_statuses:
            summary["fixture_statuses"] = fixture_statuses
        implementation_statuses = _metadata_value_counts(scorer_rows, "implementation_status")
        if implementation_statuses:
            summary["implementation_statuses"] = implementation_statuses
        scorers[scorer] = summary

    return {
        "metric_contract": CANDIDATE_SCORER_METRIC_CONTRACT,
        "scorers": scorers,
        "slices": {
            "regime": _property_accuracy_slice(rows, "regime"),
            "degradation_condition": _property_accuracy_slice(rows, "degradation_condition"),
            "question_family": _property_accuracy_slice(rows, "question_family"),
        },
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _property_accuracy_slice(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)

    result: dict[str, dict[str, Any]] = {}
    for value, value_rows in sorted(grouped.items()):
        by_scorer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in value_rows:
            by_scorer[str(row["scorer"])].append(row)
        result[value] = {}
        for scorer, scorer_rows in sorted(by_scorer.items()):
            accuracies = [
                float(row["property_sufficiency_accuracy"])
                for row in scorer_rows
                if row["property_sufficiency_accuracy"] is not None
            ]
            result[value][scorer] = {
                **_metadata_status_payload(scorer_rows),
                "cases": len(scorer_rows),
                "mean_property_sufficiency_accuracy": (
                    sum(accuracies) / len(accuracies) if accuracies else None
                ),
            }
    return result


def _metadata_status_payload(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    payload: dict[str, dict[str, int]] = {}
    fixture_statuses = _metadata_value_counts(rows, "fixture_status")
    if fixture_statuses:
        payload["fixture_statuses"] = fixture_statuses
    implementation_statuses = _metadata_value_counts(rows, "implementation_status")
    if implementation_statuses:
        payload["implementation_statuses"] = implementation_statuses
    return payload


def _metadata_value_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        value = metadata.get(field)
        if value:
            counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _property_prediction_issues(output: ScorerOutput) -> list[dict[str, Any]]:
    properties = [label.property for label in output.property_predictions]
    missing = sorted(set(DECISION_EVENT_PROPERTIES) - set(properties))
    extra = sorted(set(properties) - set(DECISION_EVENT_PROPERTIES))
    duplicates = sorted(
        property_name for property_name in set(properties) if properties.count(property_name) > 1
    )
    issues: list[dict[str, Any]] = []
    for issue_name, property_names in (
        ("missing_property_predictions", missing),
        ("unknown_property_predictions", extra),
        ("duplicate_property_predictions", duplicates),
    ):
        if property_names:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "scorer": output.scorer,
                    "issue": issue_name,
                    "properties": property_names,
                }
            )
    return issues
