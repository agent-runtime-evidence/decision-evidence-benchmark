import csv
import json
from dataclasses import replace
from pathlib import Path

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.labels import (
    ADJUDICATION_OVERRIDE_TEMPLATE_CATEGORY,
    AnnotationRecord,
    adjudicate_cases,
    adjudication_override_template_rows,
    label_review_summary,
    read_adjudication_overrides_jsonl,
    read_annotations_jsonl,
    write_adjudication_override_template_jsonl,
    write_label_review_csv,
)


def test_label_review_summarizes_smoke_annotation_agreement() -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))

    review = label_review_summary(cases, annotations)

    assert review["valid"] is True
    assert review["case_count"] == 8
    assert review["property_row_count"] == 64
    assert review["disagreed_property_count"] == 0
    assert review["cases_with_disagreement"] == []


def test_label_review_marks_disagreements_for_adjudication(tmp_path: Path) -> None:
    cases = read_cases_jsonl(Path("data/fixtures/smoke_cases.jsonl"))
    annotations = read_annotations_jsonl(Path("data/annotations/smoke_annotations.jsonl"))
    first = annotations[0]
    first_label = first.property_labels[0]
    changed_category = "opaque" if first_label.category == "complete" else "complete"
    changed = AnnotationRecord(
        case_id=first.case_id,
        annotator_id=first.annotator_id,
        property_labels=(
            replace(first_label, category=changed_category),
            *first.property_labels[1:],
        ),
        metadata=first.metadata,
    )

    review = label_review_summary(cases, [changed, *annotations[1:]])
    csv_path = tmp_path / "review.csv"
    write_label_review_csv(csv_path, review)

    assert review["valid"] is True
    assert review["disagreed_property_count"] == 1
    assert review["cases_with_disagreement"] == [first.case_id]
    assert review["rows"][0]["needs_adjudication"] is True
    rows = list(csv.DictReader(csv_path.open()))
    assert len(rows) == 64
    assert rows[0]["needs_adjudication"] == "True"
    assert rows[0]["embedded_required"] == "True"

    template_rows = adjudication_override_template_rows(
        review,
        adjudicator_id="reviewer_1",
    )
    template_path = tmp_path / "adjudication_overrides.template.jsonl"
    write_adjudication_override_template_jsonl(
        template_path,
        review,
        adjudicator_id="reviewer_1",
    )
    written_rows = [
        json.loads(line) for line in template_path.read_text().splitlines() if line
    ]

    assert len(template_rows) == 1
    assert written_rows == template_rows
    assert template_rows[0]["case_id"] == first.case_id
    assert template_rows[0]["property"] == first_label.property
    assert template_rows[0]["category"] == ADJUDICATION_OVERRIDE_TEMPLATE_CATEGORY
    assert template_rows[0]["adjudicator_id"] == "reviewer_1"
    assert template_rows[0]["template_status"] == "requires_manual_category_selection"
    template_overrides = read_adjudication_overrides_jsonl(template_path)
    _, template_report = adjudicate_cases(
        cases,
        [changed, *annotations[1:]],
        template_overrides,
    )
    assert template_report["valid"] is False
    assert any(
        issue["issue"] == "unknown_override_category"
        for issue in template_report["issues"]
    )
