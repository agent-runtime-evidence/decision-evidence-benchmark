import json
import subprocess
import sys
from pathlib import Path

from scripts.write_manuscript_case_source_template import template_rows

SCRIPT = Path("scripts/init_manuscript_evidence_source.py")


def test_init_manuscript_evidence_source_writes_non_promoted_rows(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "sources"
    row = template_rows()[0]
    template.write_text(json.dumps(row, sort_keys=True) + "\n")

    result = _run_init(template, source_root)

    manifest = json.loads((source_root / "source_manifest.json").read_text())
    rows = [
        json.loads(line)
        for line in (source_root / "case_evidence_sources.jsonl").read_text().splitlines()
    ]
    assert result.returncode == 0
    assert manifest["source_scope"] == "manuscript_corpus_evidence_source_template"
    assert manifest["expected_case_count"] == 1
    assert len(rows) == 1
    assert rows[0]["case_id"] == row["case_id"]
    assert rows[0]["template_status"] == "requires_non_fixture_evidence"
    assert rows[0]["source_requirements"]["native_evidence_refs"] == []
    assert rows[0]["metadata"]["review_status"] == "todo"


def test_init_manuscript_evidence_source_refuses_overwrite(tmp_path: Path) -> None:
    template = tmp_path / "template.jsonl"
    source_root = tmp_path / "sources"
    template.write_text(json.dumps(template_rows()[0], sort_keys=True) + "\n")
    first = _run_init(template, source_root)

    second = _run_init(template, source_root)

    assert first.returncode == 0
    assert second.returncode == 1
    assert json.loads(second.stdout)["issue"] == "source_root_exists"


def _run_init(template: Path, source_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--template",
            str(template),
            "--source-root",
            str(source_root),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
