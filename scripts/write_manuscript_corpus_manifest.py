"""Promote the manuscript corpus manifest template after gate inputs exist."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/corpus/manuscript_corpus.template.yaml"
DEFAULT_OUT = ROOT / "data/corpus/manuscript_corpus.yaml"
DEFAULT_REPORT = ROOT / "data/results/manuscript_corpus_manifest_promotion.json"
EXPECTED_CLAIM_STATUS = "manuscript_result_candidate"


@dataclass(frozen=True)
class RequiredInput:
    role: str
    path: Path


def parse_required(value: str) -> RequiredInput:
    if ":" not in value:
        raise argparse.ArgumentTypeError("required specs must use role:path format")
    role, raw_path = value.split(":", 1)
    if not role or not raw_path:
        raise argparse.ArgumentTypeError("required specs must include non-empty role and path")
    return RequiredInput(role=role, path=Path(raw_path))


def promote_manifest(
    *,
    template_path: Path,
    out_path: Path,
    required_inputs: list[RequiredInput],
) -> tuple[bool, dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    manifest = _read_manifest(template_path, issues)
    input_records = []
    for required_input in required_inputs:
        exists = required_input.path.exists()
        input_records.append(
            {
                "role": required_input.role,
                "path": str(required_input.path),
                "exists": exists,
            }
        )
        if not exists:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_required_input",
                    "role": required_input.role,
                    "path": str(required_input.path),
                }
            )
    if manifest is not None:
        issues.extend(_manifest_issues(manifest, required_inputs=required_inputs))

    wrote_manifest = False
    manifest_already_current = False
    if not any(issue["severity"] == "error" for issue in issues) and manifest is not None:
        rendered_manifest = yaml.safe_dump(manifest, sort_keys=False)
        if out_path.exists() and out_path.read_text() != rendered_manifest:
            issues.append(
                {
                    "severity": "error",
                    "issue": "output_exists_with_different_content",
                    "path": str(out_path),
                }
            )
        elif out_path.exists():
            manifest_already_current = True
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered_manifest)
            wrote_manifest = True

    valid = not any(issue["severity"] == "error" for issue in issues)

    report = {
        "artifact_kind": "decision_evidence_manuscript_corpus_manifest_promotion",
        "valid": valid,
        "template": str(template_path),
        "out": str(out_path),
        "wrote_manifest": wrote_manifest,
        "manifest_already_current": manifest_already_current,
        "required_inputs": input_records,
        "issues": issues,
        "result_honesty": (
            "The promotion writes only the manuscript corpus manifest after required "
            "gate inputs exist. It does not create cases, annotations, scorer outputs, "
            "baseline outputs, packages, or results."
        ),
    }
    return valid, report


def _read_manifest(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not path.exists():
        issues.append(
            {
                "severity": "error",
                "issue": "missing_template",
                "path": str(path),
            }
        )
        return None
    try:
        payload = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        issues.append(
            {
                "severity": "error",
                "issue": "invalid_template_yaml",
                "path": str(path),
                "error": str(exc),
            }
        )
        return None
    if not isinstance(payload, dict):
        issues.append(
            {
                "severity": "error",
                "issue": "template_not_mapping",
                "path": str(path),
            }
        )
        return None
    return payload


def _manifest_issues(
    manifest: dict[str, Any],
    *,
    required_inputs: list[RequiredInput],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if manifest.get("claim_status") != EXPECTED_CLAIM_STATUS:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_claim_status",
                "expected": EXPECTED_CLAIM_STATUS,
                "actual": manifest.get("claim_status"),
            }
        )
    required_by_role = {item.role: str(item.path) for item in required_inputs}
    expected_case_path = required_by_role.get("case_manifest_jsonl")
    expected_annotation_path = required_by_role.get("annotation_jsonl")
    if expected_case_path:
        case_paths = _case_paths(manifest)
        if expected_case_path not in case_paths:
            issues.append(
                {
                    "severity": "error",
                    "issue": "template_case_path_mismatch",
                    "expected": expected_case_path,
                    "actual": case_paths,
                }
            )
    if expected_annotation_path:
        annotation_paths = _annotation_paths(manifest)
        if expected_annotation_path not in annotation_paths:
            issues.append(
                {
                    "severity": "error",
                    "issue": "template_annotation_path_mismatch",
                    "expected": expected_annotation_path,
                    "actual": annotation_paths,
                }
            )
    return issues


def _case_paths(manifest: dict[str, Any]) -> list[str]:
    case_files = manifest.get("case_files", [])
    if not isinstance(case_files, list):
        return []
    return [
        str(item.get("path"))
        for item in case_files
        if isinstance(item, dict) and item.get("path")
    ]


def _annotation_paths(manifest: dict[str, Any]) -> list[str]:
    label_contract = manifest.get("label_contract", {})
    if not isinstance(label_contract, dict):
        return []
    annotation_files = label_contract.get("annotation_files", [])
    if not isinstance(annotation_files, list):
        return []
    return [
        str(item.get("path"))
        for item in annotation_files
        if isinstance(item, dict) and item.get("path")
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        type=parse_required,
        help="Required gate input as role:path. Repeatable.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    valid, report = promote_manifest(
        template_path=Path(args.template),
        out_path=Path(args.out),
        required_inputs=list(args.required),
    )
    write_json(Path(args.report), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
