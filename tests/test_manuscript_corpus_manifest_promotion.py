import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path("scripts/write_manuscript_corpus_manifest.py")


def test_write_manuscript_corpus_manifest_rejects_missing_inputs(tmp_path: Path) -> None:
    template = _write_template(tmp_path)
    out = tmp_path / "corpus" / "manuscript_corpus.yaml"
    report = tmp_path / "results" / "promotion.json"
    required = _required_paths(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--out",
            str(out),
            "--report",
            str(report),
            *_required_args(required),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["wrote_manifest"] is False
    assert not out.exists()
    assert {issue["issue"] for issue in payload["issues"]} == {"missing_required_input"}


def test_write_manuscript_corpus_manifest_writes_after_required_inputs_exist(
    tmp_path: Path,
) -> None:
    template = _write_template(tmp_path)
    out = tmp_path / "corpus" / "manuscript_corpus.yaml"
    report = tmp_path / "results" / "promotion.json"
    required = _required_paths(tmp_path)
    for path in required.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"case_id":"case-1"}\n')

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--out",
            str(out),
            "--report",
            str(report),
            *_required_args(required),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    manifest = yaml.safe_load(out.read_text())
    assert result.returncode == 0
    assert payload["valid"] is True
    assert payload["wrote_manifest"] is True
    assert manifest["claim_status"] == "manuscript_result_candidate"
    assert manifest["case_files"][0]["path"] == str(required["case_manifest_jsonl"])
    assert (
        manifest["label_contract"]["annotation_files"][0]["path"]
        == str(required["annotation_jsonl"])
    )


def test_write_manuscript_corpus_manifest_does_not_overwrite_different_manifest(
    tmp_path: Path,
) -> None:
    template = _write_template(tmp_path)
    out = tmp_path / "corpus" / "manuscript_corpus.yaml"
    report = tmp_path / "results" / "promotion.json"
    required = _required_paths(tmp_path)
    for path in required.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"case_id":"case-1"}\n')
    out.write_text("schema_version: 1\ncorpus_id: local-edit\n")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--out",
            str(out),
            "--report",
            str(report),
            *_required_args(required),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    payload = json.loads(report.read_text())
    assert result.returncode == 1
    assert payload["valid"] is False
    assert payload["wrote_manifest"] is False
    assert out.read_text() == "schema_version: 1\ncorpus_id: local-edit\n"
    assert {issue["issue"] for issue in payload["issues"]} == {
        "output_exists_with_different_content"
    }


def _write_template(tmp_path: Path) -> Path:
    required = _required_paths(tmp_path)
    template = tmp_path / "corpus" / "manuscript_corpus.template.yaml"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "corpus_id: manuscript",
                "version: 1.0.0-candidate",
                "claim_status: manuscript_result_candidate",
                "expected_regimes:",
                "  - aer",
                "case_files:",
                f"  - path: {required['case_manifest_jsonl']}",
                "    role: case_manifest_jsonl",
                "label_contract:",
                "  mode: embedded_property_labels",
                "  calibration_status: manuscript_two_annotator_reviewed",
                "  required_properties:",
                "    - actor_identity",
                "  annotation_files:",
                f"    - path: {required['annotation_jsonl']}",
                "      role: two_annotator_property_labels",
                "",
            ]
        )
    )
    return template


def _required_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "case_manifest_jsonl": tmp_path / "cases" / "manuscript_cases.jsonl",
        "annotation_jsonl": tmp_path / "annotations" / "manuscript_annotations.jsonl",
        "scorer_jsonl": tmp_path / "scorers" / "decision_trace_reconstructor_outputs.jsonl",
        "llm_judge_jsonl": tmp_path / "baselines" / "llm_judge_outputs.jsonl",
    }


def _required_args(required: dict[str, Path]) -> list[str]:
    args: list[str] = []
    for role, path in required.items():
        args.extend(["--required", f"{role}:{path}"])
    return args
