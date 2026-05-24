from dataclasses import replace
from pathlib import Path

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.labels import (
    AdjudicationOverride,
    AnnotationRecord,
    adjudicate_cases,
    read_annotations_jsonl,
)


def test_adjudicate_cases_promotes_agreed_smoke_labels() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))

    adjudicated_cases, report = adjudicate_cases(cases, annotations)

    assert report["valid"] is True
    assert report["agreement_label_count"] == 64
    assert report["override_label_count"] == 0
    assert report["unresolved_label_count"] == 0
    assert len(adjudicated_cases) == 8
    first_label = adjudicated_cases[0].property_labels[0]
    assert first_label.source == "two_annotator_agreement"
    assert adjudicated_cases[0].metadata["label_status"] == "adjudicated"


def test_adjudicate_cases_requires_override_for_disagreement() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))
    changed = _change_first_annotation_label(annotations)

    _, report = adjudicate_cases(cases, [changed, *annotations[1:]])

    assert report["valid"] is False
    assert report["unresolved_label_count"] == 1
    assert any(
        issue["issue"] == "missing_adjudication_override" for issue in report["issues"]
    )


def test_adjudicate_cases_applies_disagreement_override() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))
    changed = _change_first_annotation_label(annotations)
    override = AdjudicationOverride(
        case_id=changed.case_id,
        property=changed.property_labels[0].property,
        category="complete",
        adjudicator_id="reviewer_1",
        notes="resolved in adjudication",
    )

    adjudicated_cases, report = adjudicate_cases(cases, [changed, *annotations[1:]], [override])

    assert report["valid"] is True
    assert report["override_label_count"] == 1
    assert report["unresolved_label_count"] == 0
    assert adjudicated_cases[0].property_labels[0].source == "adjudicated_override"
    assert adjudicated_cases[0].property_labels[0].notes == "resolved in adjudication"


def _change_first_annotation_label(
    annotations: list[AnnotationRecord],
) -> AnnotationRecord:
    first = annotations[0]
    first_label = first.property_labels[0]
    changed_category = "opaque" if first_label.category == "complete" else "complete"
    return AnnotationRecord(
        case_id=first.case_id,
        annotator_id=first.annotator_id,
        property_labels=(
            replace(first_label, category=changed_category),
            *first.property_labels[1:],
        ),
        metadata=first.metadata,
    )
