"""Audit scorer-facing manuscript artifacts for oracle-label leakage."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.construction_oracle import (
    DEFAULT_ORACLE_SPEC_PATH,
    ConstructionOracleSpec,
    load_oracle_spec,
    oracle_spec_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data/results/manuscript_label_leakage_audit.json"
DEFAULT_ARTIFACTS = (
    "scorer_input:data/cases/manuscript_scorer_input_cases.jsonl",
    "scorer_workbook:data/results/manuscript_scorer_workbook.csv",
    "scorer_workbook_reviewed:data/results/manuscript_scorer_workbook.reviewed.csv",
    "llm_judge_workbook:data/results/manuscript_llm_judge_workbook.csv",
    "llm_judge_workbook_reviewed:data/results/manuscript_llm_judge_workbook.reviewed.csv",
)


@dataclass(frozen=True)
class ArtifactInput:
    role: str
    path: Path


def parse_artifact(value: str) -> ArtifactInput:
    if ":" not in value:
        raise argparse.ArgumentTypeError("artifact specs must use role:path format")
    role, raw_path = value.split(":", 1)
    if not role or not raw_path:
        raise argparse.ArgumentTypeError("artifact specs must include role and path")
    return ArtifactInput(role=role, path=Path(raw_path))


def audit_artifacts(
    *,
    artifacts: list[ArtifactInput],
    oracle_spec: ConstructionOracleSpec,
    max_issues: int = 200,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    artifact_records: list[dict[str, Any]] = []
    issue_counts: Counter[str] = Counter()

    for artifact in artifacts:
        record = _artifact_record(artifact)
        artifact_records.append(record)
        if not artifact.path.exists():
            issue = {
                "severity": "warning",
                "issue": "artifact_missing",
                "role": artifact.role,
                "path": str(artifact.path),
            }
            _append_issue(issues, issue_counts, issue, max_issues=max_issues)
            continue
        rows = _read_rows(artifact.path)
        record["row_count"] = len(rows)
        for row_index, row in enumerate(rows, start=1):
            for issue in _row_issues(
                row,
                artifact=artifact,
                row_index=row_index,
                oracle_spec=oracle_spec,
            ):
                _append_issue(issues, issue_counts, issue, max_issues=max_issues)

    error_count = sum(
        count
        for issue_name, count in issue_counts.items()
        if not issue_name.startswith("artifact_missing")
    )
    return {
        "artifact_kind": "decision_evidence_manuscript_label_leakage_audit",
        "valid": error_count == 0,
        "oracle_version": oracle_spec.oracle_version,
        "oracle_spec": str(oracle_spec.path),
        "oracle_spec_sha256": oracle_spec_sha256(oracle_spec.path),
        "artifacts": artifact_records,
        "issue_count": sum(issue_counts.values()),
        "issue_counts": dict(sorted(issue_counts.items())),
        "issues_truncated": sum(issue_counts.values()) > len(issues),
        "issues": issues,
        "result_honesty": (
            "This audit checks scorer-facing artifacts for explicit oracle-label leakage. "
            "A valid audit does not prove semantic independence; it only verifies that "
            "configured label-bearing fields and degradation-condition tokens are absent."
        ),
    }


def _artifact_record(artifact: ArtifactInput) -> dict[str, Any]:
    return {
        "role": artifact.role,
        "path": str(artifact.path),
        "exists": artifact.path.exists(),
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".csv":
        with path.open(newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with path.open() as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: row must be a JSON object")
                rows.append(value)
        return rows
    raise ValueError(f"unsupported artifact suffix for leakage audit: {path}")


def _row_issues(
    row: dict[str, Any],
    *,
    artifact: ArtifactInput,
    row_index: int,
    oracle_spec: ConstructionOracleSpec,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    disallowed_fields = set(
        str(field)
        for field in oracle_spec.leakage_guard.get("disallowed_scorer_field_names", [])
    )
    disallowed_tokens = tuple(
        str(token)
        for token in oracle_spec.leakage_guard.get("disallowed_case_id_tokens", [])
    )

    for field_name, value in _flatten("", row).items():
        normalized_field = field_name.split(".")[-1]
        if normalized_field in disallowed_fields:
            issues.append(
                _issue(
                    artifact=artifact,
                    row_index=row_index,
                    issue="disallowed_field_name",
                    field=field_name,
                    value=str(value),
                )
            )
        if _token_scan_field(normalized_field):
            for token in disallowed_tokens:
                if token and token in str(value):
                    issues.append(
                        _issue(
                            artifact=artifact,
                            row_index=row_index,
                            issue="disallowed_label_token",
                            field=field_name,
                            value=str(value),
                            token=token,
                        )
                    )
    return issues


def _flatten(prefix: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        items: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.update(_flatten(child_prefix, child))
        return items
    if isinstance(value, list):
        items = {}
        for index, child in enumerate(value):
            child_prefix = f"{prefix}.{index}" if prefix else str(index)
            items.update(_flatten(child_prefix, child))
        return items
    return {prefix: value}


def _token_scan_field(field_name: str) -> bool:
    return (
        field_name == "case_id"
        or field_name.endswith("_refs")
        or field_name in {"provenance_notes", "notes", "prompt", "prompt_version"}
    )


def _issue(
    *,
    artifact: ArtifactInput,
    row_index: int,
    issue: str,
    field: str,
    value: str,
    token: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "severity": "error",
        "issue": issue,
        "role": artifact.role,
        "path": str(artifact.path),
        "row_index": row_index,
        "field": field,
        "value": value[:240],
    }
    if token is not None:
        payload["token"] = token
    return payload


def _append_issue(
    issues: list[dict[str, Any]],
    issue_counts: Counter[str],
    issue: dict[str, Any],
    *,
    max_issues: int,
) -> None:
    issue_counts[str(issue["issue"])] += 1
    if len(issues) < max_issues:
        issues.append(issue)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle-spec", default=str(DEFAULT_ORACLE_SPEC_PATH))
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        type=parse_artifact,
        help="Artifact to audit as role:path. Repeatable.",
    )
    parser.add_argument("--out", default=str(DEFAULT_REPORT))
    parser.add_argument("--max-issues", type=int, default=200)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifacts = list(args.artifact) or [parse_artifact(value) for value in DEFAULT_ARTIFACTS]
    report = audit_artifacts(
        artifacts=artifacts,
        oracle_spec=load_oracle_spec(Path(args.oracle_spec)),
        max_issues=int(args.max_issues),
    )
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
