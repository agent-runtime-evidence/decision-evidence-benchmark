"""Export manuscript-corpus source rows to a review workbook CSV/JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_source_review_workbook.csv"
DEFAULT_JSONL_OUT = ROOT / "data/results/manuscript_source_review_workbook.jsonl"
CASE_SOURCE_NAME = "case_evidence_sources.jsonl"

CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "current_template_status",
    "review_status",
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
    "reviewer_id",
    "reviewed_at",
    "authoring_notes",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def workbook_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        _workbook_row(row, row_index=index + 1) for index, row in enumerate(source_rows)
    ]


def _workbook_row(row: dict[str, Any], *, row_index: int) -> dict[str, str]:
    source_requirements = row.get("source_requirements")
    if not isinstance(source_requirements, dict):
        source_requirements = {}
    container_flags = row.get("container_flags")
    if not isinstance(container_flags, dict):
        container_flags = {}
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "row_index": str(row_index),
        "case_id": str(row.get("case_id", "")),
        "regime": str(row.get("regime", "")),
        "degradation_condition": str(row.get("degradation_condition", "")),
        "question_family": str(row.get("question_family", "")),
        "current_template_status": str(row.get("template_status", "")),
        "review_status": str(metadata.get("review_status", "todo")),
        "native_evidence_refs": _pipe_join(source_requirements.get("native_evidence_refs", [])),
        "reviewed_source_refs": _pipe_join(
            source_requirements.get("reviewed_source_refs", [])
        ),
        "evidence_plane_refs": _pipe_join(source_requirements.get("evidence_plane_refs", [])),
        "provenance_notes": str(source_requirements.get("provenance_notes", "")),
        "trace_present": _cell(container_flags.get("trace_present", "")),
        "ledger_present": _cell(container_flags.get("ledger_present", "")),
        "schema_valid": _cell(container_flags.get("schema_valid", "")),
        "checklist_complete": _cell(container_flags.get("checklist_complete", "")),
        "source_validator_passed": _cell(container_flags.get("source_validator_passed", "")),
        "llm_judge_verdict": _cell(container_flags.get("llm_judge_verdict", "")),
        "reviewer_id": str(metadata.get("reviewer_id", "")),
        "reviewed_at": str(metadata.get("reviewed_at", "")),
        "authoring_notes": str(metadata.get("authoring_notes", "")),
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--jsonl-out", default=str(DEFAULT_JSONL_OUT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_root = Path(args.source_root)
    rows = workbook_rows(read_jsonl(source_root / CASE_SOURCE_NAME))
    write_csv(Path(args.csv_out), rows)
    write_jsonl(Path(args.jsonl_out), rows)
    print(
        json.dumps(
            {
                "artifact_kind": "decision_evidence_manuscript_source_review_workbook_export",
                "source_root": str(source_root),
                "row_count": len(rows),
                "csv_out": str(args.csv_out),
                "jsonl_out": str(args.jsonl_out),
                "result_honesty": (
                    "The workbook is an authoring aid. Exporting rows does not review "
                    "or promote manuscript evidence."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
