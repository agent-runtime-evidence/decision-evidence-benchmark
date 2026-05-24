"""Export a manuscript candidate-scorer prediction workbook."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.manuscript_redaction import (
    ALLOWED_SCORER_CONTAINER_FLAGS,
    EVIDENCE_REF_FIELDS,
    SCORER_INPUT_REDACTION_STATUS,
    is_redacted_scorer_input_row,
)
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_scorer_workbook.csv"
DEFAULT_JSONL_OUT = ROOT / "data/results/manuscript_scorer_workbook.jsonl"
DEFAULT_SCORER = "decision_trace_reconstructor"
CATEGORY_PLACEHOLDER = "__SELECT_CATEGORY__"
VERDICT_PLACEHOLDER = "__SELECT_VERDICT__"
IMPLEMENTATION_STATUS_PLACEHOLDER = "__SET_IMPLEMENTATION_STATUS__"

LEGACY_CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "scorer",
    "prediction_status",
    "verdict",
    "property",
    "category",
    "required",
    "implementation_status",
    "run_id",
    "model",
    "prompt_version",
    "reviewer_id",
    "reviewed_at",
    "notes",
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
    "provenance_notes",
)
REDACTED_CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "question_family",
    "redaction_status",
    "redaction_version",
    "scorer",
    "prediction_status",
    "verdict",
    "property",
    "category",
    "required",
    "implementation_status",
    "run_id",
    "model",
    "prompt_version",
    "reviewer_id",
    "reviewed_at",
    "notes",
    "evidence_plane",
    "native_evidence_ref_count",
    "reviewed_source_ref_count",
    "evidence_plane_ref_count",
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
    "case_source_status",
)


def workbook_rows(
    cases: list[CaseManifest],
    *,
    scorer: str = DEFAULT_SCORER,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    row_index = 1
    for case in cases:
        for property_name in DECISION_EVENT_PROPERTIES:
            rows.append(_workbook_row(case, property_name, scorer=scorer, row_index=row_index))
            row_index += 1
    return rows


def redacted_workbook_rows(
    cases: list[dict[str, Any]],
    *,
    scorer: str = DEFAULT_SCORER,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    row_index = 1
    for case in cases:
        for property_name in DECISION_EVENT_PROPERTIES:
            rows.append(
                _redacted_workbook_row(
                    case,
                    property_name,
                    scorer=scorer,
                    row_index=row_index,
                )
            )
            row_index += 1
    return rows


def _workbook_row(
    case: CaseManifest,
    property_name: str,
    *,
    scorer: str,
    row_index: int,
) -> dict[str, str]:
    evidence = dict(case.evidence)
    return {
        "row_index": str(row_index),
        "case_id": case.case_id,
        "regime": case.regime,
        "degradation_condition": case.degradation_condition,
        "question_family": case.question_family,
        "scorer": scorer,
        "prediction_status": "todo",
        "verdict": VERDICT_PLACEHOLDER,
        "property": property_name,
        "category": CATEGORY_PLACEHOLDER,
        "required": "true",
        "implementation_status": IMPLEMENTATION_STATUS_PLACEHOLDER,
        "run_id": "",
        "model": "",
        "prompt_version": "",
        "reviewer_id": "",
        "reviewed_at": "",
        "notes": "",
        "native_evidence_refs": _pipe_join(evidence.get("native_evidence_refs", [])),
        "reviewed_source_refs": _pipe_join(evidence.get("reviewed_source_refs", [])),
        "evidence_plane_refs": _pipe_join(evidence.get("evidence_plane_refs", [])),
        "provenance_notes": str(evidence.get("provenance_notes", "")),
    }


def _redacted_workbook_row(
    case: dict[str, Any],
    property_name: str,
    *,
    scorer: str,
    row_index: int,
) -> dict[str, str]:
    evidence = _dict_value(case.get("evidence", {}))
    flags = _dict_value(case.get("container_flags", {}))
    metadata = _dict_value(case.get("metadata", {}))
    source_ref_counts = _dict_value(evidence.get("source_ref_counts", {}))
    row = {
        "row_index": str(row_index),
        "case_id": str(case.get("case_id", "")),
        "regime": str(case.get("regime", "")),
        "question_family": str(case.get("question_family", "")),
        "redaction_status": str(metadata.get("redaction_status", "")),
        "redaction_version": str(metadata.get("redaction_version", "")),
        "scorer": scorer,
        "prediction_status": "todo",
        "verdict": VERDICT_PLACEHOLDER,
        "property": property_name,
        "category": CATEGORY_PLACEHOLDER,
        "required": "true",
        "implementation_status": IMPLEMENTATION_STATUS_PLACEHOLDER,
        "run_id": "",
        "model": "",
        "prompt_version": "",
        "reviewer_id": "",
        "reviewed_at": "",
        "notes": "",
        "evidence_plane": str(evidence.get("evidence_plane", "")),
        "case_source_status": str(metadata.get("case_source_status", "")),
    }
    for field in EVIDENCE_REF_FIELDS:
        row[f"{field[:-1]}_count"] = str(source_ref_counts.get(field, "0"))
    for flag in ALLOWED_SCORER_CONTAINER_FLAGS:
        row[flag] = _bool_text(flags.get(flag, False))
    return row


def _dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _pipe_join(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def read_case_rows(path: Path) -> list[dict[str, Any]]:
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


def write_csv(path: Path, rows: list[dict[str, str]], *, columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--jsonl-out", default=str(DEFAULT_JSONL_OUT))
    parser.add_argument("--scorer", default=DEFAULT_SCORER)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    case_rows = read_case_rows(Path(args.cases))
    redacted_input = bool(case_rows) and all(is_redacted_scorer_input_row(row) for row in case_rows)
    if redacted_input:
        rows = redacted_workbook_rows(case_rows, scorer=str(args.scorer))
        columns = REDACTED_CSV_COLUMNS
    else:
        cases = [CaseManifest.from_dict(row) for row in case_rows]
        rows = workbook_rows(cases, scorer=str(args.scorer))
        columns = LEGACY_CSV_COLUMNS
    write_csv(Path(args.csv_out), rows, columns=columns)
    write_jsonl(Path(args.jsonl_out), rows)
    print(
        json.dumps(
            {
                "artifact_kind": "decision_evidence_manuscript_scorer_workbook_export",
                "cases": str(args.cases),
                "case_count": len(case_rows),
                "property_count": len(DECISION_EVENT_PROPERTIES),
                "row_count": len(rows),
                "scorer": str(args.scorer),
                "redacted_input": redacted_input,
                "redaction_status": SCORER_INPUT_REDACTION_STATUS if redacted_input else None,
                "csv_out": str(args.csv_out),
                "jsonl_out": str(args.jsonl_out),
                "result_honesty": (
                    "The scorer workbook is an authoring aid with placeholder "
                    "predictions. It does not create scorer outputs or manuscript results."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
