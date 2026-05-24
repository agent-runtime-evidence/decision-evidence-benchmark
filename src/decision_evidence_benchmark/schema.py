"""Core benchmark data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, cast

Verdict = Literal["sufficient", "insufficient", "abstain"]
VERDICTS = {"sufficient", "insufficient", "abstain"}

PROPERTY_CATEGORIES = {
    "complete",
    "partial",
    "opaque",
    "structurally_unfillable",
    "conflicting",
}

DECISION_EVENT_PROPERTIES = (
    "actor_identity",
    "principal_authority",
    "action_boundary",
    "policy_basis",
    "decision_basis",
    "data_resource_touch",
    "lifecycle_context",
    "verification_strength",
)


@dataclass(frozen=True)
class PropertyLabel:
    """Ground-truth or predicted sufficiency label for one property."""

    property: str
    category: str
    required: bool = True
    source: str = "synthetic"
    notes: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PropertyLabel:
        category = str(value["category"])
        if category not in PROPERTY_CATEGORIES:
            raise ValueError(f"unknown property category: {category}")
        return cls(
            property=str(value["property"]),
            category=category,
            required=bool(value.get("required", True)),
            source=str(value.get("source", "synthetic")),
            notes=str(value.get("notes", "")),
        )

    def sufficient(self, *, strict: bool = True) -> bool:
        if not self.required:
            return True
        if self.category == "complete":
            return True
        if self.category == "partial" and not strict:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "property": self.property,
            "category": self.category,
            "required": self.required,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CaseManifest:
    """One benchmark case after regime-native evidence is available."""

    case_id: str
    regime: str
    question_family: str
    degradation_condition: str
    evidence: dict[str, Any] = field(default_factory=dict)
    container_flags: dict[str, Any] = field(default_factory=dict)
    property_labels: tuple[PropertyLabel, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CaseManifest:
        return cls(
            case_id=str(value["case_id"]),
            regime=str(value["regime"]),
            question_family=str(value["question_family"]),
            degradation_condition=str(value["degradation_condition"]),
            evidence=dict(value.get("evidence", {})),
            container_flags=dict(value.get("container_flags", {})),
            property_labels=tuple(
                PropertyLabel.from_dict(item) for item in value.get("property_labels", [])
            ),
            metadata=dict(value.get("metadata", {})),
        )

    def ground_truth_sufficient(self, *, strict: bool = True) -> bool:
        if not self.property_labels:
            raise ValueError(f"case {self.case_id} has no property labels")
        return all(label.sufficient(strict=strict) for label in self.property_labels)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "regime": self.regime,
            "question_family": self.question_family,
            "degradation_condition": self.degradation_condition,
            "evidence": self.evidence,
            "container_flags": self.container_flags,
            "property_labels": [label.to_dict() for label in self.property_labels],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ScorerOutput:
    """One scorer verdict for one case."""

    case_id: str
    scorer: str
    verdict: Verdict
    metadata: dict[str, Any] = field(default_factory=dict)
    property_predictions: tuple[PropertyLabel, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ScorerOutput:
        verdict = str(value["verdict"])
        if verdict not in VERDICTS:
            raise ValueError(f"unknown scorer verdict: {verdict}")
        return cls(
            case_id=str(value["case_id"]),
            scorer=str(value["scorer"]),
            verdict=cast(Verdict, verdict),
            metadata=dict(value.get("metadata", {})),
            property_predictions=tuple(
                PropertyLabel.from_dict(item) for item in value.get("property_predictions", [])
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "scorer": self.scorer,
            "verdict": self.verdict,
            "metadata": self.metadata,
            "property_predictions": [item.to_dict() for item in self.property_predictions],
        }
