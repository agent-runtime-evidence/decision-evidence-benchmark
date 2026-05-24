"""Export a guarded manuscript annotation slice workbook."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from export_manuscript_annotation_workbook import CSV_COLUMNS as WORKBOOK_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "data/results/manuscript_annotation_workbook.csv"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_annotation_slice.csv"
DEFAULT_SUMMARY = ROOT / "data/results/manuscript_annotation_slice.json"
DEFAULT_SLICE_SIZE = 8

CSV_COLUMNS = (
    *WORKBOOK_COLUMNS,
    "slice_status",
    "annotation_instruction",
)

RESULT_HONESTY = (
    "The annotation slice is an authoring scaffold only. It is intentionally not "
    "a complete reviewed annotation workbook and does not create label evidence."
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def export_slice(
    *,
    workbook_rows: list[dict[str, str]],
    case_ids: list[str],
    slice_size: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    selected_case_ids = _select_case_ids(
        workbook_rows=workbook_rows,
        case_ids=case_ids,
        slice_size=slice_size,
    )
    rows_by_case_id = _rows_by_case_id(workbook_rows)
    rows = [
        _slice_row(row)
        for case_id in selected_case_ids
        for row in rows_by_case_id[case_id]
    ]
    summary = {
        "artifact_kind": "decision_evidence_manuscript_annotation_slice_export",
        "slice_strategy": "explicit_case_ids" if case_ids else "one_per_regime",
        "slice_size": slice_size,
        "selected_case_count": len(selected_case_ids),
        "selected_annotation_row_count": len(rows),
        "selected_property_count": len({row["property"] for row in rows}),
        "selected_annotators": sorted({row["annotator_id"] for row in rows}),
        "selected_cases": [
            {
                "case_id": case_id,
                "regime": rows_by_case_id[case_id][0].get("regime", ""),
                "degradation_condition": rows_by_case_id[case_id][0].get(
                    "degradation_condition", ""
                ),
                "question_family": rows_by_case_id[case_id][0].get("question_family", ""),
                "annotation_row_count": len(rows_by_case_id[case_id]),
            }
            for case_id in selected_case_ids
        ],
        "annotation_status_counts": dict(
            sorted(Counter(row["annotation_status"] or "__empty__" for row in rows).items())
        ),
        "category_counts": dict(
            sorted(Counter(row["category"] or "__empty__" for row in rows).items())
        ),
        "result_honesty": RESULT_HONESTY,
    }
    return rows, summary


def _select_case_ids(
    *,
    workbook_rows: list[dict[str, str]],
    case_ids: list[str],
    slice_size: int,
) -> list[str]:
    if slice_size < 1:
        raise ValueError("slice_size must be at least 1")
    if case_ids:
        return _select_explicit_case_ids(workbook_rows, case_ids)
    return _select_one_per_regime(workbook_rows, slice_size=slice_size)


def _select_explicit_case_ids(
    workbook_rows: list[dict[str, str]],
    case_ids: list[str],
) -> list[str]:
    counts = Counter(case_ids)
    duplicates = sorted(case_id for case_id, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate case IDs requested: {', '.join(duplicates)}")
    known_case_ids = {str(row.get("case_id", "")) for row in workbook_rows}
    missing = [case_id for case_id in case_ids if case_id not in known_case_ids]
    if missing:
        raise ValueError(f"case IDs not found in annotation workbook: {', '.join(missing)}")
    return case_ids


def _select_one_per_regime(
    workbook_rows: list[dict[str, str]],
    *,
    slice_size: int,
) -> list[str]:
    selected: list[str] = []
    seen_regimes: set[str] = set()
    seen_case_ids: set[str] = set()
    for row in workbook_rows:
        case_id = str(row.get("case_id", ""))
        regime = str(row.get("regime", ""))
        if not case_id or not regime or case_id in seen_case_ids or regime in seen_regimes:
            continue
        selected.append(case_id)
        seen_case_ids.add(case_id)
        seen_regimes.add(regime)
        if len(selected) == slice_size:
            break
    if len(selected) < slice_size:
        raise ValueError(
            f"one_per_regime selected {len(selected)} cases, expected {slice_size}"
        )
    return selected


def _rows_by_case_id(workbook_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    rows_by_case_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in workbook_rows:
        rows_by_case_id[str(row.get("case_id", ""))].append(row)
    return rows_by_case_id


def _slice_row(row: dict[str, str]) -> dict[str, str]:
    return {
        **{field: str(row.get(field, "")) for field in WORKBOOK_COLUMNS},
        "slice_status": "annotation_slice_not_importable",
        "annotation_instruction": (
            "Set annotation_status=annotated, choose one valid category, and add notes "
            "when useful. Merge the reviewed slice into the full workbook before import."
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
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--slice-size", type=int, default=DEFAULT_SLICE_SIZE)
    parser.add_argument("--case-id", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows, summary = export_slice(
        workbook_rows=read_csv(Path(args.workbook)),
        case_ids=[str(case_id) for case_id in args.case_id],
        slice_size=int(args.slice_size),
    )
    summary = {
        **summary,
        "workbook": str(args.workbook),
        "csv_out": str(args.csv_out),
        "summary": str(args.summary),
    }
    write_csv(Path(args.csv_out), rows)
    write_json(Path(args.summary), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
