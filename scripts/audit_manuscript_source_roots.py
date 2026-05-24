"""Audit local source roots before promoting manuscript case-source rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.schema import VERDICTS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "data/cases/manuscript_case_sources.template.jsonl"
DEFAULT_OUT = ROOT / "data/results/manuscript_source_root_audit.json"
DEFAULT_OEP_ROOT = ROOT.parent / "operational-evidence-plane"
DEFAULT_PILOT_ROOT = ROOT.parent / "anchor-level-reconstructability-pilot"
DEFAULT_MANUSCRIPT_SOURCE_ROOT = ROOT / "data/sources/manuscript_corpus"

REVIEWED_STATUS = "reviewed_non_fixture_evidence"
READY_SOURCE_SCOPE = "manuscript_corpus_evidence"
TEMPLATE_SOURCE_SCOPE = "manuscript_corpus_evidence_source_template"
CASE_SOURCE_FILE = "case_evidence_sources.jsonl"
SOURCE_MANIFEST_FILE = "source_manifest.json"
BOOLEAN_CONTAINER_FLAGS = (
    "trace_present",
    "ledger_present",
    "schema_valid",
    "checklist_complete",
    "source_validator_passed",
)
SOURCE_LIST_FIELDS = (
    "native_evidence_refs",
    "reviewed_source_refs",
    "evidence_plane_refs",
)


SOURCE_ROOTS = {
    "operational_evidence_plane": {
        "promotion_role": "advisory_reference_context",
        "required_for_promotion": False,
        "scope": "reference_demo_substrate",
        "required_files": (
            "README.md",
            "manifest/examples/code_review_agent_release.v0.json",
            "events/examples/code_review_agent_step.v0.json",
            "permissions/examples/code_review_tool_permission.v0.json",
            "traces/examples/code_review_agent_trace.v0.json",
            "playbooks/examples/code_review_reconstruction_packet.v0.json",
            "integrations/decision-trace-reconstructor/code_review_agent.jsonl",
        ),
        "candidate_refs": (
            "manifest/examples/code_review_agent_release.v0.json",
            "events/examples/code_review_agent_step.v0.json",
            "events/examples/code_review_agent_denied_step.v0.json",
            "permissions/examples/code_review_tool_permission.v0.json",
            "permissions/examples/code_review_tool_permission_denied.v0.json",
            "traces/examples/code_review_agent_trace.v0.json",
            "traces/examples/code_review_agent_denied_trace.v0.json",
            "traces/examples/code_review_agent_eval.v0.json",
            "traces/examples/code_review_agent_denied_eval.v0.json",
            "playbooks/examples/code_review_reconstruction_packet.v0.json",
            "playbooks/examples/code_review_denied_reconstruction_packet.v0.json",
            "integrations/decision-trace-reconstructor/code_review_agent.jsonl",
            "integrations/decision-trace-reconstructor/code_review_agent_denied.jsonl",
        ),
        "blocking_indicators": (
            ("README.md", "deterministic code-review demo"),
            ("README.md", "mocked LLM behavior"),
            ("docs/public_claims.md", "not production-ready"),
            ("docs/public_claims.md", "not a benchmark"),
        ),
    },
    "anchor_level_reconstructability_pilot": {
        "promotion_role": "advisory_reference_context",
        "required_for_promotion": False,
        "scope": "anchor_level_reproducibility_artifact",
        "required_files": (
            "README.md",
            "manifest.yaml",
            "reference_output.md",
            "data/results/oep/02_oep_specific.report/feasibility.json",
            "data/results/oep/02_oep_specific.report/trace.jsonld",
        ),
        "candidate_refs": (
            "manifest.yaml",
            "reference_output.md",
            "data/results/bedrock/01_dtr_anchor.report/feasibility.json",
            "data/results/langsmith/01_dtr_anchor.report/feasibility.json",
            "data/results/anthropic/01_dtr_anchor.report/feasibility.json",
            "data/results/openai_agents/01_dtr_anchor.report/feasibility.json",
            "data/results/otlp/01_dtr_anchor.report/feasibility.json",
            "data/results/mcp/01_dtr_anchor.report/feasibility.json",
            "data/results/oep/02_oep_specific.report/feasibility.json",
            "data/results/replit_drop_database/report/feasibility.json",
        ),
        "blocking_indicators": (
            ("README.md", "not real captured production traces"),
            ("README.md", "Not a corpus benchmark"),
            ("README.md", "n=1 per cell"),
            ("README.md", "anchor-sized"),
        ),
    },
}


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


def template_summary(path: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if rows is None:
        rows = read_jsonl(path)
    return {
        "path": str(path),
        "row_count": len(rows),
        "regime_count": len({row.get("regime") for row in rows}),
        "degradation_condition_count": len(
            {row.get("degradation_condition") for row in rows}
        ),
        "question_family_count": len({row.get("question_family") for row in rows}),
        "template_status_counts": _counts(str(row.get("template_status")) for row in rows),
    }


def audit_root(name: str, root: Path) -> dict[str, Any]:
    spec = SOURCE_ROOTS[name]
    required_files = tuple(str(path) for path in spec["required_files"])
    candidate_refs = tuple(str(path) for path in spec["candidate_refs"])
    missing_required = [path for path in required_files if not (root / path).exists()]
    existing_candidate_refs = [path for path in candidate_refs if (root / path).exists()]
    indicators = _matched_indicators(root, spec["blocking_indicators"])
    blockers = []
    if not root.exists():
        blockers.append("source_root_missing")
    if missing_required:
        blockers.append("required_files_missing")
    if indicators:
        blockers.append("source_scope_not_manuscript_corpus_ready")
    return {
        "name": name,
        "root": str(root),
        "exists": root.exists(),
        "promotion_role": spec["promotion_role"],
        "required_for_promotion": spec["required_for_promotion"],
        "scope": spec["scope"],
        "required_files": list(required_files),
        "missing_required_files": missing_required,
        "candidate_ref_count": len(existing_candidate_refs),
        "candidate_refs": existing_candidate_refs,
        "blocking_indicators": indicators,
        "promotion_blockers": blockers,
        "promotion_ready": not blockers,
    }


def audit_manuscript_corpus_root(
    *,
    root: Path,
    template_rows: list[dict[str, Any]],
    min_cases: int,
) -> dict[str, Any]:
    required_files = (SOURCE_MANIFEST_FILE, CASE_SOURCE_FILE)
    missing_required = [path for path in required_files if not (root / path).exists()]
    candidate_refs = [path for path in required_files if (root / path).exists()]
    blockers: list[str] = []
    manifest_report = _source_manifest_report(root / SOURCE_MANIFEST_FILE)
    row_report = _source_rows_report(
        root / CASE_SOURCE_FILE,
        template_rows=template_rows,
        min_cases=min_cases,
    )

    if not root.exists():
        blockers.append("source_root_missing")
    if missing_required:
        blockers.append("required_files_missing")
    if manifest_report["source_scope"] != READY_SOURCE_SCOPE:
        blockers.append("source_scope_not_manuscript_corpus_ready")
    blockers.extend(row_report["promotion_blockers"])

    return {
        "name": "manuscript_corpus_source",
        "root": str(root),
        "exists": root.exists(),
        "promotion_role": "required_manuscript_corpus_source",
        "required_for_promotion": True,
        "scope": manifest_report["source_scope"],
        "allowed_ready_scope": READY_SOURCE_SCOPE,
        "template_scope": TEMPLATE_SOURCE_SCOPE,
        "required_files": list(required_files),
        "missing_required_files": missing_required,
        "candidate_ref_count": len(candidate_refs),
        "candidate_refs": candidate_refs,
        "blocking_indicators": [],
        "source_manifest": manifest_report,
        "row_audit": row_report,
        "promotion_blockers": sorted(set(blockers)),
        "promotion_ready": not blockers,
    }


def build_report(
    *,
    template: Path,
    manuscript_source_root: Path,
    oep_root: Path,
    pilot_root: Path,
    min_cases: int,
) -> dict[str, Any]:
    template_rows = read_jsonl(template)
    template_report = template_summary(template, template_rows)
    roots = [
        audit_manuscript_corpus_root(
            root=manuscript_source_root,
            template_rows=template_rows,
            min_cases=min_cases,
        ),
        audit_root("operational_evidence_plane", oep_root),
        audit_root("anchor_level_reconstructability_pilot", pilot_root),
    ]
    blockers = []
    advisory_blockers = []
    if template_report["row_count"] < min_cases:
        blockers.append(
            {
                "area": "case_template",
                "issue": "insufficient_template_rows",
                "expected_min": min_cases,
                "actual": template_report["row_count"],
            }
        )
    for root in roots:
        if not root["promotion_ready"]:
            root_blocker = {
                "area": root["name"],
                "issue": "source_root_not_promotion_ready",
                "promotion_blockers": root["promotion_blockers"],
            }
            if root.get("required_for_promotion", True):
                blockers.append(root_blocker)
            else:
                advisory_blockers.append(root_blocker)
    return {
        "artifact_kind": "decision_evidence_manuscript_source_root_audit",
        "template": template_report,
        "source_roots": roots,
        "minimum_case_rows": min_cases,
        "manuscript_case_source_ready": not blockers,
        "promotion_blockers": blockers,
        "advisory_blockers": advisory_blockers,
        "result_honesty": (
            "This audit inventories local source roots only. Advisory reference roots do "
            "not promote manuscript cases; the manuscript corpus source root must still "
            "be row-reviewed before any case is marked reviewed_non_fixture_evidence."
        ),
    }


def _source_manifest_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "present": False,
            "path": str(path),
            "source_scope": "missing",
            "expected_case_count": None,
            "case_source_file": None,
        }
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        return {
            "present": True,
            "path": str(path),
            "source_scope": "invalid_manifest",
            "expected_case_count": None,
            "case_source_file": None,
        }
    return {
        "present": True,
        "path": str(path),
        "source_scope": str(payload.get("source_scope", "")),
        "source_status": str(payload.get("source_status", "")),
        "expected_case_count": payload.get("expected_case_count"),
        "case_source_file": payload.get("case_source_file"),
    }


def _source_rows_report(
    path: Path,
    *,
    template_rows: list[dict[str, Any]],
    min_cases: int,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "present": False,
            "path": str(path),
            "row_count": 0,
            "reviewed_row_count": 0,
            "issue_counts": {"case_source_file_missing": 1},
            "promotion_blockers": ["case_source_file_missing"],
        }

    rows = read_jsonl(path)
    template_by_case_id = {str(row.get("case_id", "")): row for row in template_rows}
    issues: list[str] = []
    if len(rows) < min_cases:
        issues.append("insufficient_case_source_rows")
    if len(rows) != len(template_rows):
        issues.append("case_source_template_count_mismatch")

    seen_case_ids: set[str] = set()
    duplicate_case_ids = 0
    reviewed_row_count = 0
    for row in rows:
        case_id = str(row.get("case_id", ""))
        if case_id in seen_case_ids:
            duplicate_case_ids += 1
        seen_case_ids.add(case_id)
        row_issues = _source_row_issues(row, template_by_case_id=template_by_case_id)
        issues.extend(row_issues)
        if row.get("template_status") == REVIEWED_STATUS and not row_issues:
            reviewed_row_count += 1

    missing_template_case_ids = sorted(set(template_by_case_id) - seen_case_ids)
    extra_case_ids = sorted(seen_case_ids - set(template_by_case_id))
    issues.extend(["duplicate_case_id"] * duplicate_case_ids)
    issues.extend(["missing_template_case_id"] * len(missing_template_case_ids))
    issues.extend(["case_id_not_in_template"] * len(extra_case_ids))
    issue_counts = _counts(issues)
    promotion_blockers = _promotion_blockers_for_source_issue_counts(issue_counts)
    return {
        "present": True,
        "path": str(path),
        "row_count": len(rows),
        "reviewed_row_count": reviewed_row_count,
        "missing_template_case_count": len(missing_template_case_ids),
        "extra_case_count": len(extra_case_ids),
        "duplicate_case_count": duplicate_case_ids,
        "issue_counts": issue_counts,
        "promotion_blockers": promotion_blockers,
    }


def _source_row_issues(
    row: dict[str, Any],
    *,
    template_by_case_id: dict[str, dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    case_id = str(row.get("case_id", ""))
    template_row = template_by_case_id.get(case_id)
    if not case_id.strip():
        return ["missing_case_id"]
    if not template_row:
        return ["case_id_not_in_template"]
    for field in ("regime", "degradation_condition", "question_family"):
        if str(row.get(field, "")) != str(template_row.get(field, "")):
            issues.append("taxonomy_mismatch")

    if row.get("template_status") != REVIEWED_STATUS:
        issues.append("source_row_not_reviewed")

    source_requirements = row.get("source_requirements")
    if not isinstance(source_requirements, dict):
        issues.append("missing_source_requirements")
    else:
        for field in SOURCE_LIST_FIELDS:
            values = source_requirements.get(field)
            if not _non_placeholder_refs(values):
                issues.append("source_refs_incomplete")
        provenance_notes = source_requirements.get("provenance_notes")
        if not isinstance(provenance_notes, str) or _placeholder(provenance_notes):
            issues.append("provenance_notes_incomplete")

    container_flags = row.get("container_flags")
    if not isinstance(container_flags, dict):
        issues.append("missing_container_flags")
    else:
        for flag in BOOLEAN_CONTAINER_FLAGS:
            if not isinstance(container_flags.get(flag), bool):
                issues.append("container_flags_incomplete")
        if container_flags.get("llm_judge_verdict") not in VERDICTS:
            issues.append("invalid_llm_judge_verdict")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        issues.append("review_metadata_incomplete")
    else:
        for field in ("reviewer_id", "reviewed_at"):
            value = metadata.get(field)
            if not isinstance(value, str) or _placeholder(value):
                issues.append("review_metadata_incomplete")
    return issues


def _promotion_blockers_for_source_issue_counts(issue_counts: dict[str, int]) -> list[str]:
    blockers: list[str] = []
    if issue_counts.get("case_source_file_missing"):
        blockers.append("case_source_file_missing")
    if issue_counts.get("insufficient_case_source_rows") or issue_counts.get(
        "case_source_template_count_mismatch"
    ):
        blockers.append("case_source_coverage_incomplete")
    if issue_counts.get("source_row_not_reviewed"):
        blockers.append("source_rows_not_reviewed")
    if issue_counts.get("source_refs_incomplete") or issue_counts.get(
        "provenance_notes_incomplete"
    ):
        blockers.append("source_refs_incomplete")
    if issue_counts.get("container_flags_incomplete") or issue_counts.get(
        "invalid_llm_judge_verdict"
    ):
        blockers.append("container_flags_incomplete")
    if issue_counts.get("review_metadata_incomplete"):
        blockers.append("review_metadata_incomplete")
    for issue in (
        "missing_case_id",
        "case_id_not_in_template",
        "missing_template_case_id",
        "duplicate_case_id",
        "taxonomy_mismatch",
        "missing_source_requirements",
        "missing_container_flags",
    ):
        if issue_counts.get(issue):
            blockers.append("case_source_rows_invalid")
            break
    return sorted(set(blockers))


def _non_placeholder_refs(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, str) and not _placeholder(item) for item in value)


def _placeholder(value: str) -> bool:
    stripped = value.strip()
    return not stripped or stripped.startswith("__") or stripped.endswith("__")


def _matched_indicators(
    root: Path, indicators: Any
) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for relative_path, needle in indicators:
        path = root / str(relative_path)
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")
        if str(needle).lower() in text.lower():
            matches.append({"path": str(relative_path), "indicator": str(needle)})
    return matches


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--manuscript-source-root", default=str(DEFAULT_MANUSCRIPT_SOURCE_ROOT))
    parser.add_argument("--oep-root", default=str(DEFAULT_OEP_ROOT))
    parser.add_argument("--pilot-root", default=str(DEFAULT_PILOT_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--min-cases", type=int, default=64)
    parser.add_argument("--fail-on-blockers", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report(
        template=Path(args.template),
        manuscript_source_root=Path(args.manuscript_source_root),
        oep_root=Path(args.oep_root),
        pilot_root=Path(args.pilot_root),
        min_cases=int(args.min_cases),
    )
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_blockers and not report["manuscript_case_source_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
