"""End-to-end result package assembly."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from decision_evidence_benchmark.artifacts import build_run_manifest, sha256_file
from decision_evidence_benchmark.baselines import (
    BASELINE_REGISTRY,
    ImportedBaseline,
    baseline_result_rows,
    validate_imported_baselines,
)
from decision_evidence_benchmark.corpus import validate_corpus_manifest
from decision_evidence_benchmark.evaluation import (
    evaluate_scorer_outputs,
    validate_scorer_outputs,
)
from decision_evidence_benchmark.io import (
    read_cases_jsonl,
    read_scorer_outputs_jsonl,
    write_cases_jsonl,
    write_json,
    write_jsonl,
)
from decision_evidence_benchmark.labels import (
    adjudicate_cases,
    calibration_summary,
    label_review_summary,
    read_adjudication_overrides_jsonl,
    read_annotations_jsonl,
    write_label_review_csv,
)
from decision_evidence_benchmark.metrics.overclaim import summarize_outputs
from decision_evidence_benchmark.readiness import build_readiness_report
from decision_evidence_benchmark.readiness_gaps import build_readiness_gap_report


@dataclass(frozen=True)
class ResultPackagePaths:
    adjudicated_corpus_manifest: Path
    corpus_validation: Path
    label_calibration: Path
    label_review: Path
    label_review_csv: Path
    label_adjudication: Path
    adjudicated_cases: Path
    scorer_validation: Path
    scorer_results: Path
    scorer_summary: Path
    baseline_validation: Path
    baseline_results: Path
    baseline_summary: Path
    run_manifest: Path
    readiness_report: Path
    readiness_gaps: Path
    package_manifest: Path


def default_result_package_paths(out_dir: Path, prefix: str) -> ResultPackagePaths:
    return ResultPackagePaths(
        adjudicated_corpus_manifest=out_dir / f"{prefix}_adjudicated_corpus.yaml",
        corpus_validation=out_dir / f"{prefix}_corpus_validation.json",
        label_calibration=out_dir / f"{prefix}_label_calibration.json",
        label_review=out_dir / f"{prefix}_label_review.json",
        label_review_csv=out_dir / f"{prefix}_label_review.csv",
        label_adjudication=out_dir / f"{prefix}_label_adjudication.json",
        adjudicated_cases=out_dir / f"{prefix}_adjudicated_cases.jsonl",
        scorer_validation=out_dir / f"{prefix}_scorer_validation.json",
        scorer_results=out_dir / f"{prefix}_scorer_results.jsonl",
        scorer_summary=out_dir / f"{prefix}_scorer_summary.json",
        baseline_validation=out_dir / f"{prefix}_baseline_validation.json",
        baseline_results=out_dir / f"{prefix}_baseline_results.jsonl",
        baseline_summary=out_dir / f"{prefix}_baseline_summary.json",
        run_manifest=out_dir / f"{prefix}_run_manifest.json",
        readiness_report=out_dir / f"{prefix}_readiness_report.json",
        readiness_gaps=out_dir / f"{prefix}_readiness_gaps.json",
        package_manifest=out_dir / f"{prefix}_package_manifest.json",
    )


def build_result_package(
    *,
    corpus_manifest_path: Path,
    cases_path: Path,
    annotations_path: Path,
    scorer_predictions_path: Path,
    out_dir: Path,
    prefix: str,
    baselines: Sequence[str] | None = None,
    run_claim_status: str = "mechanical_run_only",
    adjudication_overrides_path: Path | None = None,
    llm_judge_predictions_path: Path | None = None,
) -> dict[str, Any]:
    paths = default_result_package_paths(out_dir, prefix)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = read_cases_jsonl(cases_path)
    annotations = read_annotations_jsonl(annotations_path)
    scorer_outputs = read_scorer_outputs_jsonl(scorer_predictions_path)
    baseline_names = tuple(baselines or sorted(BASELINE_REGISTRY))
    imported_baselines = _imported_baselines(
        llm_judge_predictions_path=llm_judge_predictions_path,
    )

    label_calibration = calibration_summary(cases, annotations)
    write_json(paths.label_calibration, label_calibration)

    label_review = label_review_summary(cases, annotations)
    write_json(paths.label_review, label_review)
    write_label_review_csv(paths.label_review_csv, label_review)

    adjudication_overrides = (
        read_adjudication_overrides_jsonl(adjudication_overrides_path)
        if adjudication_overrides_path
        else []
    )
    adjudicated_cases, label_adjudication = adjudicate_cases(
        cases,
        annotations,
        adjudication_overrides,
    )
    write_json(paths.label_adjudication, label_adjudication)
    write_cases_jsonl(paths.adjudicated_cases, adjudicated_cases)
    _write_adjudicated_corpus_manifest(
        source_path=corpus_manifest_path,
        out_path=paths.adjudicated_corpus_manifest,
        adjudicated_cases_path=paths.adjudicated_cases,
    )

    corpus_validation = validate_corpus_manifest(paths.adjudicated_corpus_manifest)
    write_json(paths.corpus_validation, corpus_validation)

    scorer_validation = validate_scorer_outputs(adjudicated_cases, scorer_outputs)
    write_json(paths.scorer_validation, scorer_validation)

    scorer_evaluation = evaluate_scorer_outputs(adjudicated_cases, scorer_outputs)
    write_jsonl(paths.scorer_results, scorer_evaluation["rows"])
    write_json(paths.scorer_summary, scorer_evaluation["summary"])

    baseline_validation = validate_imported_baselines(
        adjudicated_cases,
        baseline_names,
        imported_baselines=imported_baselines,
    )
    write_json(paths.baseline_validation, baseline_validation)

    baseline_rows = baseline_result_rows(
        adjudicated_cases,
        baseline_names,
        imported_baselines=imported_baselines,
    )
    write_jsonl(paths.baseline_results, baseline_rows)
    baseline_summary = summarize_outputs(baseline_rows)
    write_json(paths.baseline_summary, baseline_summary)

    run_manifest = build_run_manifest(
        cases_path=paths.adjudicated_cases,
        output_paths=(paths.baseline_results, paths.baseline_summary),
        case_count=len(adjudicated_cases),
        baselines=baseline_names,
        supporting_input_paths=(
            paths.adjudicated_corpus_manifest,
            paths.corpus_validation,
            paths.label_calibration,
            paths.label_review,
            paths.label_adjudication,
            paths.scorer_validation,
            paths.scorer_summary,
            paths.baseline_validation,
            *(
                imported.source_path
                for imported in imported_baselines.values()
                if imported.source_path
            ),
        ),
        claim_status=run_claim_status,
    )
    write_json(paths.run_manifest, run_manifest)

    readiness_report = build_readiness_report(
        corpus_validation_path=paths.corpus_validation,
        label_calibration_path=paths.label_calibration,
        label_review_path=paths.label_review,
        label_adjudication_path=paths.label_adjudication,
        scorer_validation_path=paths.scorer_validation,
        scorer_summary_path=paths.scorer_summary,
        baseline_validation_path=paths.baseline_validation,
        baseline_summary_path=paths.baseline_summary,
        run_manifest_path=paths.run_manifest,
        required_baselines=baseline_names,
    )
    write_json(paths.readiness_report, readiness_report)
    readiness_gaps = build_readiness_gap_report(readiness_report)
    write_json(paths.readiness_gaps, readiness_gaps)

    package_manifest = _package_manifest(
        paths=paths,
        corpus_manifest_path=corpus_manifest_path,
        cases_path=cases_path,
        annotations_path=annotations_path,
        adjudication_overrides_path=adjudication_overrides_path,
        scorer_predictions_path=scorer_predictions_path,
        llm_judge_predictions_path=llm_judge_predictions_path,
        case_count=len(adjudicated_cases),
        baseline_names=baseline_names,
        run_claim_status=run_claim_status,
        label_adjudication=label_adjudication,
        readiness_report=readiness_report,
    )
    write_json(paths.package_manifest, package_manifest)
    return package_manifest


def _imported_baselines(
    *,
    llm_judge_predictions_path: Path | None,
) -> dict[str, ImportedBaseline]:
    if not llm_judge_predictions_path:
        return {}
    return {
        "llm_judge": ImportedBaseline(
            name="llm_judge",
            outputs=tuple(read_scorer_outputs_jsonl(llm_judge_predictions_path)),
            source_path=llm_judge_predictions_path,
        )
    }


def validate_result_package_manifest(
    manifest: dict[str, Any],
    *,
    verify_files: bool = True,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if manifest.get("schema_version") != 1:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_schema_version",
                "actual": manifest.get("schema_version"),
            }
        )
    if manifest.get("artifact_kind") != "decision_evidence_result_package":
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_artifact_kind",
                "actual": manifest.get("artifact_kind"),
            }
        )

    input_artifacts = _artifact_records(
        manifest.get("input_artifacts"),
        field="input_artifacts",
        issues=issues,
    )
    output_artifacts = _artifact_records(
        manifest.get("output_artifacts"),
        field="output_artifacts",
        issues=issues,
    )
    _require_roles(
        input_artifacts,
        field="input_artifacts",
        roles=("corpus_manifest", "case_manifest_jsonl", "annotation_jsonl", "scorer_jsonl"),
        issues=issues,
    )
    _require_roles(
        output_artifacts,
        field="output_artifacts",
        roles=(
            "corpus_validation",
            "adjudicated_corpus_manifest",
            "label_calibration",
            "label_review",
            "label_review_csv",
            "label_adjudication",
            "adjudicated_cases",
            "scorer_validation",
            "scorer_results",
            "scorer_summary",
            "baseline_validation",
            "baseline_results",
            "baseline_summary",
            "run_manifest",
            "readiness_report",
            "readiness_gaps",
        ),
        issues=issues,
    )
    if verify_files:
        for field_name, records in (
            ("input_artifacts", input_artifacts),
            ("output_artifacts", output_artifacts),
        ):
            for index, record in enumerate(records):
                issues.extend(
                    _artifact_integrity_issues(record, field=field_name, index=index)
                )

    return {
        "metric_contract": "decision_evidence_result_package_validation",
        "claim_status": manifest.get("claim_status"),
        "input_count": len(input_artifacts),
        "output_count": len(output_artifacts),
        "input_roles": sorted({str(record.get("role", "")) for record in input_artifacts}),
        "output_roles": sorted({str(record.get("role", "")) for record in output_artifacts}),
        "mechanics_valid": manifest.get("mechanics_valid"),
        "manuscript_result_ready": manifest.get("manuscript_result_ready"),
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }


def validate_result_package_file(path: Path, *, verify_files: bool = True) -> dict[str, Any]:
    return validate_result_package_manifest(
        json.loads(path.read_text()),
        verify_files=verify_files,
    )


def _package_manifest(
    *,
    paths: ResultPackagePaths,
    corpus_manifest_path: Path,
    cases_path: Path,
    annotations_path: Path,
    adjudication_overrides_path: Path | None,
    scorer_predictions_path: Path,
    llm_judge_predictions_path: Path | None,
    case_count: int,
    baseline_names: Sequence[str],
    run_claim_status: str,
    label_adjudication: dict[str, Any],
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    input_artifacts = [
        _artifact_record(corpus_manifest_path, role="corpus_manifest"),
        _artifact_record(cases_path, role="case_manifest_jsonl"),
        _artifact_record(annotations_path, role="annotation_jsonl"),
        _artifact_record(scorer_predictions_path, role="scorer_jsonl"),
    ]
    if adjudication_overrides_path:
        input_artifacts.append(
            _artifact_record(adjudication_overrides_path, role="adjudication_overrides_jsonl")
        )
    if llm_judge_predictions_path:
        input_artifacts.append(
            _artifact_record(llm_judge_predictions_path, role="llm_judge_jsonl")
        )

    inputs = {
        "corpus_manifest": str(corpus_manifest_path),
        "cases": str(cases_path),
        "annotations": str(annotations_path),
        "scorer_predictions": str(scorer_predictions_path),
    }
    if adjudication_overrides_path:
        inputs["adjudication_overrides"] = str(adjudication_overrides_path)
    if llm_judge_predictions_path:
        inputs["llm_judge_predictions"] = str(llm_judge_predictions_path)

    return {
        "schema_version": 1,
        "artifact_kind": "decision_evidence_result_package",
        "claim_status": run_claim_status,
        "result_honesty": (
            "A result package is manuscript-ready only when readiness_report."
            "manuscript_result_ready is true."
        ),
        "inputs": inputs,
        "outputs": {field.name: str(getattr(paths, field.name)) for field in fields(paths)},
        "input_artifacts": input_artifacts,
        "output_artifacts": [
            _artifact_record(
                paths.adjudicated_corpus_manifest,
                role="adjudicated_corpus_manifest",
            ),
            _artifact_record(paths.corpus_validation, role="corpus_validation"),
            _artifact_record(paths.label_calibration, role="label_calibration"),
            _artifact_record(paths.label_review, role="label_review"),
            _artifact_record(paths.label_review_csv, role="label_review_csv"),
            _artifact_record(paths.label_adjudication, role="label_adjudication"),
            _artifact_record(paths.adjudicated_cases, role="adjudicated_cases"),
            _artifact_record(paths.scorer_validation, role="scorer_validation"),
            _artifact_record(paths.scorer_results, role="scorer_results"),
            _artifact_record(paths.scorer_summary, role="scorer_summary"),
            _artifact_record(paths.baseline_validation, role="baseline_validation"),
            _artifact_record(paths.baseline_results, role="baseline_results"),
            _artifact_record(paths.baseline_summary, role="baseline_summary"),
            _artifact_record(paths.run_manifest, role="run_manifest"),
            _artifact_record(paths.readiness_report, role="readiness_report"),
            _artifact_record(paths.readiness_gaps, role="readiness_gaps"),
        ],
        "package_manifest_self_checksum_excluded": True,
        "case_count": case_count,
        "baselines": list(baseline_names),
        "adjudication_valid": label_adjudication["valid"],
        "adjudication_unresolved_label_count": label_adjudication[
            "unresolved_label_count"
        ],
        "mechanics_valid": readiness_report["mechanics_valid"],
        "manuscript_result_ready": readiness_report["manuscript_result_ready"],
        "blocking_reasons": readiness_report["blocking_reasons"],
    }


def _write_adjudicated_corpus_manifest(
    *,
    source_path: Path,
    out_path: Path,
    adjudicated_cases_path: Path,
) -> None:
    value = yaml.safe_load(source_path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{source_path}: corpus manifest must be a mapping")
    value["case_files"] = [
        {
            "path": str(adjudicated_cases_path),
            "role": "case_manifest_jsonl",
        }
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(value, sort_keys=False))


def _artifact_record(path: Path, *, role: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "role": role,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _artifact_records(
    value: object,
    *,
    field: str,
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        issues.append({"severity": "error", "issue": "artifact_field_not_list", "field": field})
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            records.append(item)
        else:
            issues.append(
                {
                    "severity": "error",
                    "issue": "artifact_record_not_mapping",
                    "field": field,
                    "index": index,
                }
            )
    return records


def _require_roles(
    records: list[dict[str, Any]],
    *,
    field: str,
    roles: Sequence[str],
    issues: list[dict[str, Any]],
) -> None:
    observed_roles = {str(record.get("role", "")) for record in records}
    for role in roles:
        if role not in observed_roles:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_artifact_role",
                    "field": field,
                    "role": role,
                }
            )


def _artifact_integrity_issues(
    record: dict[str, Any],
    *,
    field: str,
    index: int,
) -> list[dict[str, Any]]:
    if not record.get("path"):
        return [
            {
                "severity": "error",
                "issue": "missing_artifact_path",
                "field": field,
                "index": index,
            }
        ]
    path = Path(str(record["path"]))
    if not path.exists():
        return [
            {
                "severity": "error",
                "issue": "artifact_path_not_found",
                "field": field,
                "index": index,
                "path": str(path),
            }
        ]

    issues: list[dict[str, Any]] = []
    actual_bytes = path.stat().st_size
    if record.get("bytes") != actual_bytes:
        issues.append(
            {
                "severity": "error",
                "issue": "artifact_bytes_mismatch",
                "field": field,
                "index": index,
                "path": str(path),
                "expected": record.get("bytes"),
                "actual": actual_bytes,
            }
        )
    actual_sha256 = sha256_file(path)
    if record.get("sha256") != actual_sha256:
        issues.append(
            {
                "severity": "error",
                "issue": "artifact_sha256_mismatch",
                "field": field,
                "index": index,
                "path": str(path),
                "expected": record.get("sha256"),
                "actual": actual_sha256,
            }
        )
    return issues
