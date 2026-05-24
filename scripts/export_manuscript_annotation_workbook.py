"""Export manuscript annotation workbook rows from unadjudicated cases."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.io import read_cases_jsonl
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/cases/manuscript_cases.unadjudicated.jsonl"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_annotation_workbook.csv"
DEFAULT_JSONL_OUT = ROOT / "data/results/manuscript_annotation_workbook.jsonl"
DEFAULT_ANNOTATORS = ("manuscript_annotator_a", "manuscript_annotator_b")
ANNOTATION_CATEGORY_PLACEHOLDER = "__SELECT_CATEGORY__"

CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "property",
    "annotator_id",
    "annotation_status",
    "category",
    "required",
    "notes",
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
    "provenance_notes",
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
    "llm_judge_verdict",
)


def workbook_rows(
    cases: list[CaseManifest],
    *,
    annotators: tuple[str, str] = DEFAULT_ANNOTATORS,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    row_index = 1
    for case in cases:
        for annotator_id in annotators:
            for property_name in DECISION_EVENT_PROPERTIES:
                rows.append(_workbook_row(case, property_name, annotator_id, row_index=row_index))
                row_index += 1
    return rows


def _workbook_row(
    case: CaseManifest,
    property_name: str,
    annotator_id: str,
    *,
    row_index: int,
) -> dict[str, str]:
    evidence = dict(case.evidence)
    flags = dict(case.container_flags)
    return {
        "row_index": str(row_index),
        "case_id": case.case_id,
        "regime": case.regime,
        "degradation_condition": case.degradation_condition,
        "question_family": case.question_family,
        "property": property_name,
        "annotator_id": annotator_id,
        "annotation_status": "todo",
        "category": ANNOTATION_CATEGORY_PLACEHOLDER,
        "required": "true",
        "notes": "",
        "native_evidence_refs": _pipe_join(evidence.get("native_evidence_refs", [])),
        "reviewed_source_refs": _pipe_join(evidence.get("reviewed_source_refs", [])),
        "evidence_plane_refs": _pipe_join(evidence.get("evidence_plane_refs", [])),
        "provenance_notes": str(evidence.get("provenance_notes", "")),
        "trace_present": _cell(flags.get("trace_present", "")),
        "ledger_present": _cell(flags.get("ledger_present", "")),
        "schema_valid": _cell(flags.get("schema_valid", "")),
        "checklist_complete": _cell(flags.get("checklist_complete", "")),
        "source_validator_passed": _cell(flags.get("source_validator_passed", "")),
        "llm_judge_verdict": _cell(flags.get("llm_judge_verdict", "")),
    }


def _pipe_join(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _parse_annotators(value: str) -> tuple[str, str]:
    annotators = tuple(item.strip() for item in value.split(",") if item.strip())
    if len(annotators) != 2:
        raise ValueError("--annotators must contain exactly two comma-separated ids")
    if annotators[0] == annotators[1]:
        raise ValueError("--annotators must contain two distinct ids")
    return (annotators[0], annotators[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--jsonl-out", default=str(DEFAULT_JSONL_OUT))
    parser.add_argument("--annotators", default=",".join(DEFAULT_ANNOTATORS))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = read_cases_jsonl(Path(args.cases))
    annotators = _parse_annotators(str(args.annotators))
    rows = workbook_rows(cases, annotators=annotators)
    write_csv(Path(args.csv_out), rows)
    write_jsonl(Path(args.jsonl_out), rows)
    print(
        json.dumps(
            {
                "artifact_kind": "decision_evidence_manuscript_annotation_workbook_export",
                "cases": str(args.cases),
                "case_count": len(cases),
                "annotators": list(annotators),
                "property_count": len(DECISION_EVENT_PROPERTIES),
                "row_count": len(rows),
                "csv_out": str(args.csv_out),
                "jsonl_out": str(args.jsonl_out),
                "result_honesty": (
                    "The annotation workbook is an authoring aid with placeholder "
                    "categories. It does not create label evidence or manuscript results."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
