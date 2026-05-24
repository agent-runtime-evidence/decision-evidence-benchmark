"""Import a reviewed source workbook into the manuscript-corpus source root."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.schema import VERDICTS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
DEFAULT_WORKBOOK = ROOT / "data/results/manuscript_source_review_workbook.reviewed.csv"
DEFAULT_REPORT = ROOT / "data/results/manuscript_source_review_import.json"
CASE_SOURCE_NAME = "case_evidence_sources.jsonl"
SOURCE_MANIFEST_NAME = "source_manifest.json"
REVIEWED_STATUS = "reviewed_non_fixture_evidence"
READY_SOURCE_SCOPE = "manuscript_corpus_evidence"
ACCEPTED_REVIEW_STATUSES = {
    "ready_for_conversion",
    "source_reviewed_needs_annotation",
}
SOURCE_LIST_FIELDS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)
BOOLEAN_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
TAXONOMY_FIELDS = ("regime", "degradation_condition", "question_family")


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


def read_workbook(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def import_rows(
    *,
    source_rows: list[dict[str, Any]],
    workbook_rows: list[dict[str, Any]],
    expected_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []

    if len(source_rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_source_row_count",
                "expected": expected_count,
                "actual": len(source_rows),
            }
        )
    if len(workbook_rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_workbook_row_count",
                "expected": expected_count,
                "actual": len(workbook_rows),
            }
        )

    source_by_case_id = {str(row.get("case_id", "")): row for row in source_rows}
    for case_id, count in Counter(str(row.get("case_id", "")) for row in workbook_rows).items():
        if count > 1:
            issues.append(
                {"severity": "error", "issue": "duplicate_workbook_case_id", "case_id": case_id}
            )

    for index, source_row in enumerate(source_rows, start=1):
        case_id = str(source_row.get("case_id", ""))
        matching = [row for row in workbook_rows if str(row.get("case_id", "")) == case_id]
        if not matching:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_workbook_row",
                    "case_id": case_id,
                    "row_index": index,
                }
            )
            continue
        workbook_row = matching[0]
        row_issues = _row_issues(workbook_row, source_by_case_id=source_by_case_id)
        issues.extend(row_issues)
        if row_issues:
            continue
        output_rows.append(_reviewed_source_row(source_row, workbook_row))

    report = {
        "artifact_kind": "decision_evidence_manuscript_source_review_workbook_import",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "expected_count": expected_count,
        "source_row_count": len(source_rows),
        "workbook_row_count": len(workbook_rows),
        "output_row_count": len(output_rows),
        "review_status_counts": dict(
            sorted(Counter(str(row.get("review_status", "")) for row in workbook_rows).items())
        ),
        "issues": issues,
        "result_honesty": (
            "The importer updates the manuscript-corpus source root only when every "
            "workbook row is reviewed and complete. It does not create results."
        ),
    }
    return output_rows, report


def _row_issues(
    row: dict[str, Any],
    *,
    source_by_case_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", ""))
    source_row = source_by_case_id.get(case_id)
    if not case_id.strip():
        issues.append({"severity": "error", "issue": "missing_case_id"})
        return issues
    if not source_row:
        issues.append({"severity": "error", "issue": "case_id_not_in_source", "case_id": case_id})
        return issues

    for field in TAXONOMY_FIELDS:
        if str(row.get(field, "")) != str(source_row.get(field, "")):
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "taxonomy_mismatch",
                    "field": field,
                    "expected": source_row.get(field),
                    "actual": row.get(field),
                }
            )

    review_status = str(row.get("review_status", "")).strip()
    if review_status not in ACCEPTED_REVIEW_STATUSES:
        issues.append(
            {
                "severity": "error",
                "case_id": case_id,
                "issue": "invalid_review_status",
                "expected": sorted(ACCEPTED_REVIEW_STATUSES),
                "actual": review_status,
            }
        )

    for field in SOURCE_LIST_FIELDS:
        refs = _split_refs(row.get(field))
        if not refs:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "missing_source_refs",
                    "field": field,
                }
            )
        elif any(_placeholder(ref) for ref in refs):
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "placeholder_source_ref",
                    "field": field,
                }
            )

    for field in ("provenance_notes", "reviewer_id", "reviewed_at"):
        value = str(row.get(field, "")).strip()
        if not value:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "missing_review_field",
                    "field": field,
                }
            )
        elif _placeholder(value):
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "placeholder_review_field",
                    "field": field,
                }
            )

    for flag in BOOLEAN_CONTAINER_FLAGS:
        try:
            _parse_bool(row.get(flag))
        except ValueError:
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "invalid_container_flag",
                    "field": flag,
                    "actual": row.get(flag),
                }
            )

    verdict = str(row.get("llm_judge_verdict", "")).strip()
    if verdict not in VERDICTS:
        issues.append(
            {
                "severity": "error",
                "case_id": case_id,
                "issue": "invalid_llm_judge_verdict",
                "expected": sorted(VERDICTS),
                "actual": verdict,
            }
        )
    return issues


def _reviewed_source_row(
    source_row: dict[str, Any], workbook_row: dict[str, Any]
) -> dict[str, Any]:
    metadata = dict(source_row.get("metadata", {}))
    metadata.update(
        {
            "authoring_status": "source_reviewed",
            "review_status": str(workbook_row["review_status"]).strip(),
            "reviewer_id": str(workbook_row["reviewer_id"]).strip(),
            "reviewed_at": str(workbook_row["reviewed_at"]).strip(),
            "authoring_notes": str(workbook_row.get("authoring_notes", "")).strip(),
            "source_root_status": REVIEWED_STATUS,
            "result_honesty": (
                "Reviewed manuscript-corpus source row only. Result claims require "
                "separate annotation, adjudication, scorer, and baseline artifacts."
            ),
        }
    )
    return {
        "case_id": str(source_row["case_id"]),
        "template_status": REVIEWED_STATUS,
        "regime": str(source_row["regime"]),
        "degradation_condition": str(source_row["degradation_condition"]),
        "question_family": str(source_row["question_family"]),
        "source_requirements": {
            "native_evidence_refs": _split_refs(workbook_row.get("native_evidence_refs")),
            "reviewed_source_refs": _split_refs(workbook_row.get("reviewed_source_refs")),
            "evidence_plane_refs": _split_refs(workbook_row.get("evidence_plane_refs")),
            "provenance_notes": str(workbook_row["provenance_notes"]).strip(),
        },
        "container_flags": {
            "trace_present": _parse_bool(workbook_row.get("trace_present")),
            "ledger_present": _parse_bool(workbook_row.get("ledger_present")),
            "schema_valid": _parse_bool(workbook_row.get("schema_valid")),
            "checklist_complete": _parse_bool(workbook_row.get("checklist_complete")),
            "source_validator_passed": _parse_bool(workbook_row.get("source_validator_passed")),
            "llm_judge_verdict": str(workbook_row["llm_judge_verdict"]).strip(),
        },
        "property_label_authoring": source_row.get("property_label_authoring", []),
        "metadata": metadata,
    }


def _source_manifest(*, case_count: int) -> dict[str, Any]:
    return {
        "artifact_kind": "decision_evidence_manuscript_corpus_source_manifest",
        "schema_version": 1,
        "source_scope": READY_SOURCE_SCOPE,
        "source_status": REVIEWED_STATUS,
        "case_source_file": CASE_SOURCE_NAME,
        "expected_case_count": case_count,
        "result_honesty": (
            "Reviewed manuscript-corpus source root only. It is not a result package and "
            "does not establish empirical claims by itself."
        ),
    }


def _split_refs(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = str(value or "").split("|")
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"expected true/false, got {value!r}")


def _placeholder(value: str) -> bool:
    stripped = value.strip()
    return not stripped or stripped.startswith("__") or stripped.endswith("__")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def write_source_root(source_root: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(source_root / CASE_SOURCE_NAME, rows)
    write_json(source_root / SOURCE_MANIFEST_NAME, _source_manifest(case_count=len(rows)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--expected-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_root = Path(args.source_root)
    output_rows, report = import_rows(
        source_rows=read_jsonl(source_root / CASE_SOURCE_NAME),
        workbook_rows=read_workbook(Path(args.workbook)),
        expected_count=int(args.expected_count),
    )
    write_json(Path(args.report), report)
    if report["valid"]:
        write_source_root(source_root, output_rows)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
