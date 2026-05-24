import json
from pathlib import Path

import pytest

from decision_evidence_benchmark.adapters.registry import NATIVE_ADAPTERS
from decision_evidence_benchmark.artifacts import build_run_manifest
from decision_evidence_benchmark.cli import main
from decision_evidence_benchmark.corpus import validate_corpus_manifest
from decision_evidence_benchmark.evaluation import CANDIDATE_SCORER_METRIC_CONTRACT
from decision_evidence_benchmark.metrics.overclaim import OVERCLAIM_SUMMARY_METRIC_CONTRACT
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES

NATIVE_FIXTURES = {
    "aegis_ntc": "data/cases/aegis_ntc/missing_policy_001.native.json",
    "aer": "data/cases/aer/missing_policy_001.native.json",
    "dcc_hdp": "data/cases/dcc_hdp/missing_policy_001.native.json",
    "dynamic_capabilities": "data/cases/dynamic_capabilities/missing_policy_001.native.json",
    "ieec": "data/cases/ieec/missing_policy_001.native.json",
    "llm_audit_trails": "data/cases/llm_audit_trails/missing_policy_001.native.json",
    "mat": "data/cases/mat/missing_policy_001.native.json",
    "prov": "data/cases/prov/missing_policy_001.native.json",
}


def test_cli_run_writes_outputs(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "results.jsonl"
    summary = tmp_path / "summary.json"
    run_manifest = tmp_path / "run_manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "run",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--out",
            str(out),
            "--summary",
            str(summary),
            "--run-manifest",
            str(run_manifest),
        ],
    )

    assert main() == 0
    assert out.exists()
    payload = json.loads(summary.read_text())
    manifest = json.loads(run_manifest.read_text())
    assert "trace_present" in payload["scorers"]
    assert manifest["case_count"] == 8
    assert manifest["claim_status"] == "mechanical_run_only"
    assert manifest["outputs"][0]["path"] == str(out)
    assert manifest["inputs"][0]["role"] == "case_manifest_jsonl"


def test_cli_run_can_write_manuscript_candidate_claim_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "results.jsonl"
    summary = tmp_path / "summary.json"
    run_manifest = tmp_path / "run_manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "run",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--out",
            str(out),
            "--summary",
            str(summary),
            "--run-manifest",
            str(run_manifest),
            "--run-claim-status",
            "manuscript_result_candidate",
        ],
    )

    assert main() == 0
    manifest = json.loads(run_manifest.read_text())
    assert manifest["claim_status"] == "manuscript_result_candidate"


def test_cli_run_can_import_llm_judge_predictions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictions = tmp_path / "llm_judge_outputs.jsonl"
    _write_llm_judge_predictions(
        Path("data/fixtures/smoke_cases.jsonl"),
        predictions,
        implementation_status="documented_prompt_run",
    )
    out = tmp_path / "results.jsonl"
    summary = tmp_path / "summary.json"
    run_manifest = tmp_path / "run_manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "run",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--baseline",
            "llm_judge",
            "--llm-judge-predictions",
            str(predictions),
            "--out",
            str(out),
            "--summary",
            str(summary),
            "--run-manifest",
            str(run_manifest),
        ],
    )

    assert main() == 0
    payload = json.loads(summary.read_text())
    manifest = json.loads(run_manifest.read_text())
    assert payload["scorers"]["llm_judge"]["implementation_statuses"] == {
        "documented_prompt_run": 8
    }
    assert str(predictions) in {record["path"] for record in manifest["inputs"]}


def test_cli_validate_baseline_predictions_writes_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predictions = tmp_path / "llm_judge_outputs.jsonl"
    _write_llm_judge_predictions(
        Path("data/fixtures/smoke_cases.jsonl"),
        predictions,
        implementation_status="documented_prompt_run",
    )
    out = tmp_path / "baseline_validation.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "validate-baseline-predictions",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--baseline",
            "llm_judge",
            "--predictions",
            str(predictions),
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["valid"] is True
    assert payload["imported_baselines"] == ["llm_judge"]
    assert payload["baselines"]["llm_judge"]["known_cases"] == 8


def test_cli_run_manifest_records_supporting_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "results.jsonl"
    summary = tmp_path / "summary.json"
    run_manifest = tmp_path / "run_manifest.json"
    supporting_input = tmp_path / "supporting.json"
    supporting_input.write_text('{"valid":true}\n')
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "run",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--out",
            str(out),
            "--summary",
            str(summary),
            "--supporting-input",
            str(supporting_input),
            "--run-manifest",
            str(run_manifest),
        ],
    )

    assert main() == 0
    manifest = json.loads(run_manifest.read_text())
    assert manifest["inputs"][1]["role"] == "supporting_artifact"
    assert manifest["inputs"][1]["path"] == str(supporting_input)


def test_cli_adapt_dcc_hdp_writes_case_manifest(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "case.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "adapt-dcc-hdp",
            "--input",
            "data/cases/dcc_hdp/missing_policy_001.native.json",
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["regime"] == "dcc_hdp"
    assert payload["property_labels"][3]["property"] == "policy_basis"
    assert payload["property_labels"][3]["category"] == "opaque"


def test_cli_generic_adapt_writes_case_manifest(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "case.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "adapt",
            "--regime",
            "dcc_hdp",
            "--input",
            "data/cases/dcc_hdp/missing_policy_001.native.json",
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["case_id"] == "smoke-dcc-missing-policy-001"


@pytest.mark.parametrize("regime", sorted(NATIVE_FIXTURES))
def test_cli_generic_adapt_supports_all_registered_native_fixtures(
    regime: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert set(NATIVE_FIXTURES) == set(NATIVE_ADAPTERS)
    out = tmp_path / f"{regime}.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "adapt",
            "--regime",
            regime,
            "--input",
            NATIVE_FIXTURES[regime],
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["regime"] == regime
    assert payload["degradation_condition"] == "missing_policy"


def test_cli_evaluate_scorer_writes_summary(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "scorer_results.jsonl"
    summary = tmp_path / "scorer_summary.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "evaluate-scorer",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--predictions",
            "data/fixtures/smoke_scorer_outputs.jsonl",
            "--out",
            str(out),
            "--summary",
            str(summary),
        ],
    )

    assert main() == 0
    payload = json.loads(summary.read_text())
    assert payload["valid"] is True
    assert "decision_trace_reconstructor" in payload["scorers"]


def test_cli_validate_scorer_predictions_writes_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = tmp_path / "scorer_validation.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "validate-scorer-predictions",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--predictions",
            "data/fixtures/smoke_scorer_outputs.jsonl",
            "--out",
            str(summary),
        ],
    )

    assert main() == 0
    payload = json.loads(summary.read_text())
    assert payload["valid"] is True
    assert payload["required_scorers"] == ["decision_trace_reconstructor"]
    assert payload["scorers"]["decision_trace_reconstructor"]["known_cases"] == 8


def test_cli_calibrate_labels_writes_summary(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    summary = tmp_path / "label_calibration.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "calibrate-labels",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--annotations",
            "data/annotations/smoke_annotations.jsonl",
            "--summary",
            str(summary),
        ],
    )

    assert main() == 0
    payload = json.loads(summary.read_text())
    assert payload["valid"] is True
    assert payload["overall"]["cohen_kappa"] == 1.0


def test_cli_review_labels_writes_json_and_csv(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "label_review.json"
    csv_out = tmp_path / "label_review.csv"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "review-labels",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--annotations",
            "data/annotations/smoke_annotations.jsonl",
            "--out",
            str(out),
            "--csv-out",
            str(csv_out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["valid"] is True
    assert payload["property_row_count"] == 64
    assert payload["disagreed_property_count"] == 0
    assert csv_out.read_text().startswith("case_id,regime,degradation_condition")


def test_cli_adjudicate_labels_writes_cases_and_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_cases = tmp_path / "adjudicated_cases.jsonl"
    report = tmp_path / "adjudication.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "adjudicate-labels",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--annotations",
            "data/annotations/smoke_annotations.jsonl",
            "--out-cases",
            str(out_cases),
            "--report",
            str(report),
        ],
    )

    assert main() == 0
    payload = json.loads(report.read_text())
    assert payload["valid"] is True
    assert payload["agreement_label_count"] == 64
    cases = validate_corpus_manifest(_single_case_manifest(tmp_path, out_cases))
    assert cases["valid"] is True
    assert cases["case_count"] == 8


def test_cli_write_adjudication_overrides_template_writes_disagreement_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annotations = tmp_path / "annotations.jsonl"
    source_lines = Path("data/annotations/smoke_annotations.jsonl").read_text().splitlines()
    first = json.loads(source_lines[0])
    first["property_labels"][0]["category"] = (
        "opaque"
        if first["property_labels"][0]["category"] == "complete"
        else "complete"
    )
    annotations.write_text(
        "\n".join([json.dumps(first), *source_lines[1:]]) + "\n"
    )
    out = tmp_path / "adjudication_overrides.template.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "write-adjudication-overrides-template",
            "--cases",
            "data/fixtures/smoke_cases.jsonl",
            "--annotations",
            str(annotations),
            "--out",
            str(out),
            "--adjudicator-id",
            "reviewer_1",
        ],
    )

    assert main() == 0
    rows = [json.loads(line) for line in out.read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["category"] == "__SELECT_CATEGORY__"
    assert rows[0]["adjudicator_id"] == "reviewer_1"
    assert rows[0]["template_status"] == "requires_manual_category_selection"


def test_cli_generate_draft_corpus_writes_balanced_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = tmp_path / "cases.jsonl"
    annotations = tmp_path / "annotations.jsonl"
    scorer_outputs = tmp_path / "scorer_outputs.jsonl"
    manifest = tmp_path / "corpus.yaml"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "generate-draft-corpus",
            "--cases",
            str(cases),
            "--annotations",
            str(annotations),
            "--scorer-outputs",
            str(scorer_outputs),
            "--manifest",
            str(manifest),
        ],
    )

    assert main() == 0
    assert cases.exists()
    assert annotations.exists()
    assert scorer_outputs.exists()
    corpus = validate_corpus_manifest(manifest)
    assert corpus["valid"] is True
    assert corpus["case_count"] == 64
    assert corpus["strict_sufficiency_counts"] == {"insufficient": 56, "sufficient": 8}


def test_cli_build_result_package_writes_package_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "build-result-package",
            "--corpus-manifest",
            "data/corpus/draft_balanced_64_corpus.yaml",
            "--cases",
            "data/cases/draft_balanced_64_cases.jsonl",
            "--annotations",
            "data/annotations/draft_balanced_64_annotations.jsonl",
            "--scorer-predictions",
            "data/scorers/draft_balanced_64_scorer_outputs.jsonl",
            "--out-dir",
            str(tmp_path),
            "--prefix",
            "draft",
        ],
    )

    assert main() == 0
    package = json.loads((tmp_path / "draft_package_manifest.json").read_text())
    assert package["mechanics_valid"] is True
    assert package["manuscript_result_ready"] is False
    assert (tmp_path / "draft_label_review.json").exists()
    assert (tmp_path / "draft_label_adjudication.json").exists()
    assert (tmp_path / "draft_adjudicated_cases.jsonl").exists()
    assert (tmp_path / "draft_adjudicated_corpus.yaml").exists()
    assert (tmp_path / "draft_run_manifest.json").exists()
    assert (tmp_path / "draft_readiness_gaps.json").exists()


def test_cli_validate_result_package_writes_validation_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_dir = tmp_path / "package"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "build-result-package",
            "--corpus-manifest",
            "data/corpus/draft_balanced_64_corpus.yaml",
            "--cases",
            "data/cases/draft_balanced_64_cases.jsonl",
            "--annotations",
            "data/annotations/draft_balanced_64_annotations.jsonl",
            "--scorer-predictions",
            "data/scorers/draft_balanced_64_scorer_outputs.jsonl",
            "--out-dir",
            str(package_dir),
            "--prefix",
            "draft",
        ],
    )
    assert main() == 0

    validation = tmp_path / "validation.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "validate-result-package",
            "--manifest",
            str(package_dir / "draft_package_manifest.json"),
            "--out",
            str(validation),
        ],
    )

    assert main() == 0
    payload = json.loads(validation.read_text())
    assert payload["valid"] is True
    assert payload["output_count"] == 16


def test_cli_export_manuscript_tables_writes_csvs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_dir = tmp_path / "package"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "build-result-package",
            "--corpus-manifest",
            "data/corpus/draft_balanced_64_corpus.yaml",
            "--cases",
            "data/cases/draft_balanced_64_cases.jsonl",
            "--annotations",
            "data/annotations/draft_balanced_64_annotations.jsonl",
            "--scorer-predictions",
            "data/scorers/draft_balanced_64_scorer_outputs.jsonl",
            "--out-dir",
            str(package_dir),
            "--prefix",
            "draft",
        ],
    )
    assert main() == 0

    table_dir = tmp_path / "tables"
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "export-manuscript-tables",
            "--package-manifest",
            str(package_dir / "draft_package_manifest.json"),
            "--out-dir",
            str(table_dir),
            "--summary-out",
            str(summary),
        ],
    )

    assert main() == 0
    payload = json.loads(summary.read_text())
    assert payload["valid"] is True
    assert payload["outputs"]["gate_status_csv"] == str(table_dir / "draft_gate_status.csv")
    assert (table_dir / "draft_readiness_blockers.csv").exists()
    assert (table_dir / "draft_artifact_inventory.csv").exists()


def test_cli_readiness_report_writes_report(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    corpus = tmp_path / "corpus.json"
    calibration = tmp_path / "calibration.json"
    scorer = tmp_path / "scorer.json"
    baseline = tmp_path / "baseline.json"
    run_manifest = tmp_path / "run_manifest.json"
    report = tmp_path / "readiness.json"
    cases = tmp_path / "cases.jsonl"
    output = tmp_path / "results.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "valid": True,
                "claim_status": "smoke_only_not_empirical_evidence",
                "case_count": 1,
                "label_contract": {
                    "required_properties": list(DECISION_EVENT_PROPERTIES),
                },
                "degradation_condition_counts": {
                    "missing_policy": 1,
                },
                "question_family_counts": {
                    "policy_basis": 1,
                },
                "regime_counts": {"dcc_hdp": 1},
            }
        )
    )
    calibration.write_text(
        json.dumps(
            {
                "valid": True,
                "case_count": 1,
                "paired_case_count": 1,
                "paired_label_count": 8,
                "overall": {"cohen_kappa": 1.0},
            }
        )
    )
    scorer.write_text(
        json.dumps(
            {
                "metric_contract": CANDIDATE_SCORER_METRIC_CONTRACT,
                "valid": True,
                "scorers": {"candidate": {"cases": 1}},
            }
        )
    )
    baseline.write_text(
        json.dumps(
            {
                "metric_contract": OVERCLAIM_SUMMARY_METRIC_CONTRACT,
                "scorers": {"trace_present": {"cases": 1}},
            }
        )
    )
    cases.write_text('{"case_id":"a"}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    run_manifest.write_text(
        json.dumps(
            build_run_manifest(
                cases_path=cases,
                output_paths=(output, baseline),
                case_count=1,
                baselines=("trace_present",),
                supporting_input_paths=(corpus, calibration, scorer),
            )
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "readiness-report",
            "--corpus-validation",
            str(corpus),
            "--label-calibration",
            str(calibration),
            "--scorer-summary",
            str(scorer),
            "--baseline-summary",
            str(baseline),
            "--run-manifest",
            str(run_manifest),
            "--out",
            str(report),
            "--min-degradation-conditions",
            "1",
            "--min-question-families",
            "1",
            "--required-baseline",
            "trace_present",
            "--required-candidate-scorer",
            "candidate",
        ],
    )

    assert main() == 0
    payload = json.loads(report.read_text())
    assert payload["mechanics_valid"] is True
    assert payload["manuscript_result_ready"] is False
    assert payload["readiness_policy"]["required_corpus_claim_status"] == (
        "manuscript_result_candidate"
    )
    assert payload["readiness_policy"]["required_run_claim_status"] == (
        "manuscript_result_candidate"
    )
    assert not any(
        reason.startswith(("missing_baselines=", "missing_candidate_scorers="))
        for reason in payload["blocking_reasons"]
    )

    strict_report = tmp_path / "strict_readiness.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "readiness-report",
            "--corpus-validation",
            str(corpus),
            "--label-calibration",
            str(calibration),
            "--scorer-summary",
            str(scorer),
            "--baseline-summary",
            str(baseline),
            "--run-manifest",
            str(run_manifest),
            "--out",
            str(strict_report),
            "--fail-on-blockers",
            "--min-degradation-conditions",
            "1",
            "--min-question-families",
            "1",
            "--required-baseline",
            "trace_present",
            "--required-candidate-scorer",
            "candidate",
        ],
    )

    assert main() == 1
    assert json.loads(strict_report.read_text())["mechanics_valid"] is True


def test_cli_readiness_gaps_writes_actionable_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_report = tmp_path / "readiness.json"
    readiness_report.write_text(
        json.dumps(
            {
                "metric_contract": "decision_evidence_result_readiness",
                "mechanics_valid": True,
                "manuscript_result_ready": False,
                "blocking_reasons": [
                    (
                        "corpus_claim_status=smoke_only_not_empirical_evidence!="
                        "required_corpus_claim_status=manuscript_result_candidate"
                    ),
                    "missing_baselines=llm_judge",
                ],
            }
        )
    )
    out = tmp_path / "readiness_gaps.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "decision-evidence-benchmark",
            "readiness-gaps",
            "--readiness-report",
            str(readiness_report),
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    payload = json.loads(out.read_text())
    assert payload["valid"] is True
    assert payload["blocker_count"] == 2
    assert payload["artifact_area_counts"] == {"baselines": 1, "corpus": 1}
    assert payload["blockers"][0]["category"] == "corpus_claim_status"
    assert payload["blockers"][1]["artifact_area"] == "baselines"


def _single_case_manifest(tmp_path: Path, cases: Path) -> Path:
    manifest = tmp_path / "corpus.yaml"
    manifest.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "corpus_id: cli_adjudication_test",
                "version: 0.0.0-test",
                "claim_status: test_only",
                "expected_regimes:",
                "  - aegis_ntc",
                "  - aer",
                "  - dcc_hdp",
                "  - dynamic_capabilities",
                "  - ieec",
                "  - llm_audit_trails",
                "  - mat",
                "  - prov",
                "case_files:",
                f"  - path: {cases}",
                "    role: case_manifest_jsonl",
                "label_contract:",
                "  mode: embedded_property_labels",
                "  required_properties:",
                "    - actor_identity",
                "    - principal_authority",
                "    - action_boundary",
                "    - policy_basis",
                "    - decision_basis",
                "    - data_resource_touch",
                "    - lifecycle_context",
                "    - verification_strength",
                "",
            ]
        )
    )
    return manifest


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
