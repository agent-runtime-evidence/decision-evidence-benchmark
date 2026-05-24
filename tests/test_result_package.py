import json
from pathlib import Path

from decision_evidence_benchmark.result_package import (
    build_result_package,
    validate_result_package_file,
    validate_result_package_manifest,
)


def test_build_result_package_assembles_draft_artifacts(tmp_path: Path) -> None:
    package = build_result_package(
        corpus_manifest_path=Path("data/corpus/draft_balanced_64_corpus.yaml"),
        cases_path=Path("data/cases/draft_balanced_64_cases.jsonl"),
        annotations_path=Path("data/annotations/draft_balanced_64_annotations.jsonl"),
        scorer_predictions_path=Path("data/scorers/draft_balanced_64_scorer_outputs.jsonl"),
        out_dir=tmp_path,
        prefix="draft",
    )

    assert package["case_count"] == 64
    assert package["mechanics_valid"] is True
    assert package["manuscript_result_ready"] is False
    assert "label_calibration_status=draft_two_annotator_fixture" in package[
        "blocking_reasons"
    ]

    label_review_path = Path(package["outputs"]["label_review"])
    label_adjudication_path = Path(package["outputs"]["label_adjudication"])
    adjudicated_cases_path = Path(package["outputs"]["adjudicated_cases"])
    adjudicated_corpus_path = Path(package["outputs"]["adjudicated_corpus_manifest"])
    scorer_validation_path = Path(package["outputs"]["scorer_validation"])
    baseline_validation_path = Path(package["outputs"]["baseline_validation"])
    run_manifest_path = Path(package["outputs"]["run_manifest"])
    readiness_report_path = Path(package["outputs"]["readiness_report"])
    readiness_gaps_path = Path(package["outputs"]["readiness_gaps"])
    assert label_review_path.exists()
    assert label_adjudication_path.exists()
    assert adjudicated_cases_path.exists()
    assert adjudicated_corpus_path.exists()
    assert scorer_validation_path.exists()
    assert baseline_validation_path.exists()
    assert readiness_report_path.exists()
    assert readiness_gaps_path.exists()
    label_review = json.loads(label_review_path.read_text())
    label_adjudication = json.loads(label_adjudication_path.read_text())
    scorer_validation = json.loads(scorer_validation_path.read_text())
    baseline_validation = json.loads(baseline_validation_path.read_text())
    run_manifest = json.loads(run_manifest_path.read_text())
    readiness_report = json.loads(readiness_report_path.read_text())
    readiness_gaps = json.loads(readiness_gaps_path.read_text())
    assert label_review["property_row_count"] == 512
    assert label_adjudication["valid"] is True
    assert label_adjudication["property_count"] == 512
    assert scorer_validation["valid"] is True
    assert scorer_validation["case_count"] == 64
    assert baseline_validation["valid"] is True
    assert baseline_validation["imported_baselines"] == []
    assert package["adjudication_valid"] is True
    assert package["adjudication_unresolved_label_count"] == 0
    assert str(label_review_path) in {record["path"] for record in run_manifest["inputs"]}
    assert str(label_adjudication_path) in {
        record["path"] for record in run_manifest["inputs"]
    }
    assert run_manifest["inputs"][0]["path"] == str(adjudicated_cases_path)
    assert str(adjudicated_corpus_path) in {
        record["path"] for record in run_manifest["inputs"]
    }
    assert str(scorer_validation_path) in {
        record["path"] for record in run_manifest["inputs"]
    }
    assert str(baseline_validation_path) in {
        record["path"] for record in run_manifest["inputs"]
    }
    assert readiness_report["components"]["label_review"]["valid"] is True
    assert readiness_report["components"]["label_adjudication"]["valid"] is True
    assert readiness_report["components"]["scorer_validation"]["valid"] is True
    assert readiness_report["components"]["baseline_validation"]["valid"] is True
    assert readiness_report["observed"]["label_review_property_row_count"] == 512
    assert (
        readiness_report["observed"]["label_adjudication_unresolved_label_count"] == 0
    )
    assert readiness_gaps["valid"] is True
    assert readiness_gaps["blocker_count"] == len(package["blocking_reasons"])
    assert readiness_gaps["artifact_area_counts"]["labels"] >= 1
    validation = validate_result_package_manifest(package)
    assert validation["valid"] is True
    assert validation["input_count"] == 4
    assert validation["output_count"] == 16
    assert "adjudicated_corpus_manifest" in validation["output_roles"]
    assert "adjudicated_cases" in validation["output_roles"]
    assert "label_adjudication" in validation["output_roles"]
    assert "scorer_validation" in validation["output_roles"]
    assert "baseline_validation" in validation["output_roles"]
    assert "readiness_report" in validation["output_roles"]
    assert "readiness_gaps" in validation["output_roles"]


def test_build_result_package_records_adjudication_overrides_input(
    tmp_path: Path,
) -> None:
    overrides = tmp_path / "overrides.jsonl"
    overrides.write_text("")

    package = build_result_package(
        corpus_manifest_path=Path("data/corpus/draft_balanced_64_corpus.yaml"),
        cases_path=Path("data/cases/draft_balanced_64_cases.jsonl"),
        annotations_path=Path("data/annotations/draft_balanced_64_annotations.jsonl"),
        scorer_predictions_path=Path("data/scorers/draft_balanced_64_scorer_outputs.jsonl"),
        adjudication_overrides_path=overrides,
        out_dir=tmp_path,
        prefix="draft",
    )

    validation = validate_result_package_manifest(package)
    assert validation["valid"] is True
    assert validation["input_count"] == 5
    assert "adjudication_overrides_jsonl" in validation["input_roles"]


def test_build_result_package_can_import_llm_judge_baseline_outputs(
    tmp_path: Path,
) -> None:
    llm_judge_outputs = tmp_path / "llm_judge_outputs.jsonl"
    _write_llm_judge_predictions(
        Path("data/cases/draft_balanced_64_cases.jsonl"),
        llm_judge_outputs,
        implementation_status="documented_prompt_run",
    )

    package = build_result_package(
        corpus_manifest_path=Path("data/corpus/draft_balanced_64_corpus.yaml"),
        cases_path=Path("data/cases/draft_balanced_64_cases.jsonl"),
        annotations_path=Path("data/annotations/draft_balanced_64_annotations.jsonl"),
        scorer_predictions_path=Path("data/scorers/draft_balanced_64_scorer_outputs.jsonl"),
        llm_judge_predictions_path=llm_judge_outputs,
        out_dir=tmp_path,
        prefix="draft",
    )

    validation = validate_result_package_manifest(package)
    baseline_summary = json.loads(Path(package["outputs"]["baseline_summary"]).read_text())
    baseline_validation = json.loads(
        Path(package["outputs"]["baseline_validation"]).read_text()
    )
    assert validation["valid"] is True
    assert validation["input_count"] == 5
    assert "llm_judge_jsonl" in validation["input_roles"]
    assert baseline_validation["valid"] is True
    assert baseline_validation["baselines"]["llm_judge"]["known_cases"] == 64
    assert baseline_summary["scorers"]["llm_judge"]["implementation_statuses"] == {
        "documented_prompt_run": 64
    }
    assert not any(
        reason == "disallowed_baseline_implementation_statuses=llm_judge:fixture_placeholder"
        for reason in package["blocking_reasons"]
    )


def test_validate_result_package_detects_artifact_mutation(tmp_path: Path) -> None:
    package = build_result_package(
        corpus_manifest_path=Path("data/corpus/draft_balanced_64_corpus.yaml"),
        cases_path=Path("data/cases/draft_balanced_64_cases.jsonl"),
        annotations_path=Path("data/annotations/draft_balanced_64_annotations.jsonl"),
        scorer_predictions_path=Path("data/scorers/draft_balanced_64_scorer_outputs.jsonl"),
        out_dir=tmp_path,
        prefix="draft",
    )
    manifest_path = Path(package["outputs"]["package_manifest"])
    baseline_summary_path = Path(package["outputs"]["baseline_summary"])
    baseline_summary_path.write_text("{}\n")

    validation = validate_result_package_file(manifest_path)

    assert validation["valid"] is False
    assert any(
        issue["issue"] in {"artifact_bytes_mismatch", "artifact_sha256_mismatch"}
        for issue in validation["issues"]
    )


def _write_llm_judge_predictions(
    cases_path: Path,
    out_path: Path,
    *,
    implementation_status: str,
) -> None:
    rows = []
    for line in cases_path.read_text().splitlines():
        case = json.loads(line)
        rows.append(
            {
                "case_id": case["case_id"],
                "scorer": "llm_judge",
                "verdict": "insufficient",
                "metadata": {"implementation_status": implementation_status},
            }
        )
    out_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")
