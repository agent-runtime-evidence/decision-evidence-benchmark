"""Deterministic construction-derived labels for manuscript cases."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import yaml

from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    PROPERTY_CATEGORIES,
    CaseManifest,
    PropertyLabel,
    Verdict,
)

ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_ORACLE_SPEC_PATH: Final = ROOT / "data/oracle/construction_oracle_v1.yaml"


@dataclass(frozen=True)
class OracleRule:
    rule_id: str
    description: str
    overrides: dict[str, str]


@dataclass(frozen=True)
class ConstructionOracleSpec:
    path: Path
    schema_version: int
    oracle_version: str
    calibration_status: str
    annotation_status: str
    label_source: str
    annotation_source: str
    default_category: str
    strict_sufficient_categories: tuple[str, ...]
    properties: tuple[str, ...]
    degradation_conditions: dict[str, OracleRule]
    leakage_guard: dict[str, Any]

    @property
    def degradation_category_overrides(self) -> dict[str, dict[str, str]]:
        return {
            degradation_condition: dict(rule.overrides)
            for degradation_condition, rule in self.degradation_conditions.items()
        }


def load_oracle_spec(path: Path = DEFAULT_ORACLE_SPEC_PATH) -> ConstructionOracleSpec:
    payload = yaml.safe_load(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: oracle spec must be a mapping")
    spec = ConstructionOracleSpec(
        path=path,
        schema_version=int(payload.get("schema_version", 0)),
        oracle_version=str(payload.get("oracle_version", "")),
        calibration_status=str(payload.get("calibration_status", "")),
        annotation_status=str(payload.get("annotation_status", "")),
        label_source=str(payload.get("label_source", "")),
        annotation_source=str(payload.get("annotation_source", "")),
        default_category=str(payload.get("default_category", "")),
        strict_sufficient_categories=tuple(
            str(item) for item in payload.get("strict_sufficient_categories", [])
        ),
        properties=tuple(str(item) for item in payload.get("properties", [])),
        degradation_conditions=_parse_degradation_conditions(
            payload.get("degradation_conditions", {})
        ),
        leakage_guard=dict(payload.get("leakage_guard", {})),
    )
    _validate_spec(spec)
    return spec


@lru_cache(maxsize=1)
def default_oracle_spec() -> ConstructionOracleSpec:
    return load_oracle_spec(DEFAULT_ORACLE_SPEC_PATH)


def oracle_spec_sha256(path: Path = DEFAULT_ORACLE_SPEC_PATH) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def categories_for_degradation(
    degradation_condition: str,
    *,
    spec: ConstructionOracleSpec | None = None,
) -> dict[str, str]:
    """Return the full property-category vector implied by a degradation condition."""

    oracle_spec = spec or default_oracle_spec()
    if degradation_condition not in oracle_spec.degradation_conditions:
        raise ValueError(f"unknown degradation condition: {degradation_condition}")
    categories = {
        property_name: oracle_spec.default_category
        for property_name in oracle_spec.properties
    }
    categories.update(oracle_spec.degradation_conditions[degradation_condition].overrides)
    return categories


def labels_for_degradation(
    degradation_condition: str,
    *,
    source: str | None = None,
    spec: ConstructionOracleSpec | None = None,
) -> tuple[PropertyLabel, ...]:
    """Return deterministic property labels for a degradation condition."""

    oracle_spec = spec or default_oracle_spec()
    categories = categories_for_degradation(degradation_condition, spec=oracle_spec)
    rule = oracle_spec.degradation_conditions[degradation_condition]
    label_source = source or oracle_spec.label_source
    return tuple(
        PropertyLabel(
            property=property_name,
            category=categories[property_name],
            required=True,
            source=label_source,
            notes=_label_note(
                oracle_version=oracle_spec.oracle_version,
                rule_id=rule.rule_id,
                degradation_condition=degradation_condition,
                property_name=property_name,
                category=categories[property_name],
                overridden=property_name in rule.overrides,
            ),
        )
        for property_name in oracle_spec.properties
    )


def labels_for_case(
    case: CaseManifest,
    *,
    source: str | None = None,
    spec: ConstructionOracleSpec | None = None,
) -> tuple[PropertyLabel, ...]:
    """Return construction-derived labels for a case manifest."""

    return labels_for_degradation(case.degradation_condition, source=source, spec=spec)


def rule_id_for_degradation(
    degradation_condition: str,
    *,
    spec: ConstructionOracleSpec | None = None,
) -> str:
    oracle_spec = spec or default_oracle_spec()
    if degradation_condition not in oracle_spec.degradation_conditions:
        raise ValueError(f"unknown degradation condition: {degradation_condition}")
    return oracle_spec.degradation_conditions[degradation_condition].rule_id


def verdict_for_labels(labels: tuple[PropertyLabel, ...], *, strict: bool = True) -> Verdict:
    """Return a verdict implied by a complete property-label vector."""

    if not labels:
        raise ValueError("verdict_for_labels requires at least one label")
    if all(label.sufficient(strict=strict) for label in labels):
        return "sufficient"
    return "insufficient"


def verdict_for_case(case: CaseManifest, *, strict: bool = True) -> Verdict:
    """Return the construction-oracle sufficiency verdict for a case."""

    return verdict_for_labels(labels_for_case(case), strict=strict)


def _parse_degradation_conditions(value: object) -> dict[str, OracleRule]:
    if not isinstance(value, dict):
        raise ValueError("degradation_conditions must be a mapping")
    rules: dict[str, OracleRule] = {}
    for degradation_condition, raw_rule in value.items():
        if not isinstance(raw_rule, dict):
            raise ValueError(f"{degradation_condition}: rule must be a mapping")
        raw_overrides = raw_rule.get("overrides", {})
        if not isinstance(raw_overrides, dict):
            raise ValueError(f"{degradation_condition}: overrides must be a mapping")
        rules[str(degradation_condition)] = OracleRule(
            rule_id=str(raw_rule.get("rule_id", "")),
            description=str(raw_rule.get("description", "")),
            overrides={
                str(property_name): str(category)
                for property_name, category in raw_overrides.items()
            },
        )
    return rules


def _validate_spec(spec: ConstructionOracleSpec) -> None:
    if spec.schema_version != 1:
        raise ValueError(f"{spec.path}: unsupported oracle schema_version")
    if not spec.oracle_version:
        raise ValueError(f"{spec.path}: oracle_version is required")
    if spec.properties != DECISION_EVENT_PROPERTIES:
        raise ValueError(f"{spec.path}: properties must match Decision Event Schema order")
    if spec.default_category not in PROPERTY_CATEGORIES:
        raise ValueError(f"{spec.path}: unknown default_category={spec.default_category}")
    for category in spec.strict_sufficient_categories:
        if category not in PROPERTY_CATEGORIES:
            raise ValueError(f"{spec.path}: unknown strict sufficient category={category}")
    for degradation_condition, rule in spec.degradation_conditions.items():
        if not rule.rule_id:
            raise ValueError(f"{spec.path}: missing rule_id for {degradation_condition}")
        if not rule.description:
            raise ValueError(f"{spec.path}: missing description for {degradation_condition}")
        for property_name, category in rule.overrides.items():
            if property_name not in DECISION_EVENT_PROPERTIES:
                raise ValueError(f"{spec.path}: unknown property={property_name}")
            if category not in PROPERTY_CATEGORIES:
                raise ValueError(f"{spec.path}: unknown category={category}")


def _label_note(
    *,
    oracle_version: str,
    rule_id: str,
    degradation_condition: str,
    property_name: str,
    category: str,
    overridden: bool,
) -> str:
    if overridden:
        return (
            f"{oracle_version}: {rule_id}; degradation_condition="
            f"{degradation_condition} sets {property_name}={category}."
        )
    return (
        f"{oracle_version}: {rule_id}; degradation_condition="
        f"{degradation_condition} leaves {property_name}=complete."
    )


_DEFAULT_SPEC: Final = default_oracle_spec()
CONSTRUCTION_ORACLE_VERSION: Final = _DEFAULT_SPEC.oracle_version
CONSTRUCTION_ORACLE_CALIBRATION_STATUS: Final = _DEFAULT_SPEC.calibration_status
CONSTRUCTION_ORACLE_ANNOTATION_STATUS: Final = _DEFAULT_SPEC.annotation_status
CONSTRUCTION_ORACLE_LABEL_SOURCE: Final = _DEFAULT_SPEC.label_source
CONSTRUCTION_ORACLE_ANNOTATION_SOURCE: Final = _DEFAULT_SPEC.annotation_source
CONSTRUCTION_ORACLE_ANNOTATOR_IDS: Final = (
    "construction_rule_oracle_a",
    "construction_rule_oracle_b",
)
DEGRADATION_CATEGORY_OVERRIDES: Final = _DEFAULT_SPEC.degradation_category_overrides
