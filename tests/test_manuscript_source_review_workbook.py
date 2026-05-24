import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

INIT_SCRIPT = Path("scripts/init_manuscript_evidence_source.py")
EXPORT_SCRIPT = Path("scripts/export_manuscript_source_review_workbook.py")
IMPORT_SCRIPT = Path("scripts/import_manuscript_source_review_workbook.py")
AUDIT_SCRIPT = Path("scripts/audit_manuscript_source_roots.py")


def test_export_source_review_workbook_preserves_skeleton_rows(tmp_path: Path) -> None:
    template, source_root = _initialized_source_root(tmp_path)
    csv_out = tmp_path / "workbook.csv"
    jsonl_out = tmp_path / "workbook.jsonl"

    result = _run_export(source_root, csv_out, jsonl_out)

    csv_rows = list(csv.DictReader(csv_out.open()))
    jsonl_rows = [json.loads(line) for line in jsonl_out.read_text().splitlines()]
    assert result.returncode == 0
    assert len(csv_rows) == 1
    assert len(jsonl_rows) == 1
    assert csv_rows[0]["case_id"] == template_rows()[0]["case_id"]
    assert csv_rows[0]["current_template_status"] == "requires_non_fixture_evidence"
    assert csv_rows[0]["review_status"] == "todo"
    assert csv_rows[0]["trace_present"] == "__SET_BOOL__"


def test_import_source_review_workbook_rejects_unreviewed_skeleton(
    tmp_path: Path,
) -> None:
    _, source_root = _initialized_source_root(tmp_path)
    workbook = tmp_path / "workbook.csv"
    report = tmp_path / "report.json"
    _run_export(source_root, workbook, tmp_path / "workbook.jsonl")

    result = _run_import(source_root, workbook, report)

    payload = json.loads(report.read_text())
    issue_codes = {issue["issue"] for issue in payload["issues"]}
    assert result.returncode == 1
    assert payload["valid"] is False
    assert issue_codes >= {
        "invalid_review_status",
        "missing_source_refs",
        "missing_review_field",
        "invalid_container_flag",
        "invalid_llm_judge_verdict",
    }
    manifest = json.loads((source_root / "source_manifest.json").read_text())
    assert manifest["source_scope"] == "manuscript_corpus_evidence_source_template"


def test_import_source_review_workbook_updates_source_root_and_audit_passes(
    tmp_path: Path,
) -> None:
    template, source_root = _initialized_source_root(tmp_path)
    workbook = tmp_path / "workbook.csv"
    report = tmp_path / "report.json"
    _run_export(source_root, workbook, tmp_path / "workbook.jsonl")
    rows = list(csv.DictReader(workbook.open()))
    rows[0].update(
        {
            "review_status": "source_reviewed_needs_annotation",
            "native_evidence_refs": "native:one | native:two",
            "reviewed_source_refs": "review:one",
            "evidence_plane_refs": "plane:one",
            "provenance_notes": "Reviewed case source evidence chain.",
            "trace_present": "true",
            "ledger_present": "false",
            "schema_valid": "true",
            "checklist_complete": "true",
            "source_validator_passed": "true",
            "llm_judge_verdict": "sufficient",
            "reviewer_id": "reviewer_1",
            "reviewed_at": "2026-05-25T00:00:00Z",
            "authoring_notes": "Ready for annotation.",
        }
    )
    _write_csv(workbook, rows)

    import_result = _run_import(source_root, workbook, report)
    audit = tmp_path / "audit.json"
    audit_result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--template",
            str(template),
            "--manuscript-source-root",
            str(source_root),
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

    payload = json.loads(report.read_text())
    manifest = json.loads((source_root / "source_manifest.json").read_text())
    source_row = json.loads((source_root / "case_evidence_sources.jsonl").read_text())
    audit_payload = json.loads(audit.read_text())
    assert import_result.returncode == 0
    assert audit_result.returncode == 0
    assert payload["valid"] is True
    assert manifest["source_scope"] == "manuscript_corpus_evidence"
    assert manifest["source_status"] == "reviewed_non_fixture_evidence"
    assert source_row["template_status"] == "reviewed_non_fixture_evidence"
    assert source_row["source_requirements"]["native_evidence_refs"] == [
        "native:one",
        "native:two",
    ]
    assert source_row["container_flags"]["ledger_present"] is False
    assert source_row["metadata"]["reviewer_id"] == "reviewer_1"
    assert audit_payload["manuscript_case_source_ready"] is True


def _initialized_source_root(tmp_path: Path) -> tuple[Path, Path]:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "source_root"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
    result = subprocess.run(
        [
            sys.executable,
            str(INIT_SCRIPT),
            "--template",
            str(template),
            "--source-root",
            str(source_root),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0
    return template, source_root


def _run_export(
    source_root: Path,
    csv_out: Path,
    jsonl_out: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--source-root",
            str(source_root),
            "--csv-out",
            str(csv_out),
            "--jsonl-out",
            str(jsonl_out),
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _run_import(
    source_root: Path,
    workbook: Path,
    report: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--source-root",
            str(source_root),
            "--workbook",
            str(workbook),
            "--report",
            str(report),
            "--expected-count",
            "1",
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
