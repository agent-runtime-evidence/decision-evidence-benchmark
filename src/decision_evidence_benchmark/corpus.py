"""Corpus manifest loading and validation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest


@dataclass(frozen=True)
class CorpusCaseFile:
    path: Path
    regime: str | None = None
    role: str = "case_manifest_jsonl"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CorpusCaseFile:
        return cls(
            path=Path(str(value["path"])),
            regime=str(value["regime"]) if value.get("regime") else None,
            role=str(value.get("role", "case_manifest_jsonl")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"path": str(self.path), "role": self.role}
        if self.regime:
            payload["regime"] = self.regime
        return payload


@dataclass(frozen=True)
class CorpusManifest:
    corpus_id: str
    version: str
    claim_status: str
    case_files: tuple[CorpusCaseFile, ...]
    expected_regimes: tuple[str, ...]
    label_contract: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CorpusManifest:
        expected_regimes = tuple(str(item) for item in value.get("expected_regimes", []))
        unknown_regimes = sorted(set(expected_regimes) - set(REGIME_IDS))
        if unknown_regimes:
            raise ValueError(f"unknown expected regimes: {', '.join(unknown_regimes)}")
        return cls(
            corpus_id=str(value["corpus_id"]),
            version=str(value["version"]),
            claim_status=str(value["claim_status"]),
            case_files=tuple(
                CorpusCaseFile.from_dict(item) for item in value.get("case_files", [])
            ),
            expected_regimes=expected_regimes,
            label_contract=dict(value.get("label_contract", {})),
        )


def load_corpus_manifest(path: Path) -> CorpusManifest:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path}: corpus manifest must be a mapping")
    return CorpusManifest.from_dict(value)


def _validate_case(case: CaseManifest, *, source: CorpusCaseFile) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if source.regime and case.regime != source.regime:
        issues.append(
            {
                "severity": "error",
                "case_id": case.case_id,
                "issue": "source_regime_mismatch",
                "expected": source.regime,
                "actual": case.regime,
            }
        )

    properties = [label.property for label in case.property_labels]
    missing = sorted(set(DECISION_EVENT_PROPERTIES) - set(properties))
    extra = sorted(set(properties) - set(DECISION_EVENT_PROPERTIES))
    if missing:
        issues.append(
            {
                "severity": "error",
                "case_id": case.case_id,
                "issue": "missing_property_labels",
                "properties": missing,
            }
        )
    if extra:
        issues.append(
            {
                "severity": "error",
                "case_id": case.case_id,
                "issue": "unknown_property_labels",
                "properties": extra,
            }
        )

    duplicate_properties = sorted(
        property_name for property_name, count in Counter(properties).items() if count > 1
    )
    if duplicate_properties:
        issues.append(
            {
                "severity": "error",
                "case_id": case.case_id,
                "issue": "duplicate_property_labels",
                "properties": duplicate_properties,
            }
        )
    return issues


def validate_corpus_manifest(path: Path) -> dict[str, Any]:
    manifest = load_corpus_manifest(path)
    all_cases: list[CaseManifest] = []
    issues: list[dict[str, Any]] = []

    for case_file in manifest.case_files:
        if case_file.role != "case_manifest_jsonl":
            issues.append(
                {
                    "severity": "error",
                    "path": str(case_file.path),
                    "issue": "unsupported_case_file_role",
                    "role": case_file.role,
                }
            )
            continue
        if not case_file.path.exists():
            issues.append(
                {
                    "severity": "error",
                    "path": str(case_file.path),
                    "issue": "missing_case_file",
                }
            )
            continue
        cases = read_cases_jsonl(case_file.path)
        all_cases.extend(cases)
        for case in cases:
            issues.extend(_validate_case(case, source=case_file))

    case_ids = [case.case_id for case in all_cases]
    duplicate_case_ids = sorted(
        case_id for case_id, count in Counter(case_ids).items() if count > 1
    )
    for case_id in duplicate_case_ids:
        issues.append({"severity": "error", "case_id": case_id, "issue": "duplicate_case_id"})

    regime_counts = dict(sorted(Counter(case.regime for case in all_cases).items()))
    missing_regimes = sorted(set(manifest.expected_regimes) - set(regime_counts))
    if missing_regimes:
        issues.append(
            {
                "severity": "error",
                "issue": "missing_expected_regimes",
                "regimes": missing_regimes,
            }
        )

    return {
        "corpus_id": manifest.corpus_id,
        "version": manifest.version,
        "claim_status": manifest.claim_status,
        "case_count": len(all_cases),
        "case_files": [case_file.to_dict() for case_file in manifest.case_files],
        "expected_regimes": list(manifest.expected_regimes),
        "regime_counts": regime_counts,
        "question_family_counts": _counter_dict(case.question_family for case in all_cases),
        "degradation_condition_counts": _counter_dict(
            case.degradation_condition for case in all_cases
        ),
        "property_category_counts": _property_category_counts(all_cases),
        "strict_sufficiency_counts": {
            "sufficient": sum(case.ground_truth_sufficient() for case in all_cases),
            "insufficient": sum(not case.ground_truth_sufficient() for case in all_cases),
        },
        "label_contract": manifest.label_contract,
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _counter_dict(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _property_category_counts(cases: list[CaseManifest]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for property_name in DECISION_EVENT_PROPERTIES:
        counts[property_name] = _counter_dict(
            label.category
            for case in cases
            for label in case.property_labels
            if label.property == property_name
        )
    return counts
