import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/audit_manuscript_label_leakage.py")


def test_label_leakage_audit_flags_degradation_fields_and_case_id_tokens(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "scorer.csv"
    report = tmp_path / "leakage.json"
    artifact.write_text(
        "\n".join(
            [
                "case_id,degradation_condition,verdict",
                "manuscript-aer-missing_policy-policy_basis-001,missing_policy,insufficient",
                "",
            ]
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifact",
            f"scorer_workbook:{artifact}",
            "--out",
            str(report),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["issue_counts"]["disallowed_field_name"] == 1
    assert payload["issue_counts"]["disallowed_label_token"] == 1
    assert payload["issues"][0]["role"] == "scorer_workbook"


def test_label_leakage_audit_accepts_opaque_case_ids(tmp_path: Path) -> None:
    artifact = tmp_path / "scorer.jsonl"
    report = tmp_path / "leakage.json"
    artifact.write_text(
        json.dumps(
            {
                "case_id": "case-0001",
                "scorer": "decision_trace_reconstructor",
                "verdict": "insufficient",
            },
            sort_keys=True,
        )
        + "\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifact",
            f"scorer_outputs:{artifact}",
            "--out",
            str(report),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["issue_count"] == 0
