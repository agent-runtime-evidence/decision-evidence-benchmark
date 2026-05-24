import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.write_manuscript_case_source_template import template_rows

SCRIPT = Path("scripts/export_manuscript_evidence_workqueue.py")


def test_export_workqueue_from_needs_source_intake(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    intake = tmp_path / "intake.json"
    packet_index = tmp_path / "packets.csv"
    csv_out = tmp_path / "workqueue.csv"
    jsonl_out = tmp_path / "workqueue.jsonl"
    row = template_rows()[0]
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_packet_index(packet_index, row["case_id"], "packets/01.md")
    _write_intake(
        intake,
        [
            {
                "row_index": 1,
                "case_id": row["case_id"],
                "regime": row["regime"],
                "degradation_condition": row["degradation_condition"],
                "question_family": row["question_family"],
                "status": "needs_source",
                "next_action": "attach reviewed source refs",
                "issues": [
                    {
                        "issue": "missing_source_refs",
                        "field": "source_requirements.native_evidence_refs",
                    },
                    {"issue": "missing_provenance_notes"},
                    {"issue": "invalid_container_flag", "field": "container_flags.trace_present"},
                    {
                        "issue": "missing_property_label_category",
                        "property": "actor_identity",
                    },
                ],
            }
        ],
    )

    result = _run_workqueue(template, intake, csv_out, jsonl_out, packet_index)

    csv_rows = list(csv.DictReader(csv_out.open()))
    jsonl_rows = [json.loads(line) for line in jsonl_out.read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == 1
    assert len(jsonl_rows) == 1
    assert csv_rows[0]["status"] == "needs_source"
    assert csv_rows[0]["review_status"] == "todo"
    assert csv_rows[0]["review_packet_path"] == "packets/01.md"
    assert csv_rows[0]["needed_source_fields"] == (
        "source_requirements.native_evidence_refs | source_requirements.provenance_notes"
    )
    assert csv_rows[0]["needed_container_flags"] == "trace_present"
    assert csv_rows[0]["needed_annotation_properties"] == "actor_identity"
    assert jsonl_rows[0]["issue_codes"] == [
        "invalid_container_flag",
        "missing_property_label_category",
        "missing_provenance_notes",
        "missing_source_refs",
    ]


def test_export_workqueue_preserves_reviewed_row_values(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    intake = tmp_path / "intake.json"
    packet_index = tmp_path / "packets.csv"
    csv_out = tmp_path / "workqueue.csv"
    jsonl_out = tmp_path / "workqueue.jsonl"
    row = template_rows()[0]
    _write_packet_index(packet_index, row["case_id"], "packets/01.md")
    row["source_requirements"] = {
        "native_evidence_refs": ["native:one", "native:two"],
        "reviewed_source_refs": ["review:one"],
        "evidence_plane_refs": ["plane:one"],
        "provenance_notes": "Reviewed source note.",
    }
    row["container_flags"] = {
        "trace_present": True,
        "ledger_present": False,
        "schema_valid": True,
        "checklist_complete": True,
        "source_validator_passed": True,
        "llm_judge_verdict": "sufficient",
    }
    template.write_text(json.dumps(row, sort_keys=True) + "\n")
    _write_intake(
        intake,
        [
            {
                "row_index": 1,
                "case_id": row["case_id"],
                "regime": row["regime"],
                "degradation_condition": row["degradation_condition"],
                "question_family": row["question_family"],
                "status": "ready",
                "next_action": "row is ready",
                "issues": [],
            }
        ],
    )

    result = _run_workqueue(template, intake, csv_out, jsonl_out, packet_index)

    csv_rows = list(csv.DictReader(csv_out.open()))
    assert result.returncode == 0
    assert csv_rows[0]["review_status"] == "ready_for_conversion"
    assert csv_rows[0]["review_packet_path"] == "packets/01.md"
    assert csv_rows[0]["native_evidence_refs"] == "native:one | native:two"
    assert csv_rows[0]["reviewed_source_refs"] == "review:one"
    assert csv_rows[0]["trace_present"] == "true"
    assert csv_rows[0]["ledger_present"] == "false"


def _write_intake(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps(
            {
                "artifact_kind": "decision_evidence_manuscript_evidence_intake",
                "rows": rows,
            },
            sort_keys=True,
        )
    )


def _write_packet_index(path: Path, case_id: str, packet_path: str) -> None:
    path.write_text(
        "row_index,case_id,packet_path\n"
        f"1,{case_id},{packet_path}\n"
    )


def _run_workqueue(
    template: Path,
    intake: Path,
    csv_out: Path,
    jsonl_out: Path,
    packet_index: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--intake",
            str(intake),
            "--packet-index",
            str(packet_index),
            "--csv-out",
            str(csv_out),
            "--jsonl-out",
            str(jsonl_out),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
