"""Write redacted scorer-facing manuscript input cases and private ID map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.io import read_cases_jsonl, write_jsonl
from decision_evidence_benchmark.manuscript_redaction import (
    SCORER_INPUT_REDACTION_STATUS,
    case_id_map_row,
    redacted_case_row,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_OUT = ROOT / "data/cases/manuscript_scorer_input_cases.jsonl"
DEFAULT_CASE_ID_MAP = ROOT / "data/cases/manuscript_scorer_input_case_id_map.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_scorer_input_redaction.json"


def write_redacted_scorer_input(
    *,
    cases_path: Path,
    out: Path,
    case_id_map: Path,
    report: Path,
) -> dict[str, Any]:
    cases = read_cases_jsonl(cases_path)
    redacted_rows = [
        redacted_case_row(case, index=index) for index, case in enumerate(cases, start=1)
    ]
    map_rows = [case_id_map_row(case, index=index) for index, case in enumerate(cases, start=1)]
    issues = _redaction_issues(redacted_rows)
    valid = not any(issue["severity"] == "error" for issue in issues)

    if valid:
        write_jsonl(out, redacted_rows)
        write_jsonl(case_id_map, map_rows)

    payload = {
        "artifact_kind": "decision_evidence_manuscript_scorer_input_redaction",
        "valid": valid,
        "redaction_status": SCORER_INPUT_REDACTION_STATUS,
        "cases": str(cases_path),
        "cases_sha256": _sha256_if_exists(cases_path),
        "redacted_cases_out": str(out),
        "redacted_cases_sha256": _sha256_if_exists(out),
        "case_id_map_out": str(case_id_map),
        "case_id_map_sha256": _sha256_if_exists(case_id_map),
        "case_count": len(cases),
        "redacted_case_count": len(redacted_rows),
        "case_id_map_count": len(map_rows),
        "issues": issues,
        "result_honesty": (
            "This artifact constructs scorer-facing redacted inputs and a private ID map. "
            "It does not create labels, candidate scorer outputs, baseline outputs, or "
            "manuscript results."
        ),
    }
    _write_json(report, payload)
    return payload


def _redaction_issues(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    disallowed_fields = {
        "degradation_condition",
        "property_labels",
        "label_adjudication",
        "label_basis",
        "label_oracle",
        "strict_sufficiency",
        "ground_truth",
    }
    disallowed_tokens = (
        "complete",
        "missing_delegation",
        "missing_policy",
        "missing_context",
        "conflicting_identity",
        "partial_graph",
        "final_only",
        "artifact_only",
    )
    for index, row in enumerate(rows, start=1):
        case_id = str(row.get("case_id", ""))
        if not case_id.startswith("case-"):
            issues.append(
                {
                    "severity": "error",
                    "issue": "non_opaque_case_id",
                    "row_index": index,
                    "case_id": case_id,
                }
            )
        if case_id in seen_ids:
            issues.append(
                {
                    "severity": "error",
                    "issue": "duplicate_redacted_case_id",
                    "row_index": index,
                    "case_id": case_id,
                }
            )
        seen_ids.add(case_id)
        for field, value in _flatten("", row).items():
            normalized_field = field.split(".")[-1]
            if normalized_field in disallowed_fields:
                issues.append(
                    {
                        "severity": "error",
                        "issue": "disallowed_redacted_field",
                        "row_index": index,
                        "field": field,
                    }
                )
            if normalized_field == "case_id" or normalized_field.endswith("_refs"):
                for token in disallowed_tokens:
                    if token in str(value):
                        issues.append(
                            {
                                "severity": "error",
                                "issue": "disallowed_redacted_token",
                                "row_index": index,
                                "field": field,
                                "token": token,
                            }
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


def _sha256_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--case-id-map", default=str(DEFAULT_CASE_ID_MAP))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = write_redacted_scorer_input(
        cases_path=Path(args.cases),
        out=Path(args.out),
        case_id_map=Path(args.case_id_map),
        report=Path(args.report),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
