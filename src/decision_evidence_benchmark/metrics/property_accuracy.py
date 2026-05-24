"""Property Sufficiency Accuracy helpers."""

from __future__ import annotations

from typing import Any

from decision_evidence_benchmark.schema import PropertyLabel


def property_sufficiency_accuracy(
    truth: tuple[PropertyLabel, ...],
    predicted: tuple[PropertyLabel, ...],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    """Compare predicted per-property sufficiency against ground truth."""

    predicted_by_property = {label.property: label for label in predicted}
    rows = []
    correct = 0
    required_truth = [label for label in truth if label.required]
    for truth_label in required_truth:
        prediction = predicted_by_property.get(truth_label.property)
        truth_sufficient = truth_label.sufficient(strict=strict)
        predicted_sufficient = prediction.sufficient(strict=strict) if prediction else False
        is_correct = truth_sufficient == predicted_sufficient
        correct += int(is_correct)
        rows.append(
            {
                "property": truth_label.property,
                "truth_sufficient": truth_sufficient,
                "predicted_sufficient": predicted_sufficient,
                "correct": is_correct,
                "missing_prediction": prediction is None,
            }
        )

    total = len(required_truth)
    return {
        "correct": correct,
        "total": total,
        "accuracy": (correct / total) if total else None,
        "properties": rows,
    }

