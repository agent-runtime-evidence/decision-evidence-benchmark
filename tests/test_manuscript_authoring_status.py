import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/manuscript_authoring_status.py")


def test_manuscript_authoring_status_reports_missing_gate_inputs(tmp_path: Path) -> None:
    out = tmp_path / "status.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_args(tmp_path), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    missing_roles = {
        blocker["role"]
        for blocker in payload["blockers"]
        if blocker["reason"] == "missing_required_gate_artifact"
    }
    assert result.returncode == 0
    assert payload["manuscript_input_gate_ready"] is False
    assert missing_roles == {
        "annotation_jsonl",
        "adjudicated_cases_jsonl",
        "scorer_outputs_jsonl",
        "corpus_manifest_yaml",
    }
    assert payload["next_actions"][0].startswith("Run make write-manuscript-construction-oracle")


def test_manuscript_authoring_status_can_require_llm_judge(tmp_path: Path) -> None:
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            *_args(tmp_path),
            "--include-llm-judge",
            "--out",
            str(out),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    missing_roles = {
        blocker["role"]
        for blocker in payload["blockers"]
        if blocker["reason"] == "missing_required_gate_artifact"
    }
    assert result.returncode == 0
    assert "llm_judge_outputs_jsonl" in missing_roles
    assert any(
        action.startswith("Fill data/results/manuscript_llm_judge_workbook.reviewed.csv")
        for action in payload["next_actions"]
    )


def test_manuscript_authoring_status_reports_ready_inputs(tmp_path: Path) -> None:
    out = tmp_path / "status.json"
    for path in _all_paths(tmp_path):
        _write_artifact(path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_args(tmp_path), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    assert result.returncode == 0
    assert payload["manuscript_input_gate_ready"] is True
    assert payload["reviewed_authoring_inputs_ready"] is True
    assert payload["blockers"] == []
    assert payload["next_actions"] == ["Run make verify-manuscript-package."]
    assert payload["stage_counts"]["annotation"]["present"] == 8


def test_manuscript_authoring_status_accepts_construction_oracle_without_reviewed_workbook(
    tmp_path: Path,
) -> None:
    out = tmp_path / "status.json"
    paths = _paths(tmp_path)
    for name, path in paths.items():
        if name != "annotation_workbook_reviewed":
            _write_artifact(path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_args(tmp_path), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    blocker_roles = {blocker["role"] for blocker in payload["blockers"]}
    assert result.returncode == 0
    assert payload["reviewed_authoring_inputs_ready"] is True
    assert "annotation_workbook_reviewed_csv" not in blocker_roles


def test_manuscript_authoring_status_blocks_invalid_leakage_audit(tmp_path: Path) -> None:
    out = tmp_path / "status.json"
    paths = _paths(tmp_path)
    for path in paths.values():
        _write_artifact(path)
    paths["label_leakage_audit"].write_text(
        '{"artifact_kind":"decision_evidence_manuscript_label_leakage_audit",'
        '"valid":false,"issues":[{"issue":"disallowed_label_token"}]}\n'
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_args(tmp_path), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    assert result.returncode == 0
    assert {
        blocker["role"] for blocker in payload["blockers"]
    } == {"label_leakage_audit_report"}
    assert payload["next_actions"] == [
        "Fix scorer-facing label leakage, then rerun make audit-manuscript-label-leakage."
    ]


def test_manuscript_authoring_status_blocks_stale_non_redacted_scorer_artifacts(
    tmp_path: Path,
) -> None:
    out = tmp_path / "status.json"
    paths = _paths(tmp_path)
    for path in paths.values():
        _write_artifact(path)
    paths["scorer_workbook_reviewed"].write_text(
        "case_id,prediction_status\n"
        "manuscript-aer-complete-actor_identity-001,reviewed\n"
    )
    paths["scorer_outputs"].write_text(
        '{"case_id":"manuscript-aer-complete-actor_identity-001","metadata":{}}\n'
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_args(tmp_path), "--out", str(out)],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(out.read_text())
    blockers = {(blocker["reason"], blocker["role"]) for blocker in payload["blockers"]}
    assert result.returncode == 0
    assert (
        "non_redacted_reviewed_workbook",
        "scorer_workbook_reviewed_csv",
    ) in blockers
    assert ("non_redacted_prediction_output", "scorer_outputs_jsonl") in blockers
    assert payload["next_actions"][0].startswith(
        "Regenerate data/results/manuscript_scorer_workbook.reviewed.csv"
    )


def _args(tmp_path: Path) -> list[str]:
    paths = _paths(tmp_path)
    return [
        "--case-source-reviewed",
        str(paths["case_source_reviewed"]),
        "--unadjudicated-cases",
        str(paths["unadjudicated_cases"]),
        "--case-source-report",
        str(paths["case_source_report"]),
        "--annotation-workbook",
        str(paths["annotation_workbook"]),
        "--annotation-workbook-reviewed",
        str(paths["annotation_workbook_reviewed"]),
        "--construction-oracle",
        str(paths["construction_oracle"]),
        "--annotations",
        str(paths["annotations"]),
        "--label-calibration",
        str(paths["label_calibration"]),
        "--label-review",
        str(paths["label_review"]),
        "--label-adjudication",
        str(paths["label_adjudication"]),
        "--adjudicated-cases",
        str(paths["adjudicated_cases"]),
        "--scorer-input-redaction",
        str(paths["scorer_input_redaction"]),
        "--scorer-workbook",
        str(paths["scorer_workbook"]),
        "--scorer-workbook-reviewed",
        str(paths["scorer_workbook_reviewed"]),
        "--scorer-outputs",
        str(paths["scorer_outputs"]),
        "--scorer-import-report",
        str(paths["scorer_import_report"]),
        "--llm-judge-workbook",
        str(paths["llm_judge_workbook"]),
        "--llm-judge-workbook-reviewed",
        str(paths["llm_judge_workbook_reviewed"]),
        "--llm-judge-outputs",
        str(paths["llm_judge_outputs"]),
        "--llm-judge-import-report",
        str(paths["llm_judge_import_report"]),
        "--label-leakage-audit",
        str(paths["label_leakage_audit"]),
        "--corpus",
        str(paths["corpus"]),
        "--preflight-report",
        str(paths["preflight_report"]),
        "--adjudication-overrides",
        str(paths["adjudication_overrides"]),
    ]


def _all_paths(tmp_path: Path) -> list[Path]:
    return list(_paths(tmp_path).values())


def _paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "case_source_reviewed": tmp_path / "cases" / "case_sources.reviewed.jsonl",
        "unadjudicated_cases": tmp_path / "cases" / "cases.unadjudicated.jsonl",
        "case_source_report": tmp_path / "results" / "case_source_conversion.json",
        "annotation_workbook": tmp_path / "results" / "annotation_workbook.csv",
        "annotation_workbook_reviewed": tmp_path / "results" / "annotation_workbook.reviewed.csv",
        "construction_oracle": tmp_path / "results" / "construction_oracle.json",
        "annotations": tmp_path / "annotations" / "annotations.jsonl",
        "label_calibration": tmp_path / "results" / "label_calibration.json",
        "label_review": tmp_path / "results" / "label_review.json",
        "label_adjudication": tmp_path / "results" / "label_adjudication.json",
        "adjudicated_cases": tmp_path / "cases" / "cases.jsonl",
        "scorer_input_redaction": tmp_path / "results" / "scorer_input_redaction.json",
        "scorer_workbook": tmp_path / "results" / "scorer_workbook.csv",
        "scorer_workbook_reviewed": tmp_path / "results" / "scorer_workbook.reviewed.csv",
        "scorer_outputs": tmp_path / "scorers" / "scorer_outputs.jsonl",
        "scorer_import_report": tmp_path / "results" / "scorer_import.json",
        "llm_judge_workbook": tmp_path / "results" / "llm_judge_workbook.csv",
        "llm_judge_workbook_reviewed": tmp_path / "results" / "llm_judge_workbook.reviewed.csv",
        "llm_judge_outputs": tmp_path / "baselines" / "llm_judge_outputs.jsonl",
        "llm_judge_import_report": tmp_path / "results" / "llm_judge_import.json",
        "label_leakage_audit": tmp_path / "results" / "label_leakage_audit.json",
        "corpus": tmp_path / "corpus" / "manuscript_corpus.yaml",
        "preflight_report": tmp_path / "results" / "input_preflight.json",
        "adjudication_overrides": tmp_path / "annotations" / "adjudication_overrides.jsonl",
    }


def _write_artifact(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        if "scorer_workbook" in path.name or "llm_judge_workbook" in path.name:
            path.write_text(
                "case_id,redaction_status,status\n"
                "case-000001,scorer_input_redacted_v1,reviewed\n"
            )
        else:
            path.write_text("case_id,status\ncase-1,reviewed\n")
    elif path.suffix == ".json":
        if path.name in {"scorer_import.json", "llm_judge_import.json"}:
            path.write_text(
                '{"artifact_kind":"test_report","valid":true,'
                '"redacted_input":true,"issues":[]}\n'
            )
        else:
            path.write_text('{"artifact_kind":"test_report","valid":true,"issues":[]}\n')
    elif path.suffix == ".jsonl":
        if path.name in {"scorer_outputs.jsonl", "llm_judge_outputs.jsonl"}:
            path.write_text(
                '{"case_id":"case-1",'
                '"metadata":{"scorer_input_redaction_status":"scorer_input_redacted_v1"}}\n'
            )
        else:
            path.write_text('{"case_id":"case-1"}\n')
    else:
        path.write_text("schema_version: 1\n")
