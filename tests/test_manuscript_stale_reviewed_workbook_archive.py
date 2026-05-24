import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/archive_stale_manuscript_reviewed_workbooks.py")


def test_archives_non_redacted_reviewed_workbooks(tmp_path: Path) -> None:
    scorer = tmp_path / "scorer.reviewed.csv"
    llm_judge = tmp_path / "llm_judge.reviewed.csv"
    archive_dir = tmp_path / "archive"
    report = tmp_path / "report.json"
    scorer.write_text(
        "case_id,prediction_status\n"
        "manuscript-aer-complete-actor_identity-001,reviewed\n"
    )
    llm_judge.write_text(
        "case_id,prediction_status\n"
        "manuscript-aer-complete-actor_identity-001,reviewed\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scorer-workbook-reviewed",
            str(scorer),
            "--llm-judge-workbook-reviewed",
            str(llm_judge),
            "--archive-dir",
            str(archive_dir),
            "--report",
            str(report),
            "--archive-label",
            "test",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    archived_paths = {Path(item["archive_path"]).name for item in payload["artifacts"]}
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["archived_count"] == 2
    assert not scorer.exists()
    assert not llm_judge.exists()
    assert archived_paths == {
        "scorer.reviewed.csv.test.stale",
        "llm_judge.reviewed.csv.test.stale",
    }


def test_skips_already_redacted_reviewed_workbook(tmp_path: Path) -> None:
    scorer = tmp_path / "scorer.reviewed.csv"
    llm_judge = tmp_path / "missing_llm_judge.reviewed.csv"
    archive_dir = tmp_path / "archive"
    report = tmp_path / "report.json"
    _write_redacted_csv(scorer)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scorer-workbook-reviewed",
            str(scorer),
            "--llm-judge-workbook-reviewed",
            str(llm_judge),
            "--archive-dir",
            str(archive_dir),
            "--report",
            str(report),
            "--archive-label",
            "test",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    actions = [item["action"] for item in payload["artifacts"]]
    assert result.returncode == 0
    assert payload["archived_count"] == 0
    assert scorer.exists()
    assert actions == ["skipped", "skipped"]


def _write_redacted_csv(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "redaction_status", "prediction_status"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "case-000001",
                "redaction_status": "scorer_input_redacted_v1",
                "prediction_status": "reviewed",
            }
        )
