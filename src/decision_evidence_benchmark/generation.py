"""Draft corpus generation for exercising manuscript-scale mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from decision_evidence_benchmark.adapters.registry import REGIME_IDS
from decision_evidence_benchmark.construction_oracle import categories_for_degradation
from decision_evidence_benchmark.io import write_cases_jsonl, write_jsonl
from decision_evidence_benchmark.schema import (
    DECISION_EVENT_PROPERTIES,
    CaseManifest,
    PropertyLabel,
    ScorerOutput,
    Verdict,
)

DRAFT_CORPUS_ID = "draft_balanced_64"
DRAFT_CLAIM_STATUS = "mechanical_draft_not_empirical_evidence"
DRAFT_LABEL_CALIBRATION_STATUS = "draft_two_annotator_fixture"
DRAFT_CASE_FIXTURE_STATUS = "draft_synthetic_not_manuscript_result"
DRAFT_SCORER_FIXTURE_STATUS = "draft_synthetic_oracle"
DRAFT_GENERATION_ID = "balanced_draft_v1"

QUESTION_FAMILIES = DECISION_EVENT_PROPERTIES
DEGRADATION_CONDITIONS = (
    "complete",
    "missing_delegation",
    "missing_policy",
    "missing_context",
    "conflicting_identity",
    "partial_graph",
    "final_only",
    "artifact_only",
)

DEFAULT_DRAFT_CASES_PATH = Path("data/cases/draft_balanced_64_cases.jsonl")
DEFAULT_DRAFT_ANNOTATIONS_PATH = Path(
    "data/annotations/draft_balanced_64_annotations.jsonl"
)
DEFAULT_DRAFT_SCORER_OUTPUTS_PATH = Path(
    "data/scorers/draft_balanced_64_scorer_outputs.jsonl"
)
DEFAULT_DRAFT_CORPUS_MANIFEST_PATH = Path("data/corpus/draft_balanced_64_corpus.yaml")


@dataclass(frozen=True)
class DraftCorpusArtifactPaths:
    cases: Path
    annotations: Path
    scorer_outputs: Path
    manifest: Path


def generate_balanced_draft_cases(case_count: int = 64) -> list[CaseManifest]:
    """Return a balanced draft corpus for end-to-end pipeline exercise."""

    cycle_size = len(REGIME_IDS) * len(DEGRADATION_CONDITIONS)
    if case_count < cycle_size or case_count % cycle_size != 0:
        raise ValueError(f"case_count must be a positive multiple of {cycle_size}")

    cases: list[CaseManifest] = []
    for index in range(case_count):
        regime_index = index % len(REGIME_IDS)
        cycle_index = index // len(REGIME_IDS)
        regime = REGIME_IDS[regime_index]
        degradation_condition = DEGRADATION_CONDITIONS[
            cycle_index % len(DEGRADATION_CONDITIONS)
        ]
        question_family = QUESTION_FAMILIES[
            (cycle_index + regime_index) % len(QUESTION_FAMILIES)
        ]
        cases.append(
            CaseManifest(
                case_id=(
                    f"draft-{regime}-{degradation_condition}-"
                    f"{question_family}-{index + 1:03d}"
                ),
                regime=regime,
                question_family=question_family,
                degradation_condition=degradation_condition,
                evidence=_draft_evidence(
                    regime=regime,
                    degradation_condition=degradation_condition,
                    question_family=question_family,
                    index=index,
                ),
                container_flags=_container_flags_for(
                    regime=regime,
                    degradation_condition=degradation_condition,
                ),
                property_labels=_property_labels_for(degradation_condition),
                metadata={
                    "fixture_status": DRAFT_CASE_FIXTURE_STATUS,
                    "generation": DRAFT_GENERATION_ID,
                    "cycle_index": cycle_index,
                    "regime_index": regime_index,
                    "result_honesty": (
                        "Draft synthetic scaffolding for mechanics only; not empirical "
                        "manuscript evidence."
                    ),
                },
            )
        )
    return cases


def draft_annotation_rows(cases: list[CaseManifest]) -> list[dict[str, Any]]:
    """Return two identical draft annotation rows per case."""

    rows: list[dict[str, Any]] = []
    for case in cases:
        labels = [
            _retag_label(label, source="draft_two_annotator_fixture").to_dict()
            for label in case.property_labels
        ]
        for annotator_id in ("draft_annotator_a", "draft_annotator_b"):
            rows.append(
                {
                    "case_id": case.case_id,
                    "annotator_id": annotator_id,
                    "property_labels": labels,
                    "metadata": {
                        "fixture_status": DRAFT_LABEL_CALIBRATION_STATUS,
                        "generation": DRAFT_GENERATION_ID,
                        "result_honesty": (
                            "Mechanical twin labels for pipeline exercise only; replace "
                            "with independent two-annotator labels before manuscript use."
                        ),
                    },
                }
            )
    return rows


def draft_scorer_outputs(cases: list[CaseManifest]) -> list[ScorerOutput]:
    """Return oracle-like scorer outputs that must remain manuscript-blocking."""

    outputs: list[ScorerOutput] = []
    for case in cases:
        verdict: Verdict = "sufficient" if case.ground_truth_sufficient() else "insufficient"
        outputs.append(
            ScorerOutput(
                case_id=case.case_id,
                scorer="decision_trace_reconstructor",
                verdict=verdict,
                metadata={
                    "fixture_status": DRAFT_SCORER_FIXTURE_STATUS,
                    "generation": DRAFT_GENERATION_ID,
                    "result_honesty": (
                        "Synthetic oracle-shaped output for scorer pipeline exercise only."
                    ),
                },
                property_predictions=tuple(
                    _retag_label(label, source="draft_synthetic_prediction")
                    for label in case.property_labels
                ),
            )
        )
    return outputs


def draft_corpus_manifest(cases_path: Path, annotations_path: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "corpus_id": DRAFT_CORPUS_ID,
        "version": "0.0.0-draft",
        "claim_status": DRAFT_CLAIM_STATUS,
        "expected_regimes": sorted(REGIME_IDS),
        "case_files": [
            {
                "path": str(cases_path),
                "role": "case_manifest_jsonl",
            }
        ],
        "label_contract": {
            "mode": "embedded_property_labels",
            "calibration_status": DRAFT_LABEL_CALIBRATION_STATUS,
            "required_properties": list(DECISION_EVENT_PROPERTIES),
            "annotation_files": [
                {
                    "path": str(annotations_path),
                    "role": "two_annotator_property_labels",
                }
            ],
        },
        "readiness_targets": {
            "min_cases": 64,
            "min_regimes": 8,
            "min_degradation_conditions": 8,
            "min_question_families": 8,
            "min_cases_per_regime": 8,
            "min_cases_per_degradation_condition": 8,
            "min_cases_per_question_family": 8,
            "min_strict_sufficient_cases": 8,
            "min_strict_insufficient_cases": 8,
            "min_complete_labels_per_property": 1,
            "min_non_complete_labels_per_property": 1,
            "min_label_cohen_kappa": 0.6,
            "min_label_property_cohen_kappa": 0.6,
        },
    }


def write_draft_corpus_artifacts(
    *,
    cases_path: Path = DEFAULT_DRAFT_CASES_PATH,
    annotations_path: Path = DEFAULT_DRAFT_ANNOTATIONS_PATH,
    scorer_outputs_path: Path = DEFAULT_DRAFT_SCORER_OUTPUTS_PATH,
    manifest_path: Path = DEFAULT_DRAFT_CORPUS_MANIFEST_PATH,
    case_count: int = 64,
) -> DraftCorpusArtifactPaths:
    cases = generate_balanced_draft_cases(case_count=case_count)

    write_cases_jsonl(cases_path, cases)
    write_jsonl(annotations_path, draft_annotation_rows(cases))
    write_jsonl(
        scorer_outputs_path,
        (output.to_dict() for output in draft_scorer_outputs(cases)),
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(draft_corpus_manifest(cases_path, annotations_path), sort_keys=False)
    )
    return DraftCorpusArtifactPaths(
        cases=cases_path,
        annotations=annotations_path,
        scorer_outputs=scorer_outputs_path,
        manifest=manifest_path,
    )


def _draft_evidence(
    *,
    regime: str,
    degradation_condition: str,
    question_family: str,
    index: int,
) -> dict[str, Any]:
    return {
        "draft_fixture_ref": f"{DRAFT_GENERATION_ID}:{index + 1:03d}",
        "native_regime": regime,
        "degradation_condition": degradation_condition,
        "governance_question": question_family,
        "evidence_plane": "synthetic_mechanics_fixture",
    }


def _container_flags_for(*, regime: str, degradation_condition: str) -> dict[str, Any]:
    ledger_native_regimes = {
        "dcc_hdp",
        "dynamic_capabilities",
        "llm_audit_trails",
        "prov",
    }
    return {
        "trace_present": True,
        "ledger_present": regime in ledger_native_regimes
        or degradation_condition in {"complete", "partial_graph"},
        "schema_valid": True,
        "checklist_complete": degradation_condition
        not in {"missing_policy", "final_only", "artifact_only"},
        "source_validator_passed": degradation_condition
        not in {"conflicting_identity", "final_only"},
        "llm_judge_verdict": "sufficient",
    }


def _property_labels_for(degradation_condition: str) -> tuple[PropertyLabel, ...]:
    categories = categories_for_degradation(degradation_condition)
    return tuple(
        PropertyLabel(
            property=property_name,
            category=categories[property_name],
            source="draft_synthetic_label",
            notes=f"{degradation_condition} draft corpus scaffold.",
        )
        for property_name in DECISION_EVENT_PROPERTIES
    )


def _retag_label(label: PropertyLabel, *, source: str) -> PropertyLabel:
    return PropertyLabel(
        property=label.property,
        category=label.category,
        required=label.required,
        source=source,
        notes=label.notes,
    )
