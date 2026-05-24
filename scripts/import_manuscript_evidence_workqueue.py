"""Import a reviewed evidence workqueue into reviewed manuscript source rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.schema import VERDICTS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_WORKQUEUE = ROOT / "data/results/manuscript_evidence_workqueue.reviewed.csv"
DEFAULT_OUT = ROOT / "data/cases/manuscript_case_sources.reviewed.jsonl"
DEFAULT_REPORT = ROOT / "data/results/manuscript_evidence_workqueue_import.json"

REVIEWED_STATUS = "reviewed_non_fixture_evidence"
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


def read_workqueue(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def import_rows(
    *,
    template_rows: list[dict[str, Any]],
    workqueue_rows: list[dict[str, Any]],
    expected_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []

    if len(template_rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_template_count",
                "expected": expected_count,
                "actual": len(template_rows),
            }
        )
    if len(workqueue_rows) != expected_count:
        issues.append(
            {
                "severity": "error",
                "issue": "unexpected_workqueue_count",
                "expected": expected_count,
                "actual": len(workqueue_rows),
            }
        )

    template_by_case_id = {str(row.get("case_id")): row for row in template_rows}
    for case_id, count in Counter(str(row.get("case_id")) for row in workqueue_rows).items():
        if count > 1:
            issues.append(
                {"severity": "error", "issue": "duplicate_workqueue_case_id", "case_id": case_id}
            )

    for index, template_row in enumerate(template_rows, start=1):
        case_id = str(template_row.get("case_id", ""))
        matching = [row for row in workqueue_rows if str(row.get("case_id", "")) == case_id]
        if not matching:
            issues.append(
                {
                    "severity": "error",
                    "issue": "missing_workqueue_row",
                    "case_id": case_id,
                    "row_index": index,
                }
            )
            continue
        row = matching[0]
        row_issues = _row_issues(row, template_by_case_id=template_by_case_id)
        issues.extend(row_issues)
        if row_issues:
            continue
        output_rows.append(_reviewed_source_row(template_row, row))

    report = {
        "artifact_kind": "decision_evidence_manuscript_evidence_workqueue_import",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "expected_count": expected_count,
        "template_row_count": len(template_rows),
        "workqueue_row_count": len(workqueue_rows),
        "output_row_count": len(output_rows),
        "review_status_counts": dict(
            sorted(Counter(str(row.get("review_status", "")) for row in workqueue_rows).items())
        ),
        "issues": issues,
        "result_honesty": (
            "The importer promotes only source-reviewed rows into a reviewed case-source "
            "JSONL. It does not adjudicate property labels and does not create results."
        ),
    }
    return output_rows, report


def _row_issues(
    row: dict[str, Any],
    *,
    template_by_case_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = str(row.get("case_id", ""))
    template_row = template_by_case_id.get(case_id)
    if not case_id.strip():
        issues.append({"severity": "error", "issue": "missing_case_id"})
        return issues
    if not template_row:
        issues.append({"severity": "error", "issue": "case_id_not_in_template", "case_id": case_id})
        return issues

    for field in TAXONOMY_FIELDS:
        if str(row.get(field, "")) != str(template_row.get(field, "")):
            issues.append(
                {
                    "severity": "error",
                    "case_id": case_id,
                    "issue": "taxonomy_mismatch",
                    "field": field,
                    "expected": template_row.get(field),
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
    template_row: dict[str, Any], workqueue_row: dict[str, Any]
) -> dict[str, Any]:
    metadata = dict(template_row.get("metadata", {}))
    metadata.update(
        {
            "authoring_status": "source_reviewed",
            "review_status": str(workqueue_row["review_status"]).strip(),
            "reviewer_id": str(workqueue_row["reviewer_id"]).strip(),
            "reviewed_at": str(workqueue_row["reviewed_at"]).strip(),
            "authoring_notes": str(workqueue_row.get("authoring_notes", "")).strip(),
            "result_honesty": (
                "Source-reviewed case-source row only. Property labels and empirical "
                "results require separate annotation, adjudication, scorer, and baseline artifacts."
            ),
        }
    )
    return {
        "case_id": str(template_row["case_id"]),
        "template_status": REVIEWED_STATUS,
        "regime": str(template_row["regime"]),
        "degradation_condition": str(template_row["degradation_condition"]),
        "question_family": str(template_row["question_family"]),
        "source_requirements": {
            "native_evidence_refs": _split_refs(workqueue_row.get("native_evidence_refs")),
            "reviewed_source_refs": _split_refs(workqueue_row.get("reviewed_source_refs")),
            "evidence_plane_refs": _split_refs(workqueue_row.get("evidence_plane_refs")),
            "provenance_notes": str(workqueue_row["provenance_notes"]).strip(),
        },
        "container_flags": {
            "trace_present": _parse_bool(workqueue_row.get("trace_present")),
            "ledger_present": _parse_bool(workqueue_row.get("ledger_present")),
            "schema_valid": _parse_bool(workqueue_row.get("schema_valid")),
            "checklist_complete": _parse_bool(workqueue_row.get("checklist_complete")),
            "source_validator_passed": _parse_bool(workqueue_row.get("source_validator_passed")),
            "llm_judge_verdict": str(workqueue_row["llm_judge_verdict"]).strip(),
        },
        "property_label_authoring": template_row.get("property_label_authoring", []),
        "metadata": metadata,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--workqueue", default=str(DEFAULT_WORKQUEUE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--expected-count", type=int, default=64)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_rows, report = import_rows(
        template_rows=read_jsonl(Path(args.template)),
        workqueue_rows=read_workqueue(Path(args.workqueue)),
        expected_count=int(args.expected_count),
    )
    write_json(Path(args.report), report)
    if report["valid"]:
        write_jsonl(Path(args.out), output_rows)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
