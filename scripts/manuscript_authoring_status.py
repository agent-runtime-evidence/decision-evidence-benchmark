"""Summarize manuscript authoring artifacts and result-gate blockers."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCORER_INPUT_REDACTION_STATUS = "scorer_input_redacted_v1"
REDACTED_WORKBOOK_ROLES = {
    "scorer_workbook_csv",
    "scorer_workbook_reviewed_csv",
    "llm_judge_workbook_csv",
    "llm_judge_workbook_reviewed_csv",
}
REDACTED_REVIEWED_WORKBOOK_ROLES = {
    "scorer_workbook_reviewed_csv",
    "llm_judge_workbook_reviewed_csv",
}
REDACTED_OUTPUT_ROLES = {
    "scorer_outputs_jsonl",
    "llm_judge_outputs_jsonl",
}


@dataclass(frozen=True)
class ArtifactSpec:
    role: str
    path: Path
    stage: str
    required_for_gate: bool = False
    reviewed_authoring_input: bool = False
    report: bool = False


def build_status(specs: list[ArtifactSpec], *, include_llm_judge: bool = False) -> dict[str, Any]:
    artifacts = [_artifact_record(spec) for spec in specs]
    by_role = {str(item["role"]): item for item in artifacts}
    construction_oracle_ready = bool(
        by_role.get("construction_oracle_report", {}).get("exists")
        and by_role.get("construction_oracle_report", {}).get("report_valid") is not False
    )
    missing_gate = [
        _blocker(item, reason="missing_required_gate_artifact")
        for item in artifacts
        if item["required_for_gate"] and not item["exists"]
    ]
    missing_reviewed_inputs = [
        _blocker(item, reason="missing_reviewed_authoring_input")
        for item in artifacts
        if item["reviewed_authoring_input"] and not item["exists"]
        and not (construction_oracle_ready and item["role"] == "annotation_workbook_reviewed_csv")
    ]
    invalid_reports = [
        _blocker(item, reason="invalid_report")
        for item in artifacts
        if item["report"] and item.get("report_valid") is False
    ]
    non_redacted_import_reports = [
        _blocker(item, reason="non_redacted_import_report")
        for item in artifacts
        if item["role"] in {"scorer_import_report", "llm_judge_import_report"}
        and _role_selected_for_gate(str(item["role"]), include_llm_judge=include_llm_judge)
        and item["exists"]
        and item.get("redacted_input") is not True
    ]
    non_redacted_reviewed_workbooks = [
        _blocker(item, reason="non_redacted_reviewed_workbook")
        for item in artifacts
        if item["role"] in REDACTED_REVIEWED_WORKBOOK_ROLES
        and _role_selected_for_gate(str(item["role"]), include_llm_judge=include_llm_judge)
        and item["exists"]
        and item.get("redacted_input") is not True
    ]
    non_redacted_outputs = [
        _blocker(item, reason="non_redacted_prediction_output")
        for item in artifacts
        if item["role"] in REDACTED_OUTPUT_ROLES
        and _role_selected_for_gate(str(item["role"]), include_llm_judge=include_llm_judge)
        and item["exists"]
        and item.get("redacted_input") is not True
    ]
    blockers = [
        *missing_gate,
        *missing_reviewed_inputs,
        *invalid_reports,
        *non_redacted_reviewed_workbooks,
        *non_redacted_outputs,
        *non_redacted_import_reports,
    ]
    return {
        "artifact_kind": "decision_evidence_manuscript_authoring_status",
        "manuscript_input_gate_ready": not missing_gate,
        "reviewed_authoring_inputs_ready": not missing_reviewed_inputs,
        "blocking_item_count": len(blockers),
        "blockers": blockers,
        "selected_baselines": {
            "llm_judge": include_llm_judge,
        },
        "next_actions": _next_actions(by_role, include_llm_judge=include_llm_judge),
        "artifacts": artifacts,
        "stage_counts": _stage_counts(artifacts),
        "result_honesty": (
            "This status report is diagnostic only. It does not import reviewed "
            "workbooks, adjudicate labels, or create manuscript result artifacts."
        ),
    }


def default_specs(args: argparse.Namespace) -> list[ArtifactSpec]:
    return [
        ArtifactSpec("case_source_reviewed_jsonl", Path(args.case_source_reviewed), "source"),
        ArtifactSpec("unadjudicated_cases_jsonl", Path(args.unadjudicated_cases), "source"),
        ArtifactSpec(
            "case_source_conversion_report",
            Path(args.case_source_report),
            "source",
            report=True,
        ),
        ArtifactSpec("annotation_workbook_csv", Path(args.annotation_workbook), "annotation"),
        ArtifactSpec(
            "annotation_workbook_reviewed_csv",
            Path(args.annotation_workbook_reviewed),
            "annotation",
            reviewed_authoring_input=True,
        ),
        ArtifactSpec(
            "construction_oracle_report",
            Path(args.construction_oracle),
            "annotation",
            report=True,
        ),
        ArtifactSpec(
            "annotation_jsonl",
            Path(args.annotations),
            "annotation",
            required_for_gate=True,
        ),
        ArtifactSpec(
            "label_calibration_report",
            Path(args.label_calibration),
            "annotation",
            report=True,
        ),
        ArtifactSpec("label_review_report", Path(args.label_review), "annotation", report=True),
        ArtifactSpec(
            "label_adjudication_report",
            Path(args.label_adjudication),
            "annotation",
            report=True,
        ),
        ArtifactSpec(
            "adjudicated_cases_jsonl",
            Path(args.adjudicated_cases),
            "annotation",
            required_for_gate=True,
        ),
        ArtifactSpec(
            "scorer_input_redaction_report",
            Path(args.scorer_input_redaction),
            "candidate_scorer",
            report=True,
        ),
        ArtifactSpec("scorer_workbook_csv", Path(args.scorer_workbook), "candidate_scorer"),
        ArtifactSpec(
            "scorer_workbook_reviewed_csv",
            Path(args.scorer_workbook_reviewed),
            "candidate_scorer",
            reviewed_authoring_input=False,
        ),
        ArtifactSpec(
            "scorer_outputs_jsonl",
            Path(args.scorer_outputs),
            "candidate_scorer",
            required_for_gate=True,
        ),
        ArtifactSpec(
            "scorer_import_report",
            Path(args.scorer_import_report),
            "candidate_scorer",
            report=True,
        ),
        ArtifactSpec("llm_judge_workbook_csv", Path(args.llm_judge_workbook), "baseline"),
        ArtifactSpec(
            "llm_judge_workbook_reviewed_csv",
            Path(args.llm_judge_workbook_reviewed),
            "baseline",
            reviewed_authoring_input=bool(args.include_llm_judge),
        ),
        ArtifactSpec(
            "llm_judge_outputs_jsonl",
            Path(args.llm_judge_outputs),
            "baseline",
            required_for_gate=bool(args.include_llm_judge),
        ),
        ArtifactSpec(
            "llm_judge_import_report",
            Path(args.llm_judge_import_report),
            "baseline",
            report=True,
        ),
        ArtifactSpec(
            "label_leakage_audit_report",
            Path(args.label_leakage_audit),
            "package_gate",
            report=True,
        ),
        ArtifactSpec(
            "corpus_manifest_yaml",
            Path(args.corpus),
            "package_gate",
            required_for_gate=True,
        ),
        ArtifactSpec("preflight_report", Path(args.preflight_report), "package_gate", report=True),
        ArtifactSpec("adjudication_overrides_jsonl", Path(args.adjudication_overrides), "optional"),
    ]


def _artifact_record(spec: ArtifactSpec) -> dict[str, Any]:
    exists = spec.path.exists()
    record: dict[str, Any] = {
        "role": spec.role,
        "stage": spec.stage,
        "path": str(spec.path),
        "exists": exists,
        "required_for_gate": spec.required_for_gate,
        "reviewed_authoring_input": spec.reviewed_authoring_input,
        "report": spec.report,
    }
    if not exists:
        return record
    record["bytes"] = spec.path.stat().st_size
    if spec.path.suffix == ".csv":
        record.update(_csv_summary(spec.path, role=spec.role))
    elif spec.path.suffix == ".jsonl":
        record.update(_jsonl_summary(spec.path, role=spec.role))
    elif spec.path.suffix == ".json":
        record.update(_json_report_summary(spec.path))
    return record


def _csv_summary(path: Path, *, role: str) -> dict[str, Any]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    summary: dict[str, Any] = {
        "row_count": len(rows),
        "columns": list(reader.fieldnames or []),
    }
    if role in REDACTED_WORKBOOK_ROLES:
        redacted_rows = [
            row
            for row in rows
            if str(row.get("redaction_status", "")).strip() == SCORER_INPUT_REDACTION_STATUS
        ]
        summary["redacted_input"] = bool(rows) and len(redacted_rows) == len(rows)
        summary["redacted_row_count"] = len(redacted_rows)
    return summary


def _jsonl_summary(path: Path, *, role: str) -> dict[str, Any]:
    row_count = 0
    redacted_row_count = 0
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            row_count += 1
            if role not in REDACTED_OUTPUT_ROLES:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            metadata = value.get("metadata", {})
            if (
                isinstance(metadata, dict)
                and metadata.get("scorer_input_redaction_status")
                == SCORER_INPUT_REDACTION_STATUS
            ):
                redacted_row_count += 1
    summary: dict[str, Any] = {"row_count": row_count}
    if role in REDACTED_OUTPUT_ROLES:
        summary["redacted_input"] = row_count > 0 and redacted_row_count == row_count
        summary["redacted_row_count"] = redacted_row_count
    return summary


def _json_report_summary(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"json_valid": False, "json_error": str(exc)}
    if not isinstance(payload, dict):
        return {"json_valid": False, "json_error": "top-level JSON value is not an object"}
    summary: dict[str, Any] = {"json_valid": True}
    if "artifact_kind" in payload:
        summary["artifact_kind"] = payload["artifact_kind"]
    if "valid" in payload:
        summary["report_valid"] = bool(payload["valid"])
    if "redacted_input" in payload:
        summary["redacted_input"] = bool(payload["redacted_input"])
    if "redaction_status" in payload:
        summary["redaction_status"] = str(payload["redaction_status"])
    if "issues" in payload and isinstance(payload["issues"], list):
        summary["issue_count"] = len(payload["issues"])
    return summary


def _blocker(item: dict[str, Any], *, reason: str) -> dict[str, str]:
    return {
        "reason": reason,
        "role": str(item["role"]),
        "path": str(item["path"]),
        "stage": str(item["stage"]),
    }


def _role_selected_for_gate(role: str, *, include_llm_judge: bool) -> bool:
    if role.startswith("llm_judge_"):
        return include_llm_judge
    return True


def _stage_counts(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for artifact in artifacts:
        stage = str(artifact["stage"])
        stage_counts = counts.setdefault(stage, {"artifacts": 0, "present": 0, "missing": 0})
        stage_counts["artifacts"] += 1
        if artifact["exists"]:
            stage_counts["present"] += 1
        else:
            stage_counts["missing"] += 1
    return counts


def _next_actions(
    by_role: dict[str, dict[str, Any]],
    *,
    include_llm_judge: bool,
) -> list[str]:
    actions: list[str] = []
    construction_oracle_ready = bool(
        by_role.get("construction_oracle_report", {}).get("exists")
        and by_role.get("construction_oracle_report", {}).get("report_valid") is not False
    )
    if (
        not construction_oracle_ready
        and not by_role["annotation_workbook_reviewed_csv"]["exists"]
    ):
        actions.append(
            "Run make write-manuscript-construction-oracle, or explicitly switch to "
            "the annotation workbook path and fill "
            "data/results/manuscript_annotation_workbook.reviewed.csv."
        )
    elif not by_role["annotation_jsonl"]["exists"]:
        if construction_oracle_ready:
            actions.append("Run make write-manuscript-construction-oracle.")
        else:
            actions.append("Run make import-manuscript-annotation-workbook.")
    if by_role["annotation_jsonl"]["exists"] and not by_role["adjudicated_cases_jsonl"]["exists"]:
        if construction_oracle_ready:
            actions.append("Run make write-manuscript-construction-oracle.")
        else:
            actions.append(
                "Run make calibrate-manuscript-labels, make review-manuscript-labels, "
                "and make adjudicate-manuscript-labels."
            )
    if not by_role["scorer_outputs_jsonl"]["exists"]:
        if not by_role["scorer_workbook_reviewed_csv"]["exists"]:
            actions.append(
                "Run make write-manuscript-deterministic-scorer, or intentionally "
                "switch to the reviewed scorer workbook path."
            )
        else:
            actions.append("Run make import-manuscript-scorer-workbook.")
    elif by_role["scorer_workbook_reviewed_csv"].get("exists") and (
        by_role["scorer_workbook_reviewed_csv"].get("redacted_input") is not True
    ):
        actions.append(
            "Regenerate data/results/manuscript_scorer_workbook.reviewed.csv from "
            "the redacted scorer workbook, then rerun make import-manuscript-scorer-workbook."
        )
    elif by_role["scorer_outputs_jsonl"].get("redacted_input") is not True:
        actions.append(
            "Rerun make import-manuscript-scorer-workbook after the reviewed scorer "
            "workbook carries redacted case IDs."
        )
    elif (
        by_role.get("scorer_import_report", {}).get("exists")
        and by_role.get("scorer_import_report", {}).get("redacted_input") is not True
    ):
        actions.append(
            "Regenerate the scorer reviewed workbook from the redacted scorer input, "
            "then rerun make import-manuscript-scorer-workbook."
        )
    if include_llm_judge:
        if not by_role["llm_judge_workbook_reviewed_csv"]["exists"]:
            actions.append(
                "Fill data/results/manuscript_llm_judge_workbook.reviewed.csv, then run "
                "make import-manuscript-llm-judge-workbook."
            )
        elif by_role["llm_judge_workbook_reviewed_csv"].get("redacted_input") is not True:
            actions.append(
                "Regenerate data/results/manuscript_llm_judge_workbook.reviewed.csv "
                "from the redacted LLM-judge workbook, then rerun "
                "make import-manuscript-llm-judge-workbook."
            )
        elif not by_role["llm_judge_outputs_jsonl"]["exists"]:
            actions.append("Run make import-manuscript-llm-judge-workbook.")
        elif by_role["llm_judge_outputs_jsonl"].get("redacted_input") is not True:
            actions.append(
                "Rerun make import-manuscript-llm-judge-workbook after the reviewed "
                "LLM-judge workbook carries redacted case IDs."
            )
        elif (
            by_role.get("llm_judge_import_report", {}).get("exists")
            and by_role.get("llm_judge_import_report", {}).get("redacted_input") is not True
        ):
            actions.append(
                "Regenerate the LLM-judge reviewed workbook from the redacted scorer "
                "input, then rerun make import-manuscript-llm-judge-workbook."
            )
    if not by_role["corpus_manifest_yaml"]["exists"]:
        actions.append(
            "Run make write-manuscript-corpus-manifest after required JSONL inputs exist."
        )
    leakage_report = by_role.get("label_leakage_audit_report", {})
    if leakage_report.get("exists") and leakage_report.get("report_valid") is False:
        actions.append(
            "Fix scorer-facing label leakage, then rerun make audit-manuscript-label-leakage."
        )
    elif not leakage_report.get("exists"):
        actions.append("Run make audit-manuscript-label-leakage.")
    if not actions:
        actions.append("Run make verify-manuscript-package.")
    return actions


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case-source-reviewed",
        default="data/cases/manuscript_case_sources.reviewed.jsonl",
    )
    parser.add_argument(
        "--unadjudicated-cases",
        default="data/cases/manuscript_cases.unadjudicated.jsonl",
    )
    parser.add_argument(
        "--case-source-report",
        default="data/results/manuscript_case_source_conversion.json",
    )
    parser.add_argument(
        "--annotation-workbook",
        default="data/results/manuscript_annotation_workbook.csv",
    )
    parser.add_argument(
        "--annotation-workbook-reviewed",
        default="data/results/manuscript_annotation_workbook.reviewed.csv",
    )
    parser.add_argument(
        "--construction-oracle",
        default="data/results/manuscript_construction_oracle.json",
    )
    parser.add_argument("--annotations", default="data/annotations/manuscript_annotations.jsonl")
    parser.add_argument(
        "--label-calibration",
        default="data/results/manuscript_label_calibration.json",
    )
    parser.add_argument("--label-review", default="data/results/manuscript_label_review.json")
    parser.add_argument(
        "--label-adjudication",
        default="data/results/manuscript_label_adjudication.json",
    )
    parser.add_argument("--adjudicated-cases", default="data/cases/manuscript_cases.jsonl")
    parser.add_argument(
        "--scorer-input-redaction",
        default="data/results/manuscript_scorer_input_redaction.json",
    )
    parser.add_argument("--scorer-workbook", default="data/results/manuscript_scorer_workbook.csv")
    parser.add_argument(
        "--scorer-workbook-reviewed",
        default="data/results/manuscript_scorer_workbook.reviewed.csv",
    )
    parser.add_argument(
        "--scorer-outputs",
        default="data/scorers/decision_trace_reconstructor_outputs.jsonl",
    )
    parser.add_argument(
        "--scorer-import-report",
        default="data/results/manuscript_scorer_import.json",
    )
    parser.add_argument(
        "--llm-judge-workbook",
        default="data/results/manuscript_llm_judge_workbook.csv",
    )
    parser.add_argument(
        "--llm-judge-workbook-reviewed",
        default="data/results/manuscript_llm_judge_workbook.reviewed.csv",
    )
    parser.add_argument("--llm-judge-outputs", default="data/baselines/llm_judge_outputs.jsonl")
    parser.add_argument(
        "--llm-judge-import-report",
        default="data/results/manuscript_llm_judge_import.json",
    )
    parser.add_argument(
        "--label-leakage-audit",
        default="data/results/manuscript_label_leakage_audit.json",
    )
    parser.add_argument("--corpus", default="data/corpus/manuscript_corpus.yaml")
    parser.add_argument(
        "--preflight-report",
        default="data/results/manuscript_input_preflight.json",
    )
    parser.add_argument(
        "--adjudication-overrides",
        default="data/annotations/manuscript_adjudication_overrides.jsonl",
    )
    parser.add_argument("--out", default="data/results/manuscript_authoring_status.json")
    parser.add_argument("--include-llm-judge", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    status = build_status(
        default_specs(args),
        include_llm_judge=bool(args.include_llm_judge),
    )
    write_json(Path(args.out), status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
