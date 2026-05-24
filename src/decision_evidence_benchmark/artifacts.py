"""Reproducible artifact metadata helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_record(path: Path, *, role: str | None = None) -> dict[str, Any]:
    payload = {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    if role:
        payload["role"] = role
    return payload


def build_run_manifest(
    *,
    cases_path: Path,
    output_paths: Sequence[Path],
    case_count: int,
    baselines: Sequence[str],
    supporting_input_paths: Sequence[Path] = (),
    claim_status: str = "mechanical_run_only",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact_kind": "decision_evidence_benchmark_run",
        "claim_status": claim_status,
        "result_honesty": "Smoke and fixture outputs are not empirical evidence.",
        "inputs": [
            _artifact_record(cases_path, role="case_manifest_jsonl"),
            *(
                _artifact_record(path, role="supporting_artifact")
                for path in supporting_input_paths
            ),
        ],
        "outputs": [_artifact_record(path, role="run_output") for path in output_paths],
        "case_count": case_count,
        "baselines": list(baselines),
    }


def validate_run_manifest(
    manifest: dict[str, Any],
    *,
    expected_input_paths: Sequence[Path] = (),
    expected_output_paths: Sequence[Path] = (),
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
    if manifest.get("artifact_kind") != "decision_evidence_benchmark_run":
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_artifact_kind",
                "actual": manifest.get("artifact_kind"),
            }
        )

    inputs = _artifact_records(manifest.get("inputs"), field="inputs", issues=issues)
    outputs = _artifact_records(manifest.get("outputs"), field="outputs", issues=issues)
    _require_role(inputs, role="case_manifest_jsonl", field="inputs", issues=issues)
    _require_role(outputs, role="run_output", field="outputs", issues=issues)
    _require_expected_paths(
        inputs,
        expected_paths=expected_input_paths,
        field="inputs",
        issues=issues,
    )
    _require_expected_paths(
        outputs,
        expected_paths=expected_output_paths,
        field="outputs",
        issues=issues,
    )
    if verify_files:
        for field, records in (("inputs", inputs), ("outputs", outputs)):
            for index, record in enumerate(records):
                issues.extend(_artifact_integrity_issues(record, field=field, index=index))

    return {
        "metric_contract": "decision_evidence_run_manifest_validation",
        "claim_status": manifest.get("claim_status"),
        "input_count": len(inputs),
        "output_count": len(outputs),
        "input_roles": sorted({str(record.get("role", "")) for record in inputs}),
        "output_roles": sorted({str(record.get("role", "")) for record in outputs}),
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
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


def _require_role(
    records: list[dict[str, Any]],
    *,
    role: str,
    field: str,
    issues: list[dict[str, Any]],
) -> None:
    if not any(record.get("role") == role for record in records):
        issues.append(
            {
                "severity": "error",
                "issue": "missing_artifact_role",
                "field": field,
                "role": role,
            }
        )


def _require_expected_paths(
    records: list[dict[str, Any]],
    *,
    expected_paths: Sequence[Path],
    field: str,
    issues: list[dict[str, Any]],
) -> None:
    actual_paths = {_normalized_path(Path(str(record.get("path", "")))) for record in records}
    for expected_path in expected_paths:
        normalized_expected = _normalized_path(expected_path)
        if normalized_expected not in actual_paths:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_expected_artifact_path",
                    "field": field,
                    "path": str(expected_path),
                }
            )


def _normalized_path(path: Path) -> str:
    return str(path.expanduser().resolve() if path.exists() else path)


def _artifact_integrity_issues(
    record: dict[str, Any],
    *,
    field: str,
    index: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    path = Path(str(record.get("path", "")))
    if not record.get("path"):
        return [
            {
                "severity": "error",
                "issue": "missing_artifact_path",
                "field": field,
                "index": index,
            }
        ]
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
