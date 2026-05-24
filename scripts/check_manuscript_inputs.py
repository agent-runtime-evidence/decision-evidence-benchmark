"""Preflight required manuscript-package input files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

REQUIRED_VALID_REPORT_ROLES = {
    "label_leakage_audit_report",
    "llm_judge_import_report",
    "scorer_import_report",
    "scorer_input_redaction_report",
}
REQUIRED_REDACTED_IMPORT_REPORT_ROLES = {
    "llm_judge_import_report",
    "scorer_import_report",
}
EXPECTED_REDACTION_STATUS = "scorer_input_redacted_v1"


@dataclass(frozen=True)
class InputSpec:
    role: str
    path: Path
    required: bool


def parse_spec(value: str, *, required: bool) -> InputSpec:
    if ":" not in value:
        raise argparse.ArgumentTypeError("input specs must use role:path format")
    role, raw_path = value.split(":", 1)
    if not role or not raw_path:
        raise argparse.ArgumentTypeError("input specs must include non-empty role and path")
    return InputSpec(role=role, path=Path(raw_path), required=required)


def build_report(specs: list[InputSpec]) -> dict[str, object]:
    records: list[dict[str, object]] = []
    missing_required: list[dict[str, str]] = []
    missing_optional: list[dict[str, str]] = []
    invalid_required: list[dict[str, str]] = []

    for spec in specs:
        exists = spec.path.exists()
        record: dict[str, object] = {
            "role": spec.role,
            "path": str(spec.path),
            "required": spec.required,
            "exists": exists,
        }
        if exists and spec.path.suffix == ".json":
            record.update(_json_report_summary(spec.path))
        records.append(record)
        if not exists and spec.required:
            missing_required.append({"role": spec.role, "path": str(spec.path)})
        elif not exists:
            missing_optional.append({"role": spec.role, "path": str(spec.path)})
        elif spec.required:
            invalid_required.extend(_required_artifact_issues(spec, record))

    return {
        "artifact_kind": "decision_evidence_manuscript_input_preflight",
        "valid": not missing_required and not invalid_required,
        "inputs": records,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "invalid_required": invalid_required,
    }


def _json_report_summary(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"json_valid": False, "json_error": str(exc)}
    if not isinstance(payload, dict):
        return {"json_valid": False, "json_error": "top-level JSON value is not an object"}
    summary: dict[str, object] = {"json_valid": True}
    if "artifact_kind" in payload:
        summary["artifact_kind"] = str(payload["artifact_kind"])
    if "valid" in payload:
        summary["report_valid"] = bool(payload["valid"])
    if "redacted_input" in payload:
        summary["redacted_input"] = bool(payload["redacted_input"])
    if "redaction_status" in payload:
        summary["redaction_status"] = str(payload["redaction_status"])
    return summary


def _required_artifact_issues(
    spec: InputSpec,
    record: dict[str, object],
) -> list[dict[str, str]]:
    if spec.role not in REQUIRED_VALID_REPORT_ROLES:
        return []
    if record.get("json_valid") is not True:
        return [
            {
                "role": spec.role,
                "path": str(spec.path),
                "reason": "invalid_json_report",
            }
        ]
    if record.get("report_valid") is not True:
        return [
            {
                "role": spec.role,
                "path": str(spec.path),
                "reason": "invalid_report",
            }
        ]
    if (
        spec.role == "scorer_input_redaction_report"
        and record.get("redaction_status") != EXPECTED_REDACTION_STATUS
    ):
        return [
            {
                "role": spec.role,
                "path": str(spec.path),
                "reason": "invalid_redaction_status",
            }
        ]
    if (
        spec.role in REQUIRED_REDACTED_IMPORT_REPORT_ROLES
        and record.get("redacted_input") is not True
    ):
        return [
            {
                "role": spec.role,
                "path": str(spec.path),
                "reason": "non_redacted_import_report",
            }
        ]
    return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        type=lambda value: parse_spec(value, required=True),
        help="Required manuscript input as role:path. Repeatable.",
    )
    parser.add_argument(
        "--optional",
        action="append",
        default=[],
        type=lambda value: parse_spec(value, required=False),
        help="Optional manuscript input as role:path. Repeatable.",
    )
    parser.add_argument("--out", help="Optional path for writing the JSON report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report([*args.required, *args.optional])
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(rendered + "\n")
    print(rendered)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
