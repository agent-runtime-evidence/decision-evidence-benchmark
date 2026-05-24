"""Deterministic non-human prediction helpers for manuscript package assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from decision_evidence_benchmark.io import write_json
from decision_evidence_benchmark.manuscript_redaction import SCORER_INPUT_REDACTION_STATUS
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

DETERMINISTIC_PROPERTY_SCORER_VERSION: Final = "redacted_property_rule_scorer_v1"
DETERMINISTIC_PROPERTY_SCORER_RUN_ID: Final = "manuscript_redacted_property_rule_scorer_v1"
DETERMINISTIC_PROPERTY_SCORER_TIMESTAMP: Final = "2026-05-25T00:00:00Z"
DETERMINISTIC_PROPERTY_SCORER_NAME: Final = "decision_trace_reconstructor"


def write_deterministic_property_scorer_outputs(
    *,
    scorer_input_path: Path,
    case_id_map_path: Path,
    out_path: Path,
    report_path: Path,
    force: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Write deterministic candidate-scorer outputs from redacted scorer inputs.

    The scoring rules intentionally consume only the scorer-facing redacted case
    rows plus the private ID map needed to map outputs back to evaluation case
    IDs. The rules do not read degradation conditions, oracle labels, or source
    references.
    """

    issues: list[dict[str, Any]] = []
    redacted_rows = _read_jsonl(scorer_input_path, issues=issues, role="scorer_input")
    case_id_map = _read_case_id_map(case_id_map_path, issues=issues)
    output_rows = [
        _score_redacted_row(row, original_case_id=case_id_map.get(str(row.get("case_id", ""))))
        for row in redacted_rows
        if str(row.get("case_id", "")) in case_id_map
    ]
    _append_coverage_issues(redacted_rows, case_id_map, output_rows, issues)

    rendered = _render_jsonl(output_rows)
    wrote_outputs = False
    if not any(issue["severity"] == "error" for issue in issues):
        if out_path.exists() and out_path.read_text() != rendered and not force:
            issues.append(
                {
                    "severity": "error",
                    "issue": "output_exists_with_different_content",
                    "path": str(out_path),
                    "resolution": "rerun with --force after verifying replacement scope",
                }
            )
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered)
            wrote_outputs = True

    report = {
        "artifact_kind": "decision_evidence_manuscript_scorer_import",
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "case_count": len(redacted_rows),
        "property_count": len(DECISION_EVENT_PROPERTIES),
        "workbook_row_count": len(redacted_rows) * len(DECISION_EVENT_PROPERTIES),
        "expected_workbook_row_count": len(redacted_rows) * len(DECISION_EVENT_PROPERTIES),
        "scorer": DETERMINISTIC_PROPERTY_SCORER_NAME,
        "redacted_input": True,
        "redaction_status": SCORER_INPUT_REDACTION_STATUS,
        "case_id_map_count": len(case_id_map),
        "output_count": len(output_rows),
        "implementation_status": DETERMINISTIC_PROPERTY_SCORER_VERSION,
        "wrote_outputs": wrote_outputs,
        "issues": issues,
        "result_honesty": (
            "Deterministic candidate-scorer outputs generated from redacted scorer "
            "inputs only. This is not human annotation, not LLM judgement, and not "
            "construction-oracle label generation."
        ),
    }
    write_json(report_path, report)
    return bool(report["valid"]), report


def _score_redacted_row(row: dict[str, Any], *, original_case_id: str | None) -> dict[str, Any]:
    if not original_case_id:
        raise ValueError("original_case_id is required after coverage validation")
    case_id = str(row["case_id"])
    predictions = [
        {
            "property": property_name,
            "category": _category_for_property(property_name, row),
            "required": True,
            "source": "redacted_property_rule_scorer",
            "notes": "visible-rule-v1",
        }
        for property_name in DECISION_EVENT_PROPERTIES
    ]
    verdict = (
        "sufficient"
        if all(prediction["category"] == "complete" for prediction in predictions)
        else "insufficient"
    )
    return {
        "case_id": original_case_id,
        "scorer": DETERMINISTIC_PROPERTY_SCORER_NAME,
        "verdict": verdict,
        "metadata": {
            "implementation_status": DETERMINISTIC_PROPERTY_SCORER_VERSION,
            "run_id": DETERMINISTIC_PROPERTY_SCORER_RUN_ID,
            "model": "none",
            "prompt_version": "none",
            "reviewer_id": "deterministic_rule_engine",
            "reviewed_at": DETERMINISTIC_PROPERTY_SCORER_TIMESTAMP,
            "prediction_source": "redacted_input_rule_scorer",
            "case_source_status": row.get("metadata", {}).get("case_source_status"),
            "scorer_input_case_id": case_id,
            "scorer_input_redaction_status": SCORER_INPUT_REDACTION_STATUS,
            "result_honesty": (
                "Candidate scorer output derived from redacted visible evidence "
                "indicators only; no oracle labels or degradation names are used."
            ),
        },
        "property_predictions": predictions,
    }


def _category_for_property(property_name: str, row: dict[str, Any]) -> str:
    flags = row.get("container_flags", {})
    evidence = row.get("evidence", {})
    source_ref_counts = evidence.get("source_ref_counts", {})
    has_reviewed_sources = (
        evidence.get("evidence_plane") == "reviewed_non_fixture"
        and int(source_ref_counts.get("native_evidence_refs", 0)) > 0
        and int(source_ref_counts.get("reviewed_source_refs", 0)) > 0
        and int(source_ref_counts.get("evidence_plane_refs", 0)) > 0
    )
    trace = bool(flags.get("trace_present"))
    ledger = bool(flags.get("ledger_present"))
    schema = bool(flags.get("schema_valid"))
    checklist = bool(flags.get("checklist_complete"))
    source_validator = bool(flags.get("source_validator_passed"))

    if not has_reviewed_sources:
        return "opaque"
    if property_name == "actor_identity":
        return "complete" if trace and schema else "opaque"
    if property_name == "principal_authority":
        if ledger and source_validator:
            return "complete"
        return "partial" if ledger else "opaque"
    if property_name == "action_boundary":
        if trace and source_validator:
            return "complete"
        return "partial" if trace else "opaque"
    if property_name == "policy_basis":
        if source_validator and checklist:
            return "complete"
        return "partial" if checklist else "opaque"
    if property_name == "decision_basis":
        if trace and checklist:
            return "complete"
        return "partial" if trace else "opaque"
    if property_name == "data_resource_touch":
        if trace and schema:
            return "complete"
        return "partial" if schema else "opaque"
    if property_name == "lifecycle_context":
        if ledger and schema and checklist:
            return "complete"
        return "partial" if schema else "opaque"
    if property_name == "verification_strength":
        if ledger and schema and source_validator:
            return "complete"
        return "partial" if ledger or schema else "opaque"
    raise ValueError(f"unknown property: {property_name}")


def _read_jsonl(path: Path, *, issues: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    if not path.exists():
        issues.append(
            {
                "severity": "error",
                "issue": "missing_input",
                "role": role,
                "path": str(path),
            }
        )
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                issues.append(
                    {
                        "severity": "error",
                        "issue": "jsonl_row_not_object",
                        "role": role,
                        "path": str(path),
                        "line_number": line_number,
                    }
                )
                continue
            rows.append(value)
    return rows


def _read_case_id_map(path: Path, *, issues: list[dict[str, Any]]) -> dict[str, str]:
    rows = _read_jsonl(path, issues=issues, role="case_id_map")
    mapping: dict[str, str] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        original_case_id = str(row.get("original_case_id", "")).strip()
        if not case_id or not original_case_id:
            issues.append(
                {
                    "severity": "error",
                    "issue": "invalid_case_id_map_row",
                    "case_id": case_id,
                    "original_case_id": original_case_id,
                }
            )
            continue
        mapping[case_id] = original_case_id
    return mapping


def _append_coverage_issues(
    redacted_rows: list[dict[str, Any]],
    case_id_map: dict[str, str],
    output_rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    redacted_case_ids = {str(row.get("case_id", "")) for row in redacted_rows}
    mapped_case_ids = set(case_id_map)
    missing_map = sorted(redacted_case_ids - mapped_case_ids)
    if missing_map:
        issues.append(
            {
                "severity": "error",
                "issue": "missing_case_id_map_rows",
                "case_ids": missing_map,
            }
        )
    if len(output_rows) != len(redacted_rows):
        issues.append(
            {
                "severity": "error",
                "issue": "output_count_mismatch",
                "expected": len(redacted_rows),
                "actual": len(output_rows),
            }
        )


def _render_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
