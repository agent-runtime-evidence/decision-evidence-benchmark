"""Helpers for pinned externally generated baseline outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.baselines.registry import run_baseline
from decision_evidence_benchmark.metrics.overclaim import result_row
from decision_evidence_benchmark.schema import CaseManifest, ScorerOutput

BASELINE_OUTPUT_VALIDATION_CONTRACT = "decision_evidence_baseline_output_validation"
IMPORTED_BASELINE_IMPLEMENTATION_STATUS = "imported_model_run"


@dataclass(frozen=True)
class ImportedBaseline:
    name: str
    outputs: tuple[ScorerOutput, ...]
    source_path: Path | None = None


def baseline_result_rows(
    cases: Sequence[CaseManifest],
    baseline_names: Sequence[str],
    *,
    imported_baselines: Mapping[str, ImportedBaseline] | None = None,
    strict: bool = True,
) -> list[dict[str, Any]]:
    """Return result rows for deterministic and imported baselines."""

    imported_by_name = imported_baselines or {}
    _validate_import_scope(baseline_names, imported_by_name)
    indexed_imports = {
        name: _indexed_imported_outputs(cases, imported)
        for name, imported in imported_by_name.items()
    }

    rows: list[dict[str, Any]] = []
    for case in cases:
        for baseline_name in baseline_names:
            if baseline_name in indexed_imports:
                output = indexed_imports[baseline_name][case.case_id]
            else:
                output = run_baseline(baseline_name, case)
            rows.append(result_row(case, output, strict=strict))
    return rows


def validate_imported_baselines(
    cases: Sequence[CaseManifest],
    baseline_names: Sequence[str],
    *,
    imported_baselines: Mapping[str, ImportedBaseline] | None = None,
) -> dict[str, Any]:
    """Validate pinned external baseline outputs before metric use."""

    imported_by_name = imported_baselines or {}
    selected = set(baseline_names)
    issues: list[dict[str, Any]] = []
    for baseline_name in sorted(set(imported_by_name) - selected):
        issues.append(
            {
                "severity": "error",
                "baseline": baseline_name,
                "issue": "unselected_imported_baseline",
            }
        )
    for imported in (imported_by_name[name] for name in sorted(imported_by_name)):
        issues.extend(_imported_baseline_issues(cases, imported))

    return {
        "metric_contract": BASELINE_OUTPUT_VALIDATION_CONTRACT,
        "case_count": len(cases),
        "selected_baselines": list(baseline_names),
        "imported_baselines": sorted(imported_by_name),
        "baselines": {
            baseline_name: _imported_baseline_summary(cases, imported)
            for baseline_name, imported in sorted(imported_by_name.items())
        },
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def _validate_import_scope(
    baseline_names: Sequence[str],
    imported_baselines: Mapping[str, ImportedBaseline],
) -> None:
    selected = set(baseline_names)
    unused_imports = sorted(set(imported_baselines) - selected)
    if unused_imports:
        raise ValueError(
            "imported baseline outputs were provided for unselected baselines: "
            f"{', '.join(unused_imports)}"
        )


def _indexed_imported_outputs(
    cases: Sequence[CaseManifest],
    imported: ImportedBaseline,
) -> dict[str, ScorerOutput]:
    validation = validate_imported_baselines(
        cases,
        (imported.name,),
        imported_baselines={imported.name: imported},
    )
    if not validation["valid"]:
        source = f" in {imported.source_path}" if imported.source_path else ""
        raise ValueError(
            f"invalid imported baseline outputs for {imported.name}{source}: "
            f"{validation['issues'][0]['issue']}"
        )

    return {
        output.case_id: _with_import_metadata(output, imported)
        for output in imported.outputs
    }


def _imported_baseline_issues(
    cases: Sequence[CaseManifest],
    imported: ImportedBaseline,
) -> list[dict[str, Any]]:
    case_ids = {case.case_id for case in cases}
    observed_case_ids: set[str] = set()
    issues: list[dict[str, Any]] = []

    for output in imported.outputs:
        if output.scorer != imported.name:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "baseline": imported.name,
                    "scorer": output.scorer,
                    "issue": "scorer_baseline_mismatch",
                }
            )
            continue
        if output.case_id not in case_ids:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "baseline": imported.name,
                    "issue": "unknown_case_id",
                }
            )
            continue
        if output.case_id in observed_case_ids:
            issues.append(
                {
                    "severity": "error",
                    "case_id": output.case_id,
                    "baseline": imported.name,
                    "issue": "duplicate_baseline_output",
                }
            )
            continue
        observed_case_ids.add(output.case_id)

    missing_case_ids = sorted(case_ids - observed_case_ids)
    if missing_case_ids:
        issues.append(
            {
                "severity": "error",
                "baseline": imported.name,
                "issue": "missing_baseline_cases",
                "case_ids": missing_case_ids,
            }
        )
    return issues


def _imported_baseline_summary(
    cases: Sequence[CaseManifest],
    imported: ImportedBaseline,
) -> dict[str, Any]:
    case_ids = {case.case_id for case in cases}
    known_case_ids = {
        output.case_id
        for output in imported.outputs
        if output.scorer == imported.name and output.case_id in case_ids
    }
    payload: dict[str, Any] = {
        "outputs": len(imported.outputs),
        "known_cases": len(known_case_ids),
    }
    if imported.source_path:
        payload["source_path"] = str(imported.source_path)
    return payload


def _with_import_metadata(output: ScorerOutput, imported: ImportedBaseline) -> ScorerOutput:
    metadata = dict(output.metadata)
    metadata.setdefault("implementation_status", IMPORTED_BASELINE_IMPLEMENTATION_STATUS)
    if imported.source_path:
        metadata.setdefault("import_source_path", str(imported.source_path))
    return ScorerOutput(
        case_id=output.case_id,
        scorer=output.scorer,
        verdict=output.verdict,
        metadata=metadata,
        property_predictions=output.property_predictions,
    )
