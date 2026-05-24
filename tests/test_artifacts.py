from pathlib import Path

from decision_evidence_benchmark.artifacts import (
    build_run_manifest,
    sha256_file,
    validate_run_manifest,
)


def test_run_manifest_records_checksums(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    output = tmp_path / "results.jsonl"
    cases.write_text('{"case_id":"a"}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')

    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(output,),
        case_count=1,
        baselines=("trace_present",),
    )

    assert manifest["claim_status"] == "mechanical_run_only"
    assert manifest["inputs"][0]["role"] == "case_manifest_jsonl"
    assert manifest["inputs"][0]["sha256"] == sha256_file(cases)
    assert manifest["outputs"][0]["role"] == "run_output"
    assert manifest["outputs"][0]["sha256"] == sha256_file(output)


def test_run_manifest_records_supporting_input_checksums(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    support = tmp_path / "corpus_validation.json"
    output = tmp_path / "results.jsonl"
    cases.write_text('{"case_id":"a"}\n')
    support.write_text('{"valid":true}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')

    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(output,),
        case_count=1,
        baselines=("trace_present",),
        supporting_input_paths=(support,),
    )

    assert manifest["inputs"][1]["role"] == "supporting_artifact"
    assert manifest["inputs"][1]["path"] == str(support)
    assert manifest["inputs"][1]["sha256"] == sha256_file(support)


def test_validate_run_manifest_accepts_checksummed_artifacts(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    output = tmp_path / "results.jsonl"
    cases.write_text('{"case_id":"a"}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(output,),
        case_count=1,
        baselines=("trace_present",),
    )

    validation = validate_run_manifest(manifest)

    assert validation["valid"] is True
    assert validation["input_roles"] == ["case_manifest_jsonl"]
    assert validation["output_roles"] == ["run_output"]


def test_validate_run_manifest_rejects_checksum_mismatch(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    output = tmp_path / "results.jsonl"
    cases.write_text('{"case_id":"a"}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(output,),
        case_count=1,
        baselines=("trace_present",),
    )
    output.write_text('{"case_id":"a","verdict":"sufficient"}\n')

    validation = validate_run_manifest(manifest)

    assert validation["valid"] is False
    assert any(issue["issue"] == "artifact_sha256_mismatch" for issue in validation["issues"])


def test_validate_run_manifest_requires_input_and_output_roles() -> None:
    validation = validate_run_manifest(
        {
            "schema_version": 1,
            "artifact_kind": "decision_evidence_benchmark_run",
            "inputs": [],
            "outputs": [],
        }
    )

    assert validation["valid"] is False
    assert {
        issue["role"]
        for issue in validation["issues"]
        if issue["issue"] == "missing_artifact_role"
    } == {"case_manifest_jsonl", "run_output"}


def test_validate_run_manifest_requires_expected_artifact_paths(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    support = tmp_path / "corpus_validation.json"
    output = tmp_path / "results.jsonl"
    missing_support = tmp_path / "label_calibration.json"
    cases.write_text('{"case_id":"a"}\n')
    support.write_text('{"valid":true}\n')
    output.write_text('{"case_id":"a","verdict":"abstain"}\n')
    manifest = build_run_manifest(
        cases_path=cases,
        output_paths=(output,),
        case_count=1,
        baselines=("trace_present",),
        supporting_input_paths=(support,),
    )

    validation = validate_run_manifest(
        manifest,
        expected_input_paths=(support, missing_support),
        expected_output_paths=(output,),
    )

    assert validation["valid"] is False
    assert any(
        issue["issue"] == "missing_expected_artifact_path"
        and issue["path"] == str(missing_support)
        for issue in validation["issues"]
    )
