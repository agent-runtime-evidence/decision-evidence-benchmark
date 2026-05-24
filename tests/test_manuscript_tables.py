import csv
from pathlib import Path

from decision_evidence_benchmark.manuscript_tables import export_manuscript_tables
from decision_evidence_benchmark.result_package import build_result_package


def test_export_manuscript_tables_writes_gate_blocker_and_artifact_tables(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "package"
    package = build_result_package(
        corpus_manifest_path=Path("data/corpus/draft_balanced_64_corpus.yaml"),
        cases_path=Path("data/cases/draft_balanced_64_cases.jsonl"),
        annotations_path=Path("data/annotations/draft_balanced_64_annotations.jsonl"),
        scorer_predictions_path=Path("data/scorers/draft_balanced_64_scorer_outputs.jsonl"),
        out_dir=package_dir,
        prefix="draft",
    )
    table_dir = tmp_path / "tables"

    summary = export_manuscript_tables(
        package_manifest_path=Path(package["outputs"]["package_manifest"]),
        out_dir=table_dir,
        prefix="draft",
    )

    assert summary["valid"] is True
    assert summary["manuscript_result_ready"] is False
    assert summary["blocker_count"] == len(package["blocking_reasons"])
    assert (table_dir / "draft_table_export_summary.json").exists()

    gate_rows = _read_csv(table_dir / "draft_gate_status.csv")
    assert gate_rows == [
        {
            "claim_status": "mechanical_run_only",
            "mechanics_valid": "True",
            "manuscript_result_ready": "False",
            "case_count": "64",
            "baseline_count": "6",
            "blocker_count": str(len(package["blocking_reasons"])),
            "input_artifact_count": "4",
            "output_artifact_count": "16",
        }
    ]

    blocker_rows = _read_csv(table_dir / "draft_readiness_blockers.csv")
    assert any(row["artifact_area"] == "labels" for row in blocker_rows)
    assert any(row["category"] == "candidate_fixture_status" for row in blocker_rows)

    artifact_rows = _read_csv(table_dir / "draft_artifact_inventory.csv")
    assert any(row["role"] == "readiness_gaps" for row in artifact_rows)
    assert len(artifact_rows) == 20


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))
