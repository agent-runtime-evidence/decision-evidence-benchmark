import csv
import json
import subprocess
import sys
from pathlib import Path

from decision_evidence_benchmark.baselines.imported import (
    ImportedBaseline,
    validate_imported_baselines,
)
from decision_evidence_benchmark.evaluation import validate_scorer_outputs
from decision_evidence_benchmark.io import read_scorer_outputs_jsonl, write_cases_jsonl
from decision_evidence_benchmark.manuscript_redaction import SCORER_INPUT_REDACTION_STATUS
from decision_evidence_benchmark.schema import DECISION_EVENT_PROPERTIES, CaseManifest

SCORER_INPUT_SCRIPT = Path("scripts/write_manuscript_scorer_input.py")
SCORER_EXPORT_SCRIPT = Path("scripts/export_manuscript_scorer_workbook.py")
SCORER_IMPORT_SCRIPT = Path("scripts/import_manuscript_scorer_workbook.py")
LLM_JUDGE_EXPORT_SCRIPT = Path("scripts/export_manuscript_llm_judge_workbook.py")
LLM_JUDGE_IMPORT_SCRIPT = Path("scripts/import_manuscript_llm_judge_workbook.py")


def test_export_manuscript_scorer_workbook_writes_property_grid(tmp_path: Path) -> None:
    paths = _scorer_paths(tmp_path)
    write_cases_jsonl(paths["cases"], [_case()])

    result = subprocess.run(
        [
            sys.executable,
            str(SCORER_EXPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    csv_rows = list(csv.DictReader(paths["workbook"].open()))
    jsonl_rows = [json.loads(line) for line in paths["jsonl"].read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == len(DECISION_EVENT_PROPERTIES)
    assert len(jsonl_rows) == len(csv_rows)
    assert csv_rows[0]["prediction_status"] == "todo"
    assert csv_rows[0]["verdict"] == "__SELECT_VERDICT__"
    assert csv_rows[0]["category"] == "__SELECT_CATEGORY__"


def test_export_manuscript_scorer_workbook_uses_redacted_input(tmp_path: Path) -> None:
    paths = _redacted_scorer_paths(tmp_path)
    _write_redacted_scorer_input(paths)

    result = subprocess.run(
        [
            sys.executable,
            str(SCORER_EXPORT_SCRIPT),
            "--cases",
            str(paths["redacted_cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    csv_rows = list(csv.DictReader(paths["workbook"].open()))
    workbook_text = paths["workbook"].read_text()
    assert result.returncode == 0
    assert csv_rows[0]["case_id"] == "case-000001"
    assert csv_rows[0]["redaction_status"] == SCORER_INPUT_REDACTION_STATUS
    assert "degradation_condition" not in csv_rows[0]
    assert "native_evidence_refs" not in csv_rows[0]
    assert "manuscript-aer-complete-actor_identity-001" not in workbook_text
    assert "missing_policy" not in workbook_text


def test_import_manuscript_scorer_workbook_rejects_placeholders(tmp_path: Path) -> None:
    paths = _exported_scorer_workbook(tmp_path)

    result = _run_scorer_import(paths)

    payload = json.loads(paths["report"].read_text())
    issue_codes = {issue["issue"] for issue in payload["issues"]}
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not paths["outputs"].exists()
    assert issue_codes >= {
        "invalid_prediction_status",
        "invalid_verdict",
        "invalid_property_category",
        "missing_prediction_metadata",
    }


def test_import_manuscript_scorer_workbook_writes_valid_outputs(tmp_path: Path) -> None:
    paths = _exported_scorer_workbook(tmp_path)
    _write_reviewed_scorer_workbook(paths["workbook"])

    result = _run_scorer_import(paths)

    payload = json.loads(paths["report"].read_text())
    cases = [_case()]
    outputs = read_scorer_outputs_jsonl(paths["outputs"])
    validation = validate_scorer_outputs(cases, outputs)
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["output_count"] == 1
    assert outputs[0].metadata["implementation_status"] == "decision_trace_reconstructor_run"
    assert outputs[0].property_predictions[0].source == "manuscript_candidate_scorer_prediction"
    assert validation["valid"] is True


def test_import_manuscript_scorer_workbook_maps_redacted_ids_to_original_cases(
    tmp_path: Path,
) -> None:
    paths = _exported_redacted_scorer_workbook(tmp_path)
    _write_reviewed_scorer_workbook(paths["workbook"])

    result = _run_scorer_import(paths, case_id_map=paths["case_id_map"])

    payload = json.loads(paths["report"].read_text())
    outputs = read_scorer_outputs_jsonl(paths["outputs"])
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["redacted_input"] is True
    assert outputs[0].case_id == "manuscript-aer-complete-actor_identity-001"
    assert outputs[0].metadata["scorer_input_case_id"] == "case-000001"
    assert outputs[0].metadata["scorer_input_redaction_status"] == SCORER_INPUT_REDACTION_STATUS


def test_export_manuscript_llm_judge_workbook_writes_case_rows(tmp_path: Path) -> None:
    paths = _llm_judge_paths(tmp_path)
    write_cases_jsonl(paths["cases"], [_case()])

    result = subprocess.run(
        [
            sys.executable,
            str(LLM_JUDGE_EXPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    csv_rows = list(csv.DictReader(paths["workbook"].open()))
    jsonl_rows = [json.loads(line) for line in paths["jsonl"].read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == 1
    assert len(jsonl_rows) == 1
    assert csv_rows[0]["prediction_status"] == "todo"
    assert csv_rows[0]["scorer"] == "llm_judge"


def test_export_manuscript_llm_judge_workbook_uses_redacted_input(tmp_path: Path) -> None:
    paths = _redacted_llm_judge_paths(tmp_path)
    _write_redacted_scorer_input(paths)

    result = subprocess.run(
        [
            sys.executable,
            str(LLM_JUDGE_EXPORT_SCRIPT),
            "--cases",
            str(paths["redacted_cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    csv_rows = list(csv.DictReader(paths["workbook"].open()))
    workbook_text = paths["workbook"].read_text()
    assert result.returncode == 0
    assert csv_rows[0]["case_id"] == "case-000001"
    assert csv_rows[0]["redaction_status"] == SCORER_INPUT_REDACTION_STATUS
    assert "degradation_condition" not in csv_rows[0]
    assert "reviewed_source_refs" not in csv_rows[0]
    assert "manuscript-aer-complete-actor_identity-001" not in workbook_text


def test_import_manuscript_llm_judge_workbook_rejects_placeholders(tmp_path: Path) -> None:
    paths = _exported_llm_judge_workbook(tmp_path)

    result = _run_llm_judge_import(paths)

    payload = json.loads(paths["report"].read_text())
    issue_codes = {issue["issue"] for issue in payload["issues"]}
    assert result.returncode == 1
    assert payload["valid"] is False
    assert not paths["outputs"].exists()
    assert issue_codes >= {
        "invalid_prediction_status",
        "invalid_verdict",
        "missing_prediction_metadata",
    }


def test_import_manuscript_llm_judge_workbook_writes_valid_outputs(tmp_path: Path) -> None:
    paths = _exported_llm_judge_workbook(tmp_path)
    _write_reviewed_llm_judge_workbook(paths["workbook"])

    result = _run_llm_judge_import(paths)

    payload = json.loads(paths["report"].read_text())
    cases = [_case()]
    outputs = read_scorer_outputs_jsonl(paths["outputs"])
    validation = validate_imported_baselines(
        cases,
        ("llm_judge",),
        imported_baselines={
            "llm_judge": ImportedBaseline(name="llm_judge", outputs=tuple(outputs))
        },
    )
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["output_count"] == 1
    assert outputs[0].metadata["implementation_status"] == "documented_prompt_run"
    assert validation["valid"] is True


def test_import_manuscript_llm_judge_workbook_maps_redacted_ids_to_original_cases(
    tmp_path: Path,
) -> None:
    paths = _exported_redacted_llm_judge_workbook(tmp_path)
    _write_reviewed_llm_judge_workbook(paths["workbook"])

    result = _run_llm_judge_import(paths, case_id_map=paths["case_id_map"])

    payload = json.loads(paths["report"].read_text())
    outputs = read_scorer_outputs_jsonl(paths["outputs"])
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["redacted_input"] is True
    assert outputs[0].case_id == "manuscript-aer-complete-actor_identity-001"
    assert outputs[0].metadata["scorer_input_case_id"] == "case-000001"
    assert outputs[0].metadata["scorer_input_redaction_status"] == SCORER_INPUT_REDACTION_STATUS


def _case() -> CaseManifest:
    return CaseManifest(
        case_id="manuscript-aer-complete-actor_identity-001",
        regime="aer",
        degradation_condition="complete",
        question_family="actor_identity",
        evidence={
            "native_evidence_refs": ["data/sources/native.jsonl#case_id=case"],
            "reviewed_source_refs": ["data/sources/review.jsonl#case_id=case"],
            "evidence_plane_refs": ["data/sources/plane.jsonl#case_id=case"],
            "provenance_notes": "reviewed source row",
        },
        container_flags={
            "trace_present": True,
            "ledger_present": True,
            "schema_valid": True,
            "checklist_complete": True,
            "source_validator_passed": True,
            "llm_judge_verdict": "sufficient",
        },
        property_labels=(),
        metadata={"case_source_status": "reviewed_non_fixture_evidence"},
    )


def _scorer_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "cases": tmp_path / "cases.jsonl",
        "workbook": tmp_path / "scorer_workbook.csv",
        "jsonl": tmp_path / "scorer_workbook.jsonl",
        "outputs": tmp_path / "decision_trace_reconstructor_outputs.jsonl",
        "report": tmp_path / "scorer_import.json",
        "redacted_cases": tmp_path / "scorer_input_cases.jsonl",
        "case_id_map": tmp_path / "scorer_input_case_id_map.jsonl",
        "redaction_report": tmp_path / "scorer_input_redaction.json",
    }


def _llm_judge_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "cases": tmp_path / "cases.jsonl",
        "workbook": tmp_path / "llm_judge_workbook.csv",
        "jsonl": tmp_path / "llm_judge_workbook.jsonl",
        "outputs": tmp_path / "llm_judge_outputs.jsonl",
        "report": tmp_path / "llm_judge_import.json",
        "redacted_cases": tmp_path / "scorer_input_cases.jsonl",
        "case_id_map": tmp_path / "scorer_input_case_id_map.jsonl",
        "redaction_report": tmp_path / "scorer_input_redaction.json",
    }


def _redacted_scorer_paths(tmp_path: Path) -> dict[str, Path]:
    return _scorer_paths(tmp_path)


def _redacted_llm_judge_paths(tmp_path: Path) -> dict[str, Path]:
    return _llm_judge_paths(tmp_path)


def _exported_scorer_workbook(tmp_path: Path) -> dict[str, Path]:
    paths = _scorer_paths(tmp_path)
    write_cases_jsonl(paths["cases"], [_case()])
    result = subprocess.run(
        [
            sys.executable,
            str(SCORER_EXPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return paths


def _exported_redacted_scorer_workbook(tmp_path: Path) -> dict[str, Path]:
    paths = _scorer_paths(tmp_path)
    _write_redacted_scorer_input(paths)
    result = subprocess.run(
        [
            sys.executable,
            str(SCORER_EXPORT_SCRIPT),
            "--cases",
            str(paths["redacted_cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return paths


def _exported_llm_judge_workbook(tmp_path: Path) -> dict[str, Path]:
    paths = _llm_judge_paths(tmp_path)
    write_cases_jsonl(paths["cases"], [_case()])
    result = subprocess.run(
        [
            sys.executable,
            str(LLM_JUDGE_EXPORT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return paths


def _exported_redacted_llm_judge_workbook(tmp_path: Path) -> dict[str, Path]:
    paths = _llm_judge_paths(tmp_path)
    _write_redacted_scorer_input(paths)
    result = subprocess.run(
        [
            sys.executable,
            str(LLM_JUDGE_EXPORT_SCRIPT),
            "--cases",
            str(paths["redacted_cases"]),
            "--csv-out",
            str(paths["workbook"]),
            "--jsonl-out",
            str(paths["jsonl"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return paths


def _write_redacted_scorer_input(paths: dict[str, Path]) -> None:
    write_cases_jsonl(paths["cases"], [_case()])
    result = subprocess.run(
        [
            sys.executable,
            str(SCORER_INPUT_SCRIPT),
            "--cases",
            str(paths["cases"]),
            "--out",
            str(paths["redacted_cases"]),
            "--case-id-map",
            str(paths["case_id_map"]),
            "--report",
            str(paths["redaction_report"]),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0


def _run_scorer_import(
    paths: dict[str, Path],
    *,
    case_id_map: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(SCORER_IMPORT_SCRIPT),
        "--cases",
        str(paths["cases"]),
        "--workbook",
        str(paths["workbook"]),
        "--out",
        str(paths["outputs"]),
        "--report",
        str(paths["report"]),
    ]
    if case_id_map is not None:
        args.extend(["--case-id-map", str(case_id_map)])
    return subprocess.run(
        args,
        capture_output=True,
        check=False,
        text=True,
    )


def _run_llm_judge_import(
    paths: dict[str, Path],
    *,
    case_id_map: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(LLM_JUDGE_IMPORT_SCRIPT),
        "--cases",
        str(paths["cases"]),
        "--workbook",
        str(paths["workbook"]),
        "--out",
        str(paths["outputs"]),
        "--report",
        str(paths["report"]),
    ]
    if case_id_map is not None:
        args.extend(["--case-id-map", str(case_id_map)])
    return subprocess.run(
        args,
        capture_output=True,
        check=False,
        text=True,
    )


def _write_reviewed_scorer_workbook(path: Path) -> None:
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        row["prediction_status"] = "reviewed"
        row["verdict"] = "sufficient"
        row["category"] = "complete"
        row["implementation_status"] = "decision_trace_reconstructor_run"
        row["run_id"] = "dtr-manuscript-run-001"
        row["model"] = "deterministic"
        row["prompt_version"] = "not_applicable"
        row["reviewer_id"] = "reviewer-1"
        row["reviewed_at"] = "2026-05-25"
        row["notes"] = "reviewed candidate scorer prediction"
    _write_csv(path, rows)


def _write_reviewed_llm_judge_workbook(path: Path) -> None:
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        row["prediction_status"] = "reviewed"
        row["verdict"] = "insufficient"
        row["implementation_status"] = "documented_prompt_run"
        row["run_id"] = "llm-judge-manuscript-run-001"
        row["model"] = "reviewed-model-id"
        row["prompt_version"] = "llm_judge_prompt_v1"
        row["reviewer_id"] = "reviewer-1"
        row["reviewed_at"] = "2026-05-25"
        row["notes"] = "reviewed LLM-judge verdict"
    _write_csv(path, rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
