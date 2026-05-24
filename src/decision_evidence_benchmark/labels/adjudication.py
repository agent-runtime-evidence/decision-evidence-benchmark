"""Adjudicate two-annotator property labels into case manifests."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.construction_oracle import (
    CONSTRUCTION_ORACLE_ANNOTATION_STATUS,
    CONSTRUCTION_ORACLE_LABEL_SOURCE,
    CONSTRUCTION_ORACLE_VERSION,
)
from decision_evidence_benchmark.labels.calibration import AnnotationRecord
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    PROPERTY_CATEGORIES,
    CaseManifest,
    PropertyLabel,
)

ADJUDICATION_REPORT_METRIC_CONTRACT = "decision_evidence_label_adjudication"


@dataclass(frozen=True)
class AdjudicationOverride:
    case_id: str
    property: str
    category: str
    adjudicator_id: str
    required: bool = True
    source: str = "adjudicated_override"
    notes: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AdjudicationOverride:
        return cls(
            case_id=str(value["case_id"]),
            property=str(value["property"]),
            category=str(value["category"]),
            adjudicator_id=str(value.get("adjudicator_id", "")),
            required=bool(value.get("required", True)),
            source=str(value.get("source", "adjudicated_override")),
            notes=str(value.get("notes", "")),
        )


def read_adjudication_overrides_jsonl(path: Path) -> list[AdjudicationOverride]:
    overrides: list[AdjudicationOverride] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                overrides.append(AdjudicationOverride.from_dict(json.loads(stripped)))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid adjudication override") from exc
    return overrides


def adjudicate_cases(
    cases: list[CaseManifest],
    annotations: list[AnnotationRecord],
    overrides: list[AdjudicationOverride] | None = None,
) -> tuple[list[CaseManifest], dict[str, Any]]:
    """Return cases with property labels promoted from annotation agreement."""

    issues: list[dict[str, Any]] = []
    override_by_property = _override_index(overrides or [], cases=cases, issues=issues)
    annotations_by_pair, annotators = _annotation_index(cases, annotations, issues)
    if len(annotators) != 2:
        issues.append(
            {
                "severity": "error",
                "issue": "expected_exactly_two_annotators",
                "annotators": annotators,
            }
        )

    promoted_cases: list[CaseManifest] = []
    agreement_count = 0
    override_count = 0
    unresolved_count = 0

    for case in cases:
        adjudicated_labels: list[PropertyLabel] = []
        case_override_count = 0
        case_unresolved_count = 0
        left = (
            annotations_by_pair.get((case.case_id, annotators[0]))
            if len(annotators) == 2
            else None
        )
        right = (
            annotations_by_pair.get((case.case_id, annotators[1]))
            if len(annotators) == 2
            else None
        )
        if not left or not right:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case.case_id,
                    "issue": "missing_annotation_pair",
                    "annotators": annotators,
                }
            )
            adjudicated_labels = list(case.property_labels)
            case_unresolved_count += len(DECISION_EVENT_PROPERTIES)
            unresolved_count += len(DECISION_EVENT_PROPERTIES)
            promoted_cases.append(
                _case_with_labels(case, adjudicated_labels, annotators, 0, case_unresolved_count)
            )
            continue

        left_labels = _label_by_property(left)
        right_labels = _label_by_property(right)
        embedded_required = {label.property: label.required for label in case.property_labels}
        for property_name in DECISION_EVENT_PROPERTIES:
            override = override_by_property.get((case.case_id, property_name))
            left_label = left_labels.get(property_name)
            right_label = right_labels.get(property_name)
            if not left_label or not right_label:
                issues.append(
                    {
                        "severity": "error",
                        "case_id": case.case_id,
                        "property": property_name,
                        "issue": "missing_annotation_property",
                    }
                )
                fallback = _embedded_label(case, property_name)
                if fallback:
                    adjudicated_labels.append(fallback)
                case_unresolved_count += 1
                unresolved_count += 1
                continue

            if override:
                adjudicated_labels.append(_override_label(override, left_label, right_label))
                override_count += 1
                case_override_count += 1
                continue

            if left_label.category == right_label.category:
                label_source = _agreement_label_source(left, right)
                adjudicated_labels.append(
                    PropertyLabel(
                        property=property_name,
                        category=left_label.category,
                        required=embedded_required.get(property_name, left_label.required),
                        source=label_source,
                        notes=_agreement_label_notes(left, right, source=label_source),
                    )
                )
                agreement_count += 1
                continue

            issues.append(
                {
                    "severity": "error",
                    "case_id": case.case_id,
                    "property": property_name,
                    "issue": "missing_adjudication_override",
                    "left_annotator": left.annotator_id,
                    "left_category": left_label.category,
                    "right_annotator": right.annotator_id,
                    "right_category": right_label.category,
                }
            )
            fallback = _embedded_label(case, property_name)
            if fallback:
                adjudicated_labels.append(
                    PropertyLabel(
                        property=fallback.property,
                        category=fallback.category,
                        required=fallback.required,
                        source="unresolved_disagreement_fallback",
                        notes=(
                            f"left={left_label.category};right={right_label.category};"
                            "not manuscript-ready"
                        ),
                    )
                )
            case_unresolved_count += 1
            unresolved_count += 1

        promoted_cases.append(
            _case_with_labels(
                case,
                adjudicated_labels,
                annotators,
                case_override_count,
                case_unresolved_count,
            )
        )

    report = {
        "metric_contract": ADJUDICATION_REPORT_METRIC_CONTRACT,
        "case_count": len(cases),
        "annotators": annotators,
        "property_count": len(cases) * len(DECISION_EVENT_PROPERTIES),
        "agreement_label_count": agreement_count,
        "override_label_count": override_count,
        "unresolved_label_count": unresolved_count,
        "override_count": len(overrides or []),
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }
    return promoted_cases, report


def _annotation_index(
    cases: list[CaseManifest],
    annotations: list[AnnotationRecord],
    issues: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], AnnotationRecord], list[str]]:
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
        issues.extend(_annotation_property_issues(record))
    return by_pair, sorted({record.annotator_id for record in annotations})


def _override_index(
    overrides: list[AdjudicationOverride],
    *,
    cases: list[CaseManifest],
    issues: list[dict[str, Any]],
) -> dict[tuple[str, str], AdjudicationOverride]:
    case_ids = {case.case_id for case in cases}
    by_property: dict[tuple[str, str], AdjudicationOverride] = {}
    for override in overrides:
        key = (override.case_id, override.property)
        if override.case_id not in case_ids:
            issues.append(
                {
                    "severity": "error",
                    "case_id": override.case_id,
                    "property": override.property,
                    "issue": "unknown_override_case_id",
                }
            )
        if override.property not in DECISION_EVENT_PROPERTIES:
            issues.append(
                {
                    "severity": "error",
                    "case_id": override.case_id,
                    "property": override.property,
                    "issue": "unknown_override_property",
                }
            )
        if override.category not in PROPERTY_CATEGORIES:
            issues.append(
                {
                    "severity": "error",
                    "case_id": override.case_id,
                    "property": override.property,
                    "issue": "unknown_override_category",
                    "category": override.category,
                }
            )
        if key in by_property:
            issues.append(
                {
                    "severity": "error",
                    "case_id": override.case_id,
                    "property": override.property,
                    "issue": "duplicate_adjudication_override",
                }
            )
            continue
        by_property[key] = override
    return by_property


def _annotation_property_issues(record: AnnotationRecord) -> list[dict[str, Any]]:
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


def _case_with_labels(
    case: CaseManifest,
    labels: list[PropertyLabel],
    annotators: list[str],
    override_count: int,
    unresolved_count: int,
) -> CaseManifest:
    metadata = dict(case.metadata)
    construction_oracle_labels = (
        bool(labels)
        and unresolved_count == 0
        and all(label.source == CONSTRUCTION_ORACLE_LABEL_SOURCE for label in labels)
    )
    metadata["label_status"] = (
        CONSTRUCTION_ORACLE_ANNOTATION_STATUS
        if construction_oracle_labels
        else "adjudicated"
        if unresolved_count == 0
        else "unresolved"
    )
    if construction_oracle_labels:
        metadata["label_oracle"] = CONSTRUCTION_ORACLE_VERSION
    metadata["label_adjudication"] = {
        "annotators": annotators,
        "mode": (
            "deterministic_rule_oracle"
            if construction_oracle_labels
            else "two_annotator_adjudication"
        ),
        "override_label_count": override_count,
        "unresolved_label_count": unresolved_count,
    }
    return CaseManifest(
        case_id=case.case_id,
        regime=case.regime,
        question_family=case.question_family,
        degradation_condition=case.degradation_condition,
        evidence=dict(case.evidence),
        container_flags=dict(case.container_flags),
        property_labels=tuple(labels),
        metadata=metadata,
    )


def _label_by_property(record: AnnotationRecord) -> dict[str, PropertyLabel]:
    return {label.property: label for label in record.property_labels}


def _embedded_label(case: CaseManifest, property_name: str) -> PropertyLabel | None:
    for label in case.property_labels:
        if label.property == property_name:
            return label
    return None


def _override_label(
    override: AdjudicationOverride,
    left_label: PropertyLabel,
    right_label: PropertyLabel,
) -> PropertyLabel:
    notes = override.notes or f"left={left_label.category};right={right_label.category}"
    return PropertyLabel(
        property=override.property,
        category=override.category,
        required=override.required,
        source=override.source,
        notes=notes,
    )


def _agreement_label_source(left: AnnotationRecord, right: AnnotationRecord) -> str:
    if _is_construction_oracle_record(left) and _is_construction_oracle_record(right):
        return CONSTRUCTION_ORACLE_LABEL_SOURCE
    return "two_annotator_agreement"


def _agreement_label_notes(
    left: AnnotationRecord,
    right: AnnotationRecord,
    *,
    source: str,
) -> str:
    if source == CONSTRUCTION_ORACLE_LABEL_SOURCE:
        return (
            f"{CONSTRUCTION_ORACLE_VERSION}: deterministic construction-rule agreement; "
            f"agreed_by={left.annotator_id},{right.annotator_id}; "
            "basis=degradation_condition."
        )
    return f"agreed_by={left.annotator_id},{right.annotator_id}"


def _is_construction_oracle_record(record: AnnotationRecord) -> bool:
    return (
        record.metadata.get("annotation_source") == CONSTRUCTION_ORACLE_VERSION
        and record.metadata.get("annotation_status") == CONSTRUCTION_ORACLE_ANNOTATION_STATUS
    )
