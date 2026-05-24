import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from decision_evidence_benchmark.io import write_cases_jsonl
from decision_evidence_benchmark.schema import CaseManifest

SCRIPT = Path("scripts/write_manuscript_construction_oracle.py")


def test_write_manuscript_construction_oracle_writes_rule_labels(tmp_path: Path) -> None:
    cases = tmp_path / "cases.unadjudicated.jsonl"
    annotations = tmp_path / "annotations.jsonl"
    cases_out = tmp_path / "cases.jsonl"
    report = tmp_path / "oracle.json"
    write_cases_jsonl(
        cases,
        [
            _case("case-complete", "complete"),
            _case("case-missing-policy", "missing_policy"),
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cases",
            str(cases),
            "--annotations-out",
            str(annotations),
            "--cases-out",
            str(cases_out),
            "--report",
            str(report),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    annotation_rows = _read_jsonl(annotations)
    case_rows = _read_jsonl(cases_out)
    payload = json.loads(report.read_text())

    assert len(annotation_rows) == 4
    assert {row["metadata"]["annotation_source"] for row in annotation_rows} == {
        "construction_oracle_v1"
    }
    assert {row["metadata"]["annotation_status"] for row in annotation_rows} == {
        "construction_rule_oracle"
    }
    assert len(case_rows) == 2
    assert case_rows[0]["metadata"]["label_status"] == "construction_rule_oracle"
    assert case_rows[0]["metadata"]["label_oracle"] == "construction_oracle_v1"
    assert case_rows[0]["metadata"]["label_adjudication"]["mode"] == (
        "deterministic_rule_oracle"
    )
    missing_policy = {
        label["property"]: label for label in case_rows[1]["property_labels"]
    }
    assert missing_policy["policy_basis"]["category"] == "opaque"
    assert {label["source"] for label in case_rows[1]["property_labels"]} == {
        "construction_rule_oracle_label"
    }
    assert payload["valid"] is True
    assert payload["oracle_spec"].endswith("construction_oracle_v1.yaml")
    assert len(payload["oracle_spec_sha256"]) == 64
    assert payload["cases_sha256"] is not None
    assert payload["annotations_out_sha256"] is not None
    assert payload["cases_out_sha256"] is not None
    assert payload["oracle_rule_counts"] == {
        "rule.complete.v1": 1,
        "rule.missing_policy.v1": 1,
    }
    assert payload["strict_sufficiency_counts"] == {"insufficient": 1, "sufficient": 1}
    assert payload["calibration"]["overall"]["cohen_kappa"] == 1.0
    assert payload["label_adjudication"]["valid"] is True


def test_write_manuscript_construction_oracle_refuses_existing_outputs(
    tmp_path: Path,
) -> None:
    cases = tmp_path / "cases.unadjudicated.jsonl"
    annotations = tmp_path / "annotations.jsonl"
    cases_out = tmp_path / "cases.jsonl"
    report = tmp_path / "oracle.json"
    write_cases_jsonl(cases, [_case("case-complete", "complete")])
    annotations.write_text("keep annotations\n")
    cases_out.write_text("keep cases\n")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cases",
            str(cases),
            "--annotations-out",
            str(annotations),
            "--cases-out",
            str(cases_out),
            "--report",
            str(report),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["wrote_outputs"] is False
    assert annotations.read_text() == "keep annotations\n"
    assert cases_out.read_text() == "keep cases\n"
    assert [issue["issue"] for issue in payload["issues"]] == [
        "output_exists",
        "output_exists",
    ]


def _case(case_id: str, degradation_condition: str) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        regime="aer",
        question_family="policy_basis",
        degradation_condition=degradation_condition,
        evidence={
            "evidence_plane": "reviewed_non_fixture",
            "provenance_notes": f"test source for {case_id}",
        },
        container_flags={
            "trace_present": True,
            "ledger_present": True,
            "schema_valid": True,
            "checklist_complete": True,
            "source_validator_passed": True,
            "llm_judge_verdict": "sufficient",
        },
        metadata={"case_source_status": "reviewed_non_fixture_evidence"},
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
