import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.write_manuscript_case_source_template import template_rows

SCRIPT = Path("scripts/build_manuscript_evidence_intake.py")


def test_evidence_intake_classifies_template_rows_as_needs_source(
    tmp_path: Path,
) -> None:
    template = tmp_path / "template.jsonl"
    source_audit = tmp_path / "source_audit.json"
    out = tmp_path / "intake.json"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
    source_audit.write_text(
        json.dumps(
            {
                "manuscript_case_source_ready": False,
                "promotion_blockers": [
                    {"area": "source_audit", "issue": "source_root_not_promotion_ready"}
                ],
                "source_roots": [{"candidate_ref_count": 2}],
            },
            sort_keys=True,
        )
    )

    result = _run_intake(template, source_audit, out)

    payload = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["reviewed_case_source_ready"] is False
    assert payload["annotation_ready"] is False
    assert payload["status_counts"] == {
        "ready": 0,
        "blocked": 0,
        "needs_source": 1,
        "needs_annotation": 0,
    }
    assert payload["rows"][0]["status"] == "needs_source"
    assert payload["source_audit"]["source_audit_ready"] is False


def test_evidence_intake_classifies_reviewed_source_rows_as_needs_annotation(
    tmp_path: Path,
) -> None:
    template = tmp_path / "template.jsonl"
    source_audit = tmp_path / "source_audit.json"
    out = tmp_path / "intake.json"
    row = _reviewed_row()
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_ready_source_audit(source_audit)

    result = _run_intake(template, source_audit, out)

    payload = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["reviewed_case_source_ready"] is True
    assert payload["annotation_ready"] is False
    assert payload["status_counts"]["needs_annotation"] == 1
    assert payload["rows"][0]["status"] == "needs_annotation"


def test_evidence_intake_classifies_reviewed_and_labelled_rows_as_ready(
    tmp_path: Path,
) -> None:
    template = tmp_path / "template.jsonl"
    source_audit = tmp_path / "source_audit.json"
    out = tmp_path / "intake.json"
    row = _reviewed_row()
    for label in row["property_label_authoring"]:
        label["category"] = "complete"
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_ready_source_audit(source_audit)

    result = _run_intake(template, source_audit, out)

    payload = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["reviewed_case_source_ready"] is True
    assert payload["annotation_ready"] is True
    assert payload["status_counts"]["ready"] == 1
    assert payload["rows"][0]["status"] == "ready"


def _run_intake(template: Path, source_audit: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--source-audit",
            str(source_audit),
            "--out",
            str(out),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _reviewed_row() -> dict[str, Any]:
    row = template_rows()[0]
    row["template_status"] = "reviewed_non_fixture_evidence"
    row["source_requirements"] = {
        "native_evidence_refs": ["reviewed-native:case-001"],
        "reviewed_source_refs": ["review-log:case-001"],
        "evidence_plane_refs": ["evidence-plane:case-001"],
        "provenance_notes": "Reviewed non-fixture evidence candidate.",
    }
    row["container_flags"] = {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": True,
        "source_validator_passed": True,
        "llm_judge_verdict": "sufficient",
    }
    return row


def _write_ready_source_audit(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "manuscript_case_source_ready": True,
                "promotion_blockers": [],
                "source_roots": [{"candidate_ref_count": 3}],
            },
            sort_keys=True,
        )
    )
