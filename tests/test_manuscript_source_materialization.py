import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

MATERIALIZE_SCRIPT = Path("scripts/materialize_manuscript_source_review.py")
AUDIT_SCRIPT = Path("scripts/audit_manuscript_source_roots.py")
IMPORT_WORKQUEUE_SCRIPT = Path("scripts/import_manuscript_evidence_workqueue.py")
CONVERT_SCRIPT = Path("scripts/convert_manuscript_case_sources.py")


def test_materialize_manuscript_source_review_writes_reviewed_source_layer(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    row = template_rows()[0]
    paths["template"].write_text(json.dumps(row, sort_keys=True) + "\n")

    result = _run_materialize(paths)

    report = json.loads(paths["report"].read_text())
    manifest = json.loads((paths["source_root"] / "source_manifest.json").read_text())
    source_row = json.loads((paths["source_root"] / "case_evidence_sources.jsonl").read_text())
    native_record = json.loads((paths["source_root"] / "native_records.jsonl").read_text())
    workbook_rows = list(csv.DictReader(paths["source_workbook"].open()))
    workqueue_rows = list(csv.DictReader(paths["evidence_workqueue"].open()))
    assert result.returncode == 0
    assert report["valid"] is True
    assert report["manuscript_result_ready"] is False
    assert manifest["source_scope"] == "manuscript_corpus_evidence"
    assert manifest["source_status"] == "reviewed_non_fixture_evidence"
    assert manifest["annotation_status"] == "property_annotation_required"
    assert source_row["template_status"] == "reviewed_non_fixture_evidence"
    assert source_row["metadata"]["review_status"] == "source_reviewed_needs_annotation"
    assert source_row["metadata"]["reviewer_id"] == "deterministic_manuscript_source_materializer"
    assert source_row["source_requirements"]["native_evidence_refs"][0].endswith(
        f"#case_id={row['case_id']}"
    )
    assert source_row["property_label_authoring"][0]["category"] == "__SELECT_CATEGORY__"
    assert native_record["case_id"] == row["case_id"]
    assert workbook_rows[0]["review_status"] == "source_reviewed_needs_annotation"
    assert workqueue_rows[0]["status"] == "needs_annotation"


def test_materialized_source_layer_passes_audit_import_and_conversion(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    row = template_rows()[0]
    paths["template"].write_text(json.dumps(row, sort_keys=True) + "\n")
    materialize_result = _run_materialize(paths)

    audit = tmp_path / "audit.json"
    audit_result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--template",
            str(paths["template"]),
            "--manuscript-source-root",
            str(paths["source_root"]),
            "--oep-root",
            str(tmp_path / "missing-oep"),
            "--pilot-root",
            str(tmp_path / "missing-pilot"),
            "--out",
            str(audit),
            "--min-cases",
            "1",
            "--fail-on-blockers",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    imported = tmp_path / "imported_reviewed.jsonl"
    import_report = tmp_path / "import_report.json"
    import_result = subprocess.run(
        [
            sys.executable,
            str(IMPORT_WORKQUEUE_SCRIPT),
            "--template",
            str(paths["template"]),
            "--workqueue",
            str(paths["evidence_workqueue"]),
            "--out",
            str(imported),
            "--report",
            str(import_report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    cases = tmp_path / "cases.unadjudicated.jsonl"
    convert_report = tmp_path / "convert_report.json"
    convert_result = subprocess.run(
        [
            sys.executable,
            str(CONVERT_SCRIPT),
            "--sources",
            str(paths["reviewed_sources"]),
            "--out",
            str(cases),
            "--report",
            str(convert_report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    audit_payload = json.loads(audit.read_text())
    import_payload = json.loads(import_report.read_text())
    convert_payload = json.loads(convert_report.read_text())
    case = json.loads(cases.read_text())
    assert materialize_result.returncode == 0
    assert audit_result.returncode == 0
    assert import_result.returncode == 0
    assert convert_result.returncode == 0
    assert audit_payload["manuscript_case_source_ready"] is True
    assert import_payload["valid"] is True
    assert convert_payload["valid"] is True
    assert case["case_id"] == row["case_id"]
    assert case["property_labels"] == []
    assert case["metadata"]["case_source_status"] == "reviewed_non_fixture_evidence"


def _paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "template": tmp_path / "template.jsonl",
        "source_root": tmp_path / "source_root",
        "reviewed_sources": tmp_path / "case_sources.reviewed.jsonl",
        "source_workbook": tmp_path / "source_workbook.reviewed.csv",
        "evidence_workqueue": tmp_path / "evidence_workqueue.reviewed.csv",
        "report": tmp_path / "materialization.json",
    }


def _run_materialize(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(MATERIALIZE_SCRIPT),
            "--template",
            str(paths["template"]),
            "--source-root",
            str(paths["source_root"]),
            "--reviewed-sources",
            str(paths["reviewed_sources"]),
            "--source-workbook",
            str(paths["source_workbook"]),
            "--evidence-workqueue",
            str(paths["evidence_workqueue"]),
            "--report",
            str(paths["report"]),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
