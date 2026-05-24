"""Annotation provenance and calibration diagnostics."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.labels.agreement import cohen_kappa
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    CaseManifest,
    PropertyLabel,
)


@dataclass(frozen=True)
class AnnotationRecord:
    case_id: str
    annotator_id: str
    property_labels: tuple[PropertyLabel, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AnnotationRecord:
        return cls(
            case_id=str(value["case_id"]),
            annotator_id=str(value["annotator_id"]),
            property_labels=tuple(
                PropertyLabel.from_dict(item) for item in value.get("property_labels", [])
            ),
            metadata=dict(value.get("metadata", {})),
        )


def read_annotations_jsonl(path: Path) -> list[AnnotationRecord]:
    records: list[AnnotationRecord] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                records.append(AnnotationRecord.from_dict(json.loads(stripped)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid annotation record") from exc
    return records


def calibration_summary(
    cases: list[CaseManifest],
    annotations: list[AnnotationRecord],
) -> dict[str, Any]:
    case_ids = {case.case_id for case in cases}
    issues: list[dict[str, Any]] = []
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

        _append_property_issues(record, issues)

    annotators = sorted({record.annotator_id for record in annotations})
    if len(annotators) != 2:
        issues.append(
            {
                "severity": "error",
                "issue": "expected_exactly_two_annotators",
                "annotators": annotators,
            }
        )
        return _empty_summary(annotators, issues)

    left_id, right_id = annotators
    left_categories: list[str] = []
    right_categories: list[str] = []
    per_property: dict[str, dict[str, list[str]]] = {
        property_name: {"left": [], "right": []} for property_name in DECISION_EVENT_PROPERTIES
    }
    paired_cases = 0

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
        paired_cases += 1
        left_labels = {label.property: label.category for label in left.property_labels}
        right_labels = {label.property: label.category for label in right.property_labels}
        for property_name in DECISION_EVENT_PROPERTIES:
            if property_name not in left_labels or property_name not in right_labels:
                continue
            left_categories.append(left_labels[property_name])
            right_categories.append(right_labels[property_name])
            per_property[property_name]["left"].append(left_labels[property_name])
            per_property[property_name]["right"].append(right_labels[property_name])

    return {
        "metric_contract": "decision_evidence_label_calibration",
        "annotators": annotators,
        "case_count": len(cases),
        "paired_case_count": paired_cases,
        "paired_label_count": len(left_categories),
        "overall": _agreement_metrics(left_categories, right_categories),
        "properties": {
            property_name: _agreement_metrics(values["left"], values["right"])
            for property_name, values in per_property.items()
        },
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _append_property_issues(
    record: AnnotationRecord,
    issues: list[dict[str, Any]],
) -> None:
    properties = [label.property for label in record.property_labels]
    missing = sorted(set(DECISION_EVENT_PROPERTIES) - set(properties))
    extra = sorted(set(properties) - set(DECISION_EVENT_PROPERTIES))
    duplicates = sorted(
        property_name for property_name, count in Counter(properties).items() if count > 1
    )
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


def _agreement_metrics(left: list[str], right: list[str]) -> dict[str, Any]:
    if not left:
        return {
            "labels": 0,
            "agreement_rate": None,
            "cohen_kappa": None,
        }
    agreements = sum(
        1 for left_label, right_label in zip(left, right, strict=True) if left_label == right_label
    )
    return {
        "labels": len(left),
        "agreement_rate": agreements / len(left),
        "cohen_kappa": cohen_kappa(left, right),
    }


def _empty_summary(annotators: list[str], issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "metric_contract": "decision_evidence_label_calibration",
        "annotators": annotators,
        "case_count": 0,
        "paired_case_count": 0,
        "paired_label_count": 0,
        "overall": {"labels": 0, "agreement_rate": None, "cohen_kappa": None},
        "properties": {},
        "issues": issues,
        "valid": False,
    }
