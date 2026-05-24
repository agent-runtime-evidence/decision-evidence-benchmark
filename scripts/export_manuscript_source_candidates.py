"""Export source-root candidate refs for manuscript evidence review."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "data/results/manuscript_source_root_audit.json"
DEFAULT_CSV_OUT = ROOT / "data/results/manuscript_source_candidates.csv"
DEFAULT_JSONL_OUT = ROOT / "data/results/manuscript_source_candidates.jsonl"

CSV_COLUMNS = (
    "source_root",
    "scope",
    "promotion_ready",
    "source_use",
    "candidate_ref",
    "promotion_blockers",
    "blocking_indicators",
    "review_instruction",
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def build_rows(audit: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    for root in audit.get("source_roots", []):
        if not isinstance(root, dict):
            continue
        refs = root.get("candidate_refs", [])
        if not isinstance(refs, list):
            refs = []
        for ref in refs:
            rows.append(_candidate_row(root, str(ref)))

    report = {
        "artifact_kind": "decision_evidence_manuscript_source_candidate_export",
        "source_audit_path": str(audit.get("source_audit_path", DEFAULT_AUDIT)),
        "source_root_count": len(
            [root for root in audit.get("source_roots", []) if isinstance(root, dict)]
        ),
        "candidate_ref_count": len(rows),
        "promotion_ready_ref_count": sum(
            1 for row in rows if row["promotion_ready"] == "true"
        ),
        "result_honesty": (
            "Candidate refs are source-review aids only. Exporting a ref does not mark "
            "any manuscript case as reviewed_non_fixture_evidence."
        ),
    }
    return rows, report


def _candidate_row(root: dict[str, Any], candidate_ref: str) -> dict[str, str]:
    promotion_ready = bool(root.get("promotion_ready"))
    blockers = _pipe_join(root.get("promotion_blockers", []))
    indicators = _indicator_summary(root.get("blocking_indicators", []))
    promotion_role = str(root.get("promotion_role", ""))
    return {
        "source_root": str(root.get("name", "")),
        "scope": str(root.get("scope", "")),
        "promotion_ready": "true" if promotion_ready else "false",
        "source_use": _source_use(
            promotion_ready=promotion_ready,
            promotion_role=promotion_role,
            blockers=blockers,
        ),
        "candidate_ref": candidate_ref,
        "promotion_blockers": blockers,
        "blocking_indicators": indicators,
        "review_instruction": _review_instruction(
            promotion_ready=promotion_ready,
            promotion_role=promotion_role,
            blockers=blockers,
        ),
    }


def _source_use(*, promotion_ready: bool, promotion_role: str, blockers: str) -> str:
    if promotion_ready:
        return "case_source_candidate_after_row_review"
    if promotion_role == "required_manuscript_corpus_source":
        return "manuscript_corpus_source_needs_review"
    if "source_scope_not_manuscript_corpus_ready" in blockers:
        return "reference_context_only_until_corpus_scope_exists"
    if "required_files_missing" in blockers or "source_root_missing" in blockers:
        return "not_reviewable_until_source_root_complete"
    return "not_reviewable_until_audit_blockers_clear"


def _review_instruction(
    *,
    promotion_ready: bool,
    promotion_role: str,
    blockers: str,
) -> str:
    if promotion_ready:
        return (
            "Review this ref against a specific manuscript case row, add provenance notes, "
            "container flags, reviewer_id, and reviewed_at before import."
        )
    if promotion_role == "required_manuscript_corpus_source":
        return (
            "Fill the manuscript-corpus source rows with concrete refs, provenance notes, "
            "container flags, reviewer_id, and reviewed_at; rerun the audit before import."
        )
    if "source_scope_not_manuscript_corpus_ready" in blockers:
        return (
            "Use as background or reproducibility context only; do not mark a case row "
            "reviewed until a manuscript-corpus evidence source exists."
        )
    return "Resolve source-root audit blockers before row-level review."


def _indicator_summary(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    parts = []
    for item in value:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        indicator = str(item.get("indicator", "")).strip()
        if path and indicator:
            parts.append(f"{path}: {indicator}")
    return " | ".join(parts)


def _pipe_join(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
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
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--jsonl-out", default=str(DEFAULT_JSONL_OUT))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = read_json(Path(args.audit))
    audit["source_audit_path"] = str(args.audit)
    rows, report = build_rows(audit)
    write_csv(Path(args.csv_out), rows)
    write_jsonl(Path(args.jsonl_out), rows)
    print(
        json.dumps(
            {
                **report,
                "csv_out": str(args.csv_out),
                "jsonl_out": str(args.jsonl_out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
