import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/export_manuscript_source_candidates.py")


def test_export_source_candidates_preserves_scope_blockers(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    csv_out = tmp_path / "candidates.csv"
    jsonl_out = tmp_path / "candidates.jsonl"
    audit.write_text(
        json.dumps(
            {
                "source_roots": [
                    {
                        "name": "operational_evidence_plane",
                        "scope": "reference_demo_substrate",
                        "promotion_ready": False,
                        "promotion_blockers": ["source_scope_not_manuscript_corpus_ready"],
                        "blocking_indicators": [
                            {
                                "path": "README.md",
                                "indicator": "deterministic code-review demo",
                            }
                        ],
                        "candidate_refs": [
                            "manifest/examples/code_review_agent_release.v0.json"
                        ],
                    }
                ]
            },
            sort_keys=True,
        )
    )

    result = _run_export(audit, csv_out, jsonl_out)

    csv_rows = list(csv.DictReader(csv_out.open()))
    jsonl_rows = [json.loads(line) for line in jsonl_out.read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == 1
    assert len(jsonl_rows) == 1
    assert csv_rows[0]["promotion_ready"] == "false"
    assert csv_rows[0]["source_use"] == "reference_context_only_until_corpus_scope_exists"
    assert "deterministic code-review demo" in csv_rows[0]["blocking_indicators"]
    assert "do not mark a case row reviewed" in csv_rows[0]["review_instruction"]


def test_export_source_candidates_marks_promotion_ready_refs(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    csv_out = tmp_path / "candidates.csv"
    jsonl_out = tmp_path / "candidates.jsonl"
    audit.write_text(
        json.dumps(
            {
                "source_roots": [
                    {
                        "name": "manuscript_corpus_root",
                        "scope": "manuscript_corpus_evidence",
                        "promotion_ready": True,
                        "promotion_blockers": [],
                        "blocking_indicators": [],
                        "candidate_refs": ["cases/case_001.json"],
                    }
                ]
            },
            sort_keys=True,
        )
    )

    result = _run_export(audit, csv_out, jsonl_out)

    csv_rows = list(csv.DictReader(csv_out.open()))
    assert result.returncode == 0
    assert csv_rows[0]["promotion_ready"] == "true"
    assert csv_rows[0]["source_use"] == "case_source_candidate_after_row_review"
    assert "Review this ref against a specific manuscript case row" in csv_rows[0][
        "review_instruction"
    ]


def _run_export(
    audit: Path,
    csv_out: Path,
    jsonl_out: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--audit",
            str(audit),
            "--csv-out",
            str(csv_out),
            "--jsonl-out",
            str(jsonl_out),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
