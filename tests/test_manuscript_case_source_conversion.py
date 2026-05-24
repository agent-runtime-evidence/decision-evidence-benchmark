import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

SCRIPT = Path("scripts/convert_manuscript_case_sources.py")


def test_convert_manuscript_case_sources_rejects_template_rows(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources.jsonl"
    out = tmp_path / "cases.jsonl"
    report = tmp_path / "report.json"
    sources.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sources",
            str(sources),
            "--out",
            str(out),
            "--report",
            str(report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not out.exists()
    assert {issue["issue"] for issue in payload["issues"]} >= {
        "template_row_not_reviewed",
        "missing_source_refs",
        "missing_provenance_notes",
        "invalid_container_flag",
        "invalid_llm_judge_verdict",
    }


def test_convert_manuscript_case_sources_writes_unadjudicated_cases(
    tmp_path: Path,
) -> None:
    sources = tmp_path / "sources.jsonl"
    out = tmp_path / "cases.jsonl"
    report = tmp_path / "report.json"
    row = template_rows()[0]
    row["template_status"] = "reviewed_non_fixture_evidence"
    row["source_requirements"] = {
        "native_evidence_refs": ["oep:events/examples/code_review_agent_step.v0.json"],
        "reviewed_source_refs": ["review:case-001"],
        "evidence_plane_refs": ["oep:trace:pder_code_review_read_diff_0001"],
        "provenance_notes": "Reviewed local OEP evidence chain fixture.",
    }
    row["container_flags"] = {
        "trace_present": True,
        "ledger_present": True,
        "schema_valid": True,
        "checklist_complete": True,
        "source_validator_passed": True,
        "llm_judge_verdict": "sufficient",
    }
    sources.write_text(json.dumps(row, sort_keys=True) + "\n")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sources",
            str(sources),
            "--out",
            str(out),
            "--report",
            str(report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    case = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["output_case_count"] == 1
    assert case["case_id"] == row["case_id"]
    assert case["evidence"]["evidence_plane"] == "reviewed_non_fixture"
    assert case["property_labels"] == []
    assert case["metadata"]["case_source_status"] == "reviewed_non_fixture_evidence"

