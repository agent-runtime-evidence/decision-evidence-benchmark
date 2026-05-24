"""Export a guarded manuscript source-review slice workbook."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
DEFAULT_PACKET_INDEX = ROOT / "data/results/manuscript_source_review_packets.csv"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_source_review_slice.csv"
DEFAULT_SUMMARY = ROOT / "data/results/manuscript_source_review_slice.json"
CASE_SOURCE_NAME = "case_evidence_sources.jsonl"
DEFAULT_SLICE_SIZE = 8

CSV_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "packet_path",
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
    "slice_status",
    "review_instruction",
)

RESULT_HONESTY = (
    "The source-review slice is an authoring scaffold only. It is intentionally "
    "not a complete 64-row reviewed workbook and does not promote manuscript evidence."
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def export_slice(
    *,
    source_rows: list[dict[str, Any]],
    packet_index_rows: list[dict[str, str]],
    case_ids: list[str],
    slice_size: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    selected_rows = _select_rows(
        source_rows=source_rows,
        case_ids=case_ids,
        slice_size=slice_size,
    )
    packet_paths = _packet_paths(packet_index_rows)
    rows = [
        _slice_row(row, row_index=index + 1, packet_paths=packet_paths)
        for index, row in enumerate(selected_rows)
    ]
    missing_packet_case_ids = [
        row["case_id"] for row in rows if not row["packet_path"].strip()
    ]
    summary = {
        "artifact_kind": "decision_evidence_manuscript_source_review_slice_export",
        "slice_strategy": "explicit_case_ids" if case_ids else "one_per_regime",
        "slice_size": slice_size,
        "selected_case_count": len(rows),
        "selected_regime_count": len({row["regime"] for row in rows}),
        "selected_cases": [
            {
                "case_id": row["case_id"],
                "regime": row["regime"],
                "degradation_condition": row["degradation_condition"],
                "question_family": row["question_family"],
                "packet_path": row["packet_path"],
            }
            for row in rows
        ],
        "missing_packet_case_ids": missing_packet_case_ids,
        "review_status_counts": dict(
            sorted(Counter(row["review_status"] or "__empty__" for row in rows).items())
        ),
        "result_honesty": RESULT_HONESTY,
    }
    return rows, summary


def _select_rows(
    *,
    source_rows: list[dict[str, Any]],
    case_ids: list[str],
    slice_size: int,
) -> list[dict[str, Any]]:
    if slice_size < 1:
        raise ValueError("slice_size must be at least 1")
    if case_ids:
        return _select_explicit_case_ids(source_rows, case_ids)
    return _select_one_per_regime(source_rows, slice_size=slice_size)


def _select_explicit_case_ids(
    source_rows: list[dict[str, Any]],
    case_ids: list[str],
) -> list[dict[str, Any]]:
    counts = Counter(case_ids)
    duplicates = sorted(case_id for case_id, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate case IDs requested: {', '.join(duplicates)}")
    source_by_case_id = {str(row.get("case_id", "")): row for row in source_rows}
    missing = [case_id for case_id in case_ids if case_id not in source_by_case_id]
    if missing:
        raise ValueError(f"case IDs not found in source root: {', '.join(missing)}")
    return [source_by_case_id[case_id] for case_id in case_ids]


def _select_one_per_regime(
    source_rows: list[dict[str, Any]],
    *,
    slice_size: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_regimes: set[str] = set()
    for row in source_rows:
        regime = str(row.get("regime", ""))
        if not regime or regime in seen_regimes:
            continue
        selected.append(row)
        seen_regimes.add(regime)
        if len(selected) == slice_size:
            break
    if len(selected) < slice_size:
        raise ValueError(
            f"one_per_regime selected {len(selected)} rows, expected {slice_size}"
        )
    return selected


def _packet_paths(packet_index_rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        str(row.get("case_id", "")): str(row.get("packet_path", ""))
        for row in packet_index_rows
    }


def _slice_row(
    row: dict[str, Any],
    *,
    row_index: int,
    packet_paths: dict[str, str],
) -> dict[str, str]:
    case_id = str(row.get("case_id", ""))
    return {
        "row_index": str(row_index),
        "case_id": case_id,
        "regime": str(row.get("regime", "")),
        "degradation_condition": str(row.get("degradation_condition", "")),
        "question_family": str(row.get("question_family", "")),
        "packet_path": packet_paths.get(case_id, ""),
        "current_template_status": str(row.get("template_status", "")),
        "review_status": "",
        "native_evidence_refs": "",
        "reviewed_source_refs": "",
        "evidence_plane_refs": "",
        "provenance_notes": "",
        "trace_present": "",
        "ledger_present": "",
        "schema_valid": "",
        "checklist_complete": "",
        "source_validator_passed": "",
        "llm_judge_verdict": "",
        "reviewer_id": "",
        "reviewed_at": "",
        "authoring_notes": "",
        "slice_status": "source_review_slice_not_importable",
        "review_instruction": (
            "Fill this row from the packet, then merge reviewed values into the "
            "full 64-row source review workbook before import."
        ),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--packet-index", default=str(DEFAULT_PACKET_INDEX))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--slice-size", type=int, default=DEFAULT_SLICE_SIZE)
    parser.add_argument("--case-id", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_root = Path(args.source_root)
    rows, summary = export_slice(
        source_rows=read_jsonl(source_root / CASE_SOURCE_NAME),
        packet_index_rows=read_csv(Path(args.packet_index)),
        case_ids=[str(case_id) for case_id in args.case_id],
        slice_size=int(args.slice_size),
    )
    summary = {
        **summary,
        "source_root": str(source_root),
        "packet_index": str(args.packet_index),
        "csv_out": str(args.csv_out),
        "summary": str(args.summary),
    }
    write_csv(Path(args.csv_out), rows)
    write_json(Path(args.summary), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
