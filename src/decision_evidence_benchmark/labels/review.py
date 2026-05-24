"""Detailed two-annotator label review exports."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.labels.calibration import AnnotationRecord
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

LABEL_REVIEW_METRIC_CONTRACT = "decision_evidence_label_review"
ADJUDICATION_OVERRIDE_TEMPLATE_CATEGORY = "__SELECT_CATEGORY__"
LABEL_REVIEW_CSV_FIELDS = (
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "property",
    "embedded_category",
    "embedded_required",
    "left_annotator",
    "left_category",
    "right_annotator",
    "right_category",
    "agreed",
    "needs_adjudication",
)


def label_review_summary(
    cases: list[CaseManifest],
    annotations: list[AnnotationRecord],
) -> dict[str, Any]:
    """Return row-level pairwise annotation review with adjudication flags."""

    issues: list[dict[str, Any]] = []
    case_ids = {case.case_id for case in cases}
    by_pair: dict[tuple[str, str], AnnotationRecord] = {}

    for record in annotations:
        if record.case_id not in case_ids:
            issues.append(
                {
                    "severity": "error",
                    "case_id": record.case_id,
                    "annotator_id": record.annotator_id,
                    "issue": "unknown_case_id",
                }
            )
        pair = (record.case_id, record.annotator_id)
        if pair in by_pair:
            issues.append(
                {
                    "severity": "error",
                    "case_id": record.case_id,
                    "annotator_id": record.annotator_id,
                    "issue": "duplicate_annotation_record",
                }
            )
            continue
        by_pair[pair] = record
        issues.extend(_property_issues(record))

    annotators = sorted({record.annotator_id for record in annotations})
    if len(annotators) != 2:
        issues.append(
            {
                "severity": "error",
                "issue": "expected_exactly_two_annotators",
                "annotators": annotators,
            }
        )
        return _review_payload(annotators=annotators, rows=[], issues=issues)

    left_id, right_id = annotators
    rows: list[dict[str, Any]] = []
    for case in cases:
        left = by_pair.get((case.case_id, left_id))
        right = by_pair.get((case.case_id, right_id))
        if not left or not right:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case.case_id,
                    "issue": "missing_annotation_pair",
                    "annotators": annotators,
                }
            )
            continue

        left_labels = _category_by_property(left)
        right_labels = _category_by_property(right)
        embedded_labels = {label.property: label for label in case.property_labels}
        for property_name in DECISION_EVENT_PROPERTIES:
            left_category = left_labels.get(property_name)
            right_category = right_labels.get(property_name)
            embedded_label = embedded_labels.get(property_name)
            embedded_category = embedded_label.category if embedded_label else None
            if left_category is None or right_category is None:
                continue
            agreed = left_category == right_category
            rows.append(
                {
                    "case_id": case.case_id,
                    "regime": case.regime,
                    "degradation_condition": case.degradation_condition,
                    "question_family": case.question_family,
                    "property": property_name,
                    "embedded_category": embedded_category,
                    "embedded_required": embedded_label.required if embedded_label else True,
                    "left_annotator": left_id,
                    "left_category": left_category,
                    "right_annotator": right_id,
                    "right_category": right_category,
                    "agreed": agreed,
                    "needs_adjudication": not agreed,
                }
            )

    return _review_payload(annotators=annotators, rows=rows, issues=issues)


def write_label_review_csv(path: Path, review: dict[str, Any]) -> None:
    """Write row-level review details to CSV for manual adjudication."""

    path.parent.mkdir(parents=True, exist_ok=True)
    rows = review.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("label review rows must be a list")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_REVIEW_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            if isinstance(row, dict):
                writer.writerow({field: row.get(field, "") for field in LABEL_REVIEW_CSV_FIELDS})


def adjudication_override_template_rows(
    review: dict[str, Any],
    *,
    adjudicator_id: str = "",
) -> list[dict[str, Any]]:
    """Return JSONL rows that must be edited into adjudication overrides."""

    rows = review.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("label review rows must be a list")

    template_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not bool(row.get("needs_adjudication", False)):
            continue
        template_rows.append(
            {
                "case_id": str(row["case_id"]),
                "property": str(row["property"]),
                "category": ADJUDICATION_OVERRIDE_TEMPLATE_CATEGORY,
                "adjudicator_id": adjudicator_id,
                "required": bool(row.get("embedded_required", True)),
                "source": "adjudicated_override",
                "notes": _override_template_notes(row),
                "template_status": "requires_manual_category_selection",
                "left_annotator": str(row.get("left_annotator", "")),
                "left_category": str(row.get("left_category", "")),
                "right_annotator": str(row.get("right_annotator", "")),
                "right_category": str(row.get("right_category", "")),
                "embedded_category": row.get("embedded_category"),
            }
        )
    return template_rows


def write_adjudication_override_template_jsonl(
    path: Path,
    review: dict[str, Any],
    *,
    adjudicator_id: str = "",
) -> None:
    """Write a fill-in JSONL template for disagreement adjudication."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in adjudication_override_template_rows(
            review,
            adjudicator_id=adjudicator_id,
        ):
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _review_payload(
    *,
    annotators: list[str],
    rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    disagreed_rows = [row for row in rows if row["needs_adjudication"]]
    cases_with_disagreement = sorted({str(row["case_id"]) for row in disagreed_rows})
    return {
        "metric_contract": LABEL_REVIEW_METRIC_CONTRACT,
        "annotators": annotators,
        "case_count": len({str(row["case_id"]) for row in rows}),
        "property_row_count": len(rows),
        "agreed_property_count": len(rows) - len(disagreed_rows),
        "disagreed_property_count": len(disagreed_rows),
        "cases_with_disagreement": cases_with_disagreement,
        "property_disagreement_counts": _property_disagreement_counts(rows),
        "rows": rows,
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _property_disagreement_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts = Counter(
        str(row["property"])
        for row in rows
        if bool(row.get("needs_adjudication", False))
    )
    totals = Counter(str(row["property"]) for row in rows)
    return {
        property_name: {
            "rows": totals.get(property_name, 0),
            "disagreements": counts.get(property_name, 0),
            "agreement_rate": (
                1.0 - (counts.get(property_name, 0) / totals[property_name])
                if totals.get(property_name, 0)
                else None
            ),
        }
        for property_name in DECISION_EVENT_PROPERTIES
    }


def _property_issues(record: AnnotationRecord) -> list[dict[str, Any]]:
    properties = [label.property for label in record.property_labels]
    missing = sorted(set(DECISION_EVENT_PROPERTIES) - set(properties))
    extra = sorted(set(properties) - set(DECISION_EVENT_PROPERTIES))
    duplicates = sorted(
        property_name for property_name, count in Counter(properties).items() if count > 1
    )
    issues: list[dict[str, Any]] = []
    for issue_name, property_names in (
        ("missing_property_labels", missing),
        ("unknown_property_labels", extra),
        ("duplicate_property_labels", duplicates),
    ):
        if property_names:
            issues.append(
                {
                    "severity": "error",
                    "case_id": record.case_id,
                    "annotator_id": record.annotator_id,
                    "issue": issue_name,
                    "properties": property_names,
                }
            )
    return issues


def _category_by_property(record: AnnotationRecord) -> dict[str, str]:
    return {label.property: label.category for label in record.property_labels}


def _override_template_notes(row: dict[str, Any]) -> str:
    return (
        f"left={row.get('left_annotator')}:{row.get('left_category')};"
        f"right={row.get('right_annotator')}:{row.get('right_category')};"
        f"embedded={row.get('embedded_category')}"
    )
