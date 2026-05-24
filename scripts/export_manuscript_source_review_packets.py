"""Export per-case manuscript source-review packets as authoring aids."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
DEFAULT_SOURCE_CANDIDATES = ROOT / "data/results/manuscript_source_candidates.csv"
DEFAULT_PACKET_DIR = ROOT / "data/results/manuscript_source_review_packets"
DEFAULT_INDEX_CSV = ROOT / "data/results/manuscript_source_review_packets.csv"
DEFAULT_SUMMARY = ROOT / "data/results/manuscript_source_review_packets.json"
CASE_SOURCE_NAME = "case_evidence_sources.jsonl"

ACCEPTED_REVIEW_STATUSES = ("ready_for_conversion", "source_reviewed_needs_annotation")
BOOLEAN_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
LLM_JUDGE_VERDICTS = ("abstain", "insufficient", "sufficient")
SOURCE_LIST_FIELDS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)
SOURCE_REVIEW_FIELDS = SOURCE_LIST_FIELDS + ("provenance_notes",)
REVIEW_METADATA_FIELDS = ("review_status", "reviewer_id", "reviewed_at")
REQUIRED_SOURCE_USES = (
    "case_source_candidate_after_row_review",
    "manuscript_corpus_source_needs_review",
)
ADVISORY_SOURCE_USE = "reference_context_only_until_corpus_scope_exists"

INDEX_COLUMNS = (
    "row_index",
    "case_id",
    "regime",
    "degradation_condition",
    "question_family",
    "packet_path",
    "template_status",
    "review_status",
    "missing_source_fields",
    "missing_container_flags",
    "missing_review_fields",
    "required_candidate_ref_count",
    "advisory_ref_count",
    "candidate_ref_count",
)

RESULT_HONESTY = (
    "Source-review packets are authoring aids only. Exporting packets does not review, "
    "validate, promote, or create manuscript result evidence."
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


def build_packets(
    *,
    source_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, str]],
    packet_dir: Path,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    packet_dir.mkdir(parents=True, exist_ok=True)
    required_refs = _candidate_subset(candidate_rows, REQUIRED_SOURCE_USES)
    advisory_refs = _candidate_subset(candidate_rows, (ADVISORY_SOURCE_USE,))

    index_rows: list[dict[str, str]] = []
    packet_reports: list[dict[str, Any]] = []
    for row_index, row in enumerate(source_rows, start=1):
        case_id = str(row.get("case_id", ""))
        packet_path = packet_dir / f"{row_index:02d}_{_slug(case_id)}.md"
        missing_source_fields = _missing_source_fields(row)
        missing_container_flags = _missing_container_flags(row)
        missing_review_fields = _missing_review_fields(row)
        packet_path.write_text(
            _packet_markdown(
                row=row,
                row_index=row_index,
                missing_source_fields=missing_source_fields,
                missing_container_flags=missing_container_flags,
                missing_review_fields=missing_review_fields,
                required_refs=required_refs,
                advisory_refs=advisory_refs,
            )
        )
        metadata = _dict_value(row.get("metadata"))
        index_rows.append(
            {
                "row_index": str(row_index),
                "case_id": case_id,
                "regime": str(row.get("regime", "")),
                "degradation_condition": str(row.get("degradation_condition", "")),
                "question_family": str(row.get("question_family", "")),
                "packet_path": _path_cell(packet_path),
                "template_status": str(row.get("template_status", "")),
                "review_status": str(metadata.get("review_status", "todo")),
                "missing_source_fields": _pipe_join(missing_source_fields),
                "missing_container_flags": _pipe_join(missing_container_flags),
                "missing_review_fields": _pipe_join(missing_review_fields),
                "required_candidate_ref_count": str(len(required_refs)),
                "advisory_ref_count": str(len(advisory_refs)),
                "candidate_ref_count": str(len(candidate_rows)),
            }
        )
        packet_reports.append(
            {
                "case_id": case_id,
                "packet_path": _path_cell(packet_path),
                "missing_source_fields": missing_source_fields,
                "missing_container_flags": missing_container_flags,
                "missing_review_fields": missing_review_fields,
            }
        )
    return index_rows, packet_reports


def _packet_markdown(
    *,
    row: dict[str, Any],
    row_index: int,
    missing_source_fields: list[str],
    missing_container_flags: list[str],
    missing_review_fields: list[str],
    required_refs: list[dict[str, str]],
    advisory_refs: list[dict[str, str]],
) -> str:
    metadata = _dict_value(row.get("metadata"))
    case_id = str(row.get("case_id", ""))
    sections = [
        f"# Source Review Packet: {case_id}",
        "",
        "## Case",
        "",
        f"- Row index: {row_index}",
        f"- Case ID: `{case_id}`",
        f"- Regime: `{row.get('regime', '')}`",
        f"- Degradation condition: `{row.get('degradation_condition', '')}`",
        f"- Question family: `{row.get('question_family', '')}`",
        f"- Template status: `{row.get('template_status', '')}`",
        f"- Current review status: `{metadata.get('review_status', 'todo')}`",
        "",
        "## Current Gaps",
        "",
        f"- Source fields: {_list_cell(missing_source_fields)}",
        f"- Container flags: {_list_cell(missing_container_flags)}",
        f"- Review metadata: {_list_cell(missing_review_fields)}",
        "",
        "## Fields To Fill",
        "",
        f"- `review_status`: one of `{_pipe_join(ACCEPTED_REVIEW_STATUSES)}`",
        *[f"- `{field}`" for field in SOURCE_REVIEW_FIELDS],
        *[f"- `{field}`: `true` or `false`" for field in BOOLEAN_CONTAINER_FLAGS],
        f"- `llm_judge_verdict`: one of `{_pipe_join(LLM_JUDGE_VERDICTS)}`",
        "- `reviewer_id`",
        "- `reviewed_at`",
        "- `authoring_notes` if useful",
        "",
        "## Required Manuscript Source Root Refs",
        "",
        _candidate_markdown(required_refs),
        "",
        "## Advisory Context Refs",
        "",
        _candidate_markdown(advisory_refs),
        "",
        "## Review Checklist",
        "",
        "- [ ] Native evidence refs are concrete and tied to this case.",
        "- [ ] Reviewed source refs point to source material, not fixture placeholders.",
        "- [ ] Evidence-plane refs identify trace, ledger, or decision-record material.",
        "- [ ] Provenance notes explain why the refs support the case row.",
        "- [ ] Container flags are concrete booleans and verdict values.",
        "- [ ] Reviewer metadata is filled before workbook import.",
        "- [ ] Advisory refs are used only as context unless promoted into the manuscript root.",
        "",
        "## Non-Promotion Boundary",
        "",
        RESULT_HONESTY,
        "",
    ]
    return "\n".join(sections)


def _candidate_markdown(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No candidate refs in this category."
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("source_root", ""))].append(row)

    lines: list[str] = []
    for source_root in sorted(grouped):
        lines.append(f"### {source_root or 'unknown_source_root'}")
        lines.append("")
        for row in grouped[source_root]:
            candidate_ref = str(row.get("candidate_ref", ""))
            source_use = str(row.get("source_use", ""))
            blockers = str(row.get("promotion_blockers", ""))
            instruction = str(row.get("review_instruction", ""))
            lines.append(f"- `{candidate_ref}`")
            lines.append(f"  - Source use: `{source_use}`")
            if blockers:
                lines.append(f"  - Promotion blockers: `{blockers}`")
            if instruction:
                lines.append(f"  - Review instruction: {instruction}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _candidate_subset(
    rows: list[dict[str, str]],
    source_uses: tuple[str, ...],
) -> list[dict[str, str]]:
    source_use_set = set(source_uses)
    return [row for row in rows if str(row.get("source_use", "")) in source_use_set]


def _missing_source_fields(row: dict[str, Any]) -> list[str]:
    source_requirements = _dict_value(row.get("source_requirements"))
    missing: list[str] = []
    for field in SOURCE_LIST_FIELDS:
        refs = _split_refs(source_requirements.get(field))
        if not refs or any(_placeholder(ref) for ref in refs):
            missing.append(field)
    provenance = str(source_requirements.get("provenance_notes", "")).strip()
    if _placeholder(provenance):
        missing.append("provenance_notes")
    return missing


def _missing_container_flags(row: dict[str, Any]) -> list[str]:
    container_flags = _dict_value(row.get("container_flags"))
    missing: list[str] = []
    for flag in BOOLEAN_CONTAINER_FLAGS:
        if not _bool_like(container_flags.get(flag)):
            missing.append(flag)
    verdict = str(container_flags.get("llm_judge_verdict", "")).strip()
    if verdict not in LLM_JUDGE_VERDICTS:
        missing.append("llm_judge_verdict")
    return missing


def _missing_review_fields(row: dict[str, Any]) -> list[str]:
    metadata = _dict_value(row.get("metadata"))
    missing: list[str] = []
    review_status = str(metadata.get("review_status", "")).strip()
    if review_status not in ACCEPTED_REVIEW_STATUSES:
        missing.append("review_status")
    for field in ("reviewer_id", "reviewed_at"):
        if _placeholder(str(metadata.get(field, ""))):
            missing.append(field)
    return missing


def _dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _split_refs(value: Any) -> list[str]:
    if isinstance(value, list | tuple):
        raw_values = value
    else:
        raw_values = str(value or "").split("|")
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _bool_like(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    return str(value).strip().lower() in {"true", "false"}


def _placeholder(value: str) -> bool:
    stripped = value.strip()
    return not stripped or stripped.startswith("__") or stripped.endswith("__")


def _pipe_join(value: Any) -> str:
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _list_cell(values: list[str]) -> str:
    return _pipe_join(values) if values else "none"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "case"


def _path_cell(path: Path) -> str:
    return path.as_posix()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--source-candidates", default=str(DEFAULT_SOURCE_CANDIDATES))
    parser.add_argument("--packet-dir", default=str(DEFAULT_PACKET_DIR))
    parser.add_argument("--index-csv", default=str(DEFAULT_INDEX_CSV))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_root = Path(args.source_root)
    source_rows = read_jsonl(source_root / CASE_SOURCE_NAME)
    candidate_rows = read_csv(Path(args.source_candidates))
    index_rows, packet_reports = build_packets(
        source_rows=source_rows,
        candidate_rows=candidate_rows,
        packet_dir=Path(args.packet_dir),
    )
    write_csv(Path(args.index_csv), index_rows)
    source_use_counts = Counter(str(row.get("source_use", "")) for row in candidate_rows)
    summary = {
        "artifact_kind": "decision_evidence_manuscript_source_review_packet_export",
        "source_root": str(source_root),
        "source_candidates": str(args.source_candidates),
        "packet_dir": str(args.packet_dir),
        "index_csv": str(args.index_csv),
        "packet_count": len(index_rows),
        "candidate_ref_count": len(candidate_rows),
        "required_candidate_ref_count": sum(
            source_use_counts[source_use] for source_use in REQUIRED_SOURCE_USES
        ),
        "advisory_ref_count": source_use_counts[ADVISORY_SOURCE_USE],
        "source_use_counts": dict(sorted(source_use_counts.items())),
        "current_review_status_counts": dict(
            sorted(
                Counter(
                    str(_dict_value(row.get("metadata")).get("review_status", "todo"))
                    for row in source_rows
                ).items()
            )
        ),
        "packet_reports": packet_reports,
        "result_honesty": RESULT_HONESTY,
    }
    write_json(Path(args.summary), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
