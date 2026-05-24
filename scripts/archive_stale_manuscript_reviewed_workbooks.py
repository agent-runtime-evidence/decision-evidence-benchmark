"""Archive stale non-redacted manuscript reviewed workbooks."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.manuscript_redaction import SCORER_INPUT_REDACTION_STATUS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORER_WORKBOOK_REVIEWED = ROOT / "data/results/manuscript_scorer_workbook.reviewed.csv"
DEFAULT_LLM_JUDGE_WORKBOOK_REVIEWED = (
    ROOT / "data/results/manuscript_llm_judge_workbook.reviewed.csv"
)
DEFAULT_ARCHIVE_DIR = ROOT / "data/results/manuscript_stale_reviewed_workbook_archive"
DEFAULT_REPORT = ROOT / "data/results/manuscript_stale_reviewed_workbook_archive.json"


def archive_stale_workbooks(
    *,
    workbook_paths: list[Path],
    archive_dir: Path,
    report: Path,
    archive_label: str | None = None,
) -> dict[str, Any]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    label = archive_label or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifacts = [
        _process_workbook(path, archive_dir=archive_dir, archive_label=label)
        for path in workbook_paths
    ]
    payload = {
        "artifact_kind": "decision_evidence_manuscript_stale_reviewed_workbook_archive",
        "valid": not any(artifact.get("issue_severity") == "error" for artifact in artifacts),
        "archive_dir": str(archive_dir),
        "archive_label": label,
        "archived_count": sum(1 for artifact in artifacts if artifact.get("action") == "archived"),
        "skipped_count": sum(1 for artifact in artifacts if artifact.get("action") == "skipped"),
        "artifacts": artifacts,
        "result_honesty": (
            "This target archives only local reviewed CSV workbooks that are missing "
            "the scorer-input redaction marker. It does not create reviewed predictions, "
            "candidate scorer outputs, baseline outputs, or manuscript results."
        ),
    }
    _write_json(report, payload)
    return payload


def _process_workbook(
    path: Path,
    *,
    archive_dir: Path,
    archive_label: str,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        record["action"] = "skipped"
        record["reason"] = "missing"
        return record
    try:
        summary = _csv_redaction_summary(path)
    except csv.Error as exc:
        record.update(
            {
                "action": "skipped",
                "issue": "csv_read_error",
                "issue_severity": "error",
                "error": str(exc),
            }
        )
        return record
    record.update(summary)
    if summary["redacted_input"]:
        record["action"] = "skipped"
        record["reason"] = "already_redacted"
        return record
    archive_path = _archive_path(path, archive_dir=archive_dir, archive_label=archive_label)
    shutil.move(str(path), archive_path)
    record["action"] = "archived"
    record["reason"] = "non_redacted_reviewed_workbook"
    record["archive_path"] = str(archive_path)
    return record


def _csv_redaction_summary(path: Path) -> dict[str, Any]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    columns = list(reader.fieldnames or [])
    redacted_row_count = sum(
        1
        for row in rows
        if str(row.get("redaction_status", "")).strip() == SCORER_INPUT_REDACTION_STATUS
    )
    return {
        "row_count": len(rows),
        "columns": columns,
        "redacted_row_count": redacted_row_count,
        "redacted_input": bool(rows) and redacted_row_count == len(rows),
    }


def _archive_path(path: Path, *, archive_dir: Path, archive_label: str) -> Path:
    archive_path = archive_dir / f"{path.name}.{archive_label}.stale"
    if not archive_path.exists():
        return archive_path
    for index in range(1, 1000):
        candidate = archive_dir / f"{path.name}.{archive_label}.{index}.stale"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate unique archive path for {path}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scorer-workbook-reviewed",
        default=str(DEFAULT_SCORER_WORKBOOK_REVIEWED),
    )
    parser.add_argument(
        "--llm-judge-workbook-reviewed",
        default=str(DEFAULT_LLM_JUDGE_WORKBOOK_REVIEWED),
    )
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--archive-label")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = archive_stale_workbooks(
        workbook_paths=[
            Path(args.scorer_workbook_reviewed),
            Path(args.llm_judge_workbook_reviewed),
        ],
        archive_dir=Path(args.archive_dir),
        report=Path(args.report),
        archive_label=args.archive_label,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
