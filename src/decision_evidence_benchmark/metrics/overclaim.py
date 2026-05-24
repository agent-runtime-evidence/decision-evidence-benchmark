"""Primary benchmark metric helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from decision_evidence_benchmark.schema import CaseManifest, ScorerOutput

OVERCLAIM_SUMMARY_METRIC_CONTRACT = "decision_evidence_overclaim_summary"


def result_row(case: CaseManifest, output: ScorerOutput, *, strict: bool = True) -> dict[str, Any]:
    truth = case.ground_truth_sufficient(strict=strict)
    overclaim = output.verdict == "sufficient" and not truth
    return {
        **output.to_dict(),
        "regime": case.regime,
        "question_family": case.question_family,
        "degradation_condition": case.degradation_condition,
        "ground_truth_sufficient": truth,
        "overclaim": overclaim,
    }


def _summarize_scorer_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_scorer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scorer[str(row["scorer"])].append(row)

    scorer_summaries: dict[str, dict[str, Any]] = {}
    for scorer, scorer_rows in sorted(by_scorer.items()):
        verdict_rows = [
            row for row in scorer_rows if row["verdict"] in {"sufficient", "insufficient"}
        ]
        sufficient_rows = [row for row in verdict_rows if row["verdict"] == "sufficient"]
        overclaim_rows = [row for row in verdict_rows if row["overclaim"]]
        denominator = len(verdict_rows)
        summary: dict[str, Any] = {
            "cases": len(scorer_rows),
            "verdict_cases": denominator,
            "sufficient_cases": len(sufficient_rows),
            "overclaim_cases": len(overclaim_rows),
            "overclaim_rate": (len(overclaim_rows) / denominator) if denominator else None,
        }
        implementation_statuses = _implementation_status_counts(scorer_rows)
        if implementation_statuses:
            summary["implementation_statuses"] = implementation_statuses
        scorer_summaries[scorer] = summary

    return scorer_summaries


def _implementation_status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    statuses: dict[str, int] = defaultdict(int)
    for row in rows:
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        implementation_status = metadata.get("implementation_status")
        if implementation_status:
            statuses[str(implementation_status)] += 1
    return dict(sorted(statuses.items()))


def _slice_summary(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    by_value: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_value[str(row[key])].append(row)
    return {
        value: _summarize_scorer_rows(value_rows)
        for value, value_rows in sorted(by_value.items())
    }


def summarize_outputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "metric_contract": OVERCLAIM_SUMMARY_METRIC_CONTRACT,
        "scorers": _summarize_scorer_rows(rows),
        "slices": {
            "regime": _slice_summary(rows, "regime"),
            "degradation_condition": _slice_summary(rows, "degradation_condition"),
            "question_family": _slice_summary(rows, "question_family"),
        },
    }
