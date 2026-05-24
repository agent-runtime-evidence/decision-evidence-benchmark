"""Export manuscript-facing tables from result package artifacts."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANUSCRIPT_TABLE_EXPORT_METRIC_CONTRACT = "decision_evidence_manuscript_table_export"


@dataclass(frozen=True)
class ManuscriptTablePaths:
    status_summary: Path
    gate_status_csv: Path
    readiness_blockers_csv: Path
    artifact_inventory_csv: Path


def default_manuscript_table_paths(out_dir: Path, prefix: str) -> ManuscriptTablePaths:
    return ManuscriptTablePaths(
        status_summary=out_dir / f"{prefix}_table_export_summary.json",
        gate_status_csv=out_dir / f"{prefix}_gate_status.csv",
        readiness_blockers_csv=out_dir / f"{prefix}_readiness_blockers.csv",
        artifact_inventory_csv=out_dir / f"{prefix}_artifact_inventory.csv",
    )


def default_manuscript_table_prefix(package_manifest_path: Path) -> str:
    stem = package_manifest_path.stem
    suffix = "_package_manifest"
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return stem


def export_manuscript_tables(
    *,
    package_manifest_path: Path,
    out_dir: Path,
    prefix: str | None = None,
) -> dict[str, Any]:
    package_manifest = json.loads(package_manifest_path.read_text())
    table_prefix = prefix or default_manuscript_table_prefix(package_manifest_path)
    paths = default_manuscript_table_paths(out_dir, table_prefix)
    out_dir.mkdir(parents=True, exist_ok=True)

    readiness_gaps, issues = _read_readiness_gaps(
        package_manifest,
        package_manifest_path=package_manifest_path,
    )
    blockers = _blocker_rows(readiness_gaps)
    input_artifacts = _artifact_rows(package_manifest.get("input_artifacts"), "input")
    output_artifacts = _artifact_rows(package_manifest.get("output_artifacts"), "output")
    gate_row = _gate_status_row(
        package_manifest,
        readiness_gaps=readiness_gaps,
        input_artifact_count=len(input_artifacts),
        output_artifact_count=len(output_artifacts),
    )

    _write_csv(paths.gate_status_csv, [gate_row], tuple(gate_row))
    _write_csv(
        paths.readiness_blockers_csv,
        blockers,
        (
            "artifact_area",
            "category",
            "reason",
            "action",
            "manuscript_blocking",
        ),
    )
    _write_csv(
        paths.artifact_inventory_csv,
        [*input_artifacts, *output_artifacts],
        ("artifact_set", "role", "path", "bytes", "sha256"),
    )

    summary = {
        "metric_contract": MANUSCRIPT_TABLE_EXPORT_METRIC_CONTRACT,
        "source_package_manifest": str(package_manifest_path),
        "claim_status": package_manifest.get("claim_status"),
        "mechanics_valid": bool(package_manifest.get("mechanics_valid")),
        "manuscript_result_ready": bool(package_manifest.get("manuscript_result_ready")),
        "case_count": package_manifest.get("case_count"),
        "baseline_count": _sequence_count(package_manifest.get("baselines")),
        "blocker_count": readiness_gaps.get("blocker_count"),
        "artifact_area_counts": readiness_gaps.get("artifact_area_counts", {}),
        "outputs": {
            "status_summary": str(paths.status_summary),
            "gate_status_csv": str(paths.gate_status_csv),
            "readiness_blockers_csv": str(paths.readiness_blockers_csv),
            "artifact_inventory_csv": str(paths.artifact_inventory_csv),
        },
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }
    paths.status_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def _read_readiness_gaps(
    package_manifest: dict[str, Any],
    *,
    package_manifest_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    outputs = package_manifest.get("outputs", {})
    if not isinstance(outputs, dict) or not isinstance(outputs.get("readiness_gaps"), str):
        return {}, [{"severity": "error", "issue": "missing_readiness_gaps_output"}]
    path = _resolve_artifact_path(
        outputs["readiness_gaps"],
        package_manifest_path=package_manifest_path,
    )
    if not path.exists():
        return (
            {},
            [
                {
                    "severity": "error",
                    "issue": "readiness_gaps_path_not_found",
                    "path": str(path),
                }
            ],
        )
    return json.loads(path.read_text()), []


def _resolve_artifact_path(raw_path: str, *, package_manifest_path: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    sibling = package_manifest_path.parent / path.name
    if sibling.exists():
        return sibling
    return package_manifest_path.parent / path


def _blocker_rows(readiness_gaps: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = readiness_gaps.get("blockers", [])
    if not isinstance(blockers, list):
        return []
    rows: list[dict[str, Any]] = []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        rows.append(
            {
                "artifact_area": blocker.get("artifact_area", ""),
                "category": blocker.get("category", ""),
                "reason": blocker.get("reason", ""),
                "action": blocker.get("action", ""),
                "manuscript_blocking": blocker.get("manuscript_blocking", ""),
            }
        )
    return rows


def _artifact_rows(value: object, artifact_set: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "artifact_set": artifact_set,
                "role": item.get("role", ""),
                "path": item.get("path", ""),
                "bytes": item.get("bytes", ""),
                "sha256": item.get("sha256", ""),
            }
        )
    return rows


def _gate_status_row(
    package_manifest: dict[str, Any],
    *,
    readiness_gaps: dict[str, Any],
    input_artifact_count: int,
    output_artifact_count: int,
) -> dict[str, Any]:
    return {
        "claim_status": package_manifest.get("claim_status", ""),
        "mechanics_valid": package_manifest.get("mechanics_valid", ""),
        "manuscript_result_ready": package_manifest.get("manuscript_result_ready", ""),
        "case_count": package_manifest.get("case_count", ""),
        "baseline_count": _sequence_count(package_manifest.get("baselines")),
        "blocker_count": readiness_gaps.get("blocker_count", ""),
        "input_artifact_count": input_artifact_count,
        "output_artifact_count": output_artifact_count,
    }


def _sequence_count(value: object) -> int:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return len(value)
    return 0


def _write_csv(
    path: Path,
    rows: Sequence[dict[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
