"""Initialize the manuscript-corpus evidence source root."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"
SOURCE_MANIFEST_NAME = "source_manifest.json"
CASE_SOURCE_NAME = "case_evidence_sources.jsonl"
SOURCE_SCOPE_TEMPLATE = "manuscript_corpus_evidence_source_template"


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


def source_rows(template_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in template_rows:
        source_row = copy.deepcopy(row)
        metadata = dict(source_row.get("metadata", {}))
        metadata.update(
            {
                "authoring_status": "requires_source_material",
                "review_status": "todo",
                "source_root_status": "manuscript_corpus_source_template",
                "result_honesty": (
                    "Manuscript evidence source skeleton only. Replace placeholder "
                    "source refs, review metadata, and container flags before promotion."
                ),
            }
        )
        source_row["metadata"] = metadata
        rows.append(source_row)
    return rows


def source_manifest(*, case_count: int) -> dict[str, Any]:
    return {
        "artifact_kind": "decision_evidence_manuscript_corpus_source_manifest",
        "schema_version": 1,
        "source_scope": SOURCE_SCOPE_TEMPLATE,
        "source_status": "requires_source_material",
        "case_source_file": CASE_SOURCE_NAME,
        "expected_case_count": case_count,
        "review_contract": {
            "reviewed_template_status": "reviewed_non_fixture_evidence",
            "required_review_fields": [
                "source_requirements.native_evidence_refs",
                "source_requirements.reviewed_source_refs",
                "source_requirements.evidence_plane_refs",
                "source_requirements.provenance_notes",
                "container_flags.trace_present",
                "container_flags.ledger_present",
                "container_flags.schema_valid",
                "container_flags.checklist_complete",
                "container_flags.source_validator_passed",
                "container_flags.llm_judge_verdict",
                "metadata.reviewer_id",
                "metadata.reviewed_at",
            ],
        },
        "result_honesty": (
            "This source root is an authoring substrate, not a manuscript result. It "
            "becomes promotion-ready only after all rows are reviewed non-fixture evidence."
        ),
    }


def initialize_source_root(
    *,
    template: Path,
    source_root: Path,
    force: bool,
) -> dict[str, Any]:
    manifest_path = source_root / SOURCE_MANIFEST_NAME
    rows_path = source_root / CASE_SOURCE_NAME
    if not force and (manifest_path.exists() or rows_path.exists()):
        raise FileExistsError(
            f"{source_root} already contains manuscript evidence source files; use --force"
        )

    template_rows = read_jsonl(template)
    rows = source_rows(template_rows)
    source_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(source_manifest(case_count=len(rows)), indent=2, sort_keys=True) + "\n"
    )
    with rows_path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    return {
        "artifact_kind": "decision_evidence_manuscript_corpus_source_init",
        "source_root": str(source_root),
        "source_manifest": str(manifest_path),
        "case_source_rows": str(rows_path),
        "case_count": len(rows),
        "source_scope": SOURCE_SCOPE_TEMPLATE,
        "result_honesty": (
            "Initialized skeleton rows only; no row has been promoted to reviewed evidence."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = initialize_source_root(
            template=Path(args.template),
            source_root=Path(args.source_root),
            force=bool(args.force),
        )
    except FileExistsError as exc:
        print(json.dumps({"valid": False, "issue": "source_root_exists", "detail": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
